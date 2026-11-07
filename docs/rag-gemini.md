# Gemini RAG

The app can answer a question from retrieved SEC filing chunks using the official Google Gen AI SDK. Retrieval remains the existing `SearchEngine` `rerank` path; no reindexing is required.

## Requirements

- Python 3.10 or newer.
- Qdrant containing the existing `financial_docs` collection.
- A Gemini API key with access to the configured model. The default model is `gemini-3.1-flash-lite`; set `GEMINI_MODEL` if your account uses another supported model. The app does not silently switch models.

## Install and configure

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
@"
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-3.1-flash-lite
"@ | Set-Content .env
```

The API key is backend-only. Do not place it in browser JavaScript or the request body. Store it in the ignored `.env` file or a process environment variable; never commit `.env`. `.env.example` contains placeholders only. Optional settings are documented in `.env.example` and `config/default.yaml`:

- `GEMINI_TIMEOUT_SECONDS=30`
- `GEMINI_MAX_RETRIES=2` (up to three attempts total)
- `RAG_TOP_K=5` (1-10)
- `RAG_MAX_CONTEXT_TOKENS=8000` (conservative character-based estimate; not provider-measured)
- `RAG_MAX_OUTPUT_TOKENS=4096`
- `RAG_TOTAL_TIMEOUT_SECONDS=45`

## Run

Start Qdrant as usual, then:

```powershell
python -m hybrid_search.cli serve --port 8000
```

Open `http://localhost:8000`, choose **Hỏi đáp AI**, enter a question and filters, and submit. Search-only API behavior is unchanged.

Example:

```powershell
curl.exe -X POST http://localhost:8000/api/ask `
  -H "Content-Type: application/json" `
  -d '{"query":"Tóm tắt rủi ro chuỗi cung ứng của NVIDIA.","top_k":5,"language":"vi","tickers":["NVDA"]}'
```

The backend searches with `method="rerank"`, uses the returned chunk text as evidence, and returns citations mapped from server-side metadata. Provider usage is `null` when unavailable. Citation validation checks IDs and mapping, not whether cited content semantically supports each claim.

For questions asking for revenue growth between exactly two fiscal years, the backend tries a deterministic calculation before Gemini. It only returns a result when a retrieved table supplies both values with the same explicit unit; otherwise it returns insufficient_context and does not call Gemini.

## Errors

- `503 generation_not_configured`: set a valid `GEMINI_API_KEY`.
- `503 generation_rate_limited`: quota/rate limiting persisted through bounded retries.
- `503 generation_model_unavailable`: model name or access is unavailable; configure a model your account can use.
- `504 generation_timeout`: increase the relevant timeout cautiously or reduce context/top-k.
- `502 generation_invalid_output`: provider output or citation IDs failed validation.

## Tests

```powershell
python -m pytest tests/unit/test_rag_context.py tests/unit/test_gemini_client.py tests/unit/test_rag_service.py tests/unit/test_ask_api.py tests/unit/test_api.py -v
```

Unit tests use fake retrieval/provider dependencies and make no paid API calls. A configured API key is present in the local ignored `.env` file. Live smoke tests reached retrieval successfully, but Gemini generation timed out on repeated attempts; live answer generation is not verified. Do not treat mock test results as proof that the configured model/key/network path works. No model fallback is performed.

## Current verification

- Unit suite: 47 passed.
- git diff --check: passed (line-ending warnings only).
- Live retrieval completed in about 1.6 seconds in the previous smoke test; Gemini generation timed out, including with an extended deadline.
- The failure may be caused by network/proxy connectivity, model availability, or account access. Check those before changing the configured model. Do not expose the API key in diagnostics.
