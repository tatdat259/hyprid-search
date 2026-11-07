import asyncio
from types import SimpleNamespace
import pytest
from hybrid_search.config import AppConfig
from hybrid_search.models.answer import GeneratedAnswer, AskRequest
from hybrid_search.models.search import SearchResult
from hybrid_search.rag.gemini_client import GeminiAnswerGenerator, GenerationInvalidOutput, GenerationTimeout
from hybrid_search.rag.service import RagService

class FakeEngine:
    def __init__(self, results): self.results, self.calls = results, []
    def search(self, **kwargs): self.calls.append(kwargs); return self.results

class FakeGenerator:
    def __init__(self, result=None, error=None): self.result, self.error, self.calls = result, error, []
    async def generate(self, query, language, context, deadline):
        self.calls.append((query, language, context))
        if self.error: raise self.error
        return self.result

def result(text="Evidence says revenue was reported."):
    return SearchResult(chunk_id="C1", document_id="D1", score=0.5, rank=1, text=text,
        company="Apple Inc.", ticker="AAPL", document_type="10-K", filing_date="2024-11-01",
        fiscal_period="FY2024", section="Item 8", source_url="https://sec.gov/a", retrieval_method="rerank")

def generated():
    return SimpleNamespace(answer=GeneratedAnswer(status="answered", answer="It was reported [S1].", source_ids=["S1"]), model="fake", input_tokens=10, output_tokens=5, total_tokens=15)

@pytest.mark.asyncio
async def test_service_uses_reranker_filters_and_maps_citation():
    cfg=AppConfig(); engine=FakeEngine([result()]); gen=FakeGenerator(generated())
    response=await RagService(engine,cfg,gen).ask(AskRequest(query="Apple revenue", tickers=["AAPL"], form_types=["10-K"]))
    assert engine.calls[0]["method"] == "rerank"
    assert engine.calls[0]["filters"].tickers == ["AAPL"]
    assert response.citations[0].chunk_id == "C1"
    assert response.generation["total_tokens"] == 15

@pytest.mark.asyncio
async def test_no_context_does_not_call_generator():
    gen=FakeGenerator(generated())
    response=await RagService(FakeEngine([]),AppConfig(),gen).ask(AskRequest(query="No source"))
    assert response.status == "insufficient_context" and not gen.calls

@pytest.mark.asyncio
async def test_date_order_and_retrieval_failure_are_not_insufficient_context():
    with pytest.raises(ValueError):
        await RagService(FakeEngine([]),AppConfig(),FakeGenerator()).ask(AskRequest(query="x",filing_date_start="2024-12-01",filing_date_end="2024-01-01"))
    class Broken:
        def search(self, **kwargs): raise RuntimeError("offline")
    with pytest.raises(RuntimeError): await RagService(Broken(),AppConfig(),FakeGenerator()).ask(AskRequest(query="x"))

@pytest.mark.asyncio
async def test_gemini_retry_count_and_invalid_output():
    class Models:
        def __init__(self): self.calls=0
        async def generate_content(self, **kwargs):
            self.calls += 1
            if self.calls < 3: raise RuntimeError("503 unavailable")
            return SimpleNamespace(text='{}', candidates=[SimpleNamespace(finish_reason=None)], prompt_feedback=None, usage_metadata=None)
    models=Models(); client=SimpleNamespace(aio=SimpleNamespace(models=models))
    cfg=AppConfig(); cfg.gemini.api_key="test"; cfg.gemini.max_retries=2
    adapter=GeminiAnswerGenerator(cfg, client=client, sleep=lambda _: asyncio.sleep(0))
    with pytest.raises(GenerationInvalidOutput): await adapter.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    assert models.calls == 3

@pytest.mark.asyncio
async def test_generation_outer_deadline_is_normalized():
    class SlowGenerator:
        async def generate(self, *args, **kwargs):
            await asyncio.sleep(0.05)
    cfg = AppConfig()
    cfg.rag.total_timeout_seconds = 0.01
    with pytest.raises(GenerationTimeout):
        await RagService(FakeEngine([result()]), cfg, SlowGenerator()).ask(AskRequest(query="x"))
@pytest.mark.asyncio
async def test_service_logs_citation_validation_reason_without_answer_content():
    bad = SimpleNamespace(
        answer=GeneratedAnswer(status="answered", answer="Unsupported [S9]", source_ids=["S9"]),
        model="fake", input_tokens=None, output_tokens=None, total_tokens=None,
    )
    service = RagService(FakeEngine([result()]), AppConfig(), FakeGenerator(bad))
    with pytest.raises(GenerationInvalidOutput) as exc:
        await service.ask(AskRequest(query="Question"))
    assert exc.value.reason == "citation_validation: unknown citation source"
@pytest.mark.asyncio
async def test_revenue_growth_is_calculated_without_gemini():
    table = "Amounts in millions | 2024 | 2023 | Total net sales | 391,035 | 383,285 |"
    generator = FakeGenerator(generated())
    response = await RagService(FakeEngine([result(table)]), AppConfig(), generator).ask(
        AskRequest(query="What is Apple's revenue growth rate from FY2023 to FY2024?", language="en")
    )
    assert response.status == "answered"
    assert "2.02%" in response.answer
    assert response.generation["model"] == "deterministic-revenue-growth"
    assert response.citations[0].chunk_id == "C1"
    assert not generator.calls

@pytest.mark.asyncio
async def test_revenue_growth_without_unit_is_insufficient_context():
    table = "| Net sales | 2024 | 2023 |\n| Net sales | 391,035 | 383,285 |"
    generator = FakeGenerator(generated())
    response = await RagService(FakeEngine([result(table)]), AppConfig(), generator).ask(
        AskRequest(query="What is Apple's revenue growth rate from FY2023 to FY2024?", language="en")
    )
    assert response.status == "insufficient_context"
    assert not generator.calls

@pytest.mark.asyncio
async def test_combined_revenue_uses_two_cited_chunks_even_when_ranked_low():
    apple = result("Amounts in millions | 2024 | Total net sales | 391,035 |")
    microsoft = SearchResult(
        chunk_id="C2", document_id="D2", score=0.4, rank=19,
        text="Amounts in millions | Year Ended June 30, | 2024 | 2023 | Revenue: | Product | 64,773 | 64,699 | Service and other | 180,349 | 147,216 | Total | 245,122 | 211,915 |",
        company="Microsoft Corporation", ticker="MSFT", document_type="10-K",
        filing_date="2024-07-30", fiscal_period="FY2024", section="Financial Statements",
        source_url="https://sec.gov/m", retrieval_method="rerank",
    )
    engine = FakeEngine([apple] + [result(f"Irrelevant evidence {i}") for i in range(17)] + [microsoft])
    generator = FakeGenerator(generated())
    config = AppConfig()
    config.rag.top_k = 20
    response = await RagService(engine, config, generator).ask(
        AskRequest(query="Calculate the combined revenue of Apple and Microsoft in FY2024.", language="en")
    )
    assert engine.calls[0]["k"] == 20
    assert response.status == "answered"
    assert "636,157" in response.answer
    assert {citation.chunk_id for citation in response.citations} == {"C1", "C2"}
    assert not generator.calls