type SeverityValue = "HIGH" | "MEDIUM" | "LOW";

type SeverityBadgeProps = {
  severity: string | null | undefined;
  className?: string;
};

const normalizeSeverity = (severity: string | null | undefined): SeverityValue => {
  const normalized = (severity || "LOW").trim().toUpperCase();
  if (normalized === "HIGH") return "HIGH";
  if (normalized === "MEDIUM") return "MEDIUM";
  return "LOW";
};

const severityClassMap: Record<SeverityValue, string> = {
  HIGH: "bg-red-100 text-red-700",
  MEDIUM: "bg-yellow-100 text-yellow-700",
  LOW: "bg-green-100 text-green-700",
};

const SeverityBadge = ({ severity, className = "" }: SeverityBadgeProps) => {
  const normalizedSeverity = normalizeSeverity(severity);
  const badgeClasses = `inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ${severityClassMap[normalizedSeverity]} ${className}`.trim();

  return <span className={badgeClasses}>Severity: {normalizedSeverity}</span>;
};

export default SeverityBadge;
