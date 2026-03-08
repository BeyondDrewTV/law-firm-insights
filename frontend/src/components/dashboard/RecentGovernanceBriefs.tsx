import { ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import type { ReportListItem } from "@/api/authService";
import { DashboardCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

type RecentGovernanceBriefsProps = {
  briefs: ReportListItem[];
  escalationReportId?: number | null;
  hasEscalation?: boolean | null;
  onView: (reportId: number) => void;
  onDownload: (brief: ReportListItem) => Promise<void>;
};

const formatBriefMonth = (value: string) => {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Unknown period";
  return date.toLocaleDateString([], { month: "long", year: "numeric" });
};

export default function RecentGovernanceBriefs({
  briefs,
  escalationReportId,
  hasEscalation,
  onView,
  onDownload,
}: RecentGovernanceBriefsProps) {
  return (
    <DashboardCard title="Recent governance briefs" subtitle="Recent leadership-ready outputs from completed review cycles.">
      {briefs.length === 0 ? (
        <p className="text-sm text-neutral-700">No governance briefs generated yet. Upload feedback to begin.</p>
      ) : (
        <div className="gov-list-stack">
          {briefs.map((brief) => {
            const escalationRequired = Boolean(
              hasEscalation && escalationReportId && brief.id === escalationReportId,
            );

            return (
              <div
                key={brief.id}
                className={[
                  "flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4",
                  escalationRequired ? "border-amber-300 bg-amber-50" : "border-[var(--border)] bg-white",
                ].join(" ")}
              >
                <div>
                  <p className="text-sm font-medium text-neutral-900">{formatBriefMonth(brief.created_at)}</p>
                  <span
                    className={[
                      "mt-1 inline-flex rounded-full border px-2 py-0.5 text-xs font-medium",
                      escalationRequired
                        ? "border-amber-300 bg-amber-100 text-amber-900"
                        : "border-emerald-200 bg-emerald-50 text-emerald-800",
                    ].join(" ")}
                  >
                    {escalationRequired ? "Escalation Required" : "Ready"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <Button type="button" variant="secondary" onClick={() => onView(brief.id)}>
                    View
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void onDownload(brief)}>
                    {brief.plan_type === "free" ? "Preview Governance Brief (Watermarked)" : "Download Governance Brief PDF"}
                  </Button>
                </div>
              </div>
            );
          })}
          <div className="pt-1">
            <Link to="/dashboard/reports" className="inline-flex items-center gap-1 text-sm font-medium text-neutral-800 hover:text-neutral-900">
              View All Briefs
              <ChevronRight size={14} />
            </Link>
          </div>
        </div>
      )}
    </DashboardCard>
  );
}
