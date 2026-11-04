#!/usr/bin/env node
// cache-ttl-probe: measure how long a prompt cache lives on one endpoint/model.

import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { parseArgs } from "node:util";
import { buildRequest, type Format, FORMATS } from "./formats.ts";
import { makePrefix, newRunSalt } from "./prefix.ts";
import { renderMarkdown } from "./report.ts";
import { type Deps, PROBE_VERSION, type RunOptions, runProbe } from "./run.ts";
import { agesFor, formatDuration, planSamples } from "./schedule.ts";

const HELP = `cache-ttl-probe ${PROBE_VERSION}

Measures prompt-cache lifetime: primes one fresh prefix per sample and checks each exactly once at a fixed age.

Usage:
  cache-ttl-probe --base-url <url> --model <id> [options]

Required:
  --base-url <url>        API base URL including /v1 (e.g. http://127.0.0.1:8317/v1, https://api.anthropic.com/v1)
  --model <id>            model id to probe

Options:
  --format <f>            responses | chat | messages (default: responses)
  --key-env <NAME>        env var holding the API key (default: CACHE_PROBE_KEY); sent as Bearer and x-api-key
  --ttl <5m|1h>           explicit Anthropic-style cache_control ttl (messages; responses part-level marker)
  --beta <value>          anthropic-beta header (e.g. extended-cache-ttl-2025-04-11)
  --header <k:v>          extra header, repeatable
  --body-extra <json>     extra top-level body fields (e.g. '{"prompt_cache_options":{"ttl":"12h"}}')
  --schedule <name>       std (2.5m..2h) | long (std + 4h, 8h, 12h) | quick (5m, 7.5m, 10m) (default: std)
  --ages <list>           custom ages, comma-separated (e.g. 10m,30m,65m); overrides --schedule
  --replicas <n>          samples per age (default: 3)
  --prefix-tokens <n>     approximate prefix size (default: 2500; must exceed the provider's minimum)
  --max-output <n>        max output tokens per call (default: 16)
  --warm-fraction <f>     share of the prompt that must be cached for a warm check (default: 0.5)
  --stream                use streaming responses
  --concurrency <n>       parallel priming requests (default: 4)
  --label <text>          run label used in file names and the report (default: <model>-<format>)
  --salt <text>           run salt (default: random)
  --out <dir>             output directory (default: results)
  --dry-run               print the plan and one request body, send nothing
  -h, --help              show this help
`;

function fail(msg: string): never {
  process.stderr.write(`error: ${msg}\n\n${HELP}`);
  process.exit(2);
}

function int(value: string | undefined, name: string, def: number): number {
  if (value === undefined) return def;
  const n = Number(value);
  if (!Number.isInteger(n) || n < 1) fail(`--${name} must be a positive integer`);
  return n;
}

const { values } = parseArgs({
  options: {
    "base-url": { type: "string" },
    model: { type: "string" },
    format: { type: "string", default: "responses" },
    "key-env": { type: "string", default: "CACHE_PROBE_KEY" },
    ttl: { type: "string" },
    beta: { type: "string" },
    header: { type: "string", multiple: true },
    "body-extra": { type: "string" },
    schedule: { type: "string" },
    ages: { type: "string" },
    replicas: { type: "string" },
    "prefix-tokens": { type: "string" },
    "max-output": { type: "string" },
    "warm-fraction": { type: "string" },
    stream: { type: "boolean", default: false },
    concurrency: { type: "string" },
    label: { type: "string" },
    salt: { type: "string" },
    out: { type: "string", default: "results" },
    "dry-run": { type: "boolean", default: false },
    help: { type: "boolean", short: "h", default: false },
  },
  strict: true,
});

if (values.help) {
  process.stdout.write(HELP);
  process.exit(0);
}
const baseUrl = values["base-url"] ?? fail("--base-url is required");
const model = values.model ?? fail("--model is required");
const format = values.format as Format;
if (!FORMATS.includes(format)) fail(`--format must be one of ${FORMATS.join(", ")}`);
if (values.ttl && !/^\d+(m|h)$/.test(values.ttl)) fail("--ttl must look like 5m or 1h");

let bodyExtra: Record<string, unknown> | undefined;
if (values["body-extra"]) {
  try {
    bodyExtra = JSON.parse(values["body-extra"]);
  } catch {
    fail("--body-extra must be valid JSON");
  }
}

const extraHeaders: Record<string, string> = {};
for (const h of values.header ?? []) {
  const i = h.indexOf(":");
  if (i <= 0) fail(`--header "${h}" must be name:value`);
  extraHeaders[h.slice(0, i).trim()] = h.slice(i + 1).trim();
}
if (values.beta) extraHeaders["anthropic-beta"] = values.beta;

let ages: number[];
try {
  ages = agesFor(values.schedule, values.ages);
} catch (err) {
  fail((err as Error).message);
}

const label = (values.label ?? `${model}-${format}${values.ttl ? `-ttl${values.ttl}` : ""}`).replace(/[^\w.-]+/g, "_");
const opts: RunOptions = {
  baseUrl,
  format,
  model,
  ttl: values.ttl,
  headers: extraHeaders,
  bodyExtra,
  ages,
  replicas: int(values.replicas, "replicas", 3),
  maxOutput: int(values["max-output"], "max-output", 16),
  stream: values.stream,
  prefixTokens: int(values["prefix-tokens"], "prefix-tokens", 2500),
  runSalt: values.salt ?? newRunSalt(),
  concurrency: int(values.concurrency, "concurrency", 4),
  label,
  warmFraction: values["warm-fraction"] === undefined ? 0.5 : Number(values["warm-fraction"]),
};
if (!(opts.warmFraction! > 0 && opts.warmFraction! <= 1)) fail("--warm-fraction must be in (0, 1]");

if (values["dry-run"]) {
  const samples = planSamples(opts.ages, opts.replicas);
  const req = buildRequest(format, { model, prefix: makePrefix(opts.runSalt, "control", 40), ttl: opts.ttl, maxOutput: opts.maxOutput, stream: opts.stream, bodyExtra });
  process.stdout.write(
    `${label}: ${samples.length} samples + control, ages ${opts.ages.map(formatDuration).join(", ")}\n` +
      `POST ${baseUrl.replace(/\/+$/, "")}${req.path}\nheaders: ${Object.keys({ ...req.headers, ...extraHeaders }).join(", ") || "(none extra)"}\n` +
      `${JSON.stringify(req.body, null, 2)}\n`,
  );
  process.exit(0);
}

const key = process.env[values["key-env"] as string];
if (!key) fail(`environment variable ${values["key-env"]} is not set`);
opts.headers = { authorization: `Bearer ${key}`, "x-api-key": key, ...opts.headers };

mkdirSync(values.out as string, { recursive: true });
const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const base = join(values.out as string, `${label}-${stamp}`);

const deps: Deps = {
  now: () => Date.now(),
  sleep: (ms) => new Promise((r) => setTimeout(r, ms)),
  send: async (url, headers, body) => {
    const res = await fetch(url, { method: "POST", headers, body, signal: AbortSignal.timeout(300_000) });
    return { status: res.status, text: await res.text() };
  },
  log: (line) => process.stderr.write(`[${new Date().toISOString().slice(11, 19)}] ${line}\n`),
  onProgress: (r) => writeFileSync(`${base}.partial.json`, JSON.stringify(r, null, 2)),
};

const result = await runProbe(opts, deps);
writeFileSync(`${base}.json`, JSON.stringify(result, null, 2));
writeFileSync(`${base}.md`, renderMarkdown(result));
try {
  (await import("node:fs")).rmSync(`${base}.partial.json`, { force: true });
} catch {
  /* ignore */
}
process.stderr.write(`\n${renderMarkdown(result)}\nwrote ${base}.json and ${base}.md\n`);
process.exit(result.status === "failed" ? 1 : 0);
