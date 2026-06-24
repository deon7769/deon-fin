from __future__ import annotations

import threading
from datetime import date
from queue import Queue

from src.storage import Account, Database


def test_database_configures_sqlite_pragmas(tmp_path):
    db = Database(tmp_path / "concurrent.db")
    try:
        journal_mode = db._conn.execute("PRAGMA journal_mode").fetchone()[0]
        busy_timeout = db._conn.execute("PRAGMA busy_timeout").fetchone()[0]
        synchronous = db._conn.execute("PRAGMA synchronous").fetchone()[0]
        foreign_keys = db._conn.execute("PRAGMA foreign_keys").fetchone()[0]
    finally:
        db.close()

    assert journal_mode.lower() == "wal"
    assert busy_timeout >= 5000
    assert synchronous == 1
    assert foreign_keys == 1


def test_database_serializes_writes_before_sqlite_busy_timeout(tmp_path):
    db_path = tmp_path / "serialized.db"
    first_db = Database(db_path)
    second_db = Database(db_path)
    errors: Queue[BaseException] = Queue()
    first_write_holding_transaction = threading.Event()
    release_first_write = threading.Event()
    second_write_entered_managed_transaction = threading.Event()

    first_db.upsert_account(Account(id="first", source="csv"))
    second_db.upsert_account(Account(id="second", source="csv"))

    def first_write() -> None:
        try:
            with first_db._cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO transactions
                    (id, account_id, posted_at, amount, description, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("tx-first", "first", date(2026, 6, 1).isoformat(), -1.0, "first", "csv"),
                )
                first_write_holding_transaction.set()
                if not release_first_write.wait(timeout=2):
                    raise TimeoutError("test did not release first write")
        except BaseException as exc:
            errors.put(exc)

    def second_write() -> None:
        try:
            if not first_write_holding_transaction.wait(timeout=2):
                raise TimeoutError("first write did not start")
            with second_db._cursor() as cur:
                second_write_entered_managed_transaction.set()
                cur.execute(
                    """
                    INSERT INTO transactions
                    (id, account_id, posted_at, amount, description, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("tx-second", "second", date(2026, 6, 1).isoformat(), -2.0, "second", "csv"),
                )
        except BaseException as exc:
            errors.put(exc)

    first_thread = threading.Thread(target=first_write)
    second_thread = threading.Thread(target=second_write)
    first_thread.start()
    assert first_write_holding_transaction.wait(timeout=2)
    second_thread.start()

    try:
        assert not second_write_entered_managed_transaction.wait(timeout=0.2)
    finally:
        release_first_write.set()
        first_thread.join(timeout=2)
        second_thread.join(timeout=2)
        first_db.close()
        second_db.close()

    assert not first_thread.is_alive()
    assert not second_thread.is_alive()
    assert errors.empty(), list(errors.queue)

    check_db = Database(db_path)
    try:
        assert check_db.count_transactions() == 2
    finally:
        check_db.close()
