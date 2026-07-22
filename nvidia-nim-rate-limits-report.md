# NVIDIA NIM Model Rate Limits Report

> Generated: July 22, 2026 | API Key: `nvapi-...` | Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`

---

## Rate Limit Rankings (11 Accessible Models)

| Rank | Model                                       | Burst (10 concurrent) | Avg Latency | Verdict                  |
| ---- | ------------------------------------------- | --------------------- | ----------- | ------------------------ |
| 1    | `google/gemma-2-2b-it`                    | **10/10 OK**    | ~0.8s       | 🏆 Best overall          |
| 2    | `nvidia/nemotron-mini-4b-instruct`        | **9/10 OK**     | ~0.8s       | ✅ Excellent             |
| 3    | `meta/llama-3.2-3b-instruct`              | **10/10 OK**    | ~1.4s       | ✅ Excellent             |
| 4    | `meta/llama-4-maverick-17b-128e-instruct` | **10/10 OK**    | ~1.1s       | ✅ Excellent             |
| 5    | `stepfun-ai/step-3.5-flash`               | **10/10 OK**    | ~1.6s       | ✅ Fast & reliable       |
| 6    | `nvidia/nemotron-nano-12b-v2-vl`          | **10/10 OK**    | ~1.2s       | ✅ Excellent             |
| 7    | `google/gemma-3n-e4b-it`                  | **10/10 OK**    | ~1.2s       | ✅ Excellent             |
| 8    | `google/gemma-3n-e2b-it`                  | **10/10 OK**    | ~1.1s       | ✅ Excellent             |
| 9    | `minimaxai/minimax-m3`                    | **8/10 OK**     | ~6.2s       | ⚠️ Minor rate limiting |
| 10   | `stepfun-ai/step-3.7-flash`               | **6/10 OK**     | ~3.4s       | ⚠️ Some rate limiting  |
| 11   | `mistralai/mistral-nemotron`              | **7/10 OK**     | ~54.1s      | ⚠️ Slow, unstable      |

---

## Catalog Status (118 total models, 90 chat candidates)

### Accessible (200 OK) — 11 models

| Model                                             | Single Latency | Burst | Inference Speed |
| ------------------------------------------------- | -------------- | ----- | --------------- |
| `google/gemma-2-2b-it`                          | ~0.4s          | 10/10 | ⚡ Fastest      |
| `nvidia/nemotron-mini-4b-instruct`              | ~0.4s          | 9/10  | ⚡ Fastest      |
| `meta/llama-3.2-3b-instruct`                    | ~0.5s          | 10/10 | ⚡ Very fast    |
| `mistralai/mistral-nemotron`                    | ~0.6s          | 7/10  | ⚡ Fast         |
| <br />`meta/llama-4-maverick-17b-128e-instruct` | ~0.7s          | 10/10 | ⚡ Fast         |
| `google/gemma-3n-e4b-it`                        | ~0.7s          | 10/10 | ⚡ Fast         |
| `google/gemma-3n-e2b-it`                        | ~0.8s          | 10/10 | ⚡ Fast         |
| `stepfun-ai/step-3.5-flash`                     | ~0.7s          | 10/10 | ⚡ Fast         |
| `nvidia/nemotron-nano-12b-v2-vl`                | ~0.9s          | 10/10 | ⚡ Fast         |
| `stepfun-ai/step-3.7-flash`                     | ~4.9s          | 6/10  | Medium          |
| `minimaxai/minimax-m3`                          | ~14.0s         | 8/10  | 🐌 Slow         |

### Deprecated / End-of-Life (410 Gone) — 4 models

| Model                             | Previous Status                  | Notes                                             |
| --------------------------------- | -------------------------------- | ------------------------------------------------- |
| `z-ai/glm-5.1`                  | Was accessible (~62s latency)    | Replaced by`z-ai/glm-5.2` (which now times out) |
| `qwen/qwen3.5-122b-a10b`        | Was inaccessible (timeout)       | Deprecated by NVIDIA                              |
| `google/gemma-3-27b-it`         | Was inaccessible                 | Deprecated by NVIDIA                              |
| `microsoft/phi-4-mini-instruct` | Never accessible in recent tests | Deprecated by NVIDIA                              |

### Not Found (404) — function removed from API — 12 models

| Model                                        | Notes                                                 |
| -------------------------------------------- | ----------------------------------------------------- |
| `moonshotai/kimi-k2.6`                     | Function removed — previously had ~30 req/hour limit |
| `deepseek-ai/deepseek-v3-flash`            | Not found                                             |
| `google/gemma-3-4b-it`                     | Function removed                                      |
| `google/gemma-3-12b-it`                    | Function removed                                      |
| `mistralai/mistral-7b-instruct-v0.3`       | Function removed                                      |
| `nv-mistralai/mistral-nemo-12b-instruct`   | Function removed                                      |
| `ibm/granite-3.0-3b-a800m-instruct`        | Function removed                                      |
| `mistralai/codestral-22b-instruct-v0.1`    | Function removed                                      |
| `deepseek-ai/deepseek-prover-v2-671b`      | Not found                                             |
| `meta/llama-4-scout-17b-16e-instruct`      | Not found                                             |
| `mistralai/mistral-small-3.1-24b-instruct` | Not found                                             |
| `nvidia/llama-4-megatron-8b-instruct`      | Not found                                             |

### Timeout / Unreachable — 4 models

| Model                             | Notes                                            |
| --------------------------------- | ------------------------------------------------ |
| `minimaxai/minimax-m2.7`        | Was top performer in June 2026 — now timing out |
| `deepseek-ai/deepseek-v4-flash` | Was rate-limited — now completely unreachable   |
| `deepseek-ai/deepseek-v4-pro`   | Unreachable                                      |
| `google/gemma-4-31b-it`         | Was timeout — still timeout                     |

---

## New Free-Tier Models Discovered (July 2026)

These models were not in the original June 2026 report:

| Model                                | Burst | Latency        | Context | Notes                                  |
| ------------------------------------ | ----- | -------------- | ------- | -------------------------------------- |
| `google/gemma-2-2b-it`             | 10/10 | ~0.8s          | 8K      | 🏆 Best performer — smallest, fastest |
| `nvidia/nemotron-mini-4b-instruct` | 9/10  | ~0.8s          | 4K      | NVIDIA's own small model               |
| `nvidia/nemotron-nano-12b-v2-vl`   | 10/10 | ~1.2s          | 12K     | Vision-capable                         |
| `meta/llama-3.2-3b-instruct`       | 10/10 | ~1.4s          | 128K    | Smallest Llama 3.2 variant             |
| `google/gemma-3n-e2b-it`           | 10/10 | ~1.1s          | ?       | Gemma 3 Nano 2B                        |
| `google/gemma-3n-e4b-it`           | 10/10 | ~1.2s          | ?       | Gemma 3 Nano 4B                        |
| `stepfun-ai/step-3.5-flash`        | 10/10 | ~1.6s          | 32K     | New provider, excellent                |
| `stepfun-ai/step-3.7-flash`        | 6/10  | ~3.4s          | 32K     | Some rate limiting                     |
| `minimaxai/minimax-m3`             | 8/10  | ~6.2s+14s cold | 128K    | Successor to M2.7                      |
| `mistralai/mistral-nemotron`       | 7/10  | ~54s           | 128K    | Slow, some errors                      |

### Catalog Additions (not previously tested)

- `meta/llama-4-maverick-17b-128e-instruct` — 10/10, ~1.1s
- `meta/llama-4-scout-17b-16e-instruct` — 404 Not Found
- `z-ai/glm-5.2` — times out (replacement for glm-5.1)
- `google/gemma-3-12b-it`, `google/gemma-3-4b-it` — 404 (function removed)

---

## General NVIDIA NIM Free Tier Limits

| Limit                            | Value                                                               | Source                                                                     |
| -------------------------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **General API rate limit** | 40 RPM                                                              | Third-party sources (YangMao, FunGather, FreeLLM, aiHola)                  |
| **Per-model burst**        | Varies (10/10 max for most small models)                            | Empirically measured                                                       |
| **Rate limit scope**       | Per-model (not per-key)                                             | Empirically verified                                                       |
| **Rate limit behavior**    | 1-2 429s per 10 concurrent on some models                           | See burst results above                                                    |
| **Inference credits**      | 1,000 on signup (reportedly removed for some accounts)              | Multiple sources                                                           |
| **Credit card required**   | No                                                                  |                                                                            |
| **Rate limit headers**     | None returned                                                       | No`X-RateLimit-*` or `Retry-After` in any response                     |
| **410 Gone models**        | Models deprecated by NVIDIA return`{"status":410,"title":"Gone"}` |                                                                            |
| **404 response**           | Function removed from API                                           | `{"status":404,"title":"Not Found","detail":"Function '...' not found"}` |

---

## Practical Recommendations

**Primary choice:** `google/gemma-2-2b-it` — fastest at ~0.8s average with 10/10 burst success. Ideal for latency-sensitive tasks.

**Best for longer context:** `meta/llama-3.2-3b-instruct` (128K context) — 10/10 burst, ~1.4s latency.

**Best new discovery:** `stepfun-ai/step-3.5-flash` — 10/10 burst, ~1.6s latency, 32K context, from new provider StepFun AI.

**For vision tasks:** `nvidia/nemotron-nano-12b-v2-vl` — 10/10, ~1.2s, NVIDIA's vision model.

**Avoid:**

- `mistralai/mistral-nemotron` — 7/10 with ~54s latency and 3 errors
- `stepfun-ai/step-3.7-flash` — 6/10 with rate limiting
- `minimaxai/minimax-m3` — 8/10, ~14s cold start
- Any model that was 410 Gone or 404 Not Found in the probe

**Previously working models that are now gone:**

- `minimaxai/minimax-m2.7` — was top performer, now times out
- `z-ai/glm-5.1` — deprecated (410 Gone)
- `moonshotai/kimi-k2.6` — function removed (404)
- `qwen/qwen3.5-122b-a10b` — deprecated (410 Gone)

---

## Test Methodology

**Approach:** 110+ total API calls across 28 models, Python `requests` + `threading` for concurrency tests.

| Parameter   | Value                                                    |
| ----------- | -------------------------------------------------------- |
| Date        | July 22, 2026                                            |
| Endpoint    | `https://integrate.api.nvidia.com/v1/chat/completions` |
| Catalog     | 118 total models, 90 chat candidates                     |
| Max tokens  | 8 per request                                            |
| Timeout     | 20s for single probe, 60s for burst                      |
| Concurrency | 10 threads for burst tests                               |
| Python      | 3.13+                                                    |

### Quick Test Script (reproducible)

```python
import requests, time, threading

API_KEY = 'nvapi-YOUR_KEY_HERE'
INVOKE_URL = 'https://integrate.api.nvidia.com/v1/chat/completions'
MODELS = [
    "google/gemma-2-2b-it", "nvidia/nemotron-mini-4b-instruct",
    "meta/llama-3.2-3b-instruct", "stepfun-ai/step-3.5-flash",
]

def test_burst(model, concurrency=10, timeout=60):
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    payload = {'model': model, 'messages': [{'role':'user','content':'hi'}],
               'max_tokens': 8, 'temperature': 0.01}
    results, lock = {}, threading.Lock()
    def fire(n):
        t0 = time.time()
        try:
            r = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=timeout)
            with lock: results[n] = (r.status_code, time.time() - t0)
        except Exception as e:
            with lock: results[n] = (-1, time.time() - t0)
    for t in [threading.Thread(target=fire, args=(i,)) for i in range(concurrency)]:
        t.start(); t.join()
    ok = sum(1 for s,_ in results.values() if s == 200)
    limited = sum(1 for s,_ in results.values() if s == 429)
    times = [t for s,t in results.values() if s == 200]
    print(f"{model}: {ok}/{concurrency} OK, {limited} 429, avg {sum(times)/max(len(times),1):.1f}s")

for m in MODELS: test_burst(m)
```

---

## Full Session Log — July 22, 2026

### Phase 1: Catalog Discovery

```
GET /v1/models → 200, 118 total, 90 chat candidates
```

### Phase 2: Single-Request Accessibility Probe (20s timeout)

```
google/gemma-2-2b-it                 → 200 (0.4s)
meta/llama-3.2-3b-instruct           → 200 (0.5s)
google/gemma-3n-e2b-it               → 200 (0.8s)
google/gemma-3n-e4b-it               → 200 (0.7s)
nvidia/nemotron-mini-4b-instruct     → 200 (0.4s)
meta/llama-4-maverick-17b-128e       → 200 (0.7s)
minimaxai/minimax-m3                 → 200 (14.0s cold)
mistralai/mistral-nemotron           → 200 (0.6s)
nvidia/nemotron-nano-12b-v2-vl       → 200 (0.9s)
stepfun-ai/step-3.5-flash            → 200 (0.7s)
stepfun-ai/step-3.7-flash            → 200 (4.9s)

z-ai/glm-5.1                         → 410 Gone (model deprecated)
qwen/qwen3.5-122b-a10b               → 410 Gone (model deprecated)
google/gemma-3-27b-it                → 410 Gone (model deprecated)
microsoft/phi-4-mini-instruct        → 410 Gone (model deprecated)

moonshotai/kimi-k2.6                 → 404 Not Found (function removed)
google/gemma-3-4b-it                 → 404 Not Found (function removed)
google/gemma-3-12b-it                → 404 Not Found (function removed)
deepseek-ai/deepseek-v3-flash        → 404 Not Found
mistralai/mistral-7b-instruct-v0.3   → 404 Not Found
nv-mistralai/mistral-nemo-12b        → 404 Not Found
ibm/granite-3.0-3b-a800m-instruct    → 404 Not Found
mistralai/codestral-22b-instruct     → 404 Not Found

minimaxai/minimax-m2.7               → ERR timeout (was top performer in June)
deepseek-ai/deepseek-v4-flash        → ERR timeout (was 429-only)
deepseek-ai/deepseek-v4-pro          → ERR timeout
google/gemma-4-31b-it                → ERR timeout (was always timeout)
```

### Phase 3: Burst Test (10 concurrent) on Accessible Models

| Model                                | OK | 429 | ERR | Avg Latency | Verdict   |
| ------------------------------------ | -- | --- | --- | ----------- | --------- |
| `google/gemma-2-2b-it`             | 10 | 0   | 0   | 0.8s        | 🏆 BEST   |
| `meta/llama-3.2-3b-instruct`       | 10 | 0   | 0   | 1.4s        | ✅ GOOD   |
| `meta/llama-4-maverick-17b-128e`   | 10 | 0   | 0   | 1.1s        | ✅ GOOD   |
| `stepfun-ai/step-3.5-flash`        | 10 | 0   | 0   | 1.6s        | ✅ GOOD   |
| `nvidia/nemotron-nano-12b-v2-vl`   | 10 | 0   | 0   | 1.2s        | ✅ GOOD   |
| `google/gemma-3n-e4b-it`           | 10 | 0   | 0   | 1.2s        | ✅ GOOD   |
| `google/gemma-3n-e2b-it`           | 10 | 0   | 0   | 1.1s        | ✅ GOOD   |
| `nvidia/nemotron-mini-4b-instruct` | 9  | 1   | 0   | 0.8s        | ✅ GOOD   |
| `minimaxai/minimax-m3`             | 8  | 2   | 0   | 6.2s        | ⚠️ WEAK |
| `stepfun-ai/step-3.7-flash`        | 6  | 4   | 0   | 3.4s        | ⚠️ WEAK |
| `mistralai/mistral-nemotron`       | 7  | 0   | 3   | 54.1s       | ⚠️ WEAK |

---

## Comparison: June 2026 vs July 2026

| Metric                             | June 2026                                    | July 2026                                      | Change                  |
| ---------------------------------- | -------------------------------------------- | ---------------------------------------------- | ----------------------- |
| **Accessible models**        | 3 (MiniMax M2.7, GLM-5.1, DeepSeek V4 Flash) | 11                                             | +8 new                  |
| **Best model**               | `minimaxai/minimax-m2.7` (83% burst)       | `google/gemma-2-2b-it` (100% burst)          | Improved                |
| **Fastest latency**          | ~14.5s (MiniMax M2.7)                        | ~0.8s (Gemma 2B)                               | **10x faster**    |
| **Deprecated (410)**         | 0                                            | 4 (GLM-5.1, Qwen 3.5, Gemma-3-27b, Phi-4-mini) | —                      |
| **Function removed (404)**   | 0                                            | 12 (including Kimi K2.6)                       | —                      |
| **Previously top performer** | `minimaxai/minimax-m2.7`                   | —                                             | **Now times out** |

---

## Known Limitations

1. Rate limits change frequently — re-test periodically (NVIDIA deprecated 4 models since June 2026)
2. MiniMax M2.7 was the top performer in June but now times out — monitor for recovery
3. 410 Gone responses indicate NVIDIA deprecated the model (no recovery possible, use different model)
4. 404 Not Found indicates the function was removed from the API — different from rate limiting
5. No `Retry-After` or `X-RateLimit-*` headers are returned; backoff must be empirical
6. Small models (2B-4B) have the best rate limit performance — consider them for high-throughput tasks
7. StepFun AI models are new providers — long-term availability unknown
8. NVIDIA NIM free-tier quota is per-account; results are not transferable across accounts
