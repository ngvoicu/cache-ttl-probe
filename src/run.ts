// The measurement loop: control round, prime every sample, check each exactly once at its age.

import { buildRequest, type Format, isWarm, readStreamUsage, readUsage, type Usage } from "./formats.ts";
import { makePrefix } from "./prefix.ts";
import { formatDuration, planSamples, type Sample, shouldStop } from "./schedule.ts";

export interface RunOptions {
  baseUrl: string;
  format: Format;
  model: string;
  ttl?: string;
  headers: Record<string, string>;
  bodyExtra?: Record<string, unknown>;
  ages: number[];
  replicas: number;
  maxOutput: number;
  stream: boolean;
  prefixTokens: number;
  runSalt: string;
  concurrency: number;
  label: string;
}

export interface SendResult {
  status: number;
  text: string;
}

export interface Deps {
  now: () => number;
  sleep: (ms: number) => Promise<void>;
  /** Performs one HTTP POST. Must never log the request headers (they carry the API key). */
  send: (url: string, headers: Record<string, string>, body: string) => Promise<SendResult>;
  log: (line: string) => void;
  /** Called after every check with the partial result, so long runs can be inspected. */
  onProgress?: (result: RunResult) => void;
}

export interface Check {
  sampleId: string;
  targetAgeMs: number;
  actualAgeMs: number;
  promptTokens: number;
  cachedTokens: number;
  warm: boolean;
}

export interface RunResult {
  probeVersion: string;
  label: string;
  baseUrl: string;
  format: Format;
  model: string;
  ttl?: string;
  runSalt: string;
  replicas: number;
  plannedAges: number[];
  startedAt: string;
  finishedAt?: string;
  control?: { prime: Usage; check: Usage; warm: boolean };
  status: "running" | "completed" | "stopped-early" | "no-observable-cache" | "failed";
  error?: string;
  checks: Check[];
}

export const PROBE_VERSION = "0.1.0";
const RETRY_DELAYS_MS = [2_000, 5_000, 15_000, 30_000];

export class HttpError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function retryable(err: unknown): boolean {
  if (err instanceof HttpError) return err.status === 408 || err.status === 429 || err.status >= 500;
  return true; // network errors
}

/** Sends one request for a prefix and returns its usage, retrying transient failures. */
async function call(o: RunOptions, deps: Deps, prefix: string): Promise<{ usage: Usage; startedAt: number }> {
  const req = buildRequest(o.format, {
    model: o.model,
    prefix,
    ttl: o.ttl,
    maxOutput: o.maxOutput,
    stream: o.stream,
    bodyExtra: o.bodyExtra,
  });
  const url = o.baseUrl.replace(/\/+$/, "") + req.path;
  const headers = { "content-type": "application/json", ...req.headers, ...o.headers };
  const body = JSON.stringify(req.body);
  for (let attempt = 0; ; attempt++) {
    const startedAt = deps.now();
    try {
      const res = await deps.send(url, headers, body);
      if (res.status < 200 || res.status >= 300) throw new HttpError(res.status, `HTTP ${res.status}: ${res.text.slice(0, 300)}`);
      let usage: Usage | undefined;
      if (o.stream) usage = readStreamUsage(o.format, res.text);
      else {
        try {
          usage = readUsage(o.format, JSON.parse(res.text));
        } catch {
          usage = readStreamUsage(o.format, res.text); // some proxies answer with SSE anyway
        }
      }
      if (!usage) throw new HttpError(502, `no usage in response: ${res.text.slice(0, 200)}`);
      return { usage, startedAt };
    } catch (err) {
      if (attempt >= RETRY_DELAYS_MS.length || !retryable(err)) throw err;
      deps.log(`  retry in ${RETRY_DELAYS_MS[attempt] / 1000}s: ${(err as Error).message}`);
      await deps.sleep(RETRY_DELAYS_MS[attempt]);
    }
  }
}

async function pool<T>(items: T[], limit: number, fn: (item: T) => Promise<void>): Promise<void> {
  let next = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) await fn(items[next++]);
  });
  await Promise.all(workers);
}

export async function runProbe(o: RunOptions, deps: Deps): Promise<RunResult> {
  const result: RunResult = {
    probeVersion: PROBE_VERSION,
    label: o.label,
    baseUrl: o.baseUrl,
    format: o.format,
    model: o.model,
    ttl: o.ttl,
    runSalt: o.runSalt,
    replicas: o.replicas,
    plannedAges: o.ages,
    startedAt: new Date(deps.now()).toISOString(),
    status: "running",
    checks: [],
  };
  const finish = (status: RunResult["status"], error?: string) => {
    result.status = status;
    if (error) result.error = error;
    result.finishedAt = new Date(deps.now()).toISOString();
    deps.onProgress?.(result);
    return result;
  };

  try {
    // Control: an immediate re-send must hit the cache, otherwise nothing below can be measured.
    deps.log(`control: ${o.label}`);
    const controlPrefix = makePrefix(o.runSalt, "control", o.prefixTokens);
    const prime = await call(o, deps, controlPrefix);
    let check: Usage | undefined;
    for (const wait of [3_000, 10_000]) {
      await deps.sleep(wait);
      check = (await call(o, deps, controlPrefix)).usage;
      if (isWarm(check)) break;
    }
    const warm = check !== undefined && isWarm(check);
    result.control = { prime: prime.usage, check: check as Usage, warm };
    deps.log(`  control ${warm ? "warm" : "COLD"} (cached ${check?.cachedTokens}/${check?.promptTokens})`);
    if (!warm) return finish("no-observable-cache", "an immediate re-send was not served from cache");

    // Prime every sample once.
    const samples = planSamples(o.ages, o.replicas);
    const primedAt = new Map<string, number>();
    deps.log(`priming ${samples.length} samples`);
    await pool(samples, o.concurrency, async (s) => {
      const { startedAt } = await call(o, deps, makePrefix(o.runSalt, s.id, o.prefixTokens));
      // Lifetimes count from the start of the request that wrote the entry.
      primedAt.set(s.id, startedAt);
    });
    deps.onProgress?.(result);

    // Check each sample exactly once, when it reaches its age.
    const due = samples
      .map((s) => ({ s, at: (primedAt.get(s.id) as number) + s.ageMs }))
      .sort((a, b) => a.at - b.at);
    const byAge = new Map<number, boolean[]>();
    for (const { s, at } of due) {
      if (shouldStop(o.ages, byAge, o.replicas)) {
        deps.log("two consecutive ages fully cold: stopping");
        return finish("stopped-early");
      }
      const wait = at - deps.now();
      if (wait > 0) await deps.sleep(wait);
      const { usage, startedAt } = await call(o, deps, makePrefix(o.runSalt, s.id, o.prefixTokens));
      const c: Check = {
        sampleId: s.id,
        targetAgeMs: s.ageMs,
        actualAgeMs: startedAt - (primedAt.get(s.id) as number),
        promptTokens: usage.promptTokens,
        cachedTokens: usage.cachedTokens,
        warm: isWarm(usage),
      };
      result.checks.push(c);
      const list = byAge.get(s.ageMs) ?? [];
      list.push(c.warm);
      byAge.set(s.ageMs, list);
      deps.log(`  ${formatDuration(s.ageMs)} r${s.replica}: ${c.warm ? "warm" : "cold"} (${c.cachedTokens}/${c.promptTokens})`);
      deps.onProgress?.(result);
    }
    return finish("completed");
  } catch (err) {
    return finish("failed", (err as Error).message);
  }
}

export type { Sample };
