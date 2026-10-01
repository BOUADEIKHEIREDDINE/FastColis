"""HTTP routes for the FastColis dashboard."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.backend.api.schemas import AskRequest, QueryRequest, TableRequest
from app.backend.data.catalog import SOURCE_BY_ID
from app.backend.data.loader import get_store
from app.backend.llm.query import ask_fastcolis
from app.backend.services.filters import (
    active_filter_count,
    apply_filters,
    context_label,
    filter_options,
    normalize_filters,
)
from app.backend.services.metrics import combine_for_table, dashboard_payload
from app.backend.services.quality import pipeline_quality_reports


router = APIRouter(prefix="/api")


def _filtered_frames(source_ids: list[str], filters: dict[str, Any]) -> tuple[dict[str, pd.DataFrame], list[str]]:
    if not source_ids:
        raise HTTPException(status_code=400, detail="Sélectionnez au moins une source.")
    unknown = [source_id for source_id in source_ids if source_id not in SOURCE_BY_ID]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Sources inconnues: {', '.join(unknown)}")
    store = get_store()
    missing = store.missing(source_ids)
    frames = {
        source_id: apply_filters(frame, filters)
        for source_id, frame in store.frames(source_ids).items()
    }
    return frames, missing


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if pd.isna(value) if not isinstance(value, (list, dict, pd.DataFrame)) else False:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:  # noqa: BLE001
            return str(value)
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


@router.get("/sources")
def list_sources() -> dict[str, Any]:
    store = get_store()
    return {"sources": store.list_sources()}


@router.post("/options")
def options(payload: QueryRequest) -> dict[str, Any]:
    filters = normalize_filters(payload.filters)
    source_ids = payload.sources
    store = get_store()
    frames = store.frames(source_ids)
    return {
        "options": filter_options(frames),
        "missing": store.missing(source_ids),
        "context": context_label(source_ids, filters),
    }


@router.post("/dashboard")
def dashboard(payload: QueryRequest) -> dict[str, Any]:
    filters = normalize_filters(payload.filters)
    frames, missing = _filtered_frames(payload.sources, filters)
    data = dashboard_payload(
        payload.sources,
        frames,
        filters,
        context_label(payload.sources, filters),
        active_filter_count(filters),
    )
    data["missing"] = missing
    data["options"] = filter_options(get_store().frames(payload.sources))
    return data


@router.post("/table")
def table(payload: TableRequest) -> dict[str, Any]:
    filters = normalize_filters(payload.filters)
    if payload.search:
        filters["search"] = payload.search
    frames, missing = _filtered_frames(payload.sources, filters)
    combined = combine_for_table(frames)
    sort_by = payload.sort_by if payload.sort_by in combined.columns else None
    if sort_by:
        combined = combined.sort_values(sort_by, ascending=payload.sort_dir != "desc", na_position="last")

    total = int(len(combined))
    page_size = max(5, min(payload.page_size, 100))
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(max(payload.page, 1), pages)
    start = (page - 1) * page_size
    slice_df = combined.iloc[start : start + page_size]
    records = _json_safe(slice_df.where(pd.notna(slice_df), None).to_dict(orient="records"))
    columns = [
        {"id": column, "label": column.replace("_", " ")}
        for column in combined.columns
    ]
    return {
        "columns": columns,
        "rows": records,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
        "missing": missing,
        "context": context_label(payload.sources, filters),
    }


@router.post("/export")
def export_table(payload: TableRequest) -> StreamingResponse:
    filters = normalize_filters(payload.filters)
    if payload.search:
        filters["search"] = payload.search
    frames, _missing = _filtered_frames(payload.sources, filters)
    combined = combine_for_table(frames)
    buffer = BytesIO()
    combined.to_excel(buffer, index=False)
    buffer.seek(0)
    filename = "fastcolis_export.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/ask")
def ask(payload: AskRequest) -> JSONResponse:
    result = ask_fastcolis(
        payload.question,
        payload.sources,
        payload.filters,
        model=payload.model,
        top_k=payload.top_k,
    )
    status = 200 if result.get("ok") else 503 if "Ollama" in str(result.get("error", "")) else 400
    return JSONResponse(content=_json_safe(result), status_code=status)


@router.get("/quality")
def quality() -> dict[str, Any]:
    return _json_safe(pipeline_quality_reports())


@router.get("/health")
def health() -> dict[str, Any]:
    store = get_store()
    return {"ok": True, "sources": store.list_sources()}
