import type { ReactNode } from "react";

type GovStatCardProps = {
  label: string;
  value: ReactNode;
  subtitle?: ReactNode;
  icon?: ReactNode;
  className?: string;
};

const GovStatCard = ({ label, value, subtitle, icon, className = "" }: GovStatCardProps) => {
  return (
    <article className={["gov-level-2-soft px-4 py-3", className].join(" ")} style={{ borderLeftWidth: 5, borderLeftColor: "#64748b" }}>
      <div className="flex items-start justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">{label}</span>
        {icon ? <span className="text-neutral-600">{icon}</span> : null}
      </div>
      <p className="mt-1 text-2xl font-bold text-neutral-900">{value}</p>
      {subtitle ? <p className="mt-1 text-xs text-neutral-700">{subtitle}</p> : null}
    </article>
  );
};

export default GovStatCard;
