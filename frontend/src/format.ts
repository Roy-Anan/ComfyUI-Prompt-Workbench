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
    default:
      return JSON.stringify(value);
  }
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
