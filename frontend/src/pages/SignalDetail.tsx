import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import {
  createReportAction,
  getReportActions,
  getReportDetail,
  getReportGovernanceSignals,
  getReports,
  type GovernanceSignal,
  type ReportActionItem,
  type ReportDetail,
  type ReportListItem,
} from "@/api/authService";
import ActionForm, { type ActionFormValues } from "@/components/actions/ActionForm";
import ClientQuoteCard from "@/components/ClientQuoteCard";
import PageWrapper from "@/components/governance/PageWrapper";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type SignalSeverity = "high" | "medium" | "low";

type SignalModel = {
  id: string;
  title: string;
  description: string;
  severity: SignalSeverity;
  frequencyCount: number;
  category: string;
  previousCount: number | null;
};

type ExcerptModel = {
  id: string;
  text: string;
  dateLabel: string;
  sentiment: "complaint" | "praise";
};

const parseSignalRoute = (rawSignalId: string | undefined) => {
  const raw = rawSignalId || "";
  const [reportPart, indexPart] = raw.split("-");
  const reportId = Number(reportPart);
  const index = Number(indexPart);
  return {
    raw,
    reportId: Number.isFinite(reportId) && reportId > 0 ? reportId : null,
    index: Number.isFinite(index) && index > 0 ? index - 1 : 0,
  };
};

const toSeverity = (signal: GovernanceSignal | null, index: number): SignalSeverity => {
  const normalized = String(signal?.severity || "").toLowerCase();
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  if (normalized === "low") return "low";
  if (index < 2) return "high";
  if (index < 5) return "medium";
  return "low";
};

const severityLabel = (severity: SignalSeverity) => {
  if (severity === "high") return "High";
  if (severity === "medium") return "Medium";
  return "Low";
};

const severityBadgeClass = (severity: SignalSeverity) => {
  if (severity === "high") return "border border-[#FECACA] bg-[#FEF2F2] text-[#DC2626]";
  if (severity === "medium") return "border border-[#FDE68A] bg-[#FFFBEB] text-[#D97706]";
  return "border border-slate-200 bg-slate-100 text-slate-700";
};

const parseCount = (signal: GovernanceSignal | null, fallback: number) => {
  const maybe = signal as (GovernanceSignal & { count?: number; frequency?: number }) | null;
  if (typeof maybe?.count === "number" && Number.isFinite(maybe.count)) return Math.max(1, Math.round(maybe.count));
  if (typeof maybe?.frequency === "number" && Number.isFinite(maybe.frequency)) {
    if (maybe.frequency > 0 && maybe.frequency < 1) return Math.max(1, Math.round(maybe.frequency * 100));
    return Math.max(1, Math.round(maybe.frequency));
  }
  return fallback;
};

const formatMonthYear = (value?: string | null) => {
  if (!value) return "Not available";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Not available";
  return date.toLocaleDateString([], { month: "long", year: "numeric" });
};

const formatMonthDay = (value?: string | null) => {
  if (!value) return "Not set";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Not set";
  return date.toLocaleDateString([], { month: "short", day: "numeric" });
};

const formatPeriod = (report: ReportDetail | null) => {
  if (!report) return "Not available";
  const start = report.review_date_start ? new Date(report.review_date_start) : null;
  const end = report.review_date_end ? new Date(report.review_date_end) : null;
  const validStart = Boolean(start && Number.isFinite(start.getTime()));
  const validEnd = Boolean(end && Number.isFinite(end.getTime()));
  if (validStart && validEnd && start && end) {
    const sameYear = start.getFullYear() === end.getFullYear();
    if (sameYear) {
      return `${start.toLocaleDateString([], { month: "short" })}-${end.toLocaleDateString([], {
        month: "short",
        year: "numeric",
      })}`;
    }
    return `${start.toLocaleDateString([], { month: "short", year: "numeric" })} to ${end.toLocaleDateString([], {
      month: "short",
      year: "numeric",
    })}`;
  }
  return formatMonthYear(report.created_at);
};

const deltaMeta = (current: number, previous: number) => {
  const delta = current - previous;
  const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
  const label = direction === "up" ? "Increase" : direction === "down" ? "Decrease" : "No change";
  const percent = previous > 0 ? Math.round((Math.abs(delta) / previous) * 100) : delta === 0 ? 0 : 100;
  return { delta, direction, label, percent };
};

const isActionOverdue = (action: ReportActionItem) => {
  if (!action.due_date) return false;
  if (action.status === "done") return false;
  const due = Date.parse(action.due_date);
  return Number.isFinite(due) && due < Date.now();
};

const SignalDetail = () => {
  const { signalId } = useParams<{ signalId: string }>();
  const route = useMemo(() => parseSignalRoute(signalId), [signalId]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [signal, setSignal] = useState<SignalModel | null>(null);
  const [excerpts, setExcerpts] = useState<ExcerptModel[]>([]);
  const [actions, setActions] = useState<ReportActionItem[]>([]);
  const [showActionForm, setShowActionForm] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState("");

  const loadActions = useCallback(async (reportId: number) => {
    const result = await getReportActions(reportId);
    if (result.success && result.actions) {
      setActions(result.actions);
    } else {
      setActions([]);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const reportsResult = await getReports(120);
        if (!active) return;
        const readyReports =
          reportsResult.success && reportsResult.reports
            ? reportsResult.reports
                .filter((item) => item.status === "ready")
                .sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at))
            : [];

        const targetReport =
          readyReports.find((item) => item.id === route.reportId) ||
          (readyReports[0] as ReportListItem | undefined);
        if (!targetReport?.id) {
          setError("Client issue detail is unavailable because no ready report exists.");
          setReport(null);
          setSignal(null);
          setExcerpts([]);
          setActions([]);
          setLoading(false);
          return;
        }

        const targetIndex = readyReports.findIndex((item) => item.id === targetReport.id);
        const previousReport = targetIndex >= 0 ? readyReports[targetIndex + 1] : undefined;

        const [reportResult, signalResult, previousSignalResult] = await Promise.all([
          getReportDetail(targetReport.id),
          getReportGovernanceSignals(targetReport.id),
          previousReport?.id ? getReportGovernanceSignals(previousReport.id) : Promise.resolve({ success: false as const }),
        ]);
        if (!active) return;

        if (!reportResult.success || !reportResult.report) {
          setError(reportResult.error || "Unable to load client issue detail.");
          setLoading(false);
          return;
        }

        const detail = reportResult.report;
        setReport(detail);

        const topComplaints = Array.isArray(detail.top_complaints) ? detail.top_complaints : [];
        const apiSignals = signalResult.success && signalResult.signals ? signalResult.signals : [];
        const currentSignal = apiSignals[route.index] || null;
        const signalTitle = (currentSignal?.title || topComplaints[route.index] || topComplaints[0] || "Client feedback issue").trim();
        const category = signalTitle.includes(":") ? signalTitle.split(":")[0].trim() : signalTitle;
        const frequencyCount = parseCount(currentSignal, Math.max(3, topComplaints.length + 2));
        const severity = toSeverity(currentSignal, route.index);

        const previousSignals = previousSignalResult.success && previousSignalResult.signals ? previousSignalResult.signals : [];
        const previousSignal = previousSignals.find((item) => {
          const itemTitle = (item.title || "").trim().toLowerCase();
          return itemTitle === signalTitle.toLowerCase() || itemTitle.startsWith(category.toLowerCase());
        });
        const previousCount = previousSignal ? parseCount(previousSignal, 0) : null;

        setSignal({
          id: route.raw || `${targetReport.id}-${route.index + 1}`,
          title: category || signalTitle,
          category: category || signalTitle,
          severity,
          frequencyCount,
          previousCount,
          description:
            (currentSignal?.description || "").trim() ||
            "Recurring client feedback indicating delayed responses or poor communication during matters.",
        });

        const usingComplaints = topComplaints.length > 0;
        const sourceExcerpts = usingComplaints ? topComplaints : detail.top_praise || [];
        const excerptItems = sourceExcerpts.slice(0, 5).map((text, idx) => ({
          id: `${targetReport.id}-excerpt-${idx + 1}`,
          text: String(text || "").trim(),
          dateLabel: formatMonthYear(detail.review_date_end || detail.created_at),
          sentiment: usingComplaints ? "complaint" : "praise",
        }));
        setExcerpts(excerptItems.filter((item) => item.text.length > 0));

        await loadActions(targetReport.id);
      } catch {
        if (!active) return;
        setError("Unable to load client issue detail right now.");
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    return () => {
      active = false;
    };
  }, [loadActions, route.index, route.raw, route.reportId]);

  const ownerOptions = useMemo(
    () => Array.from(new Set(actions.map((item) => (item.owner || "").trim()).filter(Boolean))),
    [actions],
  );

  const relatedActions = useMemo(() => {
    if (!signal) return [];
    const titleLower = signal.title.toLowerCase();
    const categoryLower = signal.category.toLowerCase();
    return actions.filter((action) => {
      const haystack = `${action.title} ${action.notes || ""} ${action.kpi || ""}`.toLowerCase();
      return haystack.includes(titleLower) || haystack.includes(categoryLower);
    });
  }, [actions, signal]);

  const actionPrefill = useMemo<ActionFormValues>(() => {
    if (!signal) {
      return {
        title: "",
        owner: "",
        owner_user_id: null,
        due_date: "",
        status: "open",
        timeframe: "Days 1-30",
        kpi: "",
        notes: "",
      };
    }
    return {
      title: `Review ${signal.category}`,
      owner: "",
      owner_user_id: null,
      due_date: "",
      status: "open",
      timeframe: "Days 1-30",
      kpi: "Owner assigned and remediation plan approved.",
      notes: `${signal.title}: ${signal.description}`,
    };
  }, [signal]);

  const handleCreateAction = async (values: ActionFormValues) => {
    if (!report?.id) return;
    setSubmittingAction(true);
    setActionError("");
    try {
      const result = await createReportAction(report.id, {
        title: values.title,
        owner: values.owner || undefined,
        owner_user_id: values.owner_user_id,
        status: values.status,
        due_date: values.due_date || null,
        timeframe: values.timeframe,
        kpi: values.kpi,
        notes: values.notes,
      });
      if (!result.success) {
        const message = result.error || "Unable to create action.";
        setActionError(message);
        toast.error(message);
        return;
      }
      toast.success("Action created successfully");
      setShowActionForm(false);
      await loadActions(report.id);
    } finally {
      setSubmittingAction(false);
    }
  };

  const periodLabel = useMemo(() => formatPeriod(report), [report]);
  const trend = useMemo(() => {
    if (!signal || typeof signal.previousCount !== "number") return null;
    return deltaMeta(signal.frequencyCount, signal.previousCount);
  }, [signal]);

  return (
      <PageWrapper
        title={`${DISPLAY_LABELS.clientIssueSingular} Detail`}
        description="Investigate client issue context and assign governance action."
        contentClassName="stage-sequence"
      >
        <div className="mb-4">
          <Link to="/dashboard/signals" className="text-[13px] font-medium text-[#0EA5C2] hover:text-[#0b8ca7]">
            Back to Client Issues
          </Link>
        </div>

        {error ? (
          <section className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">
            {error}
          </section>
        ) : null}

        {loading ? (
          <section className="rounded-xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
            <p className="text-sm text-neutral-700">Loading client issue detail...</p>
          </section>
        ) : signal ? (
          <div className="space-y-6">
            <section className="rounded-xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <h1 className="text-[24px] font-bold text-[#0D1B2A]">{signal.title}</h1>
                  <p className="mt-2 text-[13px] text-[#6B7280]">
                    Detected in {signal.frequencyCount} reviews | Period: {periodLabel} | Severity: {severityLabel(signal.severity)}
                  </p>
                </div>
                <span className={`shrink-0 rounded-full px-3 py-1 text-[11px] font-semibold ${severityBadgeClass(signal.severity)}`}>
                  {severityLabel(signal.severity)}
                </span>
              </div>
              <p className="mt-4 text-[14px] leading-relaxed text-[#374151]">{signal.description}</p>
            </section>

            <section className="rounded-xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
              <h2 className="text-[16px] font-semibold text-[#0D1B2A]">Trend Comparison</h2>
              {typeof signal.previousCount === "number" && trend ? (
                <div className="mt-4 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-center">
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center">
                    <p className="text-[28px] font-bold text-[#0D1B2A]">{signal.previousCount}</p>
                    <p className="mt-1 text-[12px] text-[#6B7280]">Previous Cycle</p>
                  </div>
                  <div
                    className={`text-center text-[14px] font-semibold ${
                      trend.direction === "up"
                        ? "text-[#DC2626]"
                        : trend.direction === "down"
                          ? "text-[#059669]"
                          : "text-[#6B7280]"
                    }`}
                  >
                    {trend.label} {trend.delta > 0 ? "+" : ""}
                    {trend.delta} ({trend.percent}%)
                  </div>
                  <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-center">
                    <p className="text-[28px] font-bold text-[#0D1B2A]">{signal.frequencyCount}</p>
                    <p className="mt-1 text-[12px] text-[#6B7280]">Current Cycle</p>
                  </div>
                </div>
              ) : (
                <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
                  <p className="text-[28px] font-bold text-[#0D1B2A]">{signal.frequencyCount}</p>
                  <p className="mt-1 text-[12px] text-[#6B7280]">Current Cycle</p>
                  <p className="mt-3 text-[13px] text-[#6B7280]">Trend data will appear after your next upload.</p>
                </div>
              )}
            </section>

            {excerpts.length > 0 ? (
              <section className="rounded-xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
                <h2 className="text-[14px] font-semibold text-[#374151]">Representative Anonymized Client Feedback</h2>
                <p className="mt-1 text-[12px] italic text-[#9CA3AF]">
                  These excerpts illustrate the detected pattern. They are anonymized and selected as representative
                  examples.
                </p>
                <div className="mt-4 space-y-3">
                  {excerpts.map((excerpt) => (
                    <ClientQuoteCard
                      key={excerpt.id}
                      quote={excerpt.text}
                      issue={signal.category}
                      sentiment={excerpt.sentiment}
                      meta={`Anonymous client feedback, ${excerpt.dateLabel}`}
                    />
                  ))}
                </div>
              </section>
            ) : null}

            <section className="rounded-xl border border-[#E5E7EB] bg-white p-6 shadow-sm">
              <h2 className="text-[16px] font-semibold text-[#0D1B2A]">Governance Actions for This Client Issue</h2>
              {relatedActions.length > 0 ? (
                <div className="mt-4 space-y-3">
                  {relatedActions.map((action) => (
                    <div key={action.id} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                      <p className="text-sm font-semibold text-[#0D1B2A]">{action.title}</p>
                      <p className="mt-1 text-[13px] text-[#374151]">
                        Owner: {action.owner || "Unassigned"} | Status: {action.status} | Due:{" "}
                        <span className={isActionOverdue(action) ? "text-[#DC2626]" : "text-[#374151]"}>
                          {action.due_date ? formatMonthDay(action.due_date) : "Not set"}
                        </span>
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-4">
                  <p className="text-sm text-[#6B7280]">No action assigned</p>
                  <button
                    type="button"
                    className="mt-3 rounded-[6px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#16263b]"
                    onClick={() => setShowActionForm(true)}
                  >
                    Create Governance Action
                  </button>
                </div>
              )}

              {showActionForm ? (
                <ActionForm
                  open
                  mode="create"
                  initialValues={actionPrefill}
                  ownerOptions={ownerOptions}
                  submitting={submittingAction}
                  submitLabel="Create Governance Action"
                  submittingLabel="Creating..."
                  serverError={actionError}
                  onCancel={() => {
                    if (submittingAction) return;
                    setActionError("");
                    setShowActionForm(false);
                  }}
                  onSubmit={handleCreateAction}
                />
              ) : null}
            </section>
          </div>
        ) : null}
      </PageWrapper>
  );
};

export default SignalDetail;
