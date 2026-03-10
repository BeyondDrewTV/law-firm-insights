/**
 * GovernanceEmptyState
 * ─────────────────────────────────────────────────────────────────────────────
 * Lightweight, governance-aligned empty state for list views and tab panels.
 *
 * Design:
 *   - Borderless interior layout, intended to sit inside an already-bordered
 *     card or section container (no double borders).
 *   - Optional icon slot (pass a Lucide icon element).
 *   - Title uses gov-type-h3 (card-weight, not a page-level heading).
 *   - Body uses gov-type-body.
 *   - Optional primary action (Button or Link) and a ghost/secondary action.
 *   - Three size variants: sm (in-panel), md (default), lg (full-page section).
 *
 * Usage:
 *   <GovernanceEmptyState
 *     title="No triage signals"
 *     description="All current signals are medium or low severity."
 *     primaryAction={{ label: "View all signals", onClick: () => setTab("all") }}
 *     secondaryAction={{ label: "Return to dashboard", href: "/dashboard" }}
 *   />
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export type GovernanceEmptyAction = {
  label: string;
  href?: string;
  onClick?: () => void;
};

type GovernanceEmptyStateProps = {
  /** Short factual title — what is absent */
  title: string;
  /** One or two sentences directing the partner to the next step */
  description?: string;
  /** Optional Lucide icon element, e.g. <FileText size={20} /> */
  icon?: ReactNode;
  /** Primary CTA — button or link */
  primaryAction?: GovernanceEmptyAction;
  /** Secondary / ghost CTA */
  secondaryAction?: GovernanceEmptyAction;
  /** Additional content below the CTAs (rare — use sparingly) */
  footer?: ReactNode;
  /** Layout size: sm = compact in-card, md = default, lg = full-section */
  size?: "sm" | "md" | "lg";
  className?: string;
};

const paddingBySize = {
  sm: "py-6 px-4",
  md: "py-10 px-6",
  lg: "py-16 px-8",
} as const;

function ActionButton({ action, primary }: { action: GovernanceEmptyAction; primary: boolean }) {
  const baseClass = primary
    ? "inline-flex items-center justify-center rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#16263b] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5C2] focus-visible:ring-offset-2"
    : "inline-flex items-center justify-center rounded-[8px] border border-[#D1D5DB] bg-white px-4 py-2 text-sm font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5C2] focus-visible:ring-offset-2";

  if (action.href) {
    return <Link to={action.href} className={baseClass}>{action.label}</Link>;
  }
  return (
    <button type="button" className={baseClass} onClick={action.onClick}>
      {action.label}
    </button>
  );
}

export default function GovernanceEmptyState({
  title,
  description,
  icon,
  primaryAction,
  secondaryAction,
  footer,
  size = "md",
  className = "",
}: GovernanceEmptyStateProps) {
  const padding = paddingBySize[size];

  return (
    <div className={`flex flex-col items-center justify-center text-center ${padding} ${className}`}>
      {/* Icon */}
      {icon ? (
        <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-500">
          {icon}
        </div>
      ) : null}

      {/* Title */}
      <h3 className="gov-type-h3 max-w-xs">{title}</h3>

      {/* Description */}
      {description ? (
        <p className="gov-type-body mx-auto mt-2 max-w-sm">{description}</p>
      ) : null}

      {/* Actions */}
      {(primaryAction || secondaryAction) ? (
        <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
          {primaryAction ? <ActionButton action={primaryAction} primary /> : null}
          {secondaryAction ? <ActionButton action={secondaryAction} primary={false} /> : null}
        </div>
      ) : null}

      {/* Footer slot */}
      {footer ? (
        <div className="mt-3">{footer}</div>
      ) : null}
    </div>
  );
}
