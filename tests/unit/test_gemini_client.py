import asyncio
from types import SimpleNamespace
import pytest
from hybrid_search.config import AppConfig
from hybrid_search.rag.gemini_client import (
    GeminiAnswerGenerator, GenerationBlocked, GenerationInvalidOutput,
    GenerationNotConfigured, GenerationRateLimited,
)

class FakeAioModels:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    async def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception): raise item
        return item

def response(text, finish=None, blocked=False):
    return SimpleNamespace(
        text=text,
        candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name=finish) if finish else None)],
        prompt_feedback=SimpleNamespace(block_reason="SAFETY") if blocked else None,
        usage_metadata=SimpleNamespace(prompt_token_count=8, candidates_token_count=4, total_token_count=12),
    )

def adapter(responses, retries=2):
    cfg=AppConfig(); cfg.gemini.api_key="test"; cfg.gemini.max_retries=retries
    models=FakeAioModels(responses)
    client=SimpleNamespace(aio=SimpleNamespace(models=models))
    return GeminiAnswerGenerator(cfg, client=client, sleep=lambda _: asyncio.sleep(0)), models

@pytest.mark.asyncio
async def test_gemini_success_returns_usage_and_structured_config():
    gen, models=adapter([response('{"status":"answered","answer":"Revenue [S1]","source_ids":["S1"]}')])
    result=await gen.generate("query","vi","source",asyncio.get_running_loop().time()+10)
    assert result.answer.source_ids == ["S1"]
    assert result.total_tokens == 12
    config=models.calls[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.max_output_tokens == 4096

@pytest.mark.asyncio
async def test_gemini_empty_and_truncated_output_are_invalid():
    gen,_=adapter([response("")])
    with pytest.raises(GenerationInvalidOutput) as exc:
        await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    assert exc.value.reason == "empty_response"

    gen,_=adapter([response("")])
    with pytest.raises(GenerationInvalidOutput):
        await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)

@pytest.mark.asyncio
async def test_gemini_blocked_and_truncated_output_are_not_answered():
    gen,_=adapter([response("",blocked=True)])
    with pytest.raises(GenerationBlocked): await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    gen,_=adapter([response('{"status":"answered"}',finish="MAX_TOKENS")])
    with pytest.raises(GenerationInvalidOutput): await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)

@pytest.mark.asyncio
async def test_gemini_400_is_identified_and_not_retried():
    class BadRequest(Exception):
        status_code = 400
    gen,models=adapter([BadRequest("bad request"), response("{}")])
    with pytest.raises(GenerationInvalidOutput) as exc:
        await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    assert exc.value.reason == "provider_http_400"
    assert exc.value.exception_type == "BadRequest"
    assert len(models.calls) == 1

@pytest.mark.asyncio
async def test_gemini_401_does_not_retry_and_429_retries_to_limit():
    gen,models=adapter([RuntimeError("401 unauthorized"), response("{}")])
    with pytest.raises(GenerationNotConfigured): await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    assert len(models.calls) == 1
    gen,models=adapter([RuntimeError("429 resource exhausted") for _ in range(3)])
    with pytest.raises(GenerationRateLimited): await gen.generate("q","vi","ctx",asyncio.get_running_loop().time()+10)
    assert len(models.calls) == 3
