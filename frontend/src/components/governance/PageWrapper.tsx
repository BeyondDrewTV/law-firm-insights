import type { ReactNode } from "react";

type PageWrapperProps = {
  title: string;
  description?: string;
  eyebrow?: string;
  actions?: ReactNode;
  children: ReactNode;
  contentClassName?: string;
};

const PageWrapper = ({ title, description, eyebrow, actions, children, contentClassName = "" }: PageWrapperProps) => {
  return (
    <section className="px-8 py-8">
      <div className="mx-auto w-full max-w-[1200px] space-y-8">
        <header className="workspace-shell-header flex flex-wrap items-start justify-between gap-5">
          <div className="max-w-3xl">
            {eyebrow ? <p className="workspace-shell-eyebrow">{eyebrow}</p> : null}
            <h1 className="text-2xl font-semibold text-neutral-900">{title}</h1>
            {description ? <p className="workspace-shell-description mt-2 text-sm text-neutral-700">{description}</p> : null}
          </div>
          {actions ? <div className="flex flex-wrap items-center gap-2 pt-1">{actions}</div> : null}
        </header>
        <div className={`space-y-8 ${contentClassName}`.trim()}>{children}</div>
      </div>
    </section>
  );
};

export default PageWrapper;
