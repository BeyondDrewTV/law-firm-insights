import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Info, X } from "lucide-react";
import { toast } from "sonner";

import {
  createReportAction,
  getReportDetail,
  getReportGovernanceSignals,
  getReports,
  type GovernanceSignal,
  type ReportDetail,
  type ReportListItem,
} from "@/api/authService";
import ActionForm, { type ActionFormValues } from "@/components/actions/ActionForm";
import PageWrapper from "@/components/governance/PageWrapper";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import InfoTooltip from "@/components/InfoTooltip";
import { useAuth } from "@/contexts/AuthContext";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

type SignalItem = {
  id: string;
  title: string;
  category: string;
  frequencyCount: number;
  previousCount: number | null;
  severity: "High" | "Medium" | "Low";
  description: string;
};

type GovernanceSignalLike = GovernanceSignal & {
  category?: string;
  signal_type?: string;
  theme?: string;
  frequency?: number;
  count?: number;
  source_reviews?: unknown[];
  excerpts?: unknown[];
  summary?: string;
  text?: string;
};

const toTitleCase = (value: string) =>
  value
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");

const compactWhitespace = (value: string) => value.replace(/\s+/g, " ").trim();

const truncate = (value: string, max = 60) => (value.length <= max ? value : `${value.slice(0, max - 1).trim()}...`);

const deriveCategoryLabel = (input: string, fallbackIndex: number): string => {
  const raw = compactWhitespace((input || "").replace(/[\r\n]+/g, " ").trim());
  if (!raw) return `${DISPLAY_LABELS.clientIssueSingular} ${fallbackIndex + 1}`;

  const colonSplit = raw.includes(":") ? raw.split(":").filter(Boolean).map(compactWhitespace) : [];
  const colonCandidate = colonSplit.length > 1 ? colonSplit[0] : raw;
  const sentence = compactWhitespace(colonCandidate.replace(/[.!?]+$/g, ""));
  const words = sentence.split(" ").filter(Boolean);

  if (words.length >= 1 && words.length <= 5 && sentence.length <= 60) {
    return toTitleCase(sentence);
  }

  const phraseCandidates = raw
    .split(/[.!?]/)
    .map(compactWhitespace)
    .filter(Boolean);
  const lastPhrase = phraseCandidates[phraseCandidates.length - 1] || sentence;
  const lastWords = lastPhrase.split(" ").filter(Boolean);
  const compact = lastWords.slice(-5).join(" ");
  if (compact) return toTitleCase(truncate(compact, 60));

  return toTitleCase(truncate(sentence, 60));
};

const resolveSignalTitle = (signal: GovernanceSignalLike, fallbackTitle: string, fallbackIndex: number): string => {
  const categoryCandidate =
    signal.category ||
    signal.theme ||
    signal.signal_type ||
    signal.title ||
    fallbackTitle;
  return deriveCategoryLabel(String(categoryCandidate || ""), fallbackIndex);
};

const resolveSignalDescription = (signal: GovernanceSignalLike, fallbackTitle: string): string => {
  const candidate =
    signal.description ||
    signal.summary ||
    signal.text ||
    `Detected recurring feedback pattern for ${fallbackTitle}. Review and assign ownership.`;
  const clean = compactWhitespace(String(candidate || ""));
  return truncate(clean || `Detected recurring feedback pattern for ${fallbackTitle}.`, 180);
};

const resolveSignalFrequency = (signal: GovernanceSignalLike, fallback: number): number => {
  const countCandidate =
    typeof signal.count === "number"
      ? signal.count
      : typeof signal.frequency === "number"
        ? signal.frequency
        : Array.isArray(signal.source_reviews)
          ? signal.source_reviews.length
          : Array.isArray(signal.excerpts)
            ? signal.excerpts.length
            : fallback;
  if (!Number.isFinite(countCandidate)) return fallback;
  if (countCandidate <= 0) return fallback;
  if (countCandidate > 0 && countCandidate < 1) return Math.max(1, Math.round(countCandidate * 100));
  return Math.round(countCandidate);
};

const SignalsPage = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [latestReport, setLatestReport] = useState<ReportListItem | null>(null);
  const [detail, setDetail] = useState<ReportDetail | null>(null);
  const [governanceSignals, setGovernanceSignals] = useState<GovernanceSignalLike[]>([]);
  const [previousGovernanceSignals, setPreviousGovernanceSignals] = useState<GovernanceSignalLike[]>([]);
  const [selectedSignal, setSelectedSignal] = useState<SignalItem | null>(null);
  const [actionModalOpen, setActionModalOpen] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionError, setActionError] = useState("");
  const [readyReportCount, setReadyReportCount] = useState(0);
  const [baselineDismissed, setBaselineDismissed] = useState(false);

  const baselineDismissKey = useMemo(
    () => `baseline-analysis-dismissed:${user?.firm_id ?? user?.email ?? "unknown"}`,
    [user?.email, user?.firm_id],
  );

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      const reportsResult = await getReports(50);
      if (!mounted) return;
      if (!reportsResult.success || !reportsResult.reports) {
      setError(reportsResult.error || "Unable to load client issues.");
        setLoading(false);
        return;
      }

      const latestReady = reportsResult.reports
        .filter((r) => r.status === "ready")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
      const readyReports = reportsResult.reports.filter((r) => r.status === "ready");
      const previousReady = reportsResult.reports
        .filter((r) => r.status === "ready")
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[1];
      setReadyReportCount(readyReports.length);

      if (!latestReady) {
        setLatestReport(null);
        setDetail(null);
        setError("");
        setLoading(false);
        return;
      }

      setLatestReport(latestReady);
      const [detailResult, governanceSignalsResult, previousGovernanceSignalsResult] = await Promise.all([
        getReportDetail(latestReady.id),
        getReportGovernanceSignals(latestReady.id),
        previousReady?.id ? getReportGovernanceSignals(previousReady.id) : Promise.resolve({ success: false as const }),
      ]);
      if (!mounted) return;
      if (!detailResult.success || !detailResult.report) {
        setDetail(null);
        setGovernanceSignals([]);
        setError(detailResult.error || "Unable to load client issue details.");
        setLoading(false);
        return;
      }

      setDetail(detailResult.report);
      setGovernanceSignals(
        governanceSignalsResult.success && governanceSignalsResult.signals
          ? (governanceSignalsResult.signals as GovernanceSignalLike[])
          : [],
      );
      setPreviousGovernanceSignals(
        previousGovernanceSignalsResult.success && previousGovernanceSignalsResult.signals
          ? (previousGovernanceSignalsResult.signals as GovernanceSignalLike[])
          : [],
      );
      setError("");
      setLoading(false);
    };
    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const dismissed = window.localStorage.getItem(baselineDismissKey) === "1";
    setBaselineDismissed(dismissed);
  }, [baselineDismissKey]);

  const previousSignalCountsByCategory = useMemo(() => {
    const counts = new Map<string, number>();
    previousGovernanceSignals.forEach((signal, index) => {
      const key = resolveSignalTitle(signal, signal.title || `${DISPLAY_LABELS.clientIssueSingular} ${index + 1}`, index).trim().toLowerCase();
      const frequency = resolveSignalFrequency(signal, 0);
      if (!key) return;
      if (!Number.isFinite(frequency)) return;
      counts.set(key, frequency);
    });
    return counts;
  }, [previousGovernanceSignals]);

  const signals = useMemo<SignalItem[]>(() => {
    if (!detail) return [];
    const complaints = Array.isArray(detail.top_complaints) ? detail.top_complaints : [];
    if (governanceSignals.length > 0) {
      return governanceSignals.slice(0, 12).map((signal, index) => {
        const fallbackTitle = complaints[index] || "Client feedback issue";
        const resolvedTitle = resolveSignalTitle(signal, fallbackTitle, index);
        const categoryKey = resolvedTitle.trim().toLowerCase();
        const frequencyCount = resolveSignalFrequency(signal, Math.max(3, 15 - index));
        const normalizedSeverity = String(signal.severity || "").toLowerCase();
        const severity: SignalItem["severity"] =
          normalizedSeverity === "high"
            ? "High"
            : normalizedSeverity === "medium"
              ? "Medium"
              : "Low";

        return {
          id: `${detail.id}-${index + 1}`,
          title: resolvedTitle,
          category: resolvedTitle,
          frequencyCount,
          previousCount: previousSignalCountsByCategory.get(categoryKey) ?? null,
          severity,
          description: resolveSignalDescription(signal, fallbackTitle),
        };
      });
    }

    return complaints.slice(0, 12).map((complaint, index) => {
      const frequencyCount = Math.max(3, 15 - index);
      const severity: SignalItem["severity"] = index < 2 ? "High" : index < 5 ? "Medium" : "Low";
      const title = deriveCategoryLabel(complaint, index);
      return {
        id: `${detail.id}-${index + 1}`,
        title,
        category: title,
        frequencyCount,
        previousCount: previousSignalCountsByCategory.get(title.trim().toLowerCase()) ?? null,
        severity,
        description: `Detected recurring feedback on ${title.toLowerCase()}. Review and assign an owner for governance follow-through.`,
      };
    });
  }, [detail, governanceSignals, previousSignalCountsByCategory]);

  const isNewOnlyFilter = searchParams.get("filter") === "new";
  const filteredSignals = useMemo(() => {
    if (!isNewOnlyFilter) return signals;
    return signals.filter((signal) => (signal.previousCount ?? 0) <= 0);
  }, [isNewOnlyFilter, signals]);

  const clearUrlFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("filter");
    setSearchParams(next);
  };

  const latestReportDateLabel = useMemo(() => {
    if (!latestReport?.created_at) return null;
    const date = new Date(latestReport.created_at);
    if (!Number.isFinite(date.getTime())) return null;
    return date.toLocaleDateString([], { month: "long", day: "numeric", year: "numeric" });
  }, [latestReport?.created_at]);

  const newSignalsCount = useMemo(
    () => signals.filter((signal) => (signal.previousCount ?? 0) <= 0).length,
    [signals],
  );

  const severityClass = (severity: SignalItem["severity"]) => {
    if (severity === "High") return "border-l-[3px] border-l-[#EF4444]";
    if (severity === "Medium") return "border-l-[3px] border-l-[#F59E0B]";
    return "border-l-[3px] border-l-[#10B981]";
  };

  const severityBadgeClass = (severity: SignalItem["severity"]) => {
    if (severity === "High") return "bg-[#FEF2F2] text-[#DC2626]";
    if (severity === "Medium") return "bg-[#FFFBEB] text-[#D97706]";
    return "bg-[#ECFDF5] text-[#10B981]";
  };

  const actionFormInitialValues = useMemo<ActionFormValues>(() => {
    if (!selectedSignal) {
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
      title: `Review ${selectedSignal.category}`,
      owner: "",
      owner_user_id: null,
      due_date: "",
      status: "open",
      timeframe: "Days 1-30",
      kpi: "Owner assigned and remediation plan approved.",
      notes: selectedSignal.description,
    };
  }, [selectedSignal]);

  const openActionForm = (signal: SignalItem) => {
    setActionError("");
    setSelectedSignal(signal);
    setActionModalOpen(true);
  };

  const closeActionForm = () => {
    setActionError("");
    setActionModalOpen(false);
    setSelectedSignal(null);
  };

  const handleCreateAction = async (values: ActionFormValues) => {
    if (!latestReport?.id) {
      setActionError("No report is available for action creation.");
      return;
    }

    setSubmittingAction(true);
    setActionError("");
    const result = await createReportAction(latestReport.id, {
      title: values.title,
      owner: values.owner || undefined,
      owner_user_id: values.owner_user_id,
      status: values.status,
      due_date: values.due_date || null,
      timeframe: values.timeframe,
      kpi: values.kpi,
      notes: values.notes,
    });

    setSubmittingAction(false);

    if (!result.success) {
      setActionError(result.error || "Unable to create action.");
      return;
    }

    toast.success("Governance action created.");
    closeActionForm();
  };

  const signalSharePercent = (frequencyCount: number) => {
    const totalReviews = Number(detail?.total_reviews || latestReport?.total_reviews || 0);
    if (!Number.isFinite(totalReviews) || totalReviews <= 0) return null;
    const ratio = (frequencyCount / totalReviews) * 100;
    return `${Math.max(0, Math.min(100, ratio)).toFixed(1)}% of analyzed reviews`;
  };

  const trendChange = (current: number, previous: number) => {
    const delta = current - previous;
    if (previous <= 0) {
      const direction = delta > 0 ? "Increase" : delta < 0 ? "Decrease" : "No change";
      const percent = delta === 0 ? "0%" : "100%";
      return { delta, direction, percent };
    }
    const percentChange = Math.round((Math.abs(delta) / previous) * 100);
    const direction = delta > 0 ? "Increase" : delta < 0 ? "Decrease" : "No change";
    return { delta, direction, percent: `${percentChange}%` };
  };
  const showBaselineNotice = readyReportCount === 1 && !baselineDismissed;
  const dismissBaselineNotice = () => {
    window.localStorage.setItem(baselineDismissKey, "1");
    setBaselineDismissed(true);
  };

  return (
      <PageWrapper
        eyebrow="Review Surface"
        title={DISPLAY_LABELS.clientIssuePlural}
        description="Detected recurring themes in client feedback that may require governance action."
        contentClassName="stage-sequence"
        actions={
          <InfoTooltip
            title={DISPLAY_LABELS.clientIssueTooltipTitle}
            body={DISPLAY_LABELS.clientIssueTooltipBody}
          />
        }
      >
        {showBaselineNotice ? (
          <section className="relative rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-[18px] py-[14px]">
            <button
              type="button"
              onClick={dismissBaselineNotice}
              aria-label="Dismiss baseline notice"
              className="absolute right-3 top-3 inline-flex h-6 w-6 items-center justify-center rounded text-slate-500 transition-colors hover:bg-slate-200/60 hover:text-slate-700"
            >
              <X size={14} />
            </button>
            <div className="pr-8">
              <div className="flex items-center gap-2">
                <Info size={16} className="text-[#0EA5C2]" />
                <h2 className="text-[14px] font-semibold text-[#1E40AF]">Baseline Analysis</h2>
              </div>
              <p className="mt-1 text-[13px] leading-relaxed text-[#374151]">
                This is your first review cycle. Future uploads will allow the system to detect trends and changes
                over time. Your client issues reflect patterns from this upload only.
              </p>
            </div>
          </section>
        ) : null}

        {error ? <div className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">{error}</div> : null}

        {isNewOnlyFilter ? (
          <section className="rounded-xl border border-amber-200 bg-amber-50 p-4 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-amber-900">Showing: New Client Issues Only</p>
              <button type="button" className="gov-btn-secondary" onClick={clearUrlFilter}>
                Clear filter
              </button>
            </div>
          </section>
        ) : null}

        {!loading && !error && latestReport ? (
          <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
            <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr] xl:items-start">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Current issue set</p>
                <h2 className="mt-2 text-[20px] font-semibold text-[#0D1B2A]">
                  Start with the recurring themes from {latestReportDateLabel || "the latest ready cycle"}.
                </h2>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-700">
                  Review the patterns that now deserve attention, then open a single issue for details or action creation. Use the filtered view only when you specifically need what is newly introduced.
                </p>
              </div>
              <div className="workspace-inline-stats">
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Visible issues</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{filteredSignals.length}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">New vs prior cycle</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{newSignalsCount}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Cycle date</p>
                  <p className="mt-1 text-[16px] font-semibold text-slate-900">{latestReportDateLabel || "Not available"}</p>
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {loading ? (
          <section className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <article key={`signal-skeleton-${index}`} className="rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm">
                <div className="h-4 w-40 rounded bg-neutral-200" />
                <div className="mt-3 h-3 w-20 rounded bg-neutral-100" />
                <div className="mt-4 h-7 w-16 rounded bg-neutral-200" />
              </article>
            ))}
          </section>
        ) : filteredSignals.length === 0 ? (
          <section className="rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm text-center">
            <h2 className="text-lg font-medium text-neutral-900">
              {isNewOnlyFilter ? "No new client issues in the latest cycle" : "No client issues yet"}
            </h2>
            <p className="mt-1 text-sm text-neutral-700">
              {isNewOnlyFilter
                ? "The latest ready report does not introduce any client issue categories that were absent from the previous review cycle."
                : "The first cycle starts with a CSV upload. Clarion will surface recurring client issues here once that review period is processed."}
            </p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
              {!isNewOnlyFilter ? (
                <Link to="/upload" className="gov-btn-primary">
                  Upload feedback CSV
                </Link>
              ) : null}
              <Link to="/dashboard" className="gov-btn-secondary">
                Return to overview
              </Link>
            </div>
            <div className="mt-3">
              <Link to="/demo" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-700">
                Open read-only example cycle
              </Link>
            </div>
          </section>
        ) : (
          <section className="space-y-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">Issue queue</p>
              <p className="mt-1 text-sm text-slate-700">Each card is actionable, but the first pass should stay focused on the themes that carry the strongest current signal.</p>
            </div>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {filteredSignals.map((signal) => (
                <article
                  key={signal.id}
                  className={[
                    "animate-slide-up rounded-[10px] border border-[#E5E7EB] bg-white p-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)] transition-all duration-200 ease-out hover:-translate-y-0.5 hover:shadow-md",
                    severityClass(signal.severity),
                  ].join(" ")}
                >
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-[16px] font-semibold text-[#0D1B2A]">{signal.title}</h2>
                    <span
                      className={[
                        "inline-flex rounded-full px-2 py-0.5 text-[11px] font-semibold",
                        severityBadgeClass(signal.severity),
                      ].join(" ")}
                    >
                      {signal.severity}
                    </span>
                  </div>
                  <p className="mt-2 text-[13px] text-[#6B7280]">Detected in {signal.frequencyCount} reviews</p>
                  {typeof signal.previousCount === "number" ? (
                    <p className="mt-1 text-[12px] text-[#6B7280]">
                      Previous cycle: {signal.previousCount} | Change:{" "}
                      {(() => {
                        const change = trendChange(signal.frequencyCount, signal.previousCount || 0);
                        const deltaPrefix = change.delta > 0 ? "+" : "";
                        const tone =
                          change.delta > 0 ? "text-[#DC2626]" : change.delta < 0 ? "text-[#059669]" : "text-[#6B7280]";
                        return (
                          <span className={`font-semibold ${tone}`}>
                            {deltaPrefix}
                            {change.delta} ({change.direction}
                            {change.percent})
                          </span>
                        );
                      })()}
                    </p>
                  ) : null}
                  <p className="mt-1 text-[13px] text-[#6B7280]">{signalSharePercent(signal.frequencyCount) || "Share not available"}</p>
                  <p className="mt-2 text-sm text-neutral-700">{signal.description}</p>
                  <div className="mt-4">
                    <Link
                      to={`/dashboard/signals/${signal.id}`}
                      className="inline-flex items-center rounded-md bg-[#0D1B2A] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#16263b]"
                    >
                      View Client Issue Details
                    </Link>
                    <button
                      type="button"
                      className="mt-2 block text-[13px] text-[#6B7280] underline underline-offset-4 transition-colors hover:text-[#374151]"
                      onClick={() => openActionForm(signal)}
                    >
                      Create Action Directly
                    </button>
                  </div>
                </article>
              ))}
            </div>
          </section>
        )}

        <Dialog
          open={actionModalOpen}
          onOpenChange={(open) => {
            if (!open) {
              closeActionForm();
              return;
            }
            setActionModalOpen(true);
          }}
        >
          <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create Governance Action</DialogTitle>
              <DialogDescription>
                From client issue: {selectedSignal?.category || "Selected client issue"}
              </DialogDescription>
            </DialogHeader>
            <ActionForm
              open={actionModalOpen && Boolean(selectedSignal)}
              mode="create"
              initialValues={actionFormInitialValues}
              ownerOptions={[]}
              submitting={submittingAction}
              submitLabel="Create Action"
              submittingLabel="Creating..."
              serverError={actionError}
              onCancel={closeActionForm}
              onSubmit={handleCreateAction}
            />
          </DialogContent>
        </Dialog>

        {latestReport ? (
          <p className="text-xs text-neutral-600">
            Based on: {latestReport.name} - {latestReportDateLabel || "Not available"}
          </p>
        ) : null}
      </PageWrapper>
  );
};

export default SignalsPage;
