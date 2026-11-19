// Readable summary formatting for structured rule values and comparison
// verdict values. Pure display only; it does not reinterpret the backend
// normalization or comparison verdict.

function dimension(pair: unknown): string {
  if (typeof pair !== "object" || pair === null) return String(pair);
  const record = pair as Record<string, unknown>;
  const width = record.width;
  const height = record.height;
  if (width !== undefined && height !== undefined) return `${width}×${height}`;
  return JSON.stringify(pair);
}

/**
 * Format a backend ``structured`` record (carrying a ``kind`` tag from
 * ``value_normalize``): value / range / floor / resolutions / list.
 * Unknown shapes fall back to their raw JSON so nothing is guessed.
 */
export function formatStructured(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value !== "object") return String(value);

  const record = value as Record<string, unknown>;
  switch (record.kind) {
    case "value":
      return String(record.value);
    case "range":
      return `${record.low}~${record.high}`;
    case "floor":
      return `≥${record.low}`;
    case "resolutions":
      return (Array.isArray(record.items) ? record.items : []).map(dimension).join(" / ");
    case "list":
      return (Array.isArray(record.items) ? record.items : []).map(String).join(" / ");
    case "sets":
      // Semicolon-separated suggestion groups; each group renders with its own
      // summary, joined by a semicolon. The first group is the specific set,
      // later groups are general fallbacks per the R73 priority call.
      return (Array.isArray(record.items) ? record.items : [])
        .map((item) => formatStructured(item))
        .join("；");
    default:
      return JSON.stringify(value);
  }
}

/**
 * Split a prompt text into comma/semicolon/newline separated fragments,
 * trimmed, de-duplicated and order-preserving. Pure display only.
 */
export function splitPromptFragments(text: string): string[] {
  const parts = text
    .split(/[,，;；\n]/)
    .map((part) => part.trim())
    .filter(Boolean);
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of parts) {
    if (!seen.has(part)) {
      seen.add(part);
      out.push(part);
    }
  }
  return out;
}

/** Count comma/semicolon/newline separated fragments in a prompt. */
export function countPromptFragments(text: string): number {
  return splitPromptFragments(text).length;
}

const CJK_CHAR =
  /[　-〿぀-ヿ㐀-䶿一-鿿가-힯]/g;
const ASCII_WORD = /[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+)*/g;

/**
 * Conservative dependency-free token estimate for a prompt. CJK characters
 * count as roughly one token each; ASCII words count as roughly 1.3 tokens
 * each. This is a rough read-only hint, not a tokenizer count.
 */
export function estimatePromptTokens(text: string): number {
  if (!text.trim()) return 0;
  const cjkChars = (text.match(CJK_CHAR) ?? []).length;
  const words = (text.match(ASCII_WORD) ?? []).length;
  return cjkChars + Math.ceil(words * 1.3);
}

export type FragmentDiff = {
  common: string[];
  onlySnapshot: string[];
  onlyCurrent: string[];
};

/**
 * Fragment-level read-only diff between a snapshot and the current text.
 * Matching fragments are shared; leftovers are listed on each side. No
 * synonym or similarity matching is attempted.
 */
export function diffFragments(snapshot: string, current: string): FragmentDiff {
  const a = splitPromptFragments(snapshot);
  const b = splitPromptFragments(current);
  const bSet = new Set(b);
  const aSet = new Set(a);
  return {
    common: a.filter((fragment) => bSet.has(fragment)),
    onlySnapshot: a.filter((fragment) => !bSet.has(fragment)),
    onlyCurrent: b.filter((fragment) => !aSet.has(fragment)),
  };
}

/**
 * Format a comparison verdict's extracted rule value. The verdict may hold
 * a plain number/string, a ``{low, high}`` range, a ``{floor}`` lower bound,
 * a resolution pair/array, or a plain list array. Anything unexpected keeps
 * its raw JSON.
 */
export function formatActual(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value !== "object") return String(value);

  if (Array.isArray(value)) {
    if (value.length > 0 && typeof value[0] === "object") {
      return value.map(dimension).join(" / ");
    }
    return value.map(String).join(" / ");
  }

  const record = value as Record<string, unknown>;
  if (record.low !== undefined && record.high !== undefined) {
    return `${record.low}~${record.high}`;
  }
  if (record.floor !== undefined) return `≥${record.floor}`;
  if (record.width !== undefined && record.height !== undefined) {
    return dimension(record);
  }
  return JSON.stringify(value);
}
