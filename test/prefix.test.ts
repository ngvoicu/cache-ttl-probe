import assert from "node:assert/strict";
import { test } from "node:test";
import { CHARS_PER_TOKEN, makePrefix } from "../src/prefix.ts";

test("prefix is deterministic per salt and sample", () => {
  assert.equal(makePrefix("s1", "a"), makePrefix("s1", "a"));
});

test("different samples and different salts never share a start", () => {
  const a = makePrefix("s1", "5m-r1");
  const b = makePrefix("s1", "5m-r2");
  const c = makePrefix("s2", "5m-r1");
  assert.notEqual(a.slice(0, 60), b.slice(0, 60));
  assert.notEqual(a.slice(0, 60), c.slice(0, 60));
  assert.ok(a.startsWith("Cache probe run s1, sample 5m-r1."));
});

test("prefix reaches the requested size", () => {
  const p = makePrefix("s", "x", 2500);
  assert.ok(p.length >= 2500 * CHARS_PER_TOKEN);
  assert.ok(p.length < 2500 * CHARS_PER_TOKEN + 200);
});
