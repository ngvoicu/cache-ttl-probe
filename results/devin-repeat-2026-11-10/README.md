# Devin open-weight routes, measured again with 5 samples, 2026-11-10

Route: pi → CLIProxyAPI → Devin, one Devin login, each model reached through a pool with Devin as its only member.
Method as in `../devin-harness-2026-11-08` (the `p` runs): `harness/probe.py`, a new pi session per sample with a unique
~7k-token block, resumed once after the age; warm = the reported cached tokens cover the harness prompt and at least half
the block. Effort low. These four routes gave random or contradictory rows there with 2 samples per age.

| Age | Gemini 4 Argon (D6r) | DeepSeek V4.1 Flash (D8r) | GLM-5.3 (D9r) | Grok 4.7 (D10r) |
|---|---|---|---|---|
| ~35 s (control) | 1/1 | 1/1 | 1/1 | 0/1 |
| 5 min | 3/5 | 5/5 | 5/5 | 2/5 |
| 15 min | 0/5 | 5/5 | **0/5** | 2/5 |
| 30 min | 0/5 | 5/5 | 5/5 | 0/5 |
| 1 h | 0/5 | 5/5 | 5/5 | 0/5 |
| 2 h | 0/5 | 5/5 | 0/5 | 0/5 |

The same routes on 2026-11-08 (2 samples per age), for comparison:

| Age | Argon (D6p) | DeepSeek (D8p) | GLM (D9p) | Grok (D10p) |
|---|---|---|---|---|
| 5 min | 0/2 | 2/2 | 2/2 | 1/2 |
| 15 min | 0/2 | 0/2 | 2/2 | 2/2 |
| 30 min | 0/2 | 1/2 | 0/2 | 1/2 |
| 1 h | 0/2 | 1/2 | 2/2 | 0/2 |
| 2 h | 0/2 | 1/2 | 0/2 | 1/2 |

## Reading it

- **DeepSeek V4.1 Flash: ≥ 2 h in this run** (25 of 25 warm, 13,300 – 13,600 of ~13,600 prompt tokens read from cache each time). On 2026-11-08
  the same route missed about half its checks, so it keeps the cache for hours but not on every day.
- **GLM-5.3: 1 h – 2 h, with whole-batch misses.** Warm at 1 h and cold at 2 h in both runs. But all five 15-minute
  checks were cold while the 30-minute and 1-hour ones, primed seconds earlier, were all warm (on 2026-11-08 it was the
  30-minute pair). A miss here is not about age.
- **Gemini 4 Argon: minutes at best.** 3 of 5 at 5 minutes, nothing from 15 minutes on (0 of 20).
- **Grok 4.7: unreliable.** 4 of 10 through 15 minutes, nothing from 30 minutes on (0 of 15); the control was cold too.
- A cold check often still reports the part of pi's own prompt that every session shares (5,312 tokens on GLM, 1,152
  on Grok; Argon mostly 0) and none of the unique block.

**Limit of the method:** the five samples of one age are primed within about 5 seconds of each other and checked
within about 5 seconds of each other (Argon: up to 50 s), so they are not independent. GLM shows it: each row is 5/5 or
0/5. More samples per age made the rows cleaner, not the route more predictable; telling "evicted by age" from "this
moment landed on a cold node" needs samples spread over time.

Every check ran within 50 s of its age (all but Argon's within 10 s); none was late. Devin's own CLI was not measured in this run.

Files: `D6r.jsonl`, `D8r.jsonl`, `D9r.jsonl`, `D10r.jsonl` (events), `run.sh`, `logs/` (not committed), `work-*/` (pi
sessions).
