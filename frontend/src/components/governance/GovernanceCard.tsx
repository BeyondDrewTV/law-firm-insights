/**
 * GovernanceCard
 * ─────────────────────────────────────────────────────────────────────────────
 * STANDARD CARD PATTERN FOR ALL GOVERNANCE OBJECTS (Signals, Actions, Briefs).
 *
 * Zone layout:
 *   ┌──────────────────────────────────────────────────────────┐
 *   │ [header]   title                        [status chip]   │  ← Header zone
 *   │ [summary]  brief impact / description line              │  ← Summary zone
 *   │ [meta]     owner · created · due date                   │  ← Meta zone
 *   │ [actions]  [action buttons]                             │  ← Action zone
 *   └──────────────────────────────────────────────────────────┘
 *
 * Typography classes used (see index.css gov-type-* block):
 *   title   → gov-type-h3      (15px / 600 / #0D1B2A)
 *   summary → gov-type-body    (14px / 400 / #334155)  ← via gov-body-sm alias
 *   meta    → gov-type-meta    (12px / 400 / #9CA3AF)
 *
 * Design rules:
 *   - Severity/status accent expressed as left border color only
 *   - No background color changes for severity — border only
 *   - Action row: text links and small buttons only (no primary CTA weight)
 *   - Use GovStatusChip for all status/severity chips
 *
 * Accent variants:
 *   "risk"    → red left border    (High severity, Overdue, Blocked)
 *   "warn"    → amber left border  (Medium severity, Escalation)
 *   "success" → green left border  (Low severity, Ready)
 *   "neutral" → slate left border  (default)
 * ─────────────────────────────────────────────────────────────────────────────
 */

import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export type GovernanceCardAccent = "risk" | "warn" | "success" | "neutral" | "none";

type GovernanceCardProps = {
  /** Primary title of the governance object */
  title: string;
  /** Optional link to make the title a navigable anchor */
  titleHref?: string;
  /** Status or severity chip — use GovStatusChip */
  chip?: ReactNode;
  /** One-line impact or summary */
  summary?: string;
  /** Meta items: owner, date, due date etc — rendered as pipe-separated row */
  meta?: string[];
  /** Left border accent — encodes severity/urgency */
  accent?: GovernanceCardAccent;
  /** Action buttons / links row */
  actions?: ReactNode;
  /** Optional expand/detail area (e.g. activity log) */
  detail?: ReactNode;
  className?: string;
};

const accentBorder: Record<GovernanceCardAccent, string> = {
  risk:    "border-l-[3px] border-l-[#EF4444]",
  warn:    "border-l-[3px] border-l-[#F59E0B]",
  success: "border-l-[3px] border-l-[#10B981]",
  neutral: "border-l-[3px] border-l-[#CBD5E1]",
  none:    "border-l-[3px] border-l-[#0EA5C2]",
};

export default function GovernanceCard({
  title,
  titleHref,
  chip,
  summary,
  meta,
  accent = "neutral",
  actions,
  detail,
  className = "",
}: GovernanceCardProps) {
  const metaItems = (meta || []).filter(Boolean);

  return (
    <article
      className={[
        "gov-card-surface rounded-[10px] border border-[#E5E7EB] bg-white px-5 py-[18px] shadow-[0_1px_3px_rgba(0,0,0,0.05)]",
        accentBorder[accent],
        className,
      ].join(" ")}
    >
      {/* ── Header: title + status chip ── */}
      <div className="flex items-start justify-between gap-3">
        {titleHref ? (
          <Link
            to={titleHref}
            className="gov-type-h3 min-w-0 flex-1 underline-offset-2 transition-colors duration-[150ms] hover:text-[#0D1B2A] hover:underline focus-visible:rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-[#0EA5C2] focus-visible:outline-offset-1"
          >
            {title}
          </Link>
        ) : (
          <h3 className="gov-type-h3 min-w-0 flex-1">{title}</h3>
        )}
        {chip ? <div className="shrink-0">{chip}</div> : null}
      </div>

      {/* ── Summary line ── */}
      {summary ? (
        <p className="gov-type-body mt-2">{summary}</p>
      ) : null}

      {/* ── Meta row ── */}
      {metaItems.length > 0 ? (
        <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1">
          {metaItems.map((item, index) => (
            <span key={`${item}-${index}`} className="flex items-center gap-2">
              {index > 0 ? <span className="text-[#D1D5DB]" aria-hidden>·</span> : null}
              <span className="gov-type-meta">{item}</span>
            </span>
          ))}
        </div>
      ) : null}

      {/* ── Expand / detail slot ── */}
      {detail ? <div className="mt-3">{detail}</div> : null}

      {/* ── Action row ── */}
      {actions ? (
        <div className="mt-4 flex flex-wrap items-center gap-3">
          {actions}
        </div>
      ) : null}
    </article>
  );
}
