from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .agent import AnalystError, Categorizer, FinancialAnalyst, build_financial_context
from .agent.buckets import apply_buckets_to_database
from .agent.context import account_owner_aliases, spending_value
from .agent.tags import apply_tags_to_database
from .auth.bootstrap import BootstrapInput, bootstrap_admin_family
from .config import settings
from .importers import import_nubank_csv, import_ofx, sync_pluggy_item
from .pluggy import PluggyClient
from .storage import Database
from .storage.migrate_sqlite_to_postgres import collect_sqlite_migration_report
from .storage.postgres import connect_postgres, run_postgres_migrations
from .web.repositories import buckets_repo, profile_repo, tags_repo, transactions_repo


def _fill_missing_reference_months(db: Database) -> int:
    profile = profile_repo.get_profile(db)
    start_day = int(profile["financial_month_start_day"] or 1)
    return transactions_repo.fill_missing_reference_months(db, start_day)

app = typer.Typer(help="Gestão financeira pessoal — agente CLI")
console = Console()


def _db() -> Database:
    return Database(settings.database_path)


def _auth_database_url() -> str:
    return getattr(settings, "auth_database_url", None) or settings.database_url


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
        tag_stats = apply_tags_to_database(db)
        _fill_missing_reference_months(db)
        console.print({"categories": stats, "buckets": bucket_stats, "tags": tag_stats})
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


@app.command("seed-tags")
def seed_tags() -> None:
    """Insere as 7 tags iniciais se ainda não existirem."""
    db = _db()
    try:
        inserted = tags_repo.seed_tags(db)
        console.print(f"[green]{inserted} tag(s) inserida(s).[/green]")
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
        accounts = db.list_accounts()
        account_types = {row["id"]: row["type"] for row in accounts}
        owner_names = account_owner_aliases(accounts)

        spend_by_cat: dict[str, float] = {}
        for r in rows:
            category = r["category"] or "(sem categoria)"
            spent = spending_value(
                float(r["amount"]),
                account_types.get(r["account_id"]),
                category,
                description=r["description"],
                raw_description=r["raw_description"],
                owner_names=owner_names,
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


@app.command("bootstrap-auth")
def bootstrap_auth(
    email: str = typer.Option(..., help="Email do primeiro administrador."),
    display_name: str = typer.Option("Admin", help="Nome exibido para o administrador."),
    family_name: str = typer.Option("Familia Principal", help="Nome da família inicial."),
    family_slug: str = typer.Option("familia-principal", help="Slug único da família inicial."),
    password: str = typer.Option(
        ...,
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Senha inicial do administrador.",
    ),
) -> None:
    """Cria ou atualiza o primeiro usuário owner e a família inicial no PostgreSQL."""
    auth_database_url = _auth_database_url()
    run_postgres_migrations(auth_database_url)
    with connect_postgres(auth_database_url) as conn:
        result = bootstrap_admin_family(
            conn,
            BootstrapInput(
                email=email,
                password=password,
                display_name=display_name,
                family_name=family_name,
                family_slug=family_slug,
            ),
        )
    console.print(
        "[green]Bootstrap concluído:[/green] "
        f"user={result.user_id} family={result.family_id} person={result.person_id}"
    )


@app.command("pg-migration-dry-run")
def pg_migration_dry_run(
    sqlite_path: Path | None = typer.Option(
        None,
        help="Caminho do SQLite legado. Usa settings.database_path quando omitido.",
    ),
    family_name: str = typer.Option("Familia Principal", help="Nome da família padrão da migração."),
) -> None:
    """Mostra contagens e mapeamentos da migração SQLite -> PostgreSQL sem escrever no destino."""
    source_path = sqlite_path or settings.database_path
    try:
        report = collect_sqlite_migration_report(source_path, default_family_name=family_name)
    except FileNotFoundError:
        console.print(f"[red]SQLite não encontrado: {source_path}[/red]", soft_wrap=True)
        raise typer.Exit(code=1)

    table = Table("Origem SQLite", "Destino PostgreSQL", "Linhas")
    for source, count in report.counts.items():
        table.add_row(source, report.target_tables[source], str(count))
    console.print(f"[bold]Família padrão:[/bold] {report.default_family_name}")
    console.print(f"[bold]SQLite:[/bold] {report.sqlite_path}")
    console.print(table)
    if report.ignored_counts:
        ignored_table = Table(
            "Origem SQLite",
            "Linhas",
            "Motivo",
            title="Tabelas sem destino nesta fundação",
        )
        for source, count in report.ignored_counts.items():
            ignored_table.add_row(source, str(count), report.ignored_tables[source])
        console.print(ignored_table)


@app.command()
def serve(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Sobe a UI web (FastAPI + widget Pluggy Connect) em http://HOST:PORT."""
    import uvicorn
    uvicorn.run("src.web.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    app()
