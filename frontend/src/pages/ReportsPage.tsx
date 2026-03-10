import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FileText, BookOpen } from "lucide-react";
import { toast } from "sonner";

import { getLatestExposure, getReports, type ReportListItem } from "@/api/authService";
import PageWrapper from "@/components/governance/PageWrapper";
import GovernanceBriefCard from "@/components/governance/GovernanceBriefCard";
import GovernanceEmptyState from "@/components/governance/GovernanceEmptyState";
import { BriefCardSkeleton } from "@/components/governance/skeletons";
import { PageTabs } from "@/components/governance/PageTabs";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { formatApiDate } from "@/lib/dateTime";
import { resolvePlanLimits } from "@/config/planLimits";

type BriefRow = {
  id: number;
  title: string;
  /** Period label for the meeting this brief covers (e.g. "March 2025") */
  meetingDate: string;
  /** Formatted full date for the generated/created date */
  dateLabel: string;
  /** One-liner packet summary shown inside the card */
  description: string;
  generatedBy: string;
  pdfUrl: string;
  planType: string;
  escalationRequired: boolean;
  signalsCount?: number;
  actionsCount?: number;
};

const ReportsPage = () => {
  const navigate = useNavigate();
  const { currentPlan } = useAuth();
  const maxReportsPerMonth = resolvePlanLimits(currentPlan).maxReportsPerMonth;
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [historyNotice, setHistoryNotice] = useState<string | null>(null);
  const [historyTruncated, setHistoryTruncated] = useState(false);
  const [escalationReportId, setEscalationReportId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleDownload = async (row: BriefRow) => {
    try {
      const response = await fetch(row.pdfUrl, { credentials: "include" });
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as { error?: string; message?: string };
        if (payload.error === "Report outside plan history window") {
          toast.error(
            "This report is outside your plan’s historical intelligence window. Upgrade your plan to access older governance history.",
          );
          return;
        }
        if (!response.ok) {
          toast.error(payload.message || payload.error || "Unable to open governance brief.");
          return;
        }
      }
      if (!response.ok) {
        toast.error("Unable to open governance brief.");
        return;
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch {
      toast.error("Unable to open governance brief.");
    }
  };

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      const [result, exposureResult] = await Promise.all([getReports(120), getLatestExposure()]);
      if (!mounted) return;

      if (!result.success || !result.reports) {
        setReports([]);
        setHistoryNotice(null);
        setHistoryTruncated(false);
        setEscalationReportId(null);
        setError(result.error || "Unable to load governance brief history.");
        setLoading(false);
        return;
      }

      const ready = result.reports
        .filter((report) => report.status === "ready")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setReports(ready);
      setHistoryNotice(result.history_notice || null);
      setHistoryTruncated(Boolean(result.history_truncated));
      if (exposureResult.success && exposureResult.exposure?.partner_escalation_required && exposureResult.exposure.report_id) {
        setEscalationReportId(exposureResult.exposure.report_id);
      } else {
        setEscalationReportId(null);
      }
      setError("");
      setLoading(false);
    };
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  const rows = useMemo<BriefRow[]>(() => {
    return reports.map((report) => {
      const monthYear = formatApiDate(report.created_at, { month: "long", year: "numeric" }, "Unknown date");
      const reportWithCounts = report as ReportListItem & {
        signals_count?: number;
        signal_count?: number;
        governance_signals_count?: number;
        actions_count?: number;
        governance_actions_count?: number;
      };
      const signalsCountCandidate =
        reportWithCounts.signals_count ??
        reportWithCounts.signal_count ??
        reportWithCounts.governance_signals_count;
      const actionsCountCandidate =
        reportWithCounts.actions_count ??
        reportWithCounts.governance_actions_count;

      const signalsFinal = Number.isFinite(signalsCountCandidate) ? Number(signalsCountCandidate) : undefined;
      const actionsFinal = Number.isFinite(actionsCountCandidate) ? Number(actionsCountCandidate) : undefined;
      const isEscalation = escalationReportId === report.id;

      // Build a readable packet description from available counts + status
      const descParts: string[] = [];
      if (typeof signalsFinal === "number") {
        descParts.push(`${signalsFinal} client ${signalsFinal === 1 ? "issue" : "issues"} reviewed`);
      }
      if (typeof actionsFinal === "number") {
        descParts.push(`${actionsFinal} ${actionsFinal === 1 ? "action" : "actions"} tracked`);
      }
      if (isEscalation) descParts.push("partner escalation flagged");

      return {
        id: report.id,
        title: `${monthYear} Governance Brief`,
        meetingDate: monthYear,
        dateLabel: formatApiDate(report.created_at, { month: "long", day: "numeric", year: "numeric" }, "Unknown date"),
        description: descParts.join(" · "),
        generatedBy: "System",
        pdfUrl: report.download_pdf_url,
        planType: report.plan_type,
        escalationRequired: isEscalation,
        signalsCount: signalsFinal,
        actionsCount: actionsFinal,
      };
    });
  }, [escalationReportId, reports]);

  const summary = useMemo(() => {
    const totalBriefs = rows.length;
    const escalationCount = rows.filter((row) => row.escalationRequired).length;
    const latestDate = rows[0]?.dateLabel || "Not available";
    const now = new Date();
    const reportsThisMonth = reports.filter((report) => {
      const parsed = new Date(report.created_at || "");
      return (
        Number.isFinite(parsed.getTime()) &&
        parsed.getFullYear() === now.getFullYear() &&
        parsed.getMonth() === now.getMonth()
      );
    }).length;
    return { totalBriefs, escalationCount, latestDate, reportsThisMonth };
  }, [reports, rows]);

  const latestRow = rows[0] || null;
  const archivedRows = rows.slice(1);

  // ── Workflow tab: "upcoming" | "past" ─────────────────────────────────────
  // "Upcoming Meetings" → latest brief (the one being prepared for the next session)
  // "Past Briefs"       → prior cycles (reference / comparison)
  const [briefsTab, setBriefsTab] = useState<"upcoming" | "past">("upcoming");

  return (
      <PageWrapper
        eyebrow="Leadership Artifact"
        title="Governance Briefs"
        description="Meeting-ready reports summarizing client issues, actions, and exposure status."
        contentClassName="stage-sequence"
      >
        <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
          <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr] xl:items-start">
            <div>
              <p className="gov-label">Current brief library</p>
              <h2 className="gov-section-intro mt-2">
                Review the latest governance brief first, then keep older cycles in reserve.
              </h2>
              <p className="gov-body mt-3 max-w-2xl">
                This workspace is for final leadership-facing output. Open the current brief, make any presentation-only PDF adjustments, and use older cycles as reference rather than as equal next steps.
              </p>
            </div>
            <div className="space-y-4">
              <div className="workspace-inline-stats">
                <div className="workspace-inline-stat">
                  <p className="gov-label">Briefs</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.totalBriefs}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">Escalations</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.escalationCount}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">This month</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">
                    {loading ? "..." : summary.reportsThisMonth}
                    <span className="ml-1 text-sm font-medium text-slate-500">/ {maxReportsPerMonth ?? "Unlimited"}</span>
                  </p>
                </div>
              </div>
              {latestRow ? (
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => navigate(`/dashboard/brief-customization?reportId=${latestRow.id}`)}
                >
                  Prepare brief presentation
                </Button>
              ) : null}
            </div>
          </div>
        </section>

        {historyTruncated && historyNotice ? (
          <section className="rounded-[10px] border border-[#BFDBFE] bg-[#EFF6FF] px-4 py-3 text-sm text-[#1E3A8A]">
            {historyNotice}
          </section>
        ) : null}

        {error ? (
          <div className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">
            {error}
          </div>
        ) : null}

        {loading ? (
          <section aria-label="Loading governance briefs" className="space-y-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <BriefCardSkeleton key={`brief-skeleton-${index}`} />
            ))}
          </section>
        ) : rows.length === 0 ? (
          <section className="rounded-[10px] border border-[#E5E7EB] bg-white p-10 text-center shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-600">
              <FileText size={20} />
            </div>
            <h2 className="mt-4 text-lg font-semibold text-slate-900">No governance brief yet</h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-slate-600">
              The first cycle starts with a CSV upload. Review the resulting client issues, assign follow-through, and the governance brief will appear here once that cycle is ready.
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              <Button
                type="button"
                className="rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-sm font-medium text-white hover:bg-[#16263b]"
                onClick={() => navigate("/upload")}
              >
                Upload feedback CSV
              </Button>
              <Button type="button" variant="secondary" onClick={() => navigate("/dashboard")}>
                Return to overview
              </Button>
            </div>
            <div className="mt-3">
              <Link to="/demo" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-700">
                Open read-only example cycle
              </Link>
            </div>
          </section>
        ) : (
          <div className="space-y-5">
            {/* ── Workflow tabs ─────────────────────────────────────── */}
            <PageTabs
              value={briefsTab}
              onValueChange={(v) => setBriefsTab(v as typeof briefsTab)}
              tabs={[
                {
                  value: "upcoming",
                  label: "Upcoming Meetings",
                  badgeCount: latestRow?.escalationRequired ? 1 : undefined,
                  badgeUrgent: latestRow?.escalationRequired,
                },
                {
                  value: "past",
                  label: "Past Briefs",
                  badgeCount: archivedRows.length > 0 ? archivedRows.length : undefined,
                },
              ]}
            />

            {briefsTab === "upcoming" ? (
              latestRow ? (
                <div>
                  <p className="mb-3 gov-type-eyebrow">
                    {latestRow.escalationRequired ? "Next meeting · escalation required" : "Prepared for next meeting"}
                  </p>
                  <GovernanceBriefCard
                    title={latestRow.title}
                    meetingDate={latestRow.meetingDate}
                    dateLabel={latestRow.dateLabel}
                    description={latestRow.description || undefined}
                    status={latestRow.escalationRequired ? "escalation" : "ready"}
                    signalsCount={latestRow.signalsCount}
                    actionsCount={latestRow.actionsCount}
                    generatedBy={latestRow.generatedBy}
                    planType={latestRow.planType}
                    isPast={false}
                    onView={() => navigate(`/dashboard/reports/${latestRow.id}`)}
                    onPrepare={() => navigate(`/dashboard/brief-customization?reportId=${latestRow.id}`)}
                    onDownload={() => void handleDownload(latestRow)}
                  />
                </div>
              ) : (
                <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
                  <GovernanceEmptyState
                    size="md"
                    icon={<FileText size={20} />}
                    title="No brief prepared for the upcoming meeting"
                    description="Create your first governance brief once you have reviewed your top signals and confirmed the issues that need leadership attention."
                    primaryAction={{ label: "Review client issues", href: "/dashboard/signals" }}
                    secondaryAction={{ label: "Upload feedback CSV", href: "/upload" }}
                  />
                </section>
              )
            ) : (
              archivedRows.length > 0 ? (
                <div>
                  <p className="mb-3 gov-type-eyebrow">
                    Prior meeting cycles — reference only
                  </p>
                  <div className="space-y-3">
                    {archivedRows.map((row) => (
                      <GovernanceBriefCard
                        key={row.id}
                        title={row.title}
                        meetingDate={row.meetingDate}
                        dateLabel={row.dateLabel}
                        description={row.description || undefined}
                        status={row.escalationRequired ? "escalation" : "ready"}
                        signalsCount={row.signalsCount}
                        actionsCount={row.actionsCount}
                        planType={row.planType}
                        isPast={true}
                        onView={() => navigate(`/dashboard/reports/${row.id}`)}
                        onDownload={() => void handleDownload(row)}
                      />
                    ))}
                  </div>
                </div>
              ) : (
                <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
                  <GovernanceEmptyState
                    size="md"
                    icon={<BookOpen size={20} />}
                    title="No past briefs yet"
                    description="Prior governance cycles will appear here as a reference archive once more than one brief has been completed. Use them to track issue trends across meetings."
                    primaryAction={{ label: "View upcoming brief", onClick: () => setBriefsTab("upcoming") }}
                  />
                </section>
              )
            )}
          </div>
        )}
      </PageWrapper>
  );
};

export default ReportsPage;
