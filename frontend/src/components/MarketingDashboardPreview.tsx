import type { ReportListItem, GovernanceSignal } from "@/api/authService";
import FirmGovernanceStatus from "@/components/dashboard/FirmGovernanceStatus";
import GovernanceGuidance from "@/components/dashboard/GovernanceGuidance";
import SinceLastReview from "@/components/dashboard/SinceLastReview";
import ExposureSignals from "@/components/dashboard/ExposureSignals";
import ActionTracking, { type ActionTrackingItem } from "@/components/dashboard/ActionTracking";
import RecentGovernanceBriefs from "@/components/dashboard/RecentGovernanceBriefs";

type PreviewVariant = "overview" | "library" | "operations";

interface MarketingDashboardPreviewProps {
  compact?: boolean;
  className?: string;
  variant?: PreviewVariant;
}

const sampleSignals: GovernanceSignal[] = [
  {
    id: 801,
    report_id: 50,
    title: "Communication Issues",
    description: "Recurring feedback indicates clients want clearer updates on matter progress.",
    severity: "high",
    source_metric: "communication_mentions",
    created_at: "2026-03-05T12:00:00Z",
  },
  {
    id: 802,
    report_id: 50,
    title: "Billing Clarity",
    description: "Multiple comments request better context before billing events.",
    severity: "medium",
    source_metric: "billing_clarity_mentions",
    created_at: "2026-03-05T12:00:00Z",
  },
];

const sampleActions: ActionTrackingItem[] = [
  {
    id: "act-1",
    title: "Standardize weekly client status updates",
    owner: "Partner Smith",
    dueDate: "March 18",
    status: "In Progress",
  },
  {
    id: "act-2",
    title: "Review retainer communication template",
    owner: "Operations Lead",
    dueDate: "March 22",
    status: "Planned",
  },
];

const sampleBriefs: ReportListItem[] = [
  {
    id: 50,
    name: "March Governance Brief",
    status: "ready",
    created_at: "2026-03-05T12:00:00Z",
    total_reviews: 312,
    avg_rating: 4.1,
    has_pdf: true,
    download_pdf_url: "#",
  },
  {
    id: 49,
    name: "February Governance Brief",
    status: "ready",
    created_at: "2026-02-04T12:00:00Z",
    total_reviews: 224,
    avg_rating: 4.0,
    has_pdf: true,
    download_pdf_url: "#",
  },
  {
    id: 48,
    name: "January Governance Brief",
    status: "ready",
    created_at: "2026-01-08T12:00:00Z",
    total_reviews: 198,
    avg_rating: 3.9,
    has_pdf: true,
    download_pdf_url: "#",
  },
];

const noop = () => undefined;

const MarketingDashboardPreview = ({
  compact = false,
  className = "",
  variant = "overview",
}: MarketingDashboardPreviewProps) => {
  const variantLabel =
    variant === "library"
      ? "Demo report library"
      : variant === "operations"
        ? "Demo action workflow"
        : "Demo dashboard state";

  return (
    <div className={`rounded-2xl border border-[#E5E7EB] bg-white p-4 shadow-sm ${className}`}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-600">{variantLabel}</p>
        <p className="text-[11px] text-slate-500">Read-only demo with sample law-firm data. Live workspace actions are disabled.</p>
      </div>
      <div className={`space-y-4 ${compact ? "" : "md:space-y-6"}`}>
        {variant === "overview" && (
          <>
            <FirmGovernanceStatus
              status="Moderate"
              reviewPeriodLabel="January - March 2026"
              reviewsAnalyzed={312}
              metrics={{
                signals: 8,
                newSignals: 3,
                openActions: 5,
                overdueActions: 1,
              }}
              onOpenSignals={noop}
              onOpenNewSignals={noop}
              onOpenOpenActions={noop}
              onOpenOverdueActions={noop}
            />
            {!compact && (
              <SinceLastReview
                isLoading={false}
                newFeedbackSignals={3}
                newExposureCategories={2}
                overdueActionsCreated={1}
              />
            )}
          </>
        )}

        {variant === "library" && (
          <RecentGovernanceBriefs
            briefs={sampleBriefs}
            escalationReportId={50}
            hasEscalation
            onView={noop}
            onDownload={async () => undefined}
          />
        )}

        {variant === "operations" && (
          <>
            <GovernanceGuidance
              directive="Communication complaints increased in the current cycle."
              recommendedAction="Assign partner review and update response standards."
              onOpenActions={noop}
            />
            <ExposureSignals isLoading={false} signals={sampleSignals} onCreateAction={noop} />
            {!compact && <ActionTracking actions={sampleActions} />}
          </>
        )}
      </div>
    </div>
  );
};

export default MarketingDashboardPreview;
