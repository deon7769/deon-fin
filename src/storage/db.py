from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    id              TEXT PRIMARY KEY,
    source          TEXT NOT NULL,            -- 'pluggy' | 'ofx' | 'csv'
    institution     TEXT,
    name            TEXT,
    type            TEXT,                     -- 'CHECKING' | 'CREDIT' | 'SAVINGS' | etc
    currency        TEXT DEFAULT 'BRL',
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS transactions (
    id              TEXT PRIMARY KEY,         -- deterministic hash for dedup
    account_id      TEXT NOT NULL REFERENCES accounts(id),
    posted_at       TEXT NOT NULL,            -- ISO date
    amount          REAL NOT NULL,            -- positive credit, negative debit
    description     TEXT NOT NULL,
    raw_description TEXT,
    category        TEXT,
    category_source TEXT,                     -- 'rule' | 'pluggy' | 'manual'
    source          TEXT NOT NULL,            -- 'pluggy' | 'ofx' | 'csv'
    external_id     TEXT,                     -- id no provedor original (se houver)
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transactions(account_id, posted_at);
CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);
CREATE INDEX IF NOT EXISTS idx_tx_external ON transactions(external_id);

CREATE TABLE IF NOT EXISTS pluggy_items (
    id              TEXT PRIMARY KEY,         -- itemId do Pluggy
    connector_id    INTEGER,
    connector_name  TEXT,
    status          TEXT,                     -- UPDATED | OUTDATED | LOGIN_ERROR | etc
    client_user_id  TEXT,
    last_synced_at  TEXT,
    metadata_json   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class Account:
    id: str
    source: str
    institution: str | None = None
    name: str | None = None
    type: str | None = None
    currency: str = "BRL"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Transaction:
    account_id: str
    posted_at: date
    amount: Decimal
    description: str
    source: str
    raw_description: str | None = None
    category: str | None = None
    category_source: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = ""

    def __post_init__(self) -> None:
        if not self.id:
            self.id = self._fingerprint()

    def _fingerprint(self) -> str:
        if self.external_id:
            seed = f"{self.source}|{self.external_id}"
        else:
            seed = "|".join(
                [
                    self.source,
                    self.account_id,
                    self.posted_at.isoformat(),
                    f"{self.amount:.2f}",
                    (self.raw_description or self.description).strip().lower(),
                ]
            )
        return hashlib.sha1(seed.encode("utf-8")).hexdigest()


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: FastAPI's sync routes run on a starlette
        # threadpool, so a connection created elsewhere needs cross-thread use.
        # Safe here because each Database instance is used by one request at a
        # time (FastAPI creates a fresh one per request via get_db dependency).
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    @contextmanager
    def _cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    def upsert_account(self, account: Account) -> None:
        import json
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO accounts (id, source, institution, name, type, currency, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    institution=excluded.institution,
                    name=excluded.name,
                    type=excluded.type,
                    currency=excluded.currency,
                    metadata_json=excluded.metadata_json
                """,
                (
                    account.id, account.source, account.institution, account.name,
                    account.type, account.currency, json.dumps(account.metadata),
                ),
            )

    def insert_transactions(self, txs: Iterable[Transaction]) -> tuple[int, int]:
        """Returns (inserted, skipped_duplicates)."""
        import json
        inserted = skipped = 0
        with self._cursor() as cur:
            for tx in txs:
                try:
                    cur.execute(
                        """
                        INSERT INTO transactions
                        (id, account_id, posted_at, amount, description, raw_description,
                         category, category_source, source, external_id, metadata_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            tx.id, tx.account_id, tx.posted_at.isoformat(),
                            float(tx.amount), tx.description, tx.raw_description,
                            tx.category, tx.category_source, tx.source, tx.external_id,
                            json.dumps(tx.metadata),
                        ),
                    )
                    inserted += 1
                except sqlite3.IntegrityError:
                    skipped += 1
        return inserted, skipped

    def count_transactions(self, account_id: str | None = None) -> int:
        with self._cursor() as cur:
            if account_id:
                cur.execute("SELECT COUNT(*) FROM transactions WHERE account_id=?", (account_id,))
            else:
                cur.execute("SELECT COUNT(*) FROM transactions")
            return cur.fetchone()[0]

    def list_accounts(self) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM accounts ORDER BY institution, name")
            return cur.fetchall()

    def list_transactions(
        self,
        *,
        account_id: str | None = None,
        since: date | None = None,
        limit: int = 1000,
    ) -> list[sqlite3.Row]:
        sql = "SELECT * FROM transactions WHERE 1=1"
        params: list[Any] = []
        if account_id:
            sql += " AND account_id=?"
            params.append(account_id)
        if since:
            sql += " AND posted_at >= ?"
            params.append(since.isoformat())
        sql += " ORDER BY posted_at DESC, id LIMIT ?"
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    # ------------------------------------------------------------- pluggy items
    def upsert_pluggy_item(
        self,
        item_id: str,
        *,
        connector_id: int | None = None,
        connector_name: str | None = None,
        status: str | None = None,
        client_user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        mark_synced: bool = False,
    ) -> None:
        import json
        flag = 1 if mark_synced else 0
        with self._cursor() as cur:
            cur.execute(
                """
                INSERT INTO pluggy_items
                  (id, connector_id, connector_name, status, client_user_id, metadata_json,
                   last_synced_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?,
                  CASE WHEN ? = 1 THEN datetime('now') ELSE NULL END,
                  datetime('now'))
                ON CONFLICT(id) DO UPDATE SET
                    connector_id   = COALESCE(excluded.connector_id, connector_id),
                    connector_name = COALESCE(excluded.connector_name, connector_name),
                    status         = COALESCE(excluded.status, status),
                    client_user_id = COALESCE(excluded.client_user_id, client_user_id),
                    metadata_json  = COALESCE(excluded.metadata_json, metadata_json),
                    last_synced_at = CASE WHEN ? = 1 THEN datetime('now')
                                          ELSE last_synced_at END,
                    updated_at     = datetime('now')
                """,
                (
                    item_id, connector_id, connector_name, status, client_user_id,
                    json.dumps(metadata) if metadata else None,
                    flag,
                    flag,
                ),
            )

    def list_pluggy_items(self) -> list[sqlite3.Row]:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM pluggy_items ORDER BY created_at DESC")
            return cur.fetchall()

    def get_pluggy_item(self, item_id: str) -> sqlite3.Row | None:
        with self._cursor() as cur:
            cur.execute("SELECT * FROM pluggy_items WHERE id=?", (item_id,))
            return cur.fetchone()

    def delete_pluggy_item(self, item_id: str) -> None:
        with self._cursor() as cur:
            cur.execute("DELETE FROM pluggy_items WHERE id=?", (item_id,))

    def close(self) -> None:
        self._conn.close()
