export function formatFreshnessTimestamp(value: string | null | undefined): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatFreshnessLine(label: string, value: string | null | undefined): string {
  const formatted = formatFreshnessTimestamp(value);
  return `${label}: ${formatted ?? "Not available"}`;
}

