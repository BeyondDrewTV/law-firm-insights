/**
 * SignalCard
 * Renders a single governance signal using the shared GovernanceCard pattern.
 *
 * Props map cleanly to GovernanceCard zones:
 *   title        → header title
 *   severity     → GovStatusChip + accent
 *   summary      → description line + frequency line
 *   meta         → previous count / trend (when available)
 *   actions      → "View Details" link + "Create Action" button
 *
 * Selection (Phase 6 — Evidence Triage):
 *   selected     → visually highlights the card with a teal ring
 *   onToggleSelect → called when the checkbox or card selection area is clicked
 *   selectionMode  → when true the card shows the checkbox affordance
 */

import type React from "react";
import { Link } from "react-router-dom";
import GovernanceCard, { type GovernanceCardAccent } from "./GovernanceCard";
import GovStatusChip, { type GovStatusChipVariant } from "./GovStatusChip";

export type SignalSeverity = "High" | "Medium" | "Low";

export type SignalCardProps = {
  id: string;
  title: string;
  severity: SignalSeverity;
  frequencyCount: number;
  shareLabel?: string | null;
  description: string;
  previousCount?: number | null;
  trendLabel?: string | null;
  onCreateAction?: () => void;
  // ── Selection props (optional — used in triage / bulk-select mode) ──
  selected?: boolean;
  onToggleSelect?: (id: string) => void;
  selectionMode?: boolean;
};

const severityToAccent: Record<SignalSeverity, GovernanceCardAccent> = {
  High:   "risk",
  Medium: "warn",
  Low:    "success",
};

const severityToChipVariant: Record<SignalSeverity, GovStatusChipVariant> = {
  High:   "risk",
  Medium: "warn",
  Low:    "success",
};

export default function SignalCard({
  id,
  title,
  severity,
  frequencyCount,
  shareLabel,
  description,
  previousCount,
  trendLabel,
  onCreateAction,
  selected = false,
  onToggleSelect,
  selectionMode = false,
}: SignalCardProps) {
  const metaItems: string[] = [];
  if (typeof previousCount === "number") {
    metaItems.push(`Prior cycle: ${previousCount}`);
  }
  if (trendLabel) {
    metaItems.push(trendLabel);
  }

  const summaryParts: string[] = [
    `Detected in ${frequencyCount} review${frequencyCount === 1 ? "" : "s"}`,
    shareLabel ?? "",
    description,
  ].filter(Boolean);
  const summary = summaryParts.join(" · ");

  const handleToggle = (e: React.MouseEvent | React.ChangeEvent<HTMLInputElement>) => {
    e.stopPropagation();
    onToggleSelect?.(id);
  };

  return (
    <div
      className={[
        "relative transition-all duration-150",
        selected
          ? "ring-2 ring-[#0EA5C2] ring-offset-2 rounded-[12px]"
          : selectionMode
            ? "ring-1 ring-transparent hover:ring-[#BAE6FD] hover:ring-offset-1 rounded-[12px] cursor-pointer"
            : "",
      ].join(" ")}
      onClick={selectionMode && onToggleSelect ? () => onToggleSelect(id) : undefined}
      role={selectionMode ? "button" : undefined}
      aria-pressed={selectionMode ? selected : undefined}
      tabIndex={selectionMode ? 0 : undefined}
      onKeyDown={
        selectionMode && onToggleSelect
          ? (e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); onToggleSelect(id); } }
          : undefined
      }
    >
      {/* Checkbox affordance — visible in selection mode */}
      {selectionMode ? (
        <div className="absolute left-3 top-3 z-10" onClick={(e) => e.stopPropagation()}>
          <input
            type="checkbox"
            checked={selected}
            onChange={handleToggle}
            aria-label={`Select signal: ${title}`}
            className="h-4 w-4 cursor-pointer rounded border-slate-300 accent-[#0EA5C2]"
          />
        </div>
      ) : null}

      <GovernanceCard
        title={title}
        accent={selected ? "none" : severityToAccent[severity]}
        chip={
          <GovStatusChip
            label={severity}
            variant={selected ? "info" : severityToChipVariant[severity]}
          />
        }
        summary={summary}
        meta={metaItems}
        className={selectionMode ? "pl-7" : undefined}
        actions={
          selectionMode ? (
            // In selection mode only show a compact "select / deselect" affordance
            // — primary action buttons live in the sticky selection bar
            <button
              type="button"
              className={[
                "text-[12px] font-medium transition-colors",
                selected
                  ? "text-[#0EA5C2] hover:text-[#0b8ca7]"
                  : "text-[#6B7280] hover:text-[#374151]",
              ].join(" ")}
              onClick={(e) => { e.stopPropagation(); onToggleSelect?.(id); }}
            >
              {selected ? "✓ Selected" : "Select"}
            </button>
          ) : (
            <>
              <Link
                to={`/dashboard/signals/${id}`}
                className="inline-flex items-center rounded-[6px] bg-[#0D1B2A] px-3 py-1.5 text-[12px] font-medium text-white transition-colors hover:bg-[#16263b]"
              >
                View details
              </Link>
              {onCreateAction ? (
                <button
                  type="button"
                  className="text-[12px] text-[#6B7280] underline underline-offset-4 transition-colors hover:text-[#374151]"
                  onClick={onCreateAction}
                >
                  Create action
                </button>
              ) : null}
            </>
          )
        }
      />
    </div>
  );
}
