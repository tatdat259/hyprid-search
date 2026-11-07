# /api/ask Golden Dataset Benchmark

Dataset: `evaluation/golden_dataset.yaml` (25 queries). Each request used `language=en`, `top_k=5`, no extra metadata filters.

This report measures operational behavior only. It does not establish semantic correctness; no answer text or secret is stored.

## Summary

- Total: 25
- HTTP 200: 15
- answered: 8
- insufficient_context: 7
- blocked: 0
- HTTP errors: 10
- Error codes: `{'generation_invalid_output': 9, 'generation_rate_limited': 1}`
- Latency ms: `{'mean': 1692.0, 'min': 1095.8, 'max': 3880.0}`

## Per-query results

| ID | Category | HTTP | Result/Error | Retrieved | Context | Citations | Latency ms |
|---|---|---:|---|---:|---:|---:|---:|
| exact_01 | exact_terminology | 200 | insufficient_context | 5 | 3 | 0 | 1174.7 |
| exact_02 | exact_terminology | 502 | generation_invalid_output |  |  |  | 1615.8 |
| exact_03 | exact_terminology | 502 | generation_invalid_output |  |  |  | 1788.0 |
| exact_04 | exact_terminology | 502 | generation_invalid_output |  |  |  | 1710.3 |
| exact_05 | exact_terminology | 200 | insufficient_context | 5 | 3 | 0 | 1302.4 |
| semantic_01 | semantic_questions | 200 | insufficient_context | 5 | 3 | 0 | 1541.4 |
| semantic_02 | semantic_questions | 200 | answered | 5 | 3 | 2 | 1813.6 |
| semantic_03 | semantic_questions | 502 | generation_invalid_output |  |  |  | 1389.8 |
| semantic_04 | semantic_questions | 200 | answered | 5 | 3 | 1 | 1583.6 |
| semantic_05 | semantic_questions | 200 | answered | 5 | 3 | 3 | 1697.2 |
| mixed_01 | mixed_queries | 502 | generation_invalid_output |  |  |  | 1766.4 |
| mixed_02 | mixed_queries | 200 | answered | 5 | 3 | 1 | 1560.8 |
| mixed_03 | mixed_queries | 502 | generation_invalid_output |  |  |  | 1532.3 |
| mixed_04 | mixed_queries | 200 | insufficient_context | 5 | 3 | 0 | 1342.3 |
| mixed_05 | mixed_queries | 200 | insufficient_context | 5 | 3 | 0 | 2131.9 |
| rare_01 | rare_terminology | 502 | generation_invalid_output |  |  |  | 1773.7 |
| rare_02 | rare_terminology | 503 | generation_rate_limited |  |  |  | 2653.0 |
| rare_03 | rare_terminology | 200 | insufficient_context | 5 | 3 | 0 | 1095.8 |
| rare_04 | rare_terminology | 502 | generation_invalid_output |  |  |  | 3880.0 |
| rare_05 | rare_terminology | 502 | generation_invalid_output |  |  |  | 1415.4 |
| long_01 | long_natural_language | 200 | answered | 5 | 3 | 3 | 1677.9 |
| long_02 | long_natural_language | 200 | answered | 5 | 3 | 2 | 1441.5 |
| long_03 | long_natural_language | 200 | answered | 5 | 3 | 2 | 1382.4 |
| long_04 | long_natural_language | 200 | insufficient_context | 5 | 3 | 0 | 1251.6 |
| long_05 | long_natural_language | 200 | answered | 5 | 3 | 3 | 1778.9 |
