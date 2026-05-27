"""Procedimento de validação end-to-end.

Executa, em ordem:
  1. Carrega .env e confirma variáveis obrigatórias
  2. Autentica no Pluggy e renova apiKey
  3. Lista conectores sandbox + produção (BR)
  4. Cria connect_token (necessário p/ UI futura)
  5. Roda suíte pytest completa (unit + integração)
  6. Faz ingestão real do OFX e CSV de fixtures num DB temporário
  7. Aplica categorização e imprime relatório

Saída de código:
  0  tudo passou
  >0 algum passo falhou (mensagem indica qual)
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import traceback
from datetime import date, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.panel import Panel

from src.agent import Categorizer
from src.config import settings
from src.importers import import_nubank_csv, import_ofx
from src.pluggy import PluggyClient
from src.storage import Database

console = Console()
FIXTURES = ROOT / "tests" / "fixtures"


class Step:
    def __init__(self, name: str):
        self.name = name
        self.ok = False
        self.detail = ""

    def mark(self, ok: bool, detail: str = "") -> None:
        self.ok = ok
        self.detail = detail


def step(name: str, fn):
    s = Step(name)
    console.print(f"[bold cyan]▶ {name}[/bold cyan]")
    try:
        detail = fn() or ""
        s.mark(True, detail)
        console.print(f"  [green]✓ OK[/green] {detail}\n")
    except Exception as exc:
        tb = traceback.format_exc(limit=3)
        s.mark(False, str(exc))
        console.print(f"  [red]✗ FAIL[/red]\n{tb}\n")
    return s


def main() -> int:
    console.print(Panel.fit("[bold]Validação completa do projeto[/bold]", border_style="cyan"))

    results: list[Step] = []

    results.append(step(
        "1. Variáveis de ambiente",
        lambda: f"client_id={settings.client_id[:8]}... db={settings.database_path}",
    ))

    client = PluggyClient(settings.client_id, settings.client_secret)

    def _auth():
        key = client.authenticate(force=True)
        return f"apiKey emitida ({key[:25]}...)"
    results.append(step("2. Pluggy /auth", _auth))

    def _list_conn():
        sandbox = client.list_connectors(sandbox=True, countries=["BR"])
        prod = client.list_connectors(sandbox=False, countries=["BR"])
        return f"{len(sandbox)} sandbox + {len(prod)} produção (BR)"
    results.append(step("3. Pluggy /connectors", _list_conn))

    def _connect_token():
        tok = client.create_connect_token(client_user_id="validate-setup")
        return f"connect_token gerado ({tok[:25]}...)"
    results.append(step("4. Pluggy /connect_token", _connect_token))

    def _pytest():
        cmd = [sys.executable, "-m", "pytest", "-q", "--no-header", "-x"]
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"pytest falhou:\n{proc.stdout}\n{proc.stderr}")
        last = proc.stdout.strip().splitlines()[-1] if proc.stdout else ""
        return last
    results.append(step("5. Suíte pytest completa", _pytest))

    with tempfile.TemporaryDirectory() as tmp:
        db = Database(Path(tmp) / "validate.db")

        def _ofx():
            r = import_ofx(FIXTURES / "sample.ofx", db)
            return r.summary()
        results.append(step("6a. Importar OFX de exemplo", _ofx))

        def _nubank_credit():
            r = import_nubank_csv(FIXTURES / "nubank_credit.csv", db, kind="credit")
            return r.summary()
        results.append(step("6b. Importar CSV Nubank crédito", _nubank_credit))

        def _nubank_debit():
            r = import_nubank_csv(FIXTURES / "nubank_debit.csv", db, kind="debit")
            return r.summary()
        results.append(step("6c. Importar CSV Nubank débito", _nubank_debit))

        def _categorize():
            stats = Categorizer().apply_to_database(db)
            return str(stats)
        results.append(step("7. Categorização automática", _categorize))

        def _report():
            since = date.today() - timedelta(days=3650)
            rows = db.list_transactions(since=since, limit=10_000)
            outflow = sum(r["amount"] for r in rows if r["amount"] < 0)
            inflow = sum(r["amount"] for r in rows if r["amount"] > 0)
            return f"{len(rows)} txs | entradas R${inflow:,.2f} | saídas R${outflow:,.2f}"
        results.append(step("8. Relatório consolidado", _report))

        db.close()

    client.close()

    console.print(Panel.fit("[bold]Resumo[/bold]", border_style="cyan"))
    failed = [r for r in results if not r.ok]
    for r in results:
        icon = "[green]✓[/green]" if r.ok else "[red]✗[/red]"
        console.print(f"{icon} {r.name}  {r.detail if r.ok else '— ' + r.detail}")

    if failed:
        console.print(f"\n[red]FALHA: {len(failed)} passo(s) com erro[/red]")
        return 1
    console.print("\n[bold green]Tudo certo — projeto validado.[/bold green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
