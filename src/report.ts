// Survival summary and Markdown rendering.

import type { RunResult } from "./run.ts";
import { formatDuration } from "./schedule.ts";

export interface AgeRow {
  ageMs: number;
  warm: number;
  total: number;
}

export interface Summary {
  rows: AgeRow[];
  /** Longest age where every replica was warm, with no miss at any shorter age. */
  lastAllWarmMs?: number;
  /** Shortest age with at least one cold replica. */
  firstMissMs?: number;
  /** Shortest age where every replica was cold. */
  allColdMs?: number;
}

export function summarize(result: RunResult): Summary {
  const byAge = new Map<number, AgeRow>();
  for (const c of result.checks) {
    const row = byAge.get(c.targetAgeMs) ?? { ageMs: c.targetAgeMs, warm: 0, total: 0 };
    row.total++;
    if (c.warm) row.warm++;
    byAge.set(c.targetAgeMs, row);
  }
  const rows = [...byAge.values()].sort((a, b) => a.ageMs - b.ageMs);
  const s: Summary = { rows };
  for (const r of rows) {
    if (s.firstMissMs === undefined && r.warm < r.total) s.firstMissMs = r.ageMs;
    if (s.firstMissMs === undefined && r.warm === r.total) s.lastAllWarmMs = r.ageMs;
    if (s.allColdMs === undefined && r.warm === 0) s.allColdMs = r.ageMs;
  }
  return s;
}

/** "5m–10m": last all-warm age to first fully cold age. */
export function bracket(s: Summary): string {
  if (!s.rows.length) return "no checks";
  const lo = s.lastAllWarmMs !== undefined ? formatDuration(s.lastAllWarmMs) : "<" + formatDuration(s.rows[0].ageMs);
  if (s.allColdMs === undefined) return `≥ ${formatDuration(s.rows[s.rows.length - 1].ageMs)} (never fully cold; warm through ${lo})`;
  return `${lo} – ${formatDuration(s.allColdMs)}`;
}

export function renderMarkdown(result: RunResult): string {
  const s = summarize(result);
  const lines = [
    `# ${result.label}`,
    "",
    `- Endpoint: \`${result.baseUrl}\` · format \`${result.format}\` · model \`${result.model}\`${result.ttl ? ` · ttl \`${result.ttl}\`` : ""}`,
    `- Started ${result.startedAt}${result.finishedAt ? `, finished ${result.finishedAt}` : ""} · status **${result.status}**${result.error ? ` (${result.error})` : ""}`,
    `- Probe ${result.probeVersion} · run salt \`${result.runSalt}\` · ${result.replicas} replicas per age`,
  ];
  if (result.control) {
    lines.push(
      `- Control: prime ${result.control.prime.cachedTokens}/${result.control.prime.promptTokens} cached, ` +
        `re-send ${result.control.check.cachedTokens}/${result.control.check.promptTokens} → ${result.control.warm ? "warm" : "cold"}`,
    );
  }
  lines.push("", `**Lifetime: ${bracket(s)}**`, "", "| Age | Warm | Checks |", "|---|---|---|");
  for (const r of s.rows) lines.push(`| ${formatDuration(r.ageMs)} | ${r.warm} | ${r.total} |`);
  return lines.join("\n") + "\n";
}
