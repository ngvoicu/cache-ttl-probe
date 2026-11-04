// Check ages and sample planning.

const UNIT_MS: Record<string, number> = { ms: 1, s: 1_000, m: 60_000, h: 3_600_000 };

/** Parses "90s", "2.5m", "1h", "1500ms" into milliseconds. */
export function parseDuration(text: string): number {
  const m = /^\s*(\d+(?:\.\d+)?)\s*(ms|s|m|h)\s*$/.exec(text);
  if (!m) throw new Error(`invalid duration "${text}" (use e.g. 90s, 2.5m, 1h)`);
  return Math.round(Number(m[1]) * UNIT_MS[m[2]]);
}

export function formatDuration(ms: number): string {
  if (ms % 3_600_000 === 0) return `${ms / 3_600_000}h`;
  if (ms % 60_000 === 0) return `${ms / 60_000}m`;
  if (ms >= 60_000) return `${(ms / 60_000).toFixed(1)}m`;
  return `${Math.round(ms / 1000)}s`;
}

const STD = ["2.5m", "5m", "7.5m", "10m", "15m", "20m", "25m", "30m", "40m", "50m", "60m", "75m", "90m", "120m"];
export const SCHEDULES: Record<string, string[]> = {
  std: STD,
  long: [...STD, "4h", "8h", "12h"],
  quick: ["5m", "7.5m", "10m"],
};

export function agesFor(schedule: string | undefined, custom: string | undefined): number[] {
  const list = custom ? custom.split(",") : SCHEDULES[schedule ?? "std"];
  if (!list) throw new Error(`unknown schedule "${schedule}" (std, long, quick)`);
  const ages = [...new Set(list.map(parseDuration))].sort((a, b) => a - b);
  if (!ages.length || ages[0] <= 0) throw new Error("ages must be positive");
  return ages;
}

export interface Sample {
  id: string;
  /** Planned age at check time. */
  ageMs: number;
  replica: number;
}

/** One sample per (age, replica). All are primed up front, each is checked once at its age. */
export function planSamples(ages: number[], replicas: number): Sample[] {
  const out: Sample[] = [];
  for (const ageMs of ages) {
    for (let r = 1; r <= replicas; r++) out.push({ id: `${formatDuration(ageMs)}-r${r}`, ageMs, replica: r });
  }
  return out;
}

/**
 * Stop rule: once two consecutive ages are fully cold, longer ages are not worth checking.
 * `results` maps age → warm flags of the checks done so far at that age.
 */
export function shouldStop(ages: number[], results: Map<number, boolean[]>, replicas: number): boolean {
  let coldRun = 0;
  for (const age of ages) {
    const r = results.get(age);
    if (!r || r.length < replicas) return false; // an earlier age is still incomplete (errors count as done)
    coldRun = r.every((w) => !w) ? coldRun + 1 : 0;
    if (coldRun >= 2) return true;
  }
  return false;
}
