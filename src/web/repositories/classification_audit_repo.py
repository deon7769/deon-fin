from __future__ import annotations

import json
from typing import Any, Literal

from ...storage import Database

ClassificationAuditKind = Literal["tag", "bucket"]


def _metadata(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def record(
    db: Database,
    *,
    action: str,
    kind: ClassificationAuditKind,
    target_id: int | None = None,
    target_name: str | None = None,
    match_key: str | None = None,
    affected_count: int = 0,
    preview_total: int = 0,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    metadata_json = (
        json.dumps(metadata, ensure_ascii=False, sort_keys=True)
        if metadata is not None
        else None
    )
    with db._cursor() as cur:  # type: ignore[attr-defined]
        cur.execute(
            """
            INSERT INTO classification_audit_log (
                action, kind, target_id, target_name, match_key,
                affected_count, preview_total, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action,
                kind,
                target_id,
                target_name,
                match_key,
                int(affected_count),
                int(preview_total),
                metadata_json,
            ),
        )
        audit_id = int(cur.lastrowid)
    row = db._conn.execute(
        """
        SELECT id, action, kind, target_id, target_name, match_key,
               affected_count, preview_total, metadata_json, created_at
          FROM classification_audit_log
         WHERE id=?
        """,
        (audit_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("classification audit record not found")
    return _row_to_dict(row)


def list_recent(db: Database, *, limit: int = 20) -> list[dict[str, Any]]:
    normalized_limit = min(max(int(limit), 1), 100)
    rows = db._conn.execute(
        """
        SELECT id, action, kind, target_id, target_name, match_key,
               affected_count, preview_total, metadata_json, created_at
          FROM classification_audit_log
         ORDER BY created_at DESC, id DESC
         LIMIT ?
        """,
        (normalized_limit,),
    ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = _metadata(data.pop("metadata_json", None))
    return data
