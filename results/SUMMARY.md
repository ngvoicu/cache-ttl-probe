# Prompt-cache lifetimes, measured 4–5 November 2026

Measured with `cache-ttl-probe` 0.1.0. Each sample primes a fresh ~2,500-token prefix once and checks it **once** at a fixed
age; 3 samples per age. A check is warm when ≥ 50 % of the prompt (and ≥ 500 tokens) is reported as cached. Requests use
the OpenAI Responses format with a per-sample `prompt_cache_key`, the way pi and Codex send one per conversation.

**Lifetime** = last age where all checks were warm – first age where all were cold. Mixed rows (some warm, some cold at
the same age) mean the provider spreads requests over cache nodes or evicts early; treat the lower bound as the safe value.

- `cpa-8.0.53/`: through a local [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) 8.0.53, each row pinned to
  one account by a temporary alias (removed afterwards).
- `openrouter-direct/`: straight to OpenRouter, no proxy. This is the baseline for what the upstream itself does.
- `openrouter-direct-v0.2/`: R1 measured again with probe 0.2.0 (R1b).

Known values were not measured: Claude subscription through CLIProxyAPI (CPA sets a 1 h cache) and a Claude API key
(5 min default).

## Through CLIProxyAPI 8.0.53

| Row | Route | Model | Lifetime | Notes |
|---|---|---|---|---|
| C1 | Codex subscription | `gpt-6.1-sol` | **2 h – 12 h** | warm at 2 h, 2 of 3 at 4 h, cold at 12 h; 8 h lost to a network outage |
| C2 | Codex subscription | `gpt-6.1-terra` | < 2.5 – 7.5 min | ran before the probe sent a cache key; superseded by C1 |
| D1 | Devin | `devin/claude-opus-5-5` | **≥ 2 h** | one cold check at 50 min, otherwise warm to 2 h |
| D2 | Devin | `devin/gpt-6-1-sol` | 30 – 40 min | |
| D5 | Devin | `devin/gemini-4-argon` | 2.5 – 15 min | |
| D7 | Devin | `devin/glm-5-3` | < 2.5 – 30 min | mixed |
| D8 | Devin | `devin/grok-4-7` | < 2.5 – 15 min | mixed |
| D9 | Devin | `devin/deepseek-v4-pro` | cold at 2.5 min | first attempt aborted with no checks (file kept) |
| D3, D4, D6 | Devin | `swe-2`, `muse-wonder-1-0`, `kimi-k3` | no observable cache | D4 reports no usage at all; D3 is free |
| M1 | Meta (Muse Code login) | `muse-wonder-1.0` | 2.5 min – 2 h | reliable to ~25 min, mixed after |
| M3 | Meta | `muse-spark-1.3` | 7.5 – 40 min | |
| A3 | Antigravity | `gemini-3.8-flash-high` | 2.5 – 15 min | |
| O1 | OpenRouter via `openai-compatibility` | `anthropic/claude-opus-5.5` | **no cache** | CPA sends no cache markers on this route |
| O2, O3 | same | `openai/gpt-6.1-sol`, `-terra` | 30 – 40 min | same as direct |
| O4 | same | `google/gemini-4-argon` | < 2.5 – 10 min | |
| O5 | same | `google/gemini-3.8-flash` | no observable cache | |
| O6 | same | `x-ai/grok-4.7` | < 2.5 – 15 min | |
| O7 | same | `moonshotai/kimi-k3.1-pro` | cold at 2.5 min | direct (R7) caches; mixed |
| O8 | same | `deepseek/deepseek-v4-pro` | **2 h – 4 h** | |
| O9 | same | `z-ai/glm-5.3` | 5 – 15 min | mixed |
| O10 | same | `meta/muse-wonder` | 2.5 – 7.5 min | |
| O11 | same | `mistralai/mistral-large-4-0` | ≥ 10 min | short run |
| K1 | Claude API key, Messages format, explicit `ttl: "1h"` | `claude-opus-5-5` | **30 – 65 min** | CPA passes an explicit 1 h through; the beta header is not needed |

Not measured: A1/A2 (not offered on the Antigravity account), M2 (404).

## OpenRouter through CLIProxyAPI with built-in OpenRouter support

CLIProxyAPI 8.0.53 plus router-for-me/CLIProxyAPI#7284 (cache markers, session id, reasoning levels), 2026-11-06,
real OpenRouter model ids through an `openai-compatibility` entry. Files in `cpa-8.0.53-or/`.

| Row | Model | Request | Lifetime | Notes |
|---|---|---|---|---|
| P1 | `anthropic/claude-haiku-5.5` | messages, no ttl | **5 – 7.5 min** | was "no cache" (O1) before #7284 |
| P2 | same | messages, `ttl: "1h"` | **30 – 65 min** | the client's 1-hour request reaches Anthropic |
| P3 | `openai/gpt-6.1-sol` | responses, `prompt_cache_options.ttl: "12h"` | warm at 30 min, cold at 1 h | the 12 h request is dropped: CPA's Responses → Chat Completions translation doesn't carry `prompt_cache_options`, so this is the 30-min default |

## Straight to OpenRouter

| Row | Model | Lifetime | Notes |
|---|---|---|---|
| R1 | `anthropic/claude-opus-5.5`, top-level `cache_control` + `session_id` | ~~cold at 2.5 min~~ | **probe error**: priming stalled ~6 min on retries, so the "2.5 min" and "5 min" checks ran at 6.6 and 6.7 min. Replaced by R1b |
| R1b | `anthropic/claude-haiku-5.5`, same request, probe 0.2.0 | **5 – 7.5 min** | every check within 3 s of its age; Anthropic's 5-minute tier, as through CPA (P1) |
| R1h | same, explicit `ttl: "1h"` | 30 – 65 min | |
| R2, R3 | `openai/gpt-6.1-sol`, `-terra` | 30 – 40 min | |
| R4 | `google/gemini-4-argon` | 5 – 7.5 min | |
| R5 | `google/gemini-3.8-flash` | cold at 2.5 min | |
| R6 | `x-ai/grok-4.7` | 2.5 – 15 min | |
| R7 | `moonshotai/kimi-k3.1-pro` | < 2.5 min – 1 h | mixed |
| R8 | `deepseek/deepseek-v4-pro` | ≥ 2 h | |
| R9 | `z-ai/glm-5.3` | 2.5 min – 1 h | mixed |
| R10 | `meta/muse-wonder` | 2.5 – 30 min | all warm but one check through 25 min |
| R11 | `mistralai/mistral-large-4-0` | 7.5 – 15 min | |

## Later runs (pi and vendor harnesses, one folder each)

- `harness-2026-11-07/`: vendor CLIs (Codex CLI, Muse Code, Devin CLI) vs pi through CLIProxyAPI, same accounts.
  Muse Wonder 1.0 through pi → CLIProxyAPI → Meta (H6) was warm in every check to 2 h.
- `devin-harness-2026-11-08/`, `devin-cache-investigation-2026-11-09/`: Devin models.
- `ember-2026-11-10/`: Muse Ember 1.0 through pi → CLIProxyAPI → Meta. At default retention (E1): 5 min 2/2, 30 min
  1/2, 1 h 0/2, 2 h 1/2 (random eviction). With `prompt_cache_retention: "24h"` (E2): 16/16 warm, 5 min to 4 h. See
  its README.
- `devin-repeat-2026-11-10/`: four Devin open-weight routes again, 5 samples per age (5 min – 2 h), pi → CLIProxyAPI →
  Devin. DeepSeek V4.1 Flash 25/25 warm (≥ 2 h); GLM-5.3 warm at 5 min, 30 min and 1 h, cold at 15 min and 2 h (whole
  batches); Gemini 4 Argon 3/5 at 5 min, then cold; Grok 4.7 4/10 through 15 min, then cold. See its README.
- `gpt6-2026-11-11/`: GPT-6 Astra and Luna on a ChatGPT plan, Devin, OpenRouter and an OpenAI API key (plus GPT-6.1 Sol
  on the key), 3 samples per age. OpenAI key and OpenRouter: warm at 30 min, cold at 40. Devin: warm at 30 min, cold at
  1 h. ChatGPT plan: Astra warm through 2 h; Luna misses from 15 min. Both accept ~915K input there. See its README.
- `meta-24h-2026-11-10/`: Meta's `prompt_cache_retention: "24h"` measured out to 24 hours, 3 samples per age. Nothing
  is warm at 12 or 24 hours. Muse Ember 1.0 lasts between 4 and 8 hours, Muse Wonder 1.0 between 4 and 12, and
  Muse Spark 1.3 under an hour even with the setting. See its README.

## What this means

- **Claude through CLIProxyAPI caches** on every route except OpenRouter via `openai-compatibility`: subscriptions (1 h,
  set by CPA), API keys (5 min, or 1 h when the client asks), Devin (≥ 2 h). A client that warms every ~4.5 min keeps
  any of them warm.
- **OpenRouter via `openai-compatibility` never caches Claude** on CPA without #7284, because CPA adds no
  `cache_control`. Direct OpenRouter does (R1h). With #7284 it does: 5 – 7.5 min by default (P1), 30 – 65 min when the
  client asks for 1 h (P2).
- **OpenAI's 12-hour lifetime doesn't pass through CPA to OpenRouter** yet (P3): the option is dropped when CPA
  translates Responses to Chat Completions.
- **Codex keeps the cache for hours when a cache key is sent** (C1). Without a key (C2) checks land on other cache
  nodes and look cold within minutes.
- **GPT-6.1 elsewhere lasts 30–40 min**, matching OpenAI's documented ≥ 30 min, through CPA or not.
- Many open-weight routes (GLM, Kimi, Grok, Gemini) are mixed or short: a client should not assume they cache, and
  should stop warming when a warm-up reads nothing from cache.
