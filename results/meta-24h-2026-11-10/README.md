# Meta's "24h" cache retention, measured to 24 hours, 2026-11-10 / 11

Route: pi → CLIProxyAPI → Meta Model API with a Muse Code subscription login, as in `../ember-2026-11-10`. Every
request carried `prompt_cache_retention: "24h"`, added by the CLIProxyAPI config rule described there (run E2).
Method: `harness/probe.py`, a new pi session per sample with a unique ~7k-token block, resumed once after the age;
warm = the reported cached tokens cover the harness prompt and at least half the block. Effort low. 3 samples per age;
the control (immediate re-send) was warm in all three runs; no check ran late.

- **M1, Muse Ember 1.0**: continues E2 (warm 3/3 from 5 minutes to 4 hours) with 8 h, 12 h and 24 h.
- **M2, Muse Wonder 1.0**: 4 h, 12 h, 24 h.
- **M3, Muse Spark 1.3**: 5 min, 1 h, 4 h, 24 h.

| Age | Muse Ember 1.0 (E2, then M1) | Muse Wonder 1.0 (M2) | Muse Spark 1.3 (M3) |
|---|---|---|---|
| 5 min | 3/3 (E2) | – | 3/3 |
| 30 min | 3/3 (E2) | – | – |
| 1 h | 3/3 (E2) | – | 0/3 |
| 2 h | 3/3 (E2) | – | – |
| 4 h | 3/3 (E2) | 3/3 | 0/3 |
| 8 h | 0/3 | – | – |
| 12 h | 0/3 | 0/3 | – |
| 24 h | 0/3 | 0/3 | 0/3 |

## Reading it

- **"24h" is an upper bound, as Meta says ("up to 24 hours"), and the real lifetime is much shorter.** Nothing was
  warm at 24 hours, or at 12.
- **Muse Ember 1.0: between 4 and 8 hours.** Every check through 4 hours was warm, every check from 8 hours on cold.
- **Muse Wonder 1.0: between 4 and 12 hours.** Warm at 4 hours, cold at 12.
- **Muse Spark 1.3: under an hour, even with "24h".** Warm at 5 minutes, cold at 1 hour and after. At the default
  retention it was reliable to about 7 minutes and gone by 40 (`../cpa-8.0.53`, run M3), so the setting changes
  little for this model.
- A miss is total: 0 cached tokens out of about 13,400.

Compared with the default retention, where Ember misses at random from 30 minutes on (E1), the setting is worth
having for Ember and Wonder: a reliable 4 hours. It is not a 24-hour cache.

One note on M2's last age: by then the Muse Wonder pool had gained a second member (a Devin login). CLIProxyAPI
tried it first for two of the three 24-hour checks, it failed, and CLIProxyAPI retried on the Meta login; all three
answers came from Meta, with 0 cached tokens. The 4-hour and 12-hour checks ran while Meta was the only member.

Files: `M1.jsonl`, `M2.jsonl`, `M3.jsonl` (events), `run.sh`. The logs and pi session files stay local.
