from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sources: list[str] = Field(default_factory=list)
    filters: dict[str, Any] = Field(default_factory=dict)


class TableRequest(QueryRequest):
    page: int = 1
    page_size: int = 25
    sort_by: str | None = None
    sort_dir: str = "asc"
    search: str = ""


class AskRequest(QueryRequest):
    question: str
    model: str = "mistral:latest"
    top_k: int = 8
