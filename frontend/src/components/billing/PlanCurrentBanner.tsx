import { Link } from "react-router-dom";
import PlanBadge from "@/components/dashboard/PlanBadge";
import { formatApiDate } from "@/lib/dateTime";
import type { UiPlanLimits } from "@/config/planLimits";

type FirmPlan = "free" | "team" | "firm" | "trial" | "professional" | "leadership" | null | undefined;

interface PlanCurrentBannerProps {
  firmPlan: FirmPlan;
  planLabel: string;
  isPaidSubscription: boolean;
  planLimits: UiPlanLimits;
  nextReset: string | null | undefined;
  nextUpgradePath: string;
  isLoading: boolean;
}

function historyLabel(days: number | null | undefined): string {
  if (!days) return "Unlimited";
  if (days >= 365) return `${Math.round(days / 365)} year`;
  return `${days} days`;
}

const PlanCurrentBanner = ({
  firmPlan,
  planLabel,
  isPaidSubscription,
  planLimits,
  nextReset,
  nextUpgradePath,
  isLoading,
}: PlanCurrentBannerProps) => {
  const resetLabel = nextReset ? formatApiDate(nextReset, { month: "long", day: "numeric" }, "") : "";
  const reviewLimit = planLimits.maxReviewsPerUpload ?? null;
  const reportLimit = planLimits.maxReportsPerMonth ?? null;
  const history = planLimits.historyDays ?? null;

  const isFree = !isPaidSubscription && (firmPlan === "free" || firmPlan === "trial" || !firmPlan);
  const isTeam = firmPlan === "team" || firmPlan === "professional";

  if (isLoading) {
    return (
      <div className="rounded-lg border border-neutral-200 bg-white px-5 py-5 animate-pulse">
        <div className="h-4 w-24 rounded bg-neutral-100" />
        <div className="mt-3 h-3 w-48 rounded bg-neutral-100" />
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-200 bg-white px-5 py-5 shadow-sm">
      {/* Header row: badge + title + CTA */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <PlanBadge plan={firmPlan} />
          <h2 className="text-base font-semibold text-neutral-900">
            Your current plan: <span className="text-neutral-700">{planLabel}</span>
          </h2>
        </div>

        {/* Only show upgrade CTA for Free and Team — Firm has nothing to upgrade to */}
        {!isTeam && isFree ? (
          <Link to="/pricing?intent=team" className="gov-btn-primary shrink-0 text-sm">
            Upgrade to Team — more reports &amp; reviews →
          </Link>
        ) : isTeam ? (
          <Link to="/pricing?intent=firm" className="gov-btn-secondary shrink-0 text-sm">
            Upgrade to Firm →
          </Link>
        ) : null}
      </div>

      {/* Micro-stat row */}
      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded border border-neutral-100 bg-neutral-50 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Reports / month</p>
          <p className="mt-0.5 text-sm font-semibold text-neutral-900">
            {reportLimit !== null ? reportLimit : "Unlimited"}
          </p>
        </div>
        <div className="rounded border border-neutral-100 bg-neutral-50 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Reviews / upload</p>
          <p className="mt-0.5 text-sm font-semibold text-neutral-900">
            {reviewLimit !== null ? reviewLimit : "Unlimited"}
          </p>
        </div>
        <div className="rounded border border-neutral-100 bg-neutral-50 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">History window</p>
          <p className="mt-0.5 text-sm font-semibold text-neutral-900">{historyLabel(history)}</p>
        </div>
        <div className="rounded border border-neutral-100 bg-neutral-50 px-3 py-2.5">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-neutral-500">Resets</p>
          <p className="mt-0.5 text-sm font-semibold text-neutral-900">
            {isPaidSubscription ? "Monthly" : resetLabel || "Monthly"}
          </p>
        </div>
      </div>

      {/* Free-plan one-liner callout */}
      {isFree && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded border border-blue-100 bg-blue-50 px-4 py-3">
          <p className="text-sm text-blue-900">
            <span className="font-semibold">On Free</span> you get{" "}
            {reportLimit !== null ? reportLimit : "1"} report/month, up to{" "}
            {reviewLimit !== null ? reviewLimit : "50"} reviews/upload
            {resetLabel ? `, and your quota resets on ${resetLabel}` : ""}.{" "}
            <span className="font-medium">
              Upgrade to Team for 10 reports and 250 reviews/upload — no watermarks.
            </span>
          </p>
          <Link
            to={nextUpgradePath}
            className="shrink-0 rounded border border-blue-300 bg-white px-3 py-1.5 text-xs font-semibold text-blue-800 hover:bg-blue-100 transition-colors"
          >
            See Team plan →
          </Link>
        </div>
      )}
    </div>
  );
};

export default PlanCurrentBanner;
