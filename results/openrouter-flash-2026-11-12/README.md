# GLM 5.3 Flash on OpenRouter, 2026-11-12

Route: plain HTTP → CLIProxyAPI 8.0.67 (with router-for-me/CLIProxyAPI#7284: cache markers and a session id for
OpenRouter) → OpenRouter, model `z-ai/glm-5.3-flash`. The TypeScript probe 0.2.0, Responses format, a
`prompt_cache_key` per sample; warm = at least half the prompt reported as cached. F2: 3 samples per age, no check
more than 3 seconds late. F4: the 2.5-minute age again with 10 samples, primed within a minute of each other; the
latest check ran 23 seconds late.

| Age | Warm | Cached tokens of ~6,350 |
|---|---|---|
| 2.5 min (F2) | 3/3 | 6,272 · 6,144 · 6,144 |
| 2.5 min (F4) | 4/10 | 4,480 · 0 · 0 · 0 · 6,144 · 6,144 · 0 · 0 · 0 · 5,760 |
| 5 min | 2/3 | 6,272 · 4,608 · 0 |
| 7.5 min | 2/3 | 5,120 · 5,120 · 0 |
| 10 min | 1/3 | 0 · 0 · 6,272 |
| 15 min | 1/3 | 0 · 0 · 4,480 |
| 30 min | 2/3 | 4,480 · 19 · 3,840 |
| 40 min | 0/3 | 0 · 0 · 0 |
| 1 h | 0/3 | 0 · 0 · 0 |

## Reading it

- **Not reliable at any age.** The three checks at 2.5 minutes in F2 were all warm, but ten more in F4 found the
  cache 4 times: 7 of 13 together. From 5 to 30 minutes 8 of 15 checks found it; at 40 minutes and 1 hour none
  did. The immediate re-send was warm in both runs. There is no safe lifetime to report.
- **A miss is total** (0 cached tokens), at every age. This is a hit-or-miss route, not a cache with a fixed
  lifetime. OpenRouter can send each request to a different upstream, which would explain it; the runs can't tell.
- **Hits are often partial.** A hit returns between 3,800 and 6,300 tokens of the prompt; one check at 30 minutes
  returned 19.
- **Small prompts cache only in part.** F1 used the probe's default prompt (~2,600 tokens) and stopped at the
  control: the immediate re-send had 1,280 of 2,661 tokens cached, under the half that counts as warm. F2 used a
  ~6,000-token prompt, where the re-send had 6,144 of 6,305 cached. F1 is kept for that number and is not in
  `observed.json`.
- GLM 5.3 (not Flash) on OpenRouter was reliable to 5 minutes (`../cpa-8.0.53`, run O9).

Files: `F1-*`, `F2-*`, `F4-*` `.json` / `.md` (the probe's results), `run.sh`. The logs stay local.
