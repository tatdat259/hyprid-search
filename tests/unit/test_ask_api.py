from fastapi.testclient import TestClient
from hybrid_search.config import load_config
from hybrid_search.api import create_app


def test_api_ask_without_key_returns_contract_error():
    config = load_config()
    config.gemini.api_key = None
    client = TestClient(create_app(engine=object(), config=config))
    response = client.post("/api/ask", json={"query": "What is Apple's revenue?"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "generation_not_configured"
    assert "request_id" in payload["error"]


def test_api_ask_invalid_date_has_error_envelope():
    config = load_config()
    config.gemini.api_key = None
    client = TestClient(create_app(engine=object(), config=config))
    response = client.post("/api/ask", json={"query": "x", "filing_date_start": "not-a-date"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"

from types import SimpleNamespace
from fastapi.testclient import TestClient
from hybrid_search.config import AppConfig
from hybrid_search.api import create_app
from hybrid_search.models.answer import AskResponse, Citation

class FakeRagService:
    async def ask(self, request):
        return AskResponse(
            request_id="req-1", status="answered", answer="Evidence [S1]",
            citations=[Citation(source_id="S1", chunk_id="c1", document_id="d1", company="Apple", ticker="AAPL", fiscal_period="FY2024", section="Item 8", source_url="https://sec.gov/doc")],
            retrieval={"method":"rerank","requested_k":3,"retrieved_count":1,"context_count":1},
            generation={"model":"test","input_tokens":None,"output_tokens":None,"total_tokens":None},
            timings_ms={"retrieval":2,"generation":3,"total":5},
        )

def test_api_ask_returns_cited_answer(monkeypatch):
    from hybrid_search import api
    app=create_app(engine=object(), config=AppConfig())
    monkeypatch.setattr(api, "RagService", lambda engine, config: FakeRagService())
    response=TestClient(app).post("/api/ask",json={"query":"Question?","top_k":3,"language":"en"})
    assert response.status_code==200
    data=response.json()
    assert data["status"]=="answered"
    assert data["citations"][0]["chunk_id"]=="c1"
    assert data["retrieval"]["method"]=="rerank"

class FailingRagService:
    async def ask(self, request):
        from hybrid_search.rag.gemini_client import GenerationRateLimited
        raise GenerationRateLimited()

def test_api_ask_generation_503_logs_safe_error_code(monkeypatch, caplog):
    from hybrid_search import api
    monkeypatch.setattr(api, "RagService", lambda engine, config: FailingRagService())
    response = TestClient(create_app(engine=object(), config=AppConfig())).post(
        "/api/ask", json={"query": "Question?"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "generation_rate_limited"
    assert "Ask request unavailable: generation_rate_limited" in caplog.text