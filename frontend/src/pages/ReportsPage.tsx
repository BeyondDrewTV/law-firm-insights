import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText } from "lucide-react";
import { toast } from "sonner";

import { getLatestExposure, getReports, type ReportListItem } from "@/api/authService";
import PageWrapper from "@/components/governance/PageWrapper";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { formatApiDate } from "@/lib/dateTime";
import { resolvePlanLimits } from "@/config/planLimits";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type BriefRow = {
  id: number;
  title: string;
  dateLabel: string;
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

      return {
        id: report.id,
        title: `${monthYear} Brief`,
        dateLabel: formatApiDate(report.created_at, { month: "long", day: "numeric", year: "numeric" }, "Unknown date"),
        generatedBy: "System",
        pdfUrl: report.download_pdf_url,
        planType: report.plan_type,
        escalationRequired: escalationReportId === report.id,
        signalsCount: Number.isFinite(signalsCountCandidate) ? Number(signalsCountCandidate) : undefined,
        actionsCount: Number.isFinite(actionsCountCandidate) ? Number(actionsCountCandidate) : undefined,
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
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Current brief library</p>
              <h2 className="mt-2 text-[22px] font-semibold text-[#0D1B2A]">
                Review the latest governance brief first, then keep older cycles in reserve.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
                This workspace is for final leadership-facing output. Open the current brief, make any presentation-only PDF adjustments, and use older cycles as reference rather than as equal next steps.
              </p>
            </div>
            <div className="space-y-4">
              <div className="workspace-inline-stats">
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Briefs</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.totalBriefs}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Escalations</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.escalationCount}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">This month</p>
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
          <section className="space-y-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <article key={`brief-skeleton-${index}`} className="animate-soft-scale rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm">
                <div className="h-4 w-36 rounded bg-neutral-200" />
                <div className="mt-3 h-3 w-48 rounded bg-neutral-100" />
                <div className="mt-2 h-3 w-32 rounded bg-neutral-100" />
                <div className="mt-6 h-8 w-28 rounded bg-neutral-200" />
              </article>
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
            {latestRow ? (
              <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-[280px] flex-1">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Primary brief</p>
                    <h2 className="mt-2 text-[20px] font-semibold text-[#0D1B2A]">{latestRow.title}</h2>
                    <p className="mt-1 text-[13px] text-[#6B7280]">{latestRow.dateLabel}</p>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
                      Use the current cycle as the main leadership artifact. Older briefs remain below for comparison, reference, and plan-window history.
                    </p>
                    <div className="mt-4 flex flex-wrap gap-4 text-[13px] text-slate-600">
                      {typeof latestRow.signalsCount === "number" ? <span>{latestRow.signalsCount} {DISPLAY_LABELS.clientIssuePlural.toLowerCase()} detected</span> : null}
                      {typeof latestRow.actionsCount === "number" ? <span>{latestRow.actionsCount} governance actions</span> : null}
                      <span>Generated by {latestRow.generatedBy}</span>
                    </div>
                  </div>
                  <div className="flex min-w-[250px] flex-col items-end gap-3">
                    <span
                      className={
                        latestRow.escalationRequired
                          ? "inline-flex min-w-[120px] justify-center rounded-full border border-amber-300 bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800"
                          : "inline-flex min-w-[120px] justify-center rounded-full border border-[#A7F3D0] bg-[#D1FAE5] px-2.5 py-1 text-[11px] font-semibold text-[#065F46]"
                      }
                    >
                      {latestRow.escalationRequired ? "Escalation Required" : "Ready"}
                    </span>
                    <div className="flex flex-wrap justify-end gap-2">
                      <Button type="button" variant="outline" className="rounded-[8px] border border-[#D1D5DB] bg-transparent px-3 py-2 text-[13px] font-medium text-[#0D1B2A] hover:bg-slate-50" onClick={() => navigate(`/dashboard/reports/${latestRow.id}`)}>
                        View
                      </Button>
                      <Button type="button" variant="outline" className="rounded-[8px] border border-[#D1D5DB] bg-transparent px-3 py-2 text-[13px] font-medium text-[#0D1B2A] hover:bg-slate-50" onClick={() => navigate(`/dashboard/brief-customization?reportId=${latestRow.id}`)}>
                        Prepare presentation
                      </Button>
                      <Button type="button" className="rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-medium text-white hover:bg-[#16263b]" onClick={() => void handleDownload(latestRow)}>
                        {latestRow.planType === "free" ? "Preview Governance Brief (Watermarked)" : "Download Governance Brief PDF"}
                      </Button>
                    </div>
                  </div>
                </div>
              </section>
            ) : null}

            {archivedRows.length > 0 ? (
              <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-3 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <div className="border-b border-[#E5E7EB] py-3">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Prior briefs</p>
                  <p className="mt-1 text-sm text-slate-700">Reference earlier cycles without giving them the same weight as the current leadership brief.</p>
                </div>
                <div className="workspace-divider-list">
                  {archivedRows.map((row) => (
                    <article key={row.id} className="flex flex-wrap items-start justify-between gap-4 py-4">
                      <div className="min-w-[240px] flex-1">
                        <h3 className="text-[15px] font-semibold text-[#0D1B2A]">{row.title}</h3>
                        <p className="mt-1 text-[13px] text-[#6B7280]">{row.dateLabel}</p>
                        <div className="mt-2 flex flex-wrap gap-4 text-[13px] text-slate-600">
                          {typeof row.signalsCount === "number" ? <span>{row.signalsCount} {DISPLAY_LABELS.clientIssuePlural.toLowerCase()}</span> : null}
                          {typeof row.actionsCount === "number" ? <span>{row.actionsCount} actions</span> : null}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={
                            row.escalationRequired
                              ? "inline-flex min-w-[120px] justify-center rounded-full border border-amber-300 bg-amber-100 px-2.5 py-1 text-[11px] font-semibold text-amber-800"
                              : "inline-flex min-w-[120px] justify-center rounded-full border border-[#A7F3D0] bg-[#D1FAE5] px-2.5 py-1 text-[11px] font-semibold text-[#065F46]"
                          }
                        >
                          {row.escalationRequired ? "Escalation Required" : "Ready"}
                        </span>
                        <Button type="button" variant="outline" className="rounded-[8px] border border-[#D1D5DB] bg-transparent px-3 py-2 text-[13px] font-medium text-[#0D1B2A] hover:bg-slate-50" onClick={() => navigate(`/dashboard/reports/${row.id}`)}>
                          View
                        </Button>
                        <Button type="button" className="rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-medium text-white hover:bg-[#16263b]" onClick={() => void handleDownload(row)}>
                          {row.planType === "free" ? "Preview PDF" : "Download PDF"}
                        </Button>
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}
          </div>
        )}
      </PageWrapper>
  );
};

export default ReportsPage;
