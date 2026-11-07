"""RAG orchestration, deadline management, and citation mapping."""
from __future__ import annotations
import asyncio
import time
import uuid
import logging
from datetime import date
from hybrid_search.models.answer import AskRequest, AskResponse
from hybrid_search.models.filter import MetadataFilter
from hybrid_search.rag.context_builder import ContextBuilder, CitationValidator
from hybrid_search.rag.calculations import RevenueGrowthCalculator
from hybrid_search.rag.gemini_client import (
    GeminiAnswerGenerator, GenerationTimeout, GenerationNotConfigured,
    GenerationInvalidOutput, GenerationBlocked,
)

logger = logging.getLogger(__name__)

class RagService:
    def __init__(self, engine, config, generator=None, clock=time.monotonic):
        self.engine, self.config = engine, config
        self.generator = generator or GeminiAnswerGenerator(config)
        self.clock = clock
        self._retrieval_lock = asyncio.Lock()

    async def ask(self, request: AskRequest) -> AskResponse:
        started = self.clock()
        deadline = started + self.config.rag.total_timeout_seconds
        request_id = str(uuid.uuid4())
        query = request.query.strip()
        if not query:
            raise ValueError("query is required")
        for value in (request.filing_date_start, request.filing_date_end):
            if value:
                try:
                    date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError("filing dates must be YYYY-MM-DD") from exc
        if request.filing_date_start and request.filing_date_end and request.filing_date_start > request.filing_date_end:
            raise ValueError("filing_date_start must not be after filing_date_end")
        if isinstance(self.generator, GeminiAnswerGenerator) and not self.config.gemini.api_key:
            raise GenerationNotConfigured()

        top_k = request.top_k or self.config.rag.top_k
        filters = MetadataFilter(
            tickers=request.tickers or None,
            document_types=request.form_types or None,
            sections=request.section_types or None,
            filing_date_start=request.filing_date_start or None,
            filing_date_end=request.filing_date_end or None,
        )
        retrieval_started = self.clock()
        try:
            async with self._retrieval_lock:
                results = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.engine.search, query=query, method="rerank", k=top_k,
                        filters=filters, prefetch_k=self.config.retrieval.prefetch_k,
                    ),
                    timeout=max(0, deadline - self.clock()),
                )
        except asyncio.TimeoutError as exc:
            raise GenerationTimeout() from exc
        retrieval_ms = int((self.clock() - retrieval_started) * 1000)

        reserved = 512 + (len(query) + 2) // 3 + self.config.rag.max_output_tokens
        context = ContextBuilder(max(0, self.config.rag.max_context_tokens - reserved)).build(results)
        retrieval = {
            "method": "rerank", "requested_k": top_k,
            "retrieved_count": len(results), "context_count": context.count,
        }
        empty_generation = {
            "model": self.config.gemini.model, "input_tokens": None,
            "output_tokens": None, "total_tokens": None,
        }
        if context.count == 0:
            return AskResponse(
                request_id=request_id, status="insufficient_context",
                answer="Không tìm thấy đủ ngữ cảnh trong tài liệu." if request.language == "vi" else "No relevant source context was found.",
                citations=[], retrieval=retrieval, generation=empty_generation,
                timings_ms={"retrieval": retrieval_ms, "generation": 0, "total": int((self.clock() - started) * 1000)},
            )

        calculation = RevenueGrowthCalculator.calculate_combined(query, results, request.language)
        if calculation is None:
            calculation = RevenueGrowthCalculator.calculate(query, results, request.language)
        if RevenueGrowthCalculator.calculation_requested(query):
            if calculation is None:
                return AskResponse(
                    request_id=request_id, status="insufficient_context",
                    answer="Không đủ dữ liệu có nguồn, kỳ tham chiếu hoặc đơn vị tương thích để tính." if request.language == "vi" else "There is not enough sourced data with compatible periods and units to calculate this.",
                    citations=[], retrieval=retrieval, generation=empty_generation,
                    timings_ms={"retrieval": retrieval_ms, "generation": 0, "total": int((self.clock() - started) * 1000)},
                )
            calculation_results = [result for result in results if result.chunk_id in calculation.chunk_ids]
            calculation_context = ContextBuilder(self.config.rag.max_context_tokens).build(calculation_results)
            chunk_to_source = {metadata["chunk_id"]: source_id for source_id, metadata in calculation_context.sources.items()}
            source_ids = [chunk_to_source[chunk_id] for chunk_id in calculation.chunk_ids if chunk_id in chunk_to_source]
            if not source_ids:
                return AskResponse(
                    request_id=request_id, status="insufficient_context",
                    answer="Không đủ nguồn để tính." if request.language == "vi" else "There is not enough source context to calculate this.",
                    citations=[], retrieval=retrieval, generation=empty_generation,
                    timings_ms={"retrieval": retrieval_ms, "generation": 0, "total": int((self.clock() - started) * 1000)},
                )
            cited_answer = calculation.answer + " " + " ".join(f"[{source_id}]" for source_id in source_ids)
            from hybrid_search.models.answer import GeneratedAnswer
            deterministic = GeneratedAnswer(status="answered", answer=cited_answer, source_ids=source_ids)
            citations = CitationValidator.citations(deterministic, calculation_context.sources)
            return AskResponse(
                request_id=request_id, status="answered", answer=cited_answer, citations=citations,
                retrieval=retrieval,
                generation={"model": "deterministic-revenue-growth", "input_tokens": None, "output_tokens": None, "total_tokens": None},
                timings_ms={"retrieval": retrieval_ms, "generation": 0, "total": int((self.clock() - started) * 1000)},
            )
        generation_started = self.clock()
        try:
            generated = await asyncio.wait_for(
                self.generator.generate(query, request.language, context.text, deadline),
                timeout=max(0, deadline - self.clock()),
            )
        except asyncio.TimeoutError as exc:
            raise GenerationTimeout() from exc
        except GenerationBlocked:
            return AskResponse(
                request_id=request_id, status="blocked",
                answer="Yêu cầu không thể được xử lý." if request.language == "vi" else "This request could not be processed.",
                citations=[], retrieval=retrieval, generation=empty_generation,
                timings_ms={"retrieval": retrieval_ms, "generation": int((self.clock() - generation_started) * 1000), "total": int((self.clock() - started) * 1000)},
            )
        generation_ms = int((self.clock() - generation_started) * 1000)
        try:
            citations = CitationValidator.citations(generated.answer, context.sources)
        except ValueError as exc:
            raise GenerationInvalidOutput(f"citation_validation: {exc}") from exc
        return AskResponse(
            request_id=request_id, status=generated.answer.status,
            answer=generated.answer.answer, citations=citations, retrieval=retrieval,
            generation={
                "model": generated.model, "input_tokens": generated.input_tokens,
                "output_tokens": generated.output_tokens, "total_tokens": generated.total_tokens,
            },
            timings_ms={"retrieval": retrieval_ms, "generation": generation_ms, "total": int((self.clock() - started) * 1000)},
        )
