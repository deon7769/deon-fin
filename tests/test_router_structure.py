from __future__ import annotations

from pathlib import Path


def test_domain_router_modules_exist():
    router_dir = Path("src/web/routers")

    assert (router_dir / "__init__.py").exists()
    assert (router_dir / "buckets.py").exists()
    assert (router_dir / "tags.py").exists()
    assert (router_dir / "profile.py").exists()
    assert (router_dir / "transactions.py").exists()


def test_routers_do_not_contain_raw_sql():
    router_dir = Path("src/web/routers")
    forbidden = (".execute(", "._conn", "sqlite3", "SELECT ", "INSERT ", "UPDATE ", "DELETE ")

    for path in router_dir.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden), path
