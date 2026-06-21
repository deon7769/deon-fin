from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .agent import AnalystError, Categorizer, FinancialAnalyst, build_financial_context
from .agent.buckets import apply_buckets_to_database
from .agent.context import spending_value
from .config import settings
from .importers import import_nubank_csv, import_ofx, sync_pluggy_item
from .pluggy import PluggyClient
from .storage import Database
from .web.repositories import buckets_repo, profile_repo, transactions_repo


def _fill_missing_reference_months(db: Database) -> int:
    profile = profile_repo.get_profile(db)
    start_day = int(profile["financial_month_start_day"] or 1)
    return transactions_repo.fill_missing_reference_months(db, start_day)

app = typer.Typer(help="Gestão financeira pessoal — agente CLI")
console = Console()


def _db() -> Database:
    return Database(settings.database_path)


@app.command()
def connectors(sandbox: bool = True, country: str = "BR") -> None:
    """Lista conectores disponíveis no Pluggy."""
    with PluggyClient(settings.client_id, settings.client_secret) as pc:
        items = pc.list_connectors(sandbox=sandbox, countries=[country])
    table = Table("ID", "Nome", "Tipo", "País", "Open Finance")
    for c in items:
        table.add_row(
            str(c.get("id")), c.get("name", ""), c.get("type", ""),
            c.get("country", ""), str(c.get("isOpenFinance", False)),
        )
    console.print(table)
    console.print(f"[green]Total:[/green] {len(items)} conectores")


@app.command("sync")
def sync(item_id: str, days: int = 90) -> None:
    """Sincroniza um item (conexão) Pluggy existente."""
    since = date.today() - timedelta(days=days)
    db = _db()
    try:
        with PluggyClient(settings.client_id, settings.client_secret) as pc:
            results = sync_pluggy_item(pc, db, item_id, since=since)
        for r in results:
            console.print(f"[cyan]{r.summary()}[/cyan]")
    finally:
        db.close()


@app.command("import-ofx")
def import_ofx_cmd(path: Path) -> None:
    db = _db()
    try:
        r = import_ofx(path, db)
        console.print(f"[green]{r.summary()}[/green]")
    finally:
        db.close()


@app.command("import-nubank")
def import_nubank_cmd(path: Path, kind: str = typer.Option("credit", help="'credit' ou 'debit'")) -> None:
    db = _db()
    try:
        r = import_nubank_csv(path, db, kind=kind)
        console.print(f"[green]{r.summary()}[/green]")
    finally:
        db.close()


@app.command()
def categorize() -> None:
    """Aplica as regras de categorização nas transações sem categoria."""
    db = _db()
    try:
        stats = Categorizer().apply_to_database(db)
        bucket_stats = apply_buckets_to_database(db)
        _fill_missing_reference_months(db)
        console.print({"categories": stats, "buckets": bucket_stats})
    finally:
        db.close()


@app.command("seed-buckets")
def seed_buckets() -> None:
    """Insere os 6 potes de Meta se ainda não existirem."""
    db = _db()
    try:
        inserted = buckets_repo.seed_buckets(db)
        console.print(f"[green]{inserted} pote(s) inserido(s).[/green]")
    finally:
        db.close()


@app.command("recompute-reference-month")
def recompute_reference_month() -> None:
    """Recalcula o mês de competência de todas as transações."""
    db = _db()
    try:
        profile = profile_repo.get_profile(db)
        start_day = int(profile["financial_month_start_day"] or 1)
        updated = transactions_repo.recompute_reference_months(db, start_day)
        console.print(
            f"[green]{updated} transação(ões) recalculada(s) "
            f"com início no dia {start_day}.[/green]"
        )
    finally:
        db.close()


@app.command()
def report(days: int = 30) -> None:
    """Resumo de gastos por categoria nos últimos N dias."""
    db = _db()
    try:
        since = date.today() - timedelta(days=days)
        rows = db.list_transactions(since=since, limit=10_000)
        account_types = {row["id"]: row["type"] for row in db.list_accounts()}

        spend_by_cat: dict[str, float] = {}
        for r in rows:
            category = r["category"] or "(sem categoria)"
            spent = spending_value(
                float(r["amount"]),
                account_types.get(r["account_id"]),
                category,
            )
            if spent:
                spend_by_cat[category] = spend_by_cat.get(category, 0.0) + spent

        by_cat = [
            (category, -total)
            for category, total in sorted(
                (
                    (category, round(total, 2))
                    for category, total in spend_by_cat.items()
                ),
                key=lambda kv: kv[1],
                reverse=True,
            )
            if total > 0
        ]

        table = Table("Categoria", "Total (R$)")
        for cat, total in by_cat:
            table.add_row(cat, f"{total:,.2f}")
        console.print(table)
        console.print(f"[bold]Saída total:[/bold] R$ {sum(total for _, total in by_cat):,.2f}")
    finally:
        db.close()


@app.command()
def analyze(
    kind: str = typer.Option(
        "all", help="all | budget | waste | goals (relatório completo ou seção)"
    ),
    income: float = typer.Option(
        None, help="Renda mensal líquida (sobrescreve MONTHLY_INCOME do .env)"
    ),
) -> None:
    """Análise financeira por IA (Claude): orçamento 50/30/20, desperdícios e metas."""
    db = _db()
    try:
        ctx = build_financial_context(
            db,
            monthly_income=income if income is not None else settings.monthly_income,
            goals=settings.financial_goals,
        )
    finally:
        db.close()

    try:
        analyst = FinancialAnalyst.from_settings(settings)
    except AnalystError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    console.print(
        f"[dim]Analisando {ctx.months_covered} meses com "
        f"{analyst.provider}/{analyst.model}…[/dim]"
    )
    buffer: list[str] = []
    try:
        for chunk in analyst.stream(kind, ctx.to_dict()):
            buffer.append(chunk)
            console.print(chunk, end="", soft_wrap=True, markup=False)
    except AnalystError as e:
        console.print(f"\n[red]{e}[/red]")
        raise typer.Exit(code=1)
    console.print()  # newline final


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Sobe a UI web (FastAPI + widget Pluggy Connect) em http://HOST:PORT."""
    import uvicorn
    uvicorn.run("src.web.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
