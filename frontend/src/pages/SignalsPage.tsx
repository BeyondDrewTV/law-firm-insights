import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Info, CheckSquare, Square, X, Layers, RadioTower } from "lucide-react";
import { toast } from "sonner";
import { PageTabs } from "@/components/governance/PageTabs";
import GovernanceEmptyState from "@/components/governance/GovernanceEmptyState";
import { SignalCardSkeleton } from "@/components/governance/skeletons";

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
import PromoteToActionPanel from "@/components/governance/PromoteToActionPanel";
import SignalCard from "@/components/governance/SignalCard";
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
  // ── Workflow tab: "triage" | "all" | "in-briefs" ─────────────────────────
  const [signalsTab, setSignalsTab] = useState<"triage" | "all" | "in-briefs">("all");

  // ── Evidence triage / bulk selection (Phase 6) ───────────────────────────
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkModalOpen, setBulkModalOpen] = useState(false);
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState("");

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

  // ── Tab-filtered signals ────────────────────────────────────────────────
  // "Triage"    → High severity only (needs immediate governance attention)
  // "All"       → Full issue set (existing default behaviour)
  // "In Briefs" → Signals that appear in a completed brief cycle
  //               (all signals on this page derive from a ready report, so
  //                this tab is only meaningful once there is >1 ready cycle:
  //                it shows signals that also existed in the previous cycle,
  //                i.e., persistent/recurring issues already captured in briefs)
  const tabFilteredSignals = useMemo(() => {
    if (signalsTab === "triage") {
      return filteredSignals.filter((s) => s.severity === "High");
    }
    if (signalsTab === "in-briefs") {
      // "In briefs" = signals that appeared in a prior cycle too (previousCount > 0)
      // If no previous cycle exists, falls back to all (so the tab isn't confusing)
      const hasPrevious = filteredSignals.some((s) => typeof s.previousCount === "number" && s.previousCount > 0);
      if (!hasPrevious) return filteredSignals;
      return filteredSignals.filter((s) => typeof s.previousCount === "number" && s.previousCount > 0);
    }
    return filteredSignals; // "all"
  }, [filteredSignals, signalsTab]);

  const triageCount = useMemo(() => filteredSignals.filter((s) => s.severity === "High").length, [filteredSignals]);
  const inBriefsCount = useMemo(
    () => filteredSignals.filter((s) => typeof s.previousCount === "number" && s.previousCount > 0).length,
    [filteredSignals],
  );

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

  // ── Selection helpers (Phase 6) ───────────────────────────────────────────
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    const visibleIds = tabFilteredSignals.map((s) => s.id);
    const allSelected = visibleIds.every((id) => selectedIds.has(id));
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(visibleIds));
    }
  };

  const exitSelectionMode = () => {
    setSelectionMode(false);
    setSelectedIds(new Set());
    setBulkError("");
    setBulkModalOpen(false);
  };

  const selectedSignals = useMemo(
    () => tabFilteredSignals.filter((s) => selectedIds.has(s.id)),
    [tabFilteredSignals, selectedIds],
  );

  const handleBulkCreateSignal = async (values: ActionFormValues) => {
    if (!latestReport?.id) {
      setBulkError("No report available for action creation.");
      return;
    }
    setBulkSubmitting(true);
    setBulkError("");
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
    setBulkSubmitting(false);
    if (!result.success) {
      setBulkError(result.error || "Unable to create governance action.");
      return;
    }
    toast.success(
      selectedSignals.length === 1
        ? "Governance action created."
        : `Governance action created from ${selectedSignals.length} signals.`,
    );
    exitSelectionMode();
  };

  return (
      <PageWrapper
        eyebrow="Client Feedback Evidence"
        title={DISPLAY_LABELS.clientIssuePlural}
        description="The evidence layer behind each governance brief. These recurring patterns from client feedback are what the brief distills into partner-ready decisions and actions."
        contentClassName="stage-sequence"
        actions={
          <div className="flex items-center gap-2">
            {!loading && latestReport && tabFilteredSignals.length > 0 ? (
              selectionMode ? (
                <button
                  type="button"
                  onClick={exitSelectionMode}
                  className="inline-flex items-center gap-1.5 rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-[13px] font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <X size={13} />
                  Exit selection
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setSelectionMode(true)}
                  className="inline-flex items-center gap-1.5 rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-[13px] font-medium text-slate-600 transition-colors hover:bg-slate-50"
                >
                  <Layers size={13} />
                  Select issues
                </button>
              )
            ) : null}
            <InfoTooltip
              title={DISPLAY_LABELS.clientIssueTooltipTitle}
              body={DISPLAY_LABELS.clientIssueTooltipBody}
            />
          </div>
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
                <p className="gov-label">Current issue set</p>
                <h2 className="gov-section-intro mt-2">
                  Recurring client feedback patterns from {latestReportDateLabel || "the latest ready cycle"} — the evidence this governance cycle is built on.
                </h2>
                <p className="gov-body mt-3 max-w-2xl">
                  Review the patterns that now deserve attention, then open a single issue for details or action creation. Use the filtered view only when you specifically need what is newly introduced.
                </p>
              </div>
              <div className="workspace-inline-stats">
                <div className="workspace-inline-stat">
                  <p className="gov-label">Visible issues</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{filteredSignals.length}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">New vs prior cycle</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{newSignalsCount}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">Cycle date</p>
                  <p className="mt-1 text-[16px] font-semibold text-slate-900">{latestReportDateLabel || "Not available"}</p>
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {/* ── Workflow tabs ────────────────────────────────────────────── */}
        {!loading && latestReport ? (
          <PageTabs
            value={signalsTab}
            onValueChange={(v) => {
              setSignalsTab(v as typeof signalsTab);
              // Clear selection when switching tabs — avoids stale cross-tab selections
              setSelectedIds(new Set());
            }}
            tabs={[
              {
                value: "triage",
                label: "Needs Action",
                badgeCount: triageCount,
                badgeUrgent: triageCount > 0,
              },
              { value: "all", label: "Current Cycle" },
              {
                value: "in-briefs",
                label: "In Briefs",
                badgeCount: inBriefsCount > 0 ? inBriefsCount : undefined,
              },
            ]}
          />
        ) : null}

        {loading ? (
          <section aria-label="Loading client issues" className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <SignalCardSkeleton key={`signal-skeleton-${index}`} />
            ))}
          </section>
        ) : filteredSignals.length === 0 ? (
          <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
            <GovernanceEmptyState
              size="lg"
              icon={<RadioTower size={20} />}
              title={isNewOnlyFilter ? "No new client issues in this cycle" : "No client issues yet"}
              description={
                isNewOnlyFilter
                  ? "The latest review cycle does not introduce any issue categories that were absent from the previous period."
                  : "The first governance cycle starts with a CSV upload. Clarion will surface recurring client issues here once that review period is processed."
              }
              primaryAction={!isNewOnlyFilter ? { label: "Upload feedback CSV", href: "/upload" } : undefined}
              secondaryAction={{ label: "Return to dashboard", href: "/dashboard" }}
              footer={
                <Link to="/demo" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-700">
                  Open read-only example cycle
                </Link>
              }
            />
          </section>
        ) : tabFilteredSignals.length === 0 ? (
          <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
            <GovernanceEmptyState
              size="md"
              icon={<RadioTower size={20} />}
              title={
                signalsTab === "triage"
                  ? "No high-risk signals to triage"
                  : signalsTab === "in-briefs"
                    ? "No signals included in a governance brief yet"
                    : "No signals match the current filter"
              }
              description={
                signalsTab === "triage"
                  ? "All current signals are medium or low severity. Review 'All Signals' for the full issue set and emerging patterns."
                  : signalsTab === "in-briefs"
                    ? "Signals are added to a brief when you prepare a governance packet. Return after completing your first brief cycle."
                    : "Adjust the active filter or return to all signals to see the full issue queue."
              }
              primaryAction={{ label: "View all signals", onClick: () => setSignalsTab("all") }}
            />
          </section>
        ) : (
          <section className="space-y-4">
            {/* ── Section label row + select-all ─────────────────────── */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <p className="gov-type-eyebrow">
                  {signalsTab === "triage" ? "High-severity signals" : signalsTab === "in-briefs" ? "Recurring signals in briefs" : "Current cycle evidence"}
                </p>
                <p className="mt-1 text-sm text-slate-700">
                  {selectionMode
                    ? "Click cards or checkboxes to select issues, then create a governance action for all of them at once."
                    : signalsTab === "triage"
                      ? "High-severity patterns from this cycle. These should be the first to receive an owner and a response plan before the governance brief is finalized."
                      : signalsTab === "in-briefs"
                        ? "Signals that appeared in the previous cycle and are now captured in governance briefs."
                        : "These are the patterns the governance brief is built on. Assign actions to the issues that require a partner decision or firm-wide response."}
                </p>
              </div>
              {selectionMode ? (
                <button
                  type="button"
                  onClick={toggleSelectAll}
                  className="inline-flex items-center gap-1.5 text-[13px] font-medium text-[#0EA5C2] hover:text-[#0b8ca7] transition-colors"
                >
                  {tabFilteredSignals.every((s) => selectedIds.has(s.id))
                    ? <><CheckSquare size={14} /> Deselect all</>
                    : <><Square size={14} /> Select all</>
                  }
                </button>
              ) : null}
            </div>

            {/* ── Sticky selection bar ────────────────────────────────── */}
            {selectionMode ? (
              <div
                className={[
                  "sticky top-[56px] z-20 rounded-[10px] border px-4 py-3 transition-all duration-200",
                  selectedIds.size > 0
                    ? "border-[#0EA5C2] bg-[#F0FDFF] shadow-[0_2px_8px_rgba(14,165,194,0.12)]"
                    : "border-[#E5E7EB] bg-white",
                ].join(" ")}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span
                      className={[
                        "inline-flex h-6 min-w-[24px] items-center justify-center rounded-full px-2 text-[12px] font-semibold",
                        selectedIds.size > 0
                          ? "bg-[#0EA5C2] text-white"
                          : "bg-slate-200 text-slate-500",
                      ].join(" ")}
                    >
                      {selectedIds.size}
                    </span>
                    <span className="text-[13px] text-slate-700">
                      {selectedIds.size === 0
                        ? "No issues selected — click cards to select"
                        : selectedIds.size === 1
                          ? "1 issue selected"
                          : `${selectedIds.size} issues selected`}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {selectedIds.size > 0 ? (
                      <>
                        <button
                          type="button"
                          onClick={() => setSelectedIds(new Set())}
                          className="text-[12px] text-slate-500 hover:text-slate-700 transition-colors"
                        >
                          Clear
                        </button>
                        <button
                          type="button"
                          onClick={() => { setBulkError(""); setBulkModalOpen(true); }}
                          className="inline-flex items-center gap-1.5 rounded-[7px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#16263b]"
                        >
                          <Layers size={13} />
                          Create Governance Action{selectedIds.size > 1 ? ` (${selectedIds.size} issues)` : ""}
                        </button>
                      </>
                    ) : null}
                  </div>
                </div>
              </div>
            ) : null}

            {/* ── Signal grid ─────────────────────────────────────────── */}
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {tabFilteredSignals.map((signal) => {
                const trendLabel = typeof signal.previousCount === "number"
                  ? (() => {
                      const change = trendChange(signal.frequencyCount, signal.previousCount || 0);
                      const deltaPrefix = change.delta > 0 ? "+" : "";
                      return `${deltaPrefix}${change.delta} vs prior (${change.direction})`;
                    })()
                  : null;

                return (
                  <SignalCard
                    key={signal.id}
                    id={signal.id}
                    title={signal.title}
                    severity={signal.severity}
                    frequencyCount={signal.frequencyCount}
                    shareLabel={signalSharePercent(signal.frequencyCount)}
                    description={signal.description}
                    previousCount={signal.previousCount}
                    trendLabel={trendLabel}
                    onCreateAction={selectionMode ? undefined : () => openActionForm(signal)}
                    selectionMode={selectionMode}
                    selected={selectedIds.has(signal.id)}
                    onToggleSelect={selectionMode ? toggleSelect : undefined}
                  />
                );
              })}
            </div>
          </section>
        )}

        {/* ── Single-signal action dialog (existing) ───────────────────── */}
        <Dialog
          open={actionModalOpen}
          onOpenChange={(open) => {
            if (!open) { closeActionForm(); return; }
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

        {/* ── Promote-to-Action side panel (Phase 6.2) ─────────────────── */}
        <PromoteToActionPanel
          open={bulkModalOpen}
          onOpenChange={(open) => {
            if (!open) { setBulkModalOpen(false); setBulkError(""); return; }
            setBulkModalOpen(true);
          }}
          selectedSignals={selectedSignals}
          onSubmit={handleBulkCreateSignal}
          submitting={bulkSubmitting}
          submitError={bulkError}
        />

        {latestReport ? (
          <p className="text-xs text-neutral-400 italic">
            Evidence sourced from {latestReport.name} · cycle dated {latestReportDateLabel || "Not available"}
          </p>
        ) : null}
      </PageWrapper>
  );
};

export default SignalsPage;
