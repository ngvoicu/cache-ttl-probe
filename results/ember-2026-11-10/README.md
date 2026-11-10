# Muse Ember 1.0 cache lifetime, 2026-11-10

Route: pi → CLIProxyAPI → Meta Model API (`https://api.meta.ai/v1/responses`) with a Muse Code subscription login,
through a pool with the Meta login as its only member. Method as in `../harness-2026-11-07` (run H6, Muse Wonder):
`harness/probe.py`, a new pi session per sample with a unique ~7k-token block, resumed once after the age; warm = the
reported cached tokens cover the harness prompt and at least half the block. Effort low. **Default retention**: no
`prompt_cache_retention` is sent (CLIProxyAPI's Meta executor removes it).

| Age | Muse Ember 1.0 (E1) | Muse Wonder 1.0 (H6, 2026-11-07) |
|---|---|---|
| 30 s (control) | 1/1 | – |
| 5 min | 2/2 | 3/3 |
| 30 min | 1/2 | 3/3 |
| 1 h | 0/2 | 3/3 |
| 2 h | 1/2 | 3/3 |

Misses are total (0 cached tokens), and one 2 h check was still warm: eviction looks random rather than a fixed
lifetime, which matches Meta's description of the default `in_memory` cache ("evicted under memory pressure or after
inactivity", https://dev.meta.ai/docs/prompt-caching). Only 5 minutes held every time. Two samples per age, so
treat this as indicative. Meta documents `prompt_cache_retention: "24h"` (Responses and Chat Completions) for longer
retention; not measured here.

Files: `E1.jsonl` (events), `run.sh`, `logs/`, `work-E1/` (pi sessions).
