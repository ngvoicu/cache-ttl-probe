# cache-ttl-probe

Measure how long an LLM prompt cache really lives — per endpoint, model and route.

Providers rarely publish how long a cached prompt prefix survives, and when they do it's a range ("5 to 10 minutes
of inactivity") or it only holds on their own API, not through a proxy, a reseller or a subscription backend. Agents
that keep caches warm (or that decide when a pause will cost a full re-write) need a number. This tool measures it.

- Chat Completions, Responses and Anthropic Messages formats
- Optional explicit Anthropic `cache_control` ttl (`5m` / `1h`), extra headers and body fields
- Works against any base URL: vendor APIs, OpenRouter, or a local proxy such as CLIProxyAPI
- Zero dependencies, Node ≥ 22.19 (runs the TypeScript sources directly), MIT

## Quick start

```bash
git clone https://github.com/ngvoicu/cache-ttl-probe && cd cache-ttl-probe
export CACHE_PROBE_KEY=sk-...           # never passed on the command line, never printed

# OpenAI-style Responses endpoint, default schedule (2.5 min → 2 h)
node src/cli.ts --base-url https://api.openai.com/v1 --model gpt-6.1-sol

# Anthropic, explicit 1-hour cache, three checks
node src/cli.ts --base-url https://api.anthropic.com/v1 --format messages --model claude-opus-5-5 \
  --ttl 1h --ages 10m,30m,65m

# Through a local proxy, long schedule (adds 4 h, 8 h, 12 h)
node src/cli.ts --base-url http://127.0.0.1:8317/v1 --model gpt-6.1-sol --schedule long

# Show the plan and the request body without sending anything
node src/cli.ts --base-url http://127.0.0.1:8317/v1 --model m --dry-run
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

Options: `--schedule std|long|quick`, `--ages 10m,30m`, `--replicas 3`, `--prefix-tokens 2500`, `--max-output 16`,
`--stream`, `--ttl`, `--beta`, `--header k:v`, `--body-extra '<json>'`, `--label`, `--salt`, `--out`. See `--help`.

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
