type DateInput = Date | string | number;

const ISO_DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

function isValidDate(value: Date): boolean {
  return Number.isFinite(value.getTime());
}

function normalizeDateString(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return trimmed;

  // Normalize "YYYY-MM-DD HH:mm:ss" to ISO-like format
  return trimmed.replace(
    /^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?)(.*)$/,
    "$1T$2$3",
  );
}

export function safeParseDate(input: unknown): Date | null {
  if (input instanceof Date) {
    return isValidDate(input) ? new Date(input.getTime()) : null;
  }

  if (typeof input === "number") {
    const parsed = new Date(input);
    return isValidDate(parsed) ? parsed : null;
  }

  if (typeof input === "string") {
    const normalized = normalizeDateString(input);
    if (!normalized) return null;

    if (ISO_DATE_ONLY_RE.test(normalized)) {
      const [y, m, d] = normalized.split("-").map((part) => Number(part));
      const parsed = new Date(y, m - 1, d, 12, 0, 0, 0);
      return isValidDate(parsed) ? parsed : null;
    }

    const parsed = new Date(normalized);
    return isValidDate(parsed) ? parsed : null;
  }

  return null;
}

export function toIsoDate(input: DateInput): string {
  const parsed = safeParseDate(input);
  if (!parsed) return "";
  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, "0");
  const day = String(parsed.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function formatDate(input: DateInput): string {
  const parsed = safeParseDate(input);
  if (!parsed) return "";
  return parsed.toLocaleDateString(undefined, {
    month: "short",
    day: "2-digit",
    year: "numeric",
  });
}

export function formatDateTime(input: DateInput): string {
  const parsed = safeParseDate(input);
  if (!parsed) return "";
  return parsed.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
}

// Backward-compatible wrappers used throughout the app
export function parseApiDate(value: string | null | undefined): Date | null {
  return safeParseDate(value);
}

export function toApiTimestamp(value: string | null | undefined): number | null {
  const parsed = safeParseDate(value);
  return parsed ? parsed.getTime() : null;
}

export function formatApiDate(
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  fallback = "No date",
): string {
  const parsed = safeParseDate(value);
  if (!parsed) return value || fallback;
  return parsed.toLocaleDateString(undefined, options);
}

export function formatApiDateTime(
  value: string | null | undefined,
  options?: Intl.DateTimeFormatOptions,
  fallback = "No date",
): string {
  const parsed = safeParseDate(value);
  if (!parsed) return value || fallback;
  return parsed.toLocaleString(undefined, options);
}
