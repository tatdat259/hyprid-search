"""Async Google Gen AI adapter with bounded retries and normalized errors."""
from __future__ import annotations
import asyncio
import random
import time
from dataclasses import dataclass
from typing import Any, Optional
from hybrid_search.models.answer import GeneratedAnswer
from hybrid_search.rag.prompts import SYSTEM_INSTRUCTION, build_user_prompt

class GenerationError(Exception):
    code = "generation_unavailable"

class GenerationTimeout(GenerationError): code = "generation_timeout"
class GenerationUnavailable(GenerationError): code = "generation_unavailable"
class GenerationRateLimited(GenerationError): code = "generation_rate_limited"
class GenerationModelUnavailable(GenerationError): code = "generation_model_unavailable"
class GenerationBlocked(GenerationError): code = "generation_blocked"
class GenerationInvalidOutput(GenerationError):
    code = "generation_invalid_output"
    def __init__(self, reason="invalid_output"):
        self.reason = reason
        super().__init__(reason)
class GenerationNotConfigured(GenerationError): code = "generation_not_configured"

@dataclass
class GenerationResult:
    answer: GeneratedAnswer
    model: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]

class GeminiAnswerGenerator:
    def __init__(self, config, client=None, sleep=asyncio.sleep, clock=time.monotonic):
        self.config, self._client = config, client
        self.sleep, self.clock = sleep, clock

    def _get_client(self):
        if not self.config.gemini.api_key:
            raise GenerationNotConfigured()
        if self._client is None:
            from google import genai
            from google.genai import types
            self._client = genai.Client(
                api_key=self.config.gemini.api_key,
                http_options=types.HttpOptions(timeout=int(self.config.gemini.timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)),
            )
        return self._client

    @staticmethod
    def _classify(exc: Exception) -> GenerationError:
        status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
        text = f"{type(exc).__name__} {exc}".lower()
        if status == 429 or "429" in text or "resource_exhausted" in text: return GenerationRateLimited()
        if status in (401, 403) or "401" in text or "403" in text or "permission_denied" in text or "unauthenticated" in text: return GenerationNotConfigured()
        if status == 404 or "404" in text or "not found" in text or "model" in text and "unsupported" in text: return GenerationModelUnavailable()
        if status is not None and isinstance(status, int) and status < 500: return GenerationInvalidOutput(f"provider_http_{status}")
        return GenerationUnavailable()

    async def generate(self, query: str, language: str, context: str, deadline: float) -> GenerationResult:
        client = self._get_client()
        from google.genai import types
        prompt = build_user_prompt(query, language, context)
        schema = GeneratedAnswer
        attempts = self.config.gemini.max_retries + 1
        for attempt in range(attempts):
            remaining = deadline - self.clock()
            if remaining <= 0: raise GenerationTimeout()
            try:
                response = await asyncio.wait_for(client.aio.models.generate_content(
                    model=self.config.gemini.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=schema,
                        max_output_tokens=self.config.rag.max_output_tokens,
                    ),
                ), timeout=min(remaining, self.config.gemini.timeout_seconds))
                if getattr(response, "prompt_feedback", None) and getattr(response.prompt_feedback, "block_reason", None):
                    raise GenerationBlocked()
                candidate = (getattr(response, "candidates", None) or [None])[0]
                finish = getattr(getattr(candidate, "finish_reason", None), "name", "")
                if finish in {"MAX_TOKENS", "SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT"}:
                    if finish == "MAX_TOKENS": raise GenerationInvalidOutput("max_tokens")
                    raise GenerationBlocked()
                raw = getattr(response, "text", None)
                if not raw: raise GenerationInvalidOutput("empty_response")
                try: parsed = GeneratedAnswer.model_validate_json(raw)
                except Exception as exc: raise GenerationInvalidOutput("schema_validation") from exc
                usage = getattr(response, "usage_metadata", None)
                return GenerationResult(
                    parsed, self.config.gemini.model,
                    getattr(usage, "prompt_token_count", None),
                    getattr(usage, "candidates_token_count", None),
                    getattr(usage, "total_token_count", None),
                )
            except (GenerationBlocked, GenerationInvalidOutput):
                raise
            except asyncio.TimeoutError as exc:
                error = GenerationTimeout()
            except Exception as exc:
                error = self._classify(exc)
                if isinstance(error, (GenerationNotConfigured, GenerationInvalidOutput, GenerationModelUnavailable)):
                    if isinstance(error, GenerationInvalidOutput):
                        error.exception_type = type(exc).__name__
                    raise error from exc
            if attempt + 1 >= attempts: raise error
            delay = min(0.5 * (2 ** attempt) + random.uniform(0, 0.25), max(0, deadline - self.clock()))
            if delay <= 0: raise GenerationTimeout()
            await self.sleep(delay)
        raise GenerationUnavailable()
