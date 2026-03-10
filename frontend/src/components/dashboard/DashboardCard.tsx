import type { ReactNode } from "react";

/**
 * DashboardCard
 * General-purpose card shell for dashboard modules.
 *
 * Typography defaults (override via titleClassName / subtitleClassName props):
 *   title    → gov-type-h3  (15px / 600 / #0D1B2A)
 *   subtitle → gov-type-meta (12px / 400 / #9CA3AF)
 */
type DashboardCardProps = {
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  className?: string;
  titleClassName?: string;
  subtitleClassName?: string;
};

const DashboardCard = ({
  title,
  subtitle,
  children,
  className = "",
  titleClassName = "gov-type-h3",
  subtitleClassName = "gov-type-meta",
}: DashboardCardProps) => {
  return (
    <section className={`gov-card-surface rounded-xl border border-neutral-200 bg-white p-6 shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${className}`.trim()}>
      <div className="mb-3">
        <h3 className={titleClassName}>{title}</h3>
        {subtitle ? <p className={subtitleClassName}>{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
};

export default DashboardCard;
