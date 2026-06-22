from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...storage import Database
from ..dependencies import get_db
from ..repositories import tags_repo

router = APIRouter(prefix="/api", tags=["tags"])


class TagCreateRequest(BaseModel):
    name: str
    color: str | None = None
    bucket_id: int | None = None


class TagPatchRequest(BaseModel):
    name: str | None = None
    color: str | None = None
    bucket_id: int | None = None


def _fields_set(model: BaseModel) -> set[str]:
    fields = getattr(model, "model_fields_set", None)
    if fields is None:
        fields = getattr(model, "__fields_set__", set())
    return set(fields)


def _repo_error_to_http(exc: ValueError) -> HTTPException:
    if str(exc) == "duplicate":
        return HTTPException(status_code=409, detail="tag já existe")
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/tags")
def list_tags(db: Database = Depends(get_db)) -> dict[str, list[dict[str, Any]]]:
    tags_repo.seed_tags_if_empty(db)
    return {"items": tags_repo.list_tags(db)}


@router.post("/tags", status_code=201)
def create_tag(body: TagCreateRequest, db: Database = Depends(get_db)) -> dict[str, Any]:
    try:
        return tags_repo.create_tag(
            db,
            name=body.name,
            color=body.color,
            bucket_id=body.bucket_id,
        )
    except ValueError as exc:
        raise _repo_error_to_http(exc) from exc


@router.patch("/tags/{tag_id}")
def update_tag(
    tag_id: int,
    body: TagPatchRequest,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    fields = _fields_set(body)
    updates: dict[str, Any] = {}
    if "name" in fields:
        updates["name"] = body.name
    if "color" in fields:
        updates["color"] = body.color
    if "bucket_id" in fields:
        updates["bucket_id"] = body.bucket_id

    try:
        tag = tags_repo.update_tag(db, tag_id, **updates)
    except ValueError as exc:
        raise _repo_error_to_http(exc) from exc

    if tag is None:
        raise HTTPException(status_code=404, detail="tag não encontrada")
    return tag


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Database = Depends(get_db)) -> dict[str, int]:
    result = tags_repo.delete_tag(db, tag_id)
    if result is None:
        raise HTTPException(status_code=404, detail="tag não encontrada")
    return result
