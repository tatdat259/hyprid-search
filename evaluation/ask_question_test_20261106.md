# Generated Question Test Report

- Total questions: 17
- Evidence/retrieval passed: 14/17 (82.4%)
- Scope: `/api/search` with `method=rerank`, `k=10`, and the filters from the question file.
- End-to-end `/api/ask` generation was not counted because the live provider returned `generation_invalid_output`.

| # | Expected class | Results | Term signals | Retrieval pass |
|---:|---|---:|---|:---:|
| 1 | answerable | 10 | services, revenue, 2024 | ✅ |
| 2 | answerable | 10 | supply, risk | ✅ |
| 3 | answerable | 10 | cloud, revenue, 2024 | ✅ |
| 4 | answerable | 10 | battery, supply, risk | ✅ |
| 5 | answerable | 10 | 2024, 2025 | ✅ |
| 6 | answerable | 10 | revenue, 2023, 2024 | ✅ |
| 7 | answerable | 10 | revenue, 2023, 2024 | ✅ |
| 8 | answerable | 10 | revenue, 2024, 2023 | ✅ |
| 9 | answerable | 10 | revenue, region | ✅ |
| 10 | insufficient_context | 10 | — | ❌ |
| 11 | insufficient_context | 10 | 2019 | ❌ |
| 12 | insufficient_context | 10 | — | ✅ |
| 13 | answerable | 10 | revenue, 2024 | ✅ |
| 14 | answerable | 10 | revenue, 2023, 2024 | ✅ |
| 15 | insufficient_context | 10 | gross margin, 2024 | ❌ |
| 16 | answerable | 10 | risk | ✅ |
| 17 | answerable | 10 | risk, supply | ✅ |
