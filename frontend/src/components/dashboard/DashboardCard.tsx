import type { ReactNode } from "react";

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
  titleClassName = "section-title",
  subtitleClassName = "metric-label",
}: DashboardCardProps) => {
  return (
    <section className={`rounded-xl border border-neutral-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md ${className}`.trim()}>
      <div className="mb-3">
        <h3 className={titleClassName}>{title}</h3>
        {subtitle ? <p className={subtitleClassName}>{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
};

export default DashboardCard;
