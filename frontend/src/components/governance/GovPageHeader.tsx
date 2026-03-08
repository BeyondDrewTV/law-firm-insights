import type { ReactNode } from "react";

type GovPageHeaderProps = {
  title: string;
  subtitle?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

const GovPageHeader = ({ title, subtitle, actions, className = "" }: GovPageHeaderProps) => {
  return (
    <header className={["flex flex-col gap-3 md:flex-row md:items-start md:justify-between", className].join(" ")}>
      <div>
        <h1 className="gov-h1 mb-2">{title}</h1>
        {subtitle ? <p className="text-sm text-neutral-700">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
};

export default GovPageHeader;
