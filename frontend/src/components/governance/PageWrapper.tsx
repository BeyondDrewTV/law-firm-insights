import type { ReactNode } from "react";

/**
 * PageWrapper
 * Standard page shell for all app-level governance pages.
 *
 * Typography:
 *   eyebrow     → workspace-shell-eyebrow  (11px / 700 / uppercase — legacy class, same as gov-type-eyebrow)
 *   title (h1)  → gov-type-h1              (24px / 700 / #0D1B2A)
 *   description → gov-type-body            (14px / 400 / #334155)
 */
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
    <section
      className="gov-page-shell"
      style={{
        padding: "var(--space-page-y) var(--space-page-x)",
      }}
    >
      <div
        className="mx-auto w-full"
        style={{ maxWidth: "var(--content-max-w)" }}
      >
        {/* Page header */}
        <header
          className="workspace-shell-header flex flex-wrap items-start justify-between"
          style={{ gap: "var(--space-content)", marginBottom: "var(--space-section)" }}
        >
          <div className="max-w-3xl">
            {eyebrow ? <p className="gov-type-eyebrow mb-2">{eyebrow}</p> : null}
            <h1 className="gov-type-h1">{title}</h1>
            {description ? (
              <p className="gov-type-body mt-2">{description}</p>
            ) : null}
          </div>
          {actions ? (
            <div className="flex flex-wrap items-center gap-2 pt-1">{actions}</div>
          ) : null}
        </header>

        {/* Page content */}
        <div
          className={contentClassName}
          style={{ display: "flex", flexDirection: "column", gap: "var(--space-section)" }}
        >
          {children}
        </div>
      </div>
    </section>
  );
};

export default PageWrapper;
