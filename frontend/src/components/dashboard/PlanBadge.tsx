type FirmPlan = "free" | "team" | "firm" | "trial" | "professional" | "leadership" | null | undefined;

const labelForPlan = (plan: FirmPlan) => {
  if (plan === "free" || plan === "trial") return "Free";
  if (plan === "team" || plan === "professional") return "Team";
  if (plan === "firm" || plan === "leadership") return "Firm";
  return "Free";
};

const classForPlan = (plan: FirmPlan) => {
  if (plan === "firm" || plan === "leadership") return "border-amber-300 bg-amber-50 text-amber-800";
  if (plan === "team" || plan === "professional") return "border-blue-300 bg-blue-50 text-blue-800";
  if (plan === "free" || plan === "trial") return "border-neutral-300 bg-neutral-50 text-neutral-700";
  return "border-neutral-300 bg-neutral-50 text-neutral-700";
};

const PlanBadge = ({ plan }: { plan: FirmPlan }) => {
  return (
    <span
      className={[
        "inline-flex items-center rounded border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide",
        classForPlan(plan),
      ].join(" ")}
    >
      {labelForPlan(plan)}
    </span>
  );
};

export default PlanBadge;
