// Request builders and usage readers for the three wire formats.

export type Format = "chat" | "responses" | "messages";
export const FORMATS: readonly Format[] = ["chat", "responses", "messages"];

export interface BuildOptions {
  model: string;
  prefix: string;
  /** Explicit cache lifetime for an Anthropic-style marker, e.g. "5m" or "1h". */
  ttl?: string;
  /** Max output tokens. OpenAI's Responses API requires at least 16. */
  maxOutput: number;
  stream: boolean;
  /** Extra top-level body fields, merged last (e.g. {"prompt_cache_options": {"ttl": "12h"}}). */
  bodyExtra?: Record<string, unknown>;
}

export interface ProbeRequest {
  path: string;
  headers: Record<string, string>;
  body: Record<string, unknown>;
}

export interface Usage {
  /** All prompt tokens of the request: uncached + cache reads + cache writes. */
  promptTokens: number;
  /** Prompt tokens served from cache. A missing field counts as 0. */
  cachedTokens: number;
}

const QUESTION = "Reply with the single word OK.";

function cacheControl(ttl?: string): Record<string, string> {
  return ttl ? { type: "ephemeral", ttl } : { type: "ephemeral" };
}

export function buildRequest(format: Format, o: BuildOptions): ProbeRequest {
  let req: ProbeRequest;
  switch (format) {
    case "chat":
      req = {
        path: "/chat/completions",
        headers: {},
        body: {
          model: o.model,
          messages: [
            { role: "system", content: o.prefix },
            { role: "user", content: QUESTION },
          ],
          max_tokens: o.maxOutput,
          stream: o.stream,
          ...(o.stream ? { stream_options: { include_usage: true } } : {}),
        },
      };
      break;
    case "responses": {
      // A part-level cache_control is what CLIProxyAPI's Responses→Claude translator carries over; other
      // upstreams ignore or strip it. Only sent when a ttl is requested.
      const prefixPart: Record<string, unknown> = { type: "input_text", text: o.prefix };
      if (o.ttl) prefixPart.cache_control = cacheControl(o.ttl);
      req = {
        path: "/responses",
        headers: {},
        body: {
          model: o.model,
          input: [
            { role: "developer", content: [prefixPart] },
            { role: "user", content: [{ type: "input_text", text: QUESTION }] },
          ],
          max_output_tokens: Math.max(16, o.maxOutput),
          store: false,
          stream: o.stream,
        },
      };
      break;
    }
    case "messages":
      req = {
        path: "/messages",
        headers: { "anthropic-version": "2023-06-01" },
        body: {
          model: o.model,
          max_tokens: o.maxOutput,
          stream: o.stream,
          // Anthropic caches only marked content: mark the prefix block.
          system: [{ type: "text", text: o.prefix, cache_control: cacheControl(o.ttl) }],
          messages: [{ role: "user", content: QUESTION }],
        },
      };
      break;
  }
  if (o.bodyExtra) Object.assign(req.body, o.bodyExtra);
  return req;
}

function num(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function obj(value: unknown): Record<string, unknown> | undefined {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : undefined;
}

/** Reads token usage from a non-streaming response body (or the usage object of a stream). */
export function readUsage(format: Format, payload: unknown): Usage | undefined {
  const root = obj(payload);
  if (!root) return undefined;
  // Responses wraps usage in `response` on stream events; chat/messages put it at the top.
  const usage = obj(root.usage) ?? obj(obj(root.response)?.usage) ?? obj(obj(root.message)?.usage);
  if (!usage) return undefined;
  return usageFromObject(format, usage);
}

export function usageFromObject(format: Format, usage: Record<string, unknown>): Usage {
  if (format === "messages" || "cache_read_input_tokens" in usage || "cache_creation_input_tokens" in usage) {
    const read = num(usage.cache_read_input_tokens);
    const write = num(usage.cache_creation_input_tokens);
    const input = num(usage.input_tokens);
    return { promptTokens: input + read + write, cachedTokens: read };
  }
  if (format === "responses" || "input_tokens" in usage) {
    return {
      promptTokens: num(usage.input_tokens),
      cachedTokens: num(obj(usage.input_tokens_details)?.cached_tokens),
    };
  }
  return {
    promptTokens: num(usage.prompt_tokens),
    cachedTokens: num(obj(usage.prompt_tokens_details)?.cached_tokens) || num(usage.prompt_cache_hit_tokens),
  };
}

/**
 * Reads usage from a server-sent-event stream body. Keeps the most complete usage seen: Anthropic splits it
 * across message_start (input/cache) and message_delta (output), Responses sends it on response.completed,
 * Chat Completions on the final chunk.
 */
export function readStreamUsage(format: Format, sse: string): Usage | undefined {
  let best: Usage | undefined;
  for (const line of sse.split(/\r?\n/)) {
    if (!line.startsWith("data:")) continue;
    const data = line.slice(5).trim();
    if (!data || data === "[DONE]") continue;
    let event: unknown;
    try {
      event = JSON.parse(data);
    } catch {
      continue;
    }
    const usage = readUsage(format, event);
    if (usage && (!best || usage.promptTokens >= best.promptTokens)) best = usage;
  }
  return best;
}

/** A check is warm when at least half the prompt, and at least `minTokens`, came from cache. */
export function isWarm(u: Usage, fraction = 0.5, minTokens = 500): boolean {
  return u.promptTokens > 0 && u.cachedTokens >= fraction * u.promptTokens && u.cachedTokens >= minTokens;
}
