"""Build a bounded, ordered source context from reranked search results."""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from hybrid_search.models.search import SearchResult

@dataclass
class BuiltContext:
    text: str
    sources: dict[str, dict]
    count: int
    estimated_tokens: int

class ContextBuilder:
    def __init__(self, max_tokens: int): self.max_tokens = max_tokens

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        # Conservative estimate for mixed financial text, not provider-measured usage.
        return (len(text) + 2) // 3

    def build(self, results: list[SearchResult]) -> BuiltContext:
        parts, sources, seen, used = [], {}, set(), 0
        for result in results:
            text = result.text.strip()
            if not text: continue
            identity = result.chunk_id or hashlib.sha256(text.encode()).hexdigest()
            if identity in seen: continue
            seen.add(identity)
            sid = f"S{len(sources) + 1}"
            metadata = {
                "chunk_id": result.chunk_id, "document_id": result.document_id,
                "company": result.company, "ticker": result.ticker,
                "fiscal_period": result.fiscal_period or None,
                "document_type": result.document_type or None,
                "section": result.section or None,
                "source_url": result.source_url if result.source_url.startswith(("http://", "https://")) else None,
            }
            encoded_text = json.dumps(text, ensure_ascii=False)
            block = f"SOURCE {sid}\nMETADATA: {json.dumps(metadata, ensure_ascii=False)}\nCONTENT_JSON: {encoded_text}\nEND SOURCE {sid}"
            cost = self._estimate_tokens(block)
            if used + cost > self.max_tokens: continue
            sources[sid], used = metadata, used + cost
            parts.append(block)
        return BuiltContext("\n\n".join(parts), sources, len(parts), used)

class CitationValidator:
    pattern = re.compile(r"\[(S\d+)\]")

    @classmethod
    def citations(cls, generated, sources: dict[str, dict]) -> list[dict]:
        if generated.status == "insufficient_context":
            if generated.source_ids: raise ValueError("insufficient_context must not cite sources")
            return []
        if not generated.answer.strip(): raise ValueError("answer is empty")
        ids = list(dict.fromkeys(cls.pattern.findall(generated.answer)))
        if not ids or set(ids) != set(generated.source_ids):
            raise ValueError("answer citations and source_ids do not match")
        if any(sid not in sources for sid in ids): raise ValueError("unknown citation source")
        return [{"source_id": sid, **sources[sid]} for sid in ids]
