/**
 * Parse a backend timestamp string safely as UTC when no explicit timezone
 * designator ('Z' or '+/-HH:MM' / '+/-HHMM') is present.
 * Preserves backward compatibility with legacy naive ISO strings while
 * handling ISO 8601 UTC strings ending in 'Z' or explicit offsets cleanly.
 */
export function parseUtcTimestamp(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }

  const trimmed = String(value).trim();
  if (!trimmed) return null;

  let normalized = trimmed.replace(" ", "T");

  const hasTimePart = normalized.includes("T");
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(normalized);
  if (hasTimePart && !hasTimezone) {
    normalized = `${normalized}Z`;
  }

  const parsed = new Date(normalized);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function formatLocalTime(
  value: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  locale?: string
): string {
  const date = parseUtcTimestamp(value);
  if (!date) return "Never";
  return date.toLocaleTimeString(locale, options);
}

export function formatLocalDateTime(
  value: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  locale?: string
): string {
  const date = parseUtcTimestamp(value);
  if (!date) return "Never";
  return date.toLocaleString(locale, options);
}

export function formatLocalDate(
  value: string | Date | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  locale?: string
): string {
  const date = parseUtcTimestamp(value);
  if (!date) return "Never";
  return date.toLocaleDateString(locale, options);
}
