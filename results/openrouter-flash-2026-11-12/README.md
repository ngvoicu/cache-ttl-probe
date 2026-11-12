# GLM 5.3 Flash and DeepSeek V4.1 Flash on OpenRouter, 2026-11-12

Route: plain HTTP → CLIProxyAPI 8.0.67 (with router-for-me/CLIProxyAPI#7284: cache markers and a session id for
OpenRouter) → OpenRouter, models `z-ai/glm-5.3-flash` and `deepseek/deepseek-v4.1-flash`. The TypeScript probe
0.2.0, Responses format, a `prompt_cache_key` per sample, ~6,000-token prompt; warm = at least half the prompt
reported as cached. The immediate re-send (control) was warm in every run.

- F2 (GLM) and F3 (DeepSeek): 3 samples per age, no check more than 3 seconds late.
- F4 (GLM) and F5 (DeepSeek): the 2.5-minute age again with 10 samples. F6 (DeepSeek): the 5-minute age again with
  10 samples. In these the ten prompts were primed within a minute of each other, so they are less independent;
  the latest check ran 23 seconds late (F4).

| Age | GLM 5.3 Flash | DeepSeek V4.1 Flash |
|---|---|---|
| 2.5 min | 7/13 (F2 3/3, F4 4/10) | 13/13 (F3 3/3, F5 10/10) |
| 5 min | 2/3 | 12/13 (F3 3/3, F6 9/10) |
| 7.5 min | 2/3 | 2/3 |
| 10 min | 1/3 | 2/3 |
| 15 min | 1/3 | 1/3 |
| 30 min | 2/3 | 3/3 |
| 40 min | 0/3 | 3/3 |
| 1 h | 0/3 | 2/3 |

## Reading it

- **GLM 5.3 Flash: not reliable at any age.** About half the checks find the cache from 2.5 to 30 minutes (15 of
  28); at 40 minutes and 1 hour none do. The first three checks at 2.5 minutes were all warm; ten more found it 4
  times. No safe lifetime.
- **DeepSeek V4.1 Flash: reliable at 2.5 minutes, nearly at 5, hit-or-miss after.** 13 of 13 at 2.5 minutes, 12 of
  13 at 5 minutes, then 13 of 18 between 7.5 minutes and 1 hour with no trend: 30 and 40 minutes were fully warm
  after misses at 7.5, 10 and 15. The cache outlives an hour; what fails is finding it. By the rule used for
  `observed.json` (every check at an age warm) the safe value is 2.5 minutes, under the 5 minutes a client would
  plan for. An earlier run with 2 samples per age (`../cpa-latest-2026-11-06`, L3) also found it about half the
  time out to 2 hours.
- **A miss is total** (0 cached tokens), on both models and at every age. These are hit-or-miss routes, not caches
  with a fixed lifetime. OpenRouter can send each request to a different upstream, which would explain it; the
  runs can't tell.
- **GLM hits are often partial**: between 3,800 and 6,300 tokens of the prompt, and 19 in one check at 30 minutes.
  DeepSeek hits return nearly the whole prompt.
- **GLM caches small prompts only in part.** F1 used the probe's default prompt (~2,600 tokens) and stopped at the
  control: the immediate re-send had 1,280 of 2,661 tokens cached, under the half that counts as warm. F1 is kept
  for that number and is not in `observed.json`.
- GLM 5.3 (not Flash) on OpenRouter was reliable to 5 minutes (`../cpa-8.0.53`, run O9).

Files: `F1-*` to `F6-*` `.json` / `.md` (the probe's results), `run.sh`. The logs stay local.
