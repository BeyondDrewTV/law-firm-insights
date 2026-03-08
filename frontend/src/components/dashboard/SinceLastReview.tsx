import { AlertTriangle, CheckCircle2, Layers, TrendingUp } from "lucide-react";
import { DashboardCard } from "@/components/ui/card";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type SinceLastReviewProps = {
  isLoading: boolean;
  newFeedbackSignals: number;
  newExposureCategories: number;
  overdueActionsCreated: number;
};

const SinceLastReview = ({
  isLoading,
  newFeedbackSignals,
  newExposureCategories,
  overdueActionsCreated,
}: SinceLastReviewProps) => {
  return (
    <DashboardCard title="What changed since the last review" subtitle="Movement in client issues, exposure, and overdue follow-through.">
      {isLoading ? (
        <div className="gov-list-stack">
          <div className="h-4 w-56 animate-pulse rounded bg-neutral-200" />
          <div className="h-4 w-48 animate-pulse rounded bg-neutral-200" />
          <div className="h-4 w-52 animate-pulse rounded bg-neutral-200" />
        </div>
      ) : (
        <div className="gov-list-stack text-sm">
          <div className="flex items-center gap-2 text-slate-700">
            <TrendingUp size={14} className="text-blue-500" />
            <span>+{newFeedbackSignals} New {newFeedbackSignals === 1 ? DISPLAY_LABELS.clientIssueSingular : DISPLAY_LABELS.clientIssuePlural}</span>
          </div>
          <div className="flex items-center gap-2 text-slate-700">
            <Layers size={14} className="text-slate-500" />
            <span>{newExposureCategories} New Exposure Categor{newExposureCategories === 1 ? "y" : "ies"}</span>
          </div>
          <div className={overdueActionsCreated === 0 ? "flex items-center gap-2 text-emerald-700" : "flex items-center gap-2 text-red-600"}>
            {overdueActionsCreated === 0 ? (
              <CheckCircle2 size={14} className="text-emerald-500" />
            ) : (
              <AlertTriangle size={14} className="text-red-500" />
            )}
            <span>
              {overdueActionsCreated === 0
                ? "No Overdue Actions"
                : `${overdueActionsCreated} Overdue Action${overdueActionsCreated === 1 ? "" : "s"}`}
            </span>
          </div>
        </div>
      )}
    </DashboardCard>
  );
};

export default SinceLastReview;
