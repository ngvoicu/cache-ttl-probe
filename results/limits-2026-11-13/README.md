# Input limits, 2026-11-13

Requests through a local CLIProxyAPI, Responses format, `"Reply with just OK." + " hello" × N`, a 16-token reply,
low effort. `limits_walk.py` goes down a list of sizes: a refusal is free, so only the accepted requests cost quota.

## GPT-6.1 Sol on the ChatGPT plan (Codex login): about 922K of input

Pinned to the Codex login with a temporary single-member pool (`harness/pool.py`, removed afterwards).

| Input | Answer |
|---|---|
| 930,000 | refused: "Your input exceeds the context window of this model." |
| 915,011 | accepted |
| 922,500 | refused |

The same bounds as GPT-6 Astra, GPT-6 Luna (`../gpt6-2026-11-11`) and GPT-6.1 Terra (`../limits-2026-11-08`) on this
login. Codex's own model list gives this model a 500K default window and an 872K maximum: those are settings of the
Codex client, not the limit of the backend. Rows: `limits.jsonl`.

## swe-2 on Devin: no result

Devin's own model list gives `swe-2` a 262,000-token window. The walk found no refusal: requests of 300K, 520K, 800K,
915K, 925K and 930K input tokens were all answered with status 200 and the full prompt counted in the usage.
(The first 930K request of the day got no answer in 10 minutes; it ran before the walk wrote a row for an unanswered
request, so it is not in the file.)

That does not show that the model reads such an input. A second kind of request put one code word before the filler
and one after it and asked for both:

| Filler | Answer |
|---|---|
| 2,000 | both words, in 1.5 s |
| 250,000 | no answer in 5 minutes |
| 300,000 | no answer in 5 minutes |
| 915,000 | no answer in 3 and in 10 minutes |

So a request whose answer does not depend on the whole input is accepted at any size tried, and a request that needs
both ends gets no answer even below the listed window. Nothing here says how much of an input `swe-2` uses. It is
kept as a record and is **not** in `observed.json`. Rows: `swe-2-inconclusive.jsonl` (a row with status `null` is a
request with no answer inside the time limit).
