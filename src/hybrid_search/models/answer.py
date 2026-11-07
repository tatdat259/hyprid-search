"""API and provider models for grounded RAG answers."""
from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator

class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=4000)
    top_k: Optional[int] = Field(default=None, ge=1, le=20)
    language: Literal["vi", "en"] = "vi"
    tickers: Optional[list[str]] = None
    form_types: Optional[list[str]] = None
    section_types: Optional[list[str]] = None
    filing_date_start: Optional[str] = None
    filing_date_end: Optional[str] = None
    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value

class Citation(BaseModel):
    source_id: str
    chunk_id: str
    document_id: str
    company: str
    ticker: str
    fiscal_period: Optional[str] = None
    section: Optional[str] = None
    source_url: Optional[str] = None

class AskResponse(BaseModel):
    request_id: str
    status: Literal["answered", "insufficient_context", "blocked"]
    answer: str
    citations: list[Citation]
    retrieval: dict
    generation: dict
    timings_ms: dict[str, int]

class GeneratedAnswer(BaseModel):
    status: Literal["answered", "insufficient_context"]
    answer: str = ""
    source_ids: list[str] = Field(default_factory=list)
