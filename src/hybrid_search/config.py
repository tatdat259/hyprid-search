"""Application configuration schema and loaders."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
import yaml
from dotenv import load_dotenv


class EdgarConfig(BaseModel):
    user_agent: str = Field(default="FinancialIntelligenceResearch/1.0 (research@example.com)")
    rate_limit_per_second: float = Field(default=8.0)
    request_timeout_seconds: float = Field(default=30.0)
    max_retries: int = Field(default=3)
    cache_dir: str = Field(default="data/raw/edgar")


class ChunkingConfig(BaseModel):
    chunk_size_tokens: int = Field(default=500)
    chunk_overlap_tokens: int = Field(default=100)


class EmbeddingsConfig(BaseModel):
    dense_model: str = Field(default="BAAI/bge-small-en-v1.5")
    bm25_model: str = Field(default="Qdrant/bm25")
    sparse_model: str = Field(default="prithivida/Splade_PP_en_v1")
    dense_batch_size: int = Field(default=8)
    sparse_batch_size: int = Field(default=4)
    threads: int = Field(default=2)


class QdrantConfig(BaseModel):
    url: Optional[str] = Field(default="http://localhost:6333")
    api_key: Optional[str] = Field(default=None)
    local_path: Optional[str] = Field(default="qdrant_data")
    prefer_local_embedded: bool = Field(default=False)
    collection_name: str = Field(default="financial_docs")
    dense_vector_size: int = Field(default=384)
    upsert_batch_size: int = Field(default=100)


class RetrievalConfig(BaseModel):
    default_k: int = Field(default=10)
    prefetch_k: int = Field(default=50)
    rrf_constant: int = Field(default=60)


class BenchmarkConfig(BaseModel):
    num_latency_runs: int = Field(default=5)
    k_values: List[int] = Field(default_factory=lambda: [5, 10, 20])



class GeminiConfig(BaseModel):
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="gemini-3.8-flash", min_length=1)
    timeout_seconds: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=5)


class RagConfig(BaseModel):
    top_k: int = Field(default=20, ge=1, le=20)
    max_context_tokens: int = Field(default=8000, ge=256)
    max_output_tokens: int = Field(default=4096, ge=64)
    total_timeout_seconds: float = Field(default=45.0, gt=0)
class CompanyConfig(BaseModel):
    ticker: str
    name: str
    cik: str
    sector: str = "Unknown"
    geography: str = "US"
    forms: List[str] = Field(default_factory=lambda: ["10-K", "10-Q"])


class AppConfig(BaseModel):
    edgar: EdgarConfig = Field(default_factory=EdgarConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    embeddings: EmbeddingsConfig = Field(default_factory=EmbeddingsConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    benchmark: BenchmarkConfig = Field(default_factory=BenchmarkConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    rag: RagConfig = Field(default_factory=RagConfig)
    companies: List[CompanyConfig] = Field(default_factory=list)


def get_project_root() -> Path:
    """Returns the project root directory."""
    return Path(__file__).resolve().parent.parent.parent


def load_config(
    config_path: Optional[Path | str] = None,
    companies_path: Optional[Path | str] = None,
) -> AppConfig:
    """Loads and validates configuration from YAML files with environment variable overrides."""
    root = get_project_root()
    load_dotenv(root / ".env", override=False)
    if config_path is None:
        config_path = root / "config" / "default.yaml"
    else:
        config_path = Path(config_path)

    if companies_path is None:
        companies_path = root / "config" / "companies.yaml"
    else:
        companies_path = Path(companies_path)

    config_data: Dict[str, Any] = {}
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f)
            if isinstance(loaded, dict):
                config_data.update(loaded)

    # Load companies
    companies_list: List[Dict[str, Any]] = []
    if companies_path.exists():
        with open(companies_path, "r", encoding="utf-8") as f:
            c_loaded = yaml.safe_load(f)
            if isinstance(c_loaded, dict) and "companies" in c_loaded:
                companies_list = c_loaded["companies"]
    config_data["companies"] = companies_list

    # Environment variable overrides
    if "QDRANT_URL" in os.environ:
        config_data.setdefault("qdrant", {})["url"] = os.environ["QDRANT_URL"]
    if "QDRANT_API_KEY" in os.environ:
        config_data.setdefault("qdrant", {})["api_key"] = os.environ["QDRANT_API_KEY"]
    if "EDGAR_USER_AGENT" in os.environ:
        config_data.setdefault("edgar", {})["user_agent"] = os.environ["EDGAR_USER_AGENT"]

    if "GEMINI_API_KEY" in os.environ:
        config_data.setdefault("gemini", {})["api_key"] = os.environ["GEMINI_API_KEY"]
    if "GEMINI_MODEL" in os.environ:
        config_data.setdefault("gemini", {})["model"] = os.environ["GEMINI_MODEL"]
    for env_name, section, field, cast in [
        ("GEMINI_TIMEOUT_SECONDS", "gemini", "timeout_seconds", float),
        ("GEMINI_MAX_RETRIES", "gemini", "max_retries", int),
        ("RAG_TOP_K", "rag", "top_k", int),
        ("RAG_MAX_CONTEXT_TOKENS", "rag", "max_context_tokens", int),
        ("RAG_MAX_OUTPUT_TOKENS", "rag", "max_output_tokens", int),
        ("RAG_TOTAL_TIMEOUT_SECONDS", "rag", "total_timeout_seconds", float),
    ]:
        if env_name in os.environ:
            config_data.setdefault(section, {})[field] = cast(os.environ[env_name])
    return AppConfig(**config_data)
