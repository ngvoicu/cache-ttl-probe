// Prompt prefixes for cache probing.
//
// Every sample needs its own prefix: a cache entry's timer resets on each hit, so a prefix is primed once and
// checked once. The run salt goes first, so prefixes from earlier runs (or a smoke test a few minutes ago)
// can never match. Text is deterministic per (salt, sample) so a run can be reproduced.

const WORDS = (
  "amber anchor arch atlas badge basil beacon birch bison bloom brook cabin canal cedar chalk chord cider " +
  "cinder clover cobalt comet coral crane crest dawn delta dune ember fable fern fjord flint forge frost " +
  "garnet glade granite grove harbor hazel heron horizon indigo iris ivory jade juniper kelp kestrel lagoon " +
  "lantern larch ledger lilac linen lotus lumen maple marble meadow mesa mint moss nectar nimbus oak ochre " +
  "olive onyx opal orchid otter pebble pepper pine plume prairie quartz quill raven reed ridge river saffron " +
  "sage sable shale sienna slate sorrel spruce summit tamarind thistle tide timber topaz tundra umber velvet " +
  "vesper violet willow yarrow zephyr zinc"
).split(" ");

/** Roughly 4 characters per token for English-like text. */
export const CHARS_PER_TOKEN = 4;

function hash32(text: string): number {
  // FNV-1a
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A random-looking run salt; pass it explicitly to reproduce a run. */
export function newRunSalt(): string {
  return Math.random().toString(36).slice(2, 10);
}

/**
 * Builds the cacheable prefix for one sample: a header naming the run and sample, then filler sentences
 * until about `targetTokens` tokens.
 */
export function makePrefix(runSalt: string, sampleId: string, targetTokens = 2500): string {
  const rand = mulberry32(hash32(`${runSalt}/${sampleId}`));
  const targetChars = Math.max(1, targetTokens) * CHARS_PER_TOKEN;
  const parts: string[] = [
    `Cache probe run ${runSalt}, sample ${sampleId}. The text below is filler used to measure prompt-cache lifetime; ` +
      "it has no meaning. Answer the final question briefly.\n\n",
  ];
  let length = parts[0].length;
  let sentence = 0;
  while (length < targetChars) {
    const count = 8 + Math.floor(rand() * 10);
    const words: string[] = [];
    for (let i = 0; i < count; i++) words.push(WORDS[Math.floor(rand() * WORDS.length)]);
    const line = `${sentence + 1}. ${words.join(" ")}.\n`;
    parts.push(line);
    length += line.length;
    sentence++;
  }
  return parts.join("");
}
