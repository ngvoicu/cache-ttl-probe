# Why some Devin models cached worse through CPA (2026-11-09)

Run D (2026-11-08) suggested Devin CLI caches better than pi through CPA on Argon, GLM, Grok, Nemotron and SWE-2.
Checked with temporary per-account aliases `probe-devin-*` and CPA's request log.

| Test | Result |
|---|---|
| Same body twice, HTTP, Nemotron none / medium | 21,392 of 21,422 and 22,112 of 22,130 cached: random message ids don't matter |
| Two turns, HTTP, Nemotron effort none | turn 2: 23,024 of 23,094 |
| Two turns, HTTP, Nemotron low / medium / high (low → `-medium`) | turn 2: 17,664 of ~23k (checkpoint) |
| Two turns, pi, Nemotron thinking low | turn 2: 4,416 of 13,024 |
| Two turns, pi, Nemotron thinking off | turn 2: 12,976 of 13,017 |
| N1c: Devin CLI `nemotron-3-5-super-medium`, 2 min | cold (17,664 of 24,548), like pi |
| N1p: pi Nemotron thinking off, control and 2 min | warm 3/3 (≥ 99 %) |
| Two turns, HTTP, GLM-5.3 none / low; pi GLM low | turn 2 fully cached |
| Two turns, HTTP, Grok 4.7 low; Gemini 4 Argon low | turn 2: 17,280 of 17,377; 21,469 of 23,540 |

Conclusions:

- **Nemotron 3.5 Super is not a CPA problem.** D11c used `nemotron-3-5-super-none`; pi's `low` maps to
  `-medium` (Devin has none / medium / high). With reasoning on, turn 1's reasoning is not part of turn 2's prompt, so
  this hybrid (Mamba) model resumes only from an earlier cache checkpoint, in Devin CLI too. Use thinking off for cache.
- **GLM, Grok, Argon cache normally through CPA** turn to turn. Run D's long-age differences come from 2 samples per
  age: Grok was 4/10 (CLI) vs 5/10 (pi) overall; GLM 10/10 vs 6/10 (misses at 30 min and 2 h, warm at 1 h) looks like
  random node misses; Argon was poor on both (2/10 vs 0/10).
- **SWE-2:** no usable cache on either route (D12).
- Not changed: CPA sends a new random id per prompt message on every request; harmless (identical bodies cache).
