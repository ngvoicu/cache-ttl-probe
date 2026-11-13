import assert from "node:assert/strict";
import { test } from "node:test";
import { agesFor, formatDuration, parseDuration, planSamples, shouldStop } from "../src/schedule.ts";

test("durations", () => {
  assert.equal(parseDuration("90s"), 90_000);
  assert.equal(parseDuration("2.5m"), 150_000);
  assert.equal(parseDuration("1h"), 3_600_000);
  assert.throws(() => parseDuration("5 minutes"));
  assert.equal(formatDuration(150_000), "2.5m");
  assert.equal(formatDuration(3_600_000), "1h");
});

test("schedules", () => {
  assert.equal(agesFor(undefined, undefined).length, 14);
  assert.equal(agesFor("long", undefined).at(-1), 12 * 3_600_000);
  // Custom ages are added to the start of the ladder: every evaluation checks at 2.5, 5 and 7.5 minutes.
  assert.deepEqual(agesFor("std", "30m,10m,10m"), [150_000, 300_000, 450_000, 600_000, 1_800_000]);
  assert.deepEqual(agesFor("std", "5m,1h"), [150_000, 300_000, 450_000, 3_600_000]);
  for (const name of ["std", "long", "quick"]) assert.deepEqual(agesFor(name, undefined).slice(0, 3), [150_000, 300_000, 450_000], name);
  assert.throws(() => agesFor("nope", undefined));
});

test("plan: one sample per age and replica, unique ids", () => {
  const s = planSamples([300_000, 600_000], 3);
  assert.equal(s.length, 6);
  assert.equal(new Set(s.map((x) => x.id)).size, 6);
});

test("stop after two consecutive fully cold ages", () => {
  const ages = [1, 2, 3, 4];
  const r = new Map<number, boolean[]>([[1, [true, true]], [2, [false, false]]]);
  assert.equal(shouldStop(ages, r, 2), false);
  r.set(3, [false, false]);
  assert.equal(shouldStop(ages, r, 2), true);
  const fuzzy = new Map<number, boolean[]>([[1, [false, false]], [2, [true, false]], [3, [false, false]]]);
  assert.equal(shouldStop(ages, fuzzy, 2), false, "a warm replica resets the run");
});

test("the harness probe has the same ladders", async () => {
  const { readFileSync } = await import("node:fs");
  const { SCHEDULES, LADDER_START } = await import("../src/schedule.ts");
  const source = readFileSync(new URL("../harness/probe.py", import.meta.url), "utf8");
  const list = (name: string): string[] => {
    const found = new RegExp(`^${name} = \\[(.*)\\]$`, "m").exec(source);
    assert.ok(found, `${name} is not in harness/probe.py`);
    return [...found[1].matchAll(/"([^"]+)"/g)].map((item) => item[1]);
  };
  assert.deepEqual(list("LADDER_START"), LADDER_START);
  assert.deepEqual([...list("LADDER_START"), ...list("STD_REST")], SCHEDULES.std);
  assert.deepEqual([...list("LADDER_START"), ...list("STD_REST"), ...list("LONG_REST")], SCHEDULES.long);
});
