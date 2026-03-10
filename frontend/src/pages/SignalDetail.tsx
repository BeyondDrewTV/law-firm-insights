/**
 * SignalDetail — Governance Hub Layout
 * ─────────────────────────────────────────────────────────────────────────────
 * Two-column layout on desktop (lg+):
 *
 *   ┌────────────────────────────────┬──────────────────────┐
 *   │  LEFT COLUMN (~60%)            │  RIGHT COLUMN (~40%) │
 *   │                                │                      │
 *   │  Signal header (title + desc)  │  Risk summary panel  │
 *   │  Representative feedback       │  Briefs panel        │
 *   │  Linked actions                │  Timeline            │
 *   └────────────────────────────────┴──────────────────────┘
 *
 * Mobile (< lg): stacked order — summary → feedback → actions → briefs
 * via CSS order utilities on the right-column panels.
 *
 * No data-fetching changes — same API calls, same state, layout only.
 * ─────────────────────────────────────────────────────────────────────────────
 */

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
import GovernanceCard from "@/components/governance/GovernanceCard";
import GovStatusChip, {
  resolveChipVariantForSeverity,
  resolveChipVariantForActionStatus,
} from "@/components/governance/GovStatusChip";
import PageWrapper from "@/components/governance/PageWrapper";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

// ── Types ─────────────────────────────────────────────────────────────────────

type SignalSeverity = "high" | "medium" | "low";

type SignalModel = {
  id: string;
  title: string;
  description: string;
  severity: SignalSeverity;
  frequencyCount: number;
  category: string;
  previousCount: number | null;
  createdAt?: string;
};

type ExcerptModel = {
  id: string;
  text: string;
  dateLabel: string;
  sentiment: "complaint" | "praise";
};

// ── Pure helper functions ─────────────────────────────────────────────────────

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

const formatLong = (value?: string | null) => {
  if (!value) return "Not available";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Not available";
  return date.toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" });
};

const formatPeriod = (report: ReportDetail | null) => {
  if (!report) return "Not available";
  const start = report.review_date_start ? new Date(report.review_date_start) : null;
  const end = report.review_date_end ? new Date(report.review_date_end) : null;
  const validStart = Boolean(start && Number.isFinite(start?.getTime()));
  const validEnd = Boolean(end && Number.isFinite(end?.getTime()));
  if (validStart && validEnd && start && end) {
    const sameYear = start.getFullYear() === end.getFullYear();
    if (sameYear) {
      return `${start.toLocaleDateString([], { month: "short" })}–${end.toLocaleDateString([], { month: "short", year: "numeric" })}`;
    }
    return `${start.toLocaleDateString([], { month: "short", year: "numeric" })} – ${end.toLocaleDateString([], { month: "short", year: "numeric" })}`;
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

const actionStatusLabel = (action: ReportActionItem) => {
  if (isActionOverdue(action)) return "Overdue";
  if (action.status === "done") return "Completed";
  if (action.status === "in_progress") return "In Progress";
  if (action.status === "blocked") return "Blocked";
  return "Open";
};

// ── Component ─────────────────────────────────────────────────────────────────

const SignalDetail = () => {
  const { signalId } = useParams<{ signalId: string }>();
  const route = useMemo(() => parseSignalRoute(signalId), [signalId]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [reportListItem, setReportListItem] = useState<ReportListItem | null>(null);
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
          setReportListItem(null);
          setSignal(null);
          setExcerpts([]);
          setActions([]);
          setLoading(false);
          return;
        }

        setReportListItem(targetReport);
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
          createdAt: targetReport.created_at,
          description:
            (currentSignal?.description || "").trim() ||
            "Recurring client feedback indicating delayed responses or poor communication during matters.",
        });

        const usingComplaints = topComplaints.length > 0;
        const sourceExcerpts = usingComplaints ? topComplaints : (detail.top_praise || []);
        const excerptItems = sourceExcerpts.slice(0, 5).map((text, idx) => ({
          id: `${targetReport.id}-excerpt-${idx + 1}`,
          text: String(text || "").trim(),
          dateLabel: formatMonthYear(detail.review_date_end || detail.created_at),
          sentiment: usingComplaints ? ("complaint" as const) : ("praise" as const),
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
    return () => { active = false; };
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
    if (!signal) return { title: "", owner: "", owner_user_id: null, due_date: "", status: "open", timeframe: "Days 1-30", kpi: "", notes: "" };
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

  // Briefs panel: this signal's cycle has a brief if a ready report exists
  const briefsForSignal = useMemo(() => {
    if (!reportListItem) return [];
    return [{
      id: reportListItem.id,
      label: `${formatMonthYear(reportListItem.created_at)} Brief`,
      period: periodLabel,
    }];
  }, [reportListItem, periodLabel]);

  // Timeline events derived from existing data
  const timeline = useMemo(() => {
    const events: { label: string; date: string; note?: string }[] = [];
    if (signal?.createdAt) {
      events.push({ label: "Signal detected", date: formatLong(signal.createdAt) });
    }
    if (signal?.severity === "high") {
      events.push({ label: "Flagged for escalation", date: formatLong(signal.createdAt), note: "High severity" });
    }
    const latestAction = relatedActions
      .filter((a) => a.updated_at || a.created_at)
      .sort((a, b) => Date.parse(b.updated_at || b.created_at || "") - Date.parse(a.updated_at || a.created_at || ""))[0];
    if (latestAction) {
      events.push({ label: "Action last updated", date: formatLong(latestAction.updated_at || latestAction.created_at) });
    }
    return events;
  }, [signal, relatedActions]);


  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <PageWrapper
      title={`${DISPLAY_LABELS.clientIssueSingular} Detail`}
      description="Evidence, ownership, and leadership visibility in one view."
      contentClassName="stage-sequence"
    >
      {/* Back nav */}
      <div>
        <Link to="/dashboard/signals" className="text-[13px] font-medium text-[#0EA5C2] hover:text-[#0b8ca7]">
          ← Back to Signals
        </Link>
      </div>

      {/* Error state */}
      {error ? (
        <section className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">
          {error}
        </section>
      ) : null}

      {/* Loading state */}
      {loading ? (
        <section className="space-y-4">
          <div className="h-24 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
          <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
            <div className="space-y-4">
              <div className="h-40 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
              <div className="h-32 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
            </div>
            <div className="space-y-4">
              <div className="h-48 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
            </div>
          </div>
        </section>
      ) : signal ? (
        <div className="space-y-6">

          {/* ── Signal header + primary actions ─────────────────────── */}
          <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <GovStatusChip
                    label={severityLabel(signal.severity)}
                    variant={resolveChipVariantForSeverity(signal.severity)}
                  />
                  <span className="gov-type-eyebrow">
                    Client Issue
                  </span>
                </div>
                <h1 className="mt-2 text-[22px] font-bold leading-snug text-[#0D1B2A]">{signal.title}</h1>
                <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-[#374151]">{signal.description}</p>
              </div>
              {/* Primary actions */}
              <div className="flex shrink-0 flex-wrap items-center gap-2 pt-1">
                <button
                  type="button"
                  className="inline-flex items-center rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#16263b]"
                  onClick={() => { setActionError(""); setShowActionForm(true); }}
                >
                  Create Action
                </button>
                <button
                  type="button"
                  disabled
                  title="Available after the next governance brief is generated"
                  className="inline-flex items-center rounded-[8px] border border-[#D1D5DB] bg-white px-4 py-2 text-[13px] font-medium text-slate-400 cursor-not-allowed"
                >
                  Add to Brief
                </button>
              </div>
            </div>
          </section>


          {/* ── Two-column governance hub ────────────────────────────── */}
          {/* Mobile: right-col panels interleave via order utilities    */}
          {/* Desktop (lg+): true two-column grid                        */}
          <div className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-start">

            {/* ════════════════════════════════════════════════════════
                LEFT COLUMN — Evidence + Actions
                On mobile these render between the right-col panels via
                order-2 / order-3 (right-col panels use order-1 / order-4)
                ════════════════════════════════════════════════════════ */}
            <div className="order-2 space-y-6 lg:order-1">

              {/* Representative feedback */}
              {excerpts.length > 0 ? (
                <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                  <div className="mb-1">
                    <p className="gov-type-eyebrow">
                      Representative Feedback
                    </p>
                    <h2 className="mt-1 text-[16px] font-semibold text-[#0D1B2A]">
                      Evidence excerpts from this cycle
                    </h2>
                    <p className="mt-1 text-[12px] italic text-[#9CA3AF]">
                      Anonymized; selected as representative examples only.
                    </p>
                  </div>
                  <div className="mt-4 space-y-3">
                    {excerpts.map((excerpt) => (
                      <ClientQuoteCard
                        key={excerpt.id}
                        quote={excerpt.text}
                        issue={signal.category}
                        sentiment={excerpt.sentiment}
                        meta={`Anonymous client feedback · ${excerpt.dateLabel}`}
                      />
                    ))}
                  </div>
                </section>
              ) : null}

              {/* Linked actions */}
              <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="gov-type-eyebrow">
                      Linked Actions
                    </p>
                    <h2 className="mt-1 text-[16px] font-semibold text-[#0D1B2A]">
                      Governance follow-through
                    </h2>
                  </div>
                  {!showActionForm && relatedActions.length > 0 ? (
                    <button
                      type="button"
                      className="rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                      onClick={() => { setActionError(""); setShowActionForm(true); }}
                    >
                      + Add action
                    </button>
                  ) : null}
                </div>

                {relatedActions.length > 0 ? (
                  <div className="mt-4 space-y-3">
                    {relatedActions.map((action) => (
                      <GovernanceCard
                        key={action.id}
                        title={action.title}
                        chip={
                          <GovStatusChip
                            label={actionStatusLabel(action)}
                            variant={resolveChipVariantForActionStatus(action.status, isActionOverdue(action))}
                            size="sm"
                          />
                        }
                        summary={action.notes || action.kpi || undefined}
                        meta={[
                          action.owner ? `Owner: ${action.owner}` : "Unassigned",
                          action.due_date
                            ? `Due ${formatMonthDay(action.due_date)}${isActionOverdue(action) ? " — overdue" : ""}`
                            : "No due date",
                        ]}
                        accent={
                          isActionOverdue(action) || action.status === "blocked"
                            ? "risk"
                            : action.status === "in_progress"
                              ? "warn"
                              : action.status === "done"
                                ? "success"
                                : "neutral"
                        }
                      />
                    ))}
                  </div>
                ) : (
                  <div className="mt-4">
                    <p className="text-[13px] text-[#6B7280]">
                      No action has been assigned for this signal yet.
                    </p>
                  </div>
                )}

                {!showActionForm && relatedActions.length === 0 ? (
                  <div className="mt-4">
                    <button
                      type="button"
                      className="inline-flex items-center rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#16263b]"
                      onClick={() => { setActionError(""); setShowActionForm(true); }}
                    >
                      Create Governance Action
                    </button>
                  </div>
                ) : null}

                {showActionForm ? (
                  <div className="mt-5 rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
                    <p className="mb-3 gov-type-eyebrow">
                      New action
                    </p>
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
                  </div>
                ) : null}
              </section>
            </div>


            {/* ════════════════════════════════════════════════════════
                RIGHT COLUMN — Summary · Briefs · Timeline
                On mobile: order-1 renders summary first (above evidence),
                order-3 renders briefs/timeline after actions.
                ════════════════════════════════════════════════════════ */}
            <div className="order-1 space-y-4 lg:order-2">

              {/* Risk summary panel */}
              <aside className="rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <p className="gov-type-eyebrow">
                  Signal Summary
                </p>

                <dl className="mt-3 space-y-3">
                  {/* Risk level */}
                  <div className="flex items-center justify-between gap-2">
                    <dt className="text-[12px] text-slate-500">Risk level</dt>
                    <dd>
                      <GovStatusChip
                        label={severityLabel(signal.severity)}
                        variant={resolveChipVariantForSeverity(signal.severity)}
                        size="sm"
                      />
                    </dd>
                  </div>

                  {/* Frequency */}
                  <div className="flex items-center justify-between gap-2">
                    <dt className="text-[12px] text-slate-500">Affected reviews</dt>
                    <dd className="text-[13px] font-semibold text-[#0D1B2A]">{signal.frequencyCount}</dd>
                  </div>

                  {/* Trend */}
                  {trend ? (
                    <div className="flex items-center justify-between gap-2">
                      <dt className="text-[12px] text-slate-500">vs prior cycle</dt>
                      <dd
                        className={[
                          "text-[13px] font-semibold",
                          trend.direction === "up"
                            ? "text-[#DC2626]"
                            : trend.direction === "down"
                              ? "text-[#059669]"
                              : "text-[#6B7280]",
                        ].join(" ")}
                      >
                        {trend.delta > 0 ? "+" : ""}{trend.delta} ({trend.percent}%)
                      </dd>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-2">
                      <dt className="text-[12px] text-slate-500">vs prior cycle</dt>
                      <dd className="text-[12px] text-slate-400">First cycle</dd>
                    </div>
                  )}

                  {/* Review period */}
                  <div className="flex items-center justify-between gap-2">
                    <dt className="text-[12px] text-slate-500">Review period</dt>
                    <dd className="text-[12px] font-medium text-[#374151]">{periodLabel}</dd>
                  </div>

                  {/* Open actions */}
                  <div className="flex items-center justify-between gap-2">
                    <dt className="text-[12px] text-slate-500">Linked actions</dt>
                    <dd className="text-[13px] font-semibold text-[#0D1B2A]">{relatedActions.length}</dd>
                  </div>
                </dl>
              </aside>

              {/* Governance Briefs panel */}
              <aside className="order-3 rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] lg:order-none">
                <p className="gov-type-eyebrow">
                  In Governance Briefs
                </p>
                {briefsForSignal.length > 0 ? (
                  <ul className="mt-3 space-y-2">
                    {briefsForSignal.map((brief) => (
                      <li key={brief.id}>
                        <Link
                          to={`/dashboard/reports/${brief.id}`}
                          className="flex items-center justify-between gap-2 rounded-[8px] border border-[#E5E7EB] bg-[#FAFBFC] px-3 py-2.5 transition-colors hover:bg-slate-50"
                        >
                          <div>
                            <p className="text-[13px] font-medium text-[#0D1B2A]">{brief.label}</p>
                            <p className="text-[11px] text-slate-400">{brief.period}</p>
                          </div>
                          <span className="text-[11px] font-medium text-[#0EA5C2]">View →</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-3 text-[12px] text-slate-400">
                    This signal has not yet appeared in a completed brief.
                  </p>
                )}
              </aside>

              {/* Timeline */}
              <aside className="order-4 rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] lg:order-none">
                <p className="gov-type-eyebrow">
                  Activity Timeline
                </p>
                {timeline.length > 0 ? (
                  <ol className="relative mt-3 ml-2 space-y-4 border-l border-[#E5E7EB] pl-4">
                    {timeline.map((event, idx) => (
                      <li key={`timeline-${idx}`} className="relative">
                        {/* Dot */}
                        <span className="absolute -left-[21px] top-[3px] h-2 w-2 rounded-full border-2 border-[#0EA5C2] bg-white" />
                        <p className="text-[13px] font-medium text-[#0D1B2A]">{event.label}</p>
                        <p className="text-[11px] text-slate-400">{event.date}</p>
                        {event.note ? (
                          <p className="mt-0.5 text-[11px] text-slate-400 italic">{event.note}</p>
                        ) : null}
                      </li>
                    ))}
                  </ol>
                ) : (
                  <p className="mt-3 text-[12px] text-slate-400">No timeline events available.</p>
                )}
              </aside>

            </div>
            {/* end right column */}
          </div>
          {/* end two-column grid */}

        </div>
      ) : null}
    </PageWrapper>
  );
};

export default SignalDetail;
