# Muse Ember 1.0 cache lifetime, 2026-11-10

Route: pi → CLIProxyAPI → Meta Model API (`https://api.meta.ai/v1/responses`) with a Muse Code subscription login,
through a pool with the Meta login as its only member. Method as in `../harness-2026-11-07` (run H6, Muse Wonder):
`harness/probe.py`, a new pi session per sample with a unique ~7k-token block, resumed once after the age; warm = the
reported cached tokens cover the harness prompt and at least half the block. Effort low.

- **E1, default retention**: no `prompt_cache_retention` is sent (CLIProxyAPI's Meta executor removes it).
- **E2, 24h retention**: same route and method, with `prompt_cache_retention: "24h"` added to every Muse request by a
  CLIProxyAPI config rule (`payload.override`, models `muse-*`, protocol `meta`; payload rules run after the executor
  removes the field). The value reaches Meta: an invalid one is rejected with "expected `in_memory` or `24h`".

| Age | Muse Ember 1.0, default (E1) | Muse Ember 1.0, 24h (E2) | Muse Wonder 1.0, default (H6, 2026-11-07) |
|---|---|---|---|
| 30 s (control) | 1/1 | 1/1 | – |
| 5 min | 2/2 | 3/3 | 3/3 |
| 30 min | 1/2 | 3/3 | 3/3 |
| 1 h | 0/2 | 3/3 | 3/3 |
| 2 h | 1/2 | 3/3 | 3/3 |
| 4 h | – | 3/3 | – |

At the default retention, misses are total (0 cached tokens), and one 2 h check was still warm: eviction looks random
rather than a fixed lifetime, which matches Meta's description of the default `in_memory` cache ("evicted under memory
pressure", https://dev.meta.ai/docs/prompt-caching). With `"24h"` ("keeping the cached prefix active for longer, up to
24 hours", Responses API only) every check through 4 h was warm, with the full 13,300-token prefix read from cache.
Meta's pricing lists one cached-input rate and no charge for the longer retention.

Muse Code 1.4.15 itself doesn't send `prompt_cache_retention`, so E2 is a CLIProxyAPI configuration choice, not what
the vendor client does. Small samples (2–3 per age): treat as indicative.

Files: `E1.jsonl`, `E2.jsonl` (events), `run.sh`, `logs/` (not committed), `work-E1/`, `work-E2/` (pi sessions).
