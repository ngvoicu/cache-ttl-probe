# Muse Spark 1.3 on OpenRouter, 2026-11-12

Route: plain HTTP → CLIProxyAPI 8.0.67 (with router-for-me/CLIProxyAPI#7284: cache markers and a session id for
OpenRouter) → OpenRouter, model `meta/muse-spark-1.3`. The TypeScript probe 0.2.0, Responses format, a
`prompt_cache_key` per sample, ~2,600-token prompt; warm = at least half the prompt reported as cached. 3 samples per
age. The control (immediate re-send) was warm; no check ran late. The run stopped after 40 minutes, cold for the
second age in a row.

| Age | Warm (S1) |
|---|---|
| 2.5 min | 0/3 |
| 5 min | 2/3 |
| 7.5 min | 2/3 |
| 10 min | 1/3 |
| 15 min | 2/3 |
| 30 min | 0/3 |
| 40 min | 0/3 |

## Reading it

- **No age was fully warm, so there is no safe lifetime.** Between 5 and 15 minutes about half the checks found the
  cache (7 of 12); by 30 minutes it was gone.
- **A miss is total** (0 cached tokens), and the three cold checks at 2.5 minutes came before warm ones at 5 to 15
  minutes: this is a hit-or-miss route, not a cache with a fixed lifetime. OpenRouter can send each request to a
  different upstream, which would explain it; the run can't tell.
- On Meta's own API the same model was reliable to about 7 minutes (`../cpa-8.0.53`, run M3) and to 5 minutes with
  the 24h retention option (`../meta-24h-2026-11-10`, run M3). Muse Wonder on OpenRouter behaved like this run
  (`../openrouter-direct`, R10).

Files: `S1-*.json` / `.md` (the probe's results), `run.sh`. The logs stay local.
