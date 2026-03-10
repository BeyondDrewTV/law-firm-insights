/**
 * UploadUsageBar
 * Sidebar component for the Upload page that shows:
 *  - PlanPill (styled plan name)
 *  - Progress bar: "X of Y briefs used this month"
 *  - Reset date line
 *  - Amber callout at ≥ 80 % of cap (near-cap)
 *  - Red callout + upgrade CTA at 100 % / noReportCredits (at-cap)
 *
 * All data comes from props so the parent (Upload.tsx) keeps owning
 * the credits/plan state — no new API calls here.
 */

import { Link } from "react-router-dom";
import PlanPill from "@/components/billing/PlanPill";

type FirmPlan =
  | "free"
  | "team"
  | "firm"
  | "trial"
  | "professional"
  | "leadership"
  | null
  | undefined;

interface UploadUsageBarProps {
  firmPlan: FirmPlan;
  /** Reports consumed this calendar month */
  used: number;
  /** Monthly cap from plan limits (null = unlimited / subscription) */
  cap: number | null;
  /** True when the user has an active paid subscription (unlimited reports) */
  isSubscription: boolean;
  /** Human-readable reset date string, e.g. "April 1, 2026" */
  resetLabel: string;
  /** Still fetching credits/plan */
  isLoading: boolean;
}

/** Returns 0–100, clamped. Returns 0 for unlimited plans. */
function usagePct(used: number, cap: number | null): number {
  if (!cap) return 0;
  return Math.min(Math.round((used / cap) * 100), 100);
}

const UploadUsageBar = ({
  firmPlan,
  used,
  cap,
  isSubscription,
  resetLabel,
  isLoading,
}: UploadUsageBarProps) => {
  const pct = usagePct(used, cap);
  const atCap = !isSubscription && cap !== null && used >= cap;
  const nearCap = !atCap && !isSubscription && cap !== null && pct >= 80;

  // Determine which upgrade target to show based on current plan
  const isTeam = firmPlan === "team" || firmPlan === "professional";
  const upgradePlan = isTeam ? "firm" : "team";
  const upgradeLabel = isTeam ? "Firm" : "Team";
  const upgradeReports = isTeam ? "Unlimited" : "10";
  const upgradePath = `/pricing?intent=${upgradePlan}`;

  if (isLoading) {
    return (
      <div className="space-y-2 animate-pulse">
        <div className="h-3 w-16 rounded bg-neutral-100" />
        <div className="h-1.5 w-full rounded-full bg-neutral-100" />
        <div className="h-3 w-32 rounded bg-neutral-100" />
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Plan pill row */}
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-neutral-700">Your plan</span>
        <PlanPill plan={firmPlan} />
      </div>

      {/* Progress block — hidden for unlimited subscriptions */}
      {isSubscription ? (
        <div className="rounded border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-700">
          <span className="font-semibold text-neutral-900">Reports:</span> Unlimited (subscription)
        </div>
      ) : cap !== null ? (
        <div className="space-y-1.5">
          {/* Label row */}
          <div className="flex items-center justify-between text-xs text-neutral-700">
            <span>
              <span className="font-semibold text-neutral-900">{used}</span> of{" "}
              <span className="font-semibold text-neutral-900">{cap}</span> briefs used this month
            </span>
            <span className="font-medium text-neutral-500">{pct}%</span>
          </div>

          {/* Progress bar */}
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-200">
            <div
              className={[
                "h-full rounded-full transition-all duration-300",
                atCap
                  ? "bg-red-500"
                  : nearCap
                  ? "bg-amber-500"
                  : "bg-emerald-500",
              ].join(" ")}
              style={{ width: `${pct}%` }}
            />
          </div>

          {/* Reset line */}
          {resetLabel && (
            <p className="text-[11px] text-neutral-500">Resets on {resetLabel}</p>
          )}
        </div>
      ) : (
        // cap is null but not a subscription — shouldn't normally happen,
        // show a safe fallback
        <div className="rounded border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-700">
          <span className="font-semibold text-neutral-900">Reports used:</span> {used}
        </div>
      )}

      {/* ── Near-cap callout (≥80%, not yet at cap) ─────────────────────── */}
      {nearCap && (
        <div className="flex items-start gap-2 rounded border border-amber-200 bg-amber-50 px-3 py-2.5">
          {/* amber dot */}
          <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
          <div className="min-w-0">
            <p className="text-xs font-semibold text-amber-900">
              You're near your monthly limit.
            </p>
            <p className="mt-0.5 text-xs text-amber-800">
              Upgrade to {upgradeLabel} for {upgradeReports} reports/month.{" "}
              <Link
                to={upgradePath}
                className="font-semibold underline underline-offset-2 hover:text-amber-900"
              >
                See {upgradeLabel} plan →
              </Link>
            </p>
          </div>
        </div>
      )}

      {/* ── At-cap callout (used ≥ cap) ──────────────────────────────────── */}
      {atCap && (
        <div className="rounded border border-red-200 bg-red-50 px-3 py-3">
          <p className="text-xs font-semibold text-red-900">Monthly limit reached.</p>
          <p className="mt-1 text-xs text-red-800">
            You've used all {cap} brief{cap === 1 ? "" : "s"} for this month.
            {resetLabel ? ` New uploads resume on ${resetLabel}.` : ""}
          </p>
          <Link
            to={upgradePath}
            className="mt-2.5 inline-flex items-center rounded bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-700 transition-colors"
          >
            Upgrade to {upgradeLabel} →
          </Link>
        </div>
      )}
    </div>
  );
};

export default UploadUsageBar;
