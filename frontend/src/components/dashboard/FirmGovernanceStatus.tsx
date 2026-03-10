import { useMemo } from "react";

import { DashboardCard } from "@/components/ui/card";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useCountUp } from "@/hooks/useCountUp";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type GovernanceRisk = "Low" | "Moderate" | "High";

type FirmGovernanceStatusProps = {
  status: GovernanceRisk;
  reviewPeriodLabel: string;
  reviewsAnalyzed: number;
  loading?: boolean;
  metrics: {
    signals: number;
    newSignals: number;
    openActions: number;
    overdueActions: number;
  };
  onOpenSignals: () => void;
  onOpenNewSignals: () => void;
  onOpenOpenActions: () => void;
  onOpenOverdueActions: () => void;
};

export default function FirmGovernanceStatus({
  status,
  reviewPeriodLabel,
  reviewsAnalyzed,
  loading = false,
  metrics,
  onOpenSignals,
  onOpenNewSignals,
  onOpenOpenActions,
  onOpenOverdueActions,
}: FirmGovernanceStatusProps) {
  const statusBadgeClass = useMemo(() => {
    if (status === "High") {
      return "border-amber-300 bg-amber-50 text-amber-900";
    }
    if (status === "Moderate") {
      return "border-blue-300 bg-blue-50 text-blue-900";
    }
    return "border-emerald-300 bg-emerald-50 text-emerald-900";
  }, [status]);

  const statusLabel = `${status} Exposure`;
  const signalsCount = useCountUp(metrics.signals, 800, 0);
  const newCount = useCountUp(metrics.newSignals, 800, 100);
  const openCount = useCountUp(metrics.openActions, 800, 200);
  const overdueCount = useCountUp(metrics.overdueActions, 800, 300);

  return (
    <DashboardCard
      title="Current governance posture"
      subtitle="Where the current review cycle stands right now."
      titleClassName="text-base font-semibold text-neutral-900"
      className="animate-slide-up"
    >
      <div className="gov-card-content">
        <div>
          <span className={`inline-flex rounded-full border px-4 py-2 text-base font-semibold ${statusBadgeClass}`}>
            {statusLabel}
          </span>
        </div>

        <div className="flex flex-wrap items-center divide-x divide-[#E5E7EB] rounded-[10px] border border-[#E5E7EB] bg-white">
          <div className="px-4 py-2">
            <span className="text-[14px] font-bold text-[#0D1B2A]">{loading ? "..." : reviewsAnalyzed}</span>
            <span className="ml-1 text-[12px] font-normal text-[#6B7280]">reviews analyzed</span>
          </div>
          <div className="px-4 py-2">
            <span className="text-[14px] font-bold text-[#0D1B2A]">{loading ? "..." : metrics.signals}</span>
            <span className="ml-1 text-[12px] font-normal text-[#6B7280]">client issues detected</span>
          </div>
          <div className="px-4 py-2">
            <span className="text-[14px] font-bold text-[#0D1B2A]">{loading ? "..." : metrics.openActions}</span>
            <span className="ml-1 text-[12px] font-normal text-[#6B7280]">actions assigned</span>
          </div>
        </div>

        <p className="text-[12px] italic text-[#9CA3AF]">Current review period: {reviewPeriodLabel}</p>

        <TooltipProvider delayDuration={120}>
          <div className="gov-card-grid grid-cols-2 md:grid-cols-4">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={onOpenSignals}
                  className="rounded-[10px] border border-[#E5E7EB] border-l-[3px] border-l-transparent bg-white px-6 py-5 text-left shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition hover:border-neutral-300"
                >
                  <p className="gov-type-eyebrow">{DISPLAY_LABELS.clientIssuePlural}</p>
                  <p className="mt-1 text-[36px] font-bold leading-none text-[#0D1B2A]">{loading ? "..." : signalsCount}</p>
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p className="font-medium">{DISPLAY_LABELS.clientIssueTooltipTitle}</p>
                <p>{DISPLAY_LABELS.clientIssueTooltipBody}</p>
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={onOpenNewSignals}
                  className={[
                    "rounded-[10px] border border-[#E5E7EB] border-l-[3px] bg-white px-6 py-5 text-left shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition hover:border-neutral-300",
                    metrics.newSignals > 0 ? "border-l-[#F59E0B]" : "border-l-transparent",
                  ].join(" ")}
                >
                  <p className="gov-type-eyebrow">New</p>
                  <p className="mt-1 text-[36px] font-bold leading-none text-[#0D1B2A]">{loading ? "..." : newCount}</p>
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Client issues detected since last governance review
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={onOpenOpenActions}
                  className="rounded-[10px] border border-[#E5E7EB] border-l-[3px] border-l-transparent bg-white px-6 py-5 text-left shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition hover:border-neutral-300"
                >
                  <p className="gov-type-eyebrow">Open</p>
                  <p className="mt-1 text-[36px] font-bold leading-none text-[#0D1B2A]">{loading ? "..." : openCount}</p>
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Actions assigned but not yet completed
              </TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  onClick={onOpenOverdueActions}
                  className={[
                    "rounded-[10px] border border-[#E5E7EB] border-l-[3px] bg-white px-6 py-5 text-left shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition hover:border-neutral-300",
                    metrics.overdueActions > 0 ? "border-l-[#EF4444]" : "border-l-transparent",
                  ].join(" ")}
                >
                  <p className="gov-type-eyebrow">Overdue</p>
                  <p className="mt-1 text-[36px] font-bold leading-none text-[#0D1B2A]">{loading ? "..." : overdueCount}</p>
                </button>
              </TooltipTrigger>
              <TooltipContent>
                Actions past their due date requiring immediate attention
              </TooltipContent>
            </Tooltip>
          </div>
        </TooltipProvider>
      </div>
    </DashboardCard>
  );
}
