/**
 * PlanPill
 * A readable plan-name pill for use in sidebar and inline contexts.
 * Accepts the raw firmPlan string (including legacy aliases) and renders
 * a human label with a consistent colour token.
 *
 * Colour scheme mirrors PlanBadge but at a slightly larger size and
 * rounded-full shape to read clearly as a standalone label.
 */

type FirmPlan =
  | "free"
  | "team"
  | "firm"
  | "trial"
  | "professional"
  | "leadership"
  | null
  | undefined;

interface PlanPillProps {
  plan: FirmPlan;
  /** "sm" (default) fits sidebar; "md" works inline in headers */
  size?: "sm" | "md";
}

function labelForPlan(plan: FirmPlan): string {
  if (plan === "team" || plan === "professional") return "Team";
  if (plan === "firm" || plan === "leadership") return "Firm";
  return "Free";
}

function classesForPlan(plan: FirmPlan): string {
  if (plan === "firm" || plan === "leadership")
    return "border-amber-300 bg-amber-50 text-amber-800";
  if (plan === "team" || plan === "professional")
    return "border-blue-300 bg-blue-50 text-blue-800";
  // free / trial / null / undefined
  return "border-neutral-300 bg-neutral-50 text-neutral-600";
}

const PlanPill = ({ plan, size = "sm" }: PlanPillProps) => {
  const sizeClass =
    size === "md"
      ? "px-2.5 py-0.5 text-xs"
      : "px-2 py-0.5 text-[11px]";

  return (
    <span
      className={[
        "inline-flex items-center rounded-full border font-semibold uppercase tracking-wide",
        sizeClass,
        classesForPlan(plan),
      ].join(" ")}
    >
      {labelForPlan(plan)}
    </span>
  );
};

export default PlanPill;
