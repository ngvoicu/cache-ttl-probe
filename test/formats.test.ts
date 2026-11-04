import assert from "node:assert/strict";
import { test } from "node:test";
import { buildRequest, isWarm, readStreamUsage, readUsage } from "../src/formats.ts";

const base = { model: "m", prefix: "P", maxOutput: 16, stream: false };

test("chat request", () => {
  const r = buildRequest("chat", base);
  assert.equal(r.path, "/chat/completions");
  assert.equal((r.body.messages as any[])[0].content, "P");
  assert.equal(r.body.max_tokens, 16);
});

test("responses request: max_output_tokens >= 16, marker only with ttl", () => {
  const r = buildRequest("responses", { ...base, maxOutput: 1 });
  assert.equal(r.path, "/responses");
  assert.equal(r.body.max_output_tokens, 16);
  const part = (r.body.input as any[])[0].content[0];
  assert.equal(part.cache_control, undefined);
  const t = buildRequest("responses", { ...base, ttl: "1h" });
  assert.deepEqual((t.body.input as any[])[0].content[0].cache_control, { type: "ephemeral", ttl: "1h" });
});

test("messages request marks the prefix, ttl optional, body extra merged", () => {
  const r = buildRequest("messages", { ...base, bodyExtra: { metadata: { x: 1 } } });
  assert.equal(r.headers["anthropic-version"], "2023-06-01");
  assert.deepEqual((r.body.system as any[])[0].cache_control, { type: "ephemeral" });
  assert.deepEqual(r.body.metadata, { x: 1 });
  const t = buildRequest("messages", { ...base, ttl: "1h" });
  assert.deepEqual((t.body.system as any[])[0].cache_control, { type: "ephemeral", ttl: "1h" });
});

test("usage: chat (OpenAI and DeepSeek fields)", () => {
  assert.deepEqual(readUsage("chat", { usage: { prompt_tokens: 3000, prompt_tokens_details: { cached_tokens: 2900 } } }), { promptTokens: 3000, cachedTokens: 2900 });
  assert.deepEqual(readUsage("chat", { usage: { prompt_tokens: 3000, prompt_cache_hit_tokens: 2800 } }), { promptTokens: 3000, cachedTokens: 2800 });
  assert.deepEqual(readUsage("chat", { usage: { prompt_tokens: 3000 } }), { promptTokens: 3000, cachedTokens: 0 }, "missing field = 0");
});

test("usage: responses and messages", () => {
  assert.deepEqual(readUsage("responses", { usage: { input_tokens: 2600, input_tokens_details: { cached_tokens: 2560 } } }), { promptTokens: 2600, cachedTokens: 2560 });
  assert.deepEqual(readUsage("messages", { usage: { input_tokens: 20, cache_read_input_tokens: 2580, cache_creation_input_tokens: 0 } }), { promptTokens: 2600, cachedTokens: 2580 });
  // CPA may answer a Responses request with Anthropic-style usage fields
  assert.deepEqual(readUsage("responses", { usage: { input_tokens: 20, cache_creation_input_tokens: 2580 } }), { promptTokens: 2600, cachedTokens: 0 });
  assert.equal(readUsage("chat", { choices: [] }), undefined);
});

test("stream usage: Anthropic split events and Responses completed event", () => {
  const anthropic = [
    'data: {"type":"message_start","message":{"usage":{"input_tokens":10,"cache_read_input_tokens":2590}}}',
    'data: {"type":"message_delta","usage":{"output_tokens":3}}',
    "data: [DONE]",
  ].join("\n");
  assert.deepEqual(readStreamUsage("messages", anthropic), { promptTokens: 2600, cachedTokens: 2590 });
  const responses = 'event: response.completed\ndata: {"type":"response.completed","response":{"usage":{"input_tokens":2600,"input_tokens_details":{"cached_tokens":2048}}}}\n';
  assert.deepEqual(readStreamUsage("responses", responses), { promptTokens: 2600, cachedTokens: 2048 });
});

test("warm rule: half the prompt and at least 500 tokens", () => {
  assert.equal(isWarm({ promptTokens: 2600, cachedTokens: 2560 }), true);
  assert.equal(isWarm({ promptTokens: 2600, cachedTokens: 1000 }), false);
  assert.equal(isWarm({ promptTokens: 800, cachedTokens: 450 }), false);
  assert.equal(isWarm({ promptTokens: 0, cachedTokens: 0 }), false);
});
