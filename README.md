# groundtruth

The measuring tool behind [providers.dev](https://providers.dev): how long an LLM prompt cache really lives, and how
large the limits really are, per endpoint, model and route. It was called `cache-ttl-probe` until November 2026.

Providers rarely publish how long a cached prompt prefix survives, and when they do it's a range ("5 to 10 minutes
of inactivity") or it only holds on their own API, not through a proxy, a reseller or a subscription backend. Agents
that keep caches warm (or that decide when a pause will cost a full re-write) need a number. This tool measures it.

- Chat Completions, Responses and Anthropic Messages formats
- Optional explicit Anthropic `cache_control` ttl (`5m` / `1h`), extra headers and body fields
- Works against any base URL: vendor APIs, OpenRouter, or a local proxy such as CLIProxyAPI
- No runtime dependencies, Node ≥ 22.19, MIT (TypeScript is a build-time dependency only)

## Quick start

```bash
# run straight from GitHub (or: git clone, npm install, node src/cli.ts …)
export CACHE_PROBE_KEY=sk-...           # never passed on the command line, never printed

# OpenAI-style Responses endpoint, default schedule (2.5 min → 2 h)
npx github:ngvoicu/groundtruth --base-url https://api.openai.com/v1 --model gpt-6.1-sol

# Anthropic, explicit 1-hour cache: the first ages of every run, then 30 and 65 minutes
npx github:ngvoicu/groundtruth --base-url https://api.anthropic.com/v1 --format messages --model claude-opus-5-5 \
  --ttl 1h --ages 30m,65m

# Through a local proxy, long schedule (adds 4 h, 8 h, 12 h)
npx github:ngvoicu/groundtruth --base-url http://127.0.0.1:8317/v1 --model gpt-6.1-sol --schedule long

# Show the plan and the request body without sending anything
npx github:ngvoicu/groundtruth --base-url http://127.0.0.1:8317/v1 --model m --dry-run
```

Each run writes `results/<label>-<timestamp>.json` (every check) and `.md` (survival table), and keeps a
`.partial.json` up to date while it runs.

```
**Lifetime: 5m – 10m**

| Age | Warm | Checks |
|---|---|---|
| 2.5m | 3 | 3 |
| 5m | 3 | 3 |
| 7.5m | 1 | 3 |
| 10m | 0 | 3 |
```

`5m – 10m` reads "every replica was warm at 5 minutes, none at 10". Schedule warming against the lower bound.

## Method

1. **Control round.** Prime a fresh prefix and re-send it immediately. If the re-send isn't served from cache, the
   endpoint has no observable cache for this request shape and the run stops (`no-observable-cache`).
2. **Prime every sample once.** One sample per (age, replica), each with its own prefix, all primed up front.
3. **Check each sample exactly once**, when it reaches its age. Never poll one prefix: most caches restart their timer
   on every hit, so polling measures how long your own polling keeps the entry alive.
4. **Warm** = at least half of the prompt and at least 500 tokens reported as cached.
5. **Stop** after two consecutive ages where every replica is cold.

Ages are measured from the *start* of the priming request (Anthropic counts the lifetime from the start of the request
that wrote the entry). Each result records the actual age of every check, so late checks (sleeping laptop, retries)
are visible.

**Every evaluation starts the same way.** The prompt is sent again at once (the control: it shows that the prompt was
cached at all and that the route reports cache hits), then checked at 2.5, 5 and 7.5 minutes, and on from there:

| Schedule | Ages |
|---|---|
| `std` (default) | 2.5, 5, 7.5, 10, 15, 20, 25, 30, 40, 50 min, 1 h, 1 h 15, 1 h 30, 2 h |
| `long` | `std`, then 4 h, 8 h, 12 h |
| `quick` | 2.5, 5, 7.5, 10 min |

`--ages` adds ages to that start, it does not replace it: `--ages 30m,65m` checks at 2.5, 5, 7.5, 30 and 65 minutes.
A cache that is gone inside five minutes only shows in the first ages, and two results can only be compared when they
share them. `harness/probe.py` (the same evaluation through a real coding tool) has the same schedules, and
`scripts/build_observed.py` refuses a run dated 14 November 2026 or later that has no control or does not start at
2.5 minutes. Runs before that date keep the ages they were made with.

Options: `--schedule std|long|quick`, `--ages 30m,65m`, `--replicas 3`, `--prefix-tokens 2500`, `--max-output 16`,
`--stream`, `--ttl`, `--beta`, `--header k:v`, `--body-extra '<json>'`, `--label`, `--salt`, `--out`. See `--help`.

## observed.json

Everything measured so far, in one file: [`observed.json`](observed.json). providers.dev reads it once a day and
shows each run on the entry it belongs to. Raw results are in `results/`
(see [`results/SUMMARY.md`](results/SUMMARY.md) for the story of each run).

```bash
curl -s https://raw.githubusercontent.com/ngvoicu/groundtruth/main/observed.json
```

It holds what catalogs such as [models.dev](https://models.dev) can't: values **as measured**, including
subscription routes that have no public API (a ChatGPT plan through Codex, Devin, a Claude login, a Muse Code key).

- **`cache`**: one entry per run. `route` (whose account), `client` (what sent the requests), `model` (the id on that
  route), `options` (anything that changes caching: an explicit ttl, a retention setting, reasoning level) and
  `checks`, the raw counts per age: `{ "age": "30m", "age_s": 1800, "warm": 3, "total": 3 }`.
- Three numbers summarise a run, all in seconds, `null` when there is none:
  `all_warm_through_s` (every age up to here was fully warm: **the safe value**), `last_warm_s` (the oldest age with
  any warm check) and `first_all_cold_s` (the youngest age with none). When `last_warm_s` is past
  `first_all_cold_s`, the route misses at random rather than by age.
- `control` is an immediate re-send; `0/1` means the route showed no cache at all. `late_excluded` counts checks
  that ran too long after their age and were left out.
- `latest` marks the newest run for the same route, client, model and options. Older runs stay in the file.
- `continues` names an earlier run that this one adds checks to: older ages, or more samples of an age (same route,
  client, model and options). Its `checks` and its three summary numbers then cover that run too, and any run that
  one continues; `source` is the file with its own checks.
- `requires` / `lacks` name a CLIProxyAPI change the run had or did not have yet (for OpenRouter, the cache markers
  and session id of router-for-me/CLIProxyAPI#7284). A reader on a build with that change should skip `lacks` runs.
- `models_dev` is the matching entry in models.dev (`provider/model`) when that route exists there, and
  `base_model` is the model's id in its `models/` folder; either can be `null`.
- **`limits`**: context and output limits found by sending requests of growing size, each backed by a row of the raw
  file named in `source`.
- **`known`**: lifetimes that were **not measured** but follow from how a client or proxy builds its requests
  (for example CLIProxyAPI asking Anthropic for the 1-hour cache on Claude logins). Each has `ttl_s`, a `basis` in
  words and a `source`; `model` is `*` when it holds for every model of the route, and `when` narrows it to a
  setting.
- **`excluded`**: runs left out, and why.

Small samples (2 to 5 per age), one account per route, dated: treat them as observations, not guarantees.

Before the first commit in a clone, install the check that blocks credentials, home-folder paths and session files:
`ln -sf ../../scripts/pre-commit .git/hooks/pre-commit`.

To add a run: publish its files under `results/`, add it to [`observed/manifest.json`](observed/manifest.json)
(route, model, options: nothing that is a result), then run `python3 scripts/build_observed.py`. CI fails when
`observed.json` doesn't match the raw files.

## Pitfalls

- **Minimum cacheable length.** Below it, nothing is ever cached (OpenAI 1,024 tokens; Anthropic 512–4,096 depending on
  the model). The default 2,500-token prefix plus whatever the proxy adds clears most minimums; raise
  `--prefix-tokens` if the control round fails.
- **A missing cached-tokens field counts as 0.** Some endpoints omit it instead of reporting 0.
- **Prefixes are salted per run.** Re-running immediately never hits the previous run's cache.
- **Anthropic caches only marked content.** `messages` runs always mark the prefix; proxies that translate other formats
  to Anthropic must add markers themselves (a failing control round tells you they don't).
- **Aggregators can split caches** across upstream providers. Pin the upstream (or a single credential behind a proxy)
  for meaningful results.
- **A lifetime is a curve.** Report the bracket, not a single number; run 3+ replicas.

## Credits

The single-check-per-prefix method follows the measurement write-up
["How long does a prompt cache live? Measured TTLs for 11 LLM endpoints"](https://gist.github.com/monperrus/9784f52d5144975fd11be7f642c4a8fc).
This is an independent implementation.

## License

MIT
