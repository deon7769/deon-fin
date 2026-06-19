from __future__ import annotations

from src.storage import Database


def test_upsert_pluggy_item_new(tmp_db: Database):
    tmp_db.upsert_pluggy_item(
        "item-abc",
        connector_id=201,
        connector_name="Nubank",
        status="UPDATED",
        client_user_id="user-1",
    )
    items = tmp_db.list_pluggy_items()
    assert len(items) == 1
    assert items[0]["id"] == "item-abc"
    assert items[0]["connector_name"] == "Nubank"
    assert items[0]["last_synced_at"] is None


def test_upsert_pluggy_item_preserves_existing_fields(tmp_db: Database):
    tmp_db.upsert_pluggy_item("item-abc", connector_id=201, connector_name="Nubank")
    tmp_db.upsert_pluggy_item("item-abc", status="UPDATED")
    item = tmp_db.get_pluggy_item("item-abc")
    assert item["connector_name"] == "Nubank"  # preservado
    assert item["status"] == "UPDATED"


def test_mark_synced_updates_timestamp(tmp_db: Database):
    tmp_db.upsert_pluggy_item("item-xyz", connector_name="Itau")
    assert tmp_db.get_pluggy_item("item-xyz")["last_synced_at"] is None
    tmp_db.upsert_pluggy_item("item-xyz", mark_synced=True)
    assert tmp_db.get_pluggy_item("item-xyz")["last_synced_at"] is not None


def test_delete_pluggy_item(tmp_db: Database):
    tmp_db.upsert_pluggy_item("item-1")
    tmp_db.upsert_pluggy_item("item-2")
    tmp_db.delete_pluggy_item("item-1")
    items = tmp_db.list_pluggy_items()
    assert [i["id"] for i in items] == ["item-2"]
