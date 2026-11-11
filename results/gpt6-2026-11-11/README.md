# GPT-6 Astra and Luna on four routes, and an OpenAI API key, 2026-11-11

Every route of a local CLIProxyAPI that serves GPT-6 Astra and GPT-6 Luna, plus GPT-6.1 Sol on an OpenAI API key.
3 samples per age; a control (immediate re-send) was warm on all nine runs; no check ran late.

- **G1 – G4**: pi → CLIProxyAPI (`harness/probe.py`, a new pi session per sample with a unique ~7k-token block, resumed
  once after the age; warm = the reported cached tokens cover the harness prompt and at least half the block), pinned
  with temporary single-member pools (`harness/pool.py`).
- **G5 – G9**: plain HTTP through CLIProxyAPI (the TypeScript probe 0.2.0, Responses format, a `prompt_cache_key` per
  sample, ~2,700-token prompt; warm = at least half the prompt reported as cached). These five stopped after the
  1-hour checks, cold for the second age in a row, so they have no 2-hour row.

| Age | Codex login · Astra (G1) | Codex login · Luna (G2) | Devin · Astra (G3) | Devin · Luna (G4) |
|---|---|---|---|---|
| 5 min | 3/3 | 3/3 | 3/3 | 3/3 |
| 15 min | 3/3 | 2/3 | 3/3 | 3/3 |
| 30 min | 3/3 | 2/3 | 3/3 | 3/3 |
| 1 h | 3/3 | 1/3 | 0/3 | 0/3 |
| 2 h | 3/3 | 0/3 | 0/3 | 0/3 |

| Age | OpenAI key · 6.1 Sol (G5) | OpenAI key · Astra (G6) | OpenAI key · Luna (G7) | OpenRouter · Astra (G8) | OpenRouter · Luna (G9) |
|---|---|---|---|---|---|
| 5 min | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| 15 min | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| 30 min | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| 40 min | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |
| 1 h | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

## Reading it

- **The OpenAI API keeps the cache exactly as documented**: warm at 30 minutes, cold at 40, on all three models. So does
  OpenRouter, which routes these models to OpenAI.
- **Devin: 30 minutes**, cold by 1 hour, on both models. An earlier run with 2 samples (`../devin-harness-2026-11-08`,
  D5p) missed one Astra check at 15 minutes; with 3 samples every check through 30 minutes was warm.
- **The ChatGPT plan (Codex login) depends on the model.** Astra was warm in every check through 2 hours. Luna missed
  from 15 minutes on (2 of 3, 2 of 3, 1 of 3) and was cold at 2 hours; its misses are total (0 cached tokens), so
  only 5 minutes is reliable. Same account, same hour, same method.

## Context window on the ChatGPT plan

`limits_walk.py` (a rejection is free, so it walks down candidate sizes and stops at the first accepted one):
GPT-6 Astra and GPT-6 Luna both accepted **915,011** input tokens and refused 922,500 (`limits.jsonl`). Codex's own
model list gives them a 272K default window and an 872K maximum; the backend takes the same ~922K as GPT-6.1.

Files: `G1.jsonl` – `G4.jsonl` (events), `G5` – `G9` `.json` / `.md` (the plain probe's results), `limits.jsonl`,
`limits_walk.py`, `run.sh`. The logs and pi session files stay local.
