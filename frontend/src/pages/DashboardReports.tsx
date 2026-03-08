import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Activity, AlertTriangle, Archive, Clock3 } from "lucide-react";
import {
  getCredits,
  getReportActions,
  getReportDetail,
  getDeletedReports,
  getReports,
  restoreDeletedReport,
    type DeletedReportItem,
  type ReportActionItem,
  type ReportDetail,
  type ReportListItem,
} from "@/api/authService";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import ReportsPanel from "@/components/dashboard/ReportsPanel";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { formatApiDate, formatApiDateTime, parseApiDate, toApiTimestamp } from "@/lib/dateTime";
import { formatFreshnessLine } from "@/utils/freshnessStamp";

const formatDateTime = (value: string) => {
  return formatApiDateTime(value, undefined, value);
};

const isWithinDays = (value: string, days: number) => {
  const parsed = parseApiDate(value);
  if (!parsed) return false;
  return Date.now() - parsed.getTime() <= days * 24 * 60 * 60 * 1000;
};

const wait = (ms: number) =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, ms);
  });

const DashboardReports = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [historyNotice, setHistoryNotice] = useState<string | null>(null);
  const [historyTruncated, setHistoryTruncated] = useState(false);
  const [deletedHistoryNotice, setDeletedHistoryNotice] = useState<string | null>(null);
  const [deletedHistoryTruncated, setDeletedHistoryTruncated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportDetails, setReportDetails] = useState<Record<number, ReportDetail>>({});
  const [reportActions, setReportActions] = useState<Record<number, ReportActionItem[]>>({});
  const [deletedReports, setDeletedReports] = useState<DeletedReportItem[]>([]);
  const [deletedError, setDeletedError] = useState("");
  const [deletedLoading, setDeletedLoading] = useState(true);
  const [canRestoreDeleted, setCanRestoreDeleted] = useState(false);
  const [retentionDays, setRetentionDays] = useState(30);
  const [restoringId, setRestoringId] = useState<number | null>(null);
  const [pendingReportId, setPendingReportId] = useState<number | null>(null);
  const [showDeleted, setShowDeleted] = useState(false);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "processing" | "ready" | "failed">("all");
  const [priorityFilter, setPriorityFilter] = useState<"all" | "at_risk" | "recent">("all");
  const [matterFilter, setMatterFilter] = useState<string>("all");
  const [matterLabels, setMatterLabels] = useState<Record<number, string>>({});
  const [isAllActionsDialogOpen, setIsAllActionsDialogOpen] = useState(false);

  const allActionsDialogTriggerRef = useRef<HTMLButtonElement | null>(null);  const actionBoardRef = useRef<HTMLElement | null>(null);

  // ── Request dedupe ──────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const inflightRef = useRef(new Map<string, Promise<any>>());
  const deduped = <T,>(key: string, fn: () => Promise<T>): Promise<T> => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const hit = inflightRef.current.get(key) as Promise<T> | undefined;
    if (hit) return hit;
    const p = fn().finally(() => inflightRef.current.delete(key));
    inflightRef.current.set(key, p as Promise<unknown>);
    return p;
  };  const matterStorageKey = `reportMatterLabels:${user?.id || user?.email || "anonymous"}`;

  const deletedReportIds = useMemo(() => new Set(deletedReports.map((report) => report.id)), [deletedReports]);
  const activeReports = useMemo(
    () => reports.filter((report) => !deletedReportIds.has(report.id)),
    [deletedReportIds, reports],
  );
  const hasProcessingReports = useMemo(
    () => activeReports.some((report) => report.status === "processing"),
    [activeReports],
  );
  const actionsWorkspaceMode = searchParams.get("workspace") === "actions";
  const actionsWorkspaceView = searchParams.get("view");
  const focusedReportId = Number(searchParams.get("reportId") || 0) || null;
  const focusedActionId = Number(searchParams.get("actionId") || 0) || null;

  const loadReports = useCallback(async () => {
    setIsLoading(true);
    setError("");
    const result = await deduped("reports", () => getReports(100));
    if (result.success && result.reports) {
      setReports(result.reports);
      setHistoryNotice(result.history_notice || null);
      setHistoryTruncated(Boolean(result.history_truncated));
    } else {
      setReports([]);
      setHistoryNotice(null);
      setHistoryTruncated(false);
      setError(result.error || "Unable to load reports.");
    }
    setLastUpdatedAt(new Date());
    setIsLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadDeleted = useCallback(async () => {
    setDeletedLoading(true);
    setDeletedError("");
    const result = await deduped("deleted", () => getDeletedReports(100));
    if (result.success) {
      setDeletedReports(result.reports || []);
      setDeletedHistoryNotice(result.history_notice || null);
      setDeletedHistoryTruncated(Boolean(result.history_truncated));
      setCanRestoreDeleted(Boolean(result.can_restore));
      setRetentionDays(result.retention_days || 30);
    } else {
      setDeletedReports([]);
      setDeletedHistoryNotice(null);
      setDeletedHistoryTruncated(false);
      setDeletedError(result.error || "Unable to load recently deleted reports.");
    }
    setDeletedLoading(false);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const pending = Number(window.sessionStorage.getItem("pendingReportId") || 0);
    if (pending > 0) {
      setPendingReportId(pending);
    }
    void Promise.all([loadReports(), loadDeleted()]);
  }, [loadDeleted, loadReports]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(matterStorageKey);
      if (raw) {
        const parsed = JSON.parse(raw) as Record<string, string>;
        const normalized: Record<number, string> = {};
        Object.entries(parsed).forEach(([key, value]) => {
          const id = Number(key);
          if (Number.isFinite(id) && typeof value === "string") {
            normalized[id] = value;
          }
        });
        setMatterLabels(normalized);
      } else {
        setMatterLabels({});
      }
    } catch {
      setMatterLabels({});
    }
  }, [matterStorageKey]);

  useEffect(() => {
    try {
      window.localStorage.setItem(matterStorageKey, JSON.stringify(matterLabels));
    } catch {
      // Ignore storage write failures so the reports workspace still renders.
    }
  }, [matterLabels, matterStorageKey]);

  const matterOptions = useMemo(
    () =>
      Array.from(
        new Set(
          Object.values(matterLabels)
            .map((value) => value.trim())
            .filter(Boolean),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [matterLabels],
  );

  // Avoid fan-out fetches across many reports. Supporting data should load
  // only for the explicitly focused report detail.
  useEffect(() => {
    if (!focusedReportId) return;
    if (reportDetails[focusedReportId] && reportActions[focusedReportId]) return;
    let cancelled = false;
    const loadFocusedSupportingData = async () => {
      const [detailResult, actionsResult] = await Promise.all([
        deduped(`detail-${focusedReportId}`, () => getReportDetail(focusedReportId)),
        deduped(`actions-${focusedReportId}`, () => getReportActions(focusedReportId)),
      ]);
      if (cancelled) return;
      if (detailResult.success && detailResult.report) {
        setReportDetails((previous) => ({
          ...previous,
          [detailResult.report!.id]: detailResult.report!,
        }));
      }
      if (actionsResult.success && actionsResult.actions) {
        setReportActions((previous) => ({
          ...previous,
          [focusedReportId]: actionsResult.actions || [],
        }));
      }
    };
    void loadFocusedSupportingData();
    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusedReportId, reportActions, reportDetails]);

  const atRiskReportIds = useMemo(() => {
    const atRisk = new Set<number>();
    activeReports.forEach((report) => {
      if (report.status !== "ready") return;
      const detail = reportDetails[report.id];
      if (!detail) return;
      const lowScore = typeof detail.avg_rating === "number" && detail.avg_rating < 4.2;
      const volatileSignal = detail.top_complaints.length > detail.top_praise.length;
      if (lowScore || volatileSignal) {
        atRisk.add(report.id);
      }
    });
    return atRisk;
  }, [activeReports, reportDetails]);

  const filteredReports = useMemo(() => {
    return activeReports.filter((report) => {
      const status = pendingReportId === report.id ? "processing" : report.status;
      if (statusFilter !== "all" && status !== statusFilter) {
        return false;
      }
      if (priorityFilter === "recent" && !isWithinDays(report.created_at, 30)) {
        return false;
      }
      if (priorityFilter === "at_risk") {
        if (status !== "ready" || !atRiskReportIds.has(report.id)) {
          return false;
        }
      }
      const matterLabel = (matterLabels[report.id] || "").trim();
      if (matterFilter === "unassigned") {
        if (matterLabel.length > 0) {
          return false;
        }
      } else if (matterFilter !== "all" && matterLabel !== matterFilter) {
        return false;
      }
      if (!searchQuery.trim()) {
        return true;
      }
      const query = searchQuery.trim().toLowerCase();
      const reportName = String(report.name || "").toLowerCase();
      const reportPlanLabel = String(report.plan_label || "").toLowerCase();
      return (
        reportName.includes(query) ||
        reportPlanLabel.includes(query) ||
        matterLabel.toLowerCase().includes(query)
      );
    });
  }, [activeReports, atRiskReportIds, matterFilter, matterLabels, pendingReportId, priorityFilter, searchQuery, statusFilter]);

  const statusCounts = useMemo(() => {
    return activeReports.reduce(
      (acc, report) => {
        const effectiveStatus = pendingReportId === report.id ? "processing" : report.status;
        if (effectiveStatus === "ready") acc.ready += 1;
        if (effectiveStatus === "processing") acc.processing += 1;
        if (effectiveStatus === "failed") acc.failed += 1;
        return acc;
      },
      { ready: 0, processing: 0, failed: 0 },
    );
  }, [activeReports, pendingReportId]);

  const loadedDetailCount = useMemo(() => Object.keys(reportDetails).length, [reportDetails]);

  const implementationBoardActions = useMemo(() => {
    const rows: Array<{
      id: string;
      reportId: number;
      actionId: number | null;
      reportName: string;
      title: string;
      owner: string;
      timeframe: string;
      status: "Planned" | "In progress" | "Completed" | "Overdue";
      dueAt: number | null;
      atRiskLinked: boolean;
    }> = [];

    activeReports
      .filter((report) => report.status === "ready")
      .slice(0, 12)
      .forEach((report) => {
        const liveActions = reportActions[report.id] || [];
        if (liveActions.length > 0) {
          liveActions.forEach((action) => {
            const dueDate = parseApiDate(action.due_date);
            const isOverdue =
              action.status !== "done" &&
              dueDate &&
              !Number.isNaN(dueDate.getTime()) &&
              dueDate.getTime() < Date.now();
            const status =
              isOverdue
                ? "Overdue"
                : action.status === "done"
                  ? "Completed"
                  : action.status === "in_progress"
                    ? "In progress"
                    : "Planned";
            rows.push({
              id: `live-${report.id}-${action.id}`,
              reportId: report.id,
              actionId: action.id,
              reportName: report.name,
              title: action.title,
              owner: action.owner || "Unassigned",
              timeframe: action.due_date ? `Due ${formatApiDate(action.due_date)}` : "No due date",
              status,
              dueAt: dueDate && !Number.isNaN(dueDate.getTime()) ? dueDate.getTime() : null,
              atRiskLinked: atRiskReportIds.has(report.id),
            });
          });
          return;
        }

        const fallbackRoadmap = reportDetails[report.id]?.implementation_roadmap || [];
        fallbackRoadmap.forEach((item, index) => {
          rows.push({
            id: `roadmap-${report.id}-${index}`,
            reportId: report.id,
            actionId: null,
            reportName: report.name,
            title: item.action || `${item.theme}: ${item.kpi}`,
            owner: item.owner || "Unassigned",
            timeframe: item.timeline || "No timeframe",
            status: "Planned",
            dueAt: null,
            atRiskLinked: atRiskReportIds.has(report.id),
          });
        });
      });

    const statusRank = { Overdue: 0, "In progress": 1, Planned: 2, Completed: 3 } as const;
    return rows.sort((a, b) => {
      const groupRank = (row: (typeof rows)[number]) => {
        if (row.status === "Overdue") return 0;
        if (row.atRiskLinked) return 1;
        return 2;
      };
      const groupDelta = groupRank(a) - groupRank(b);
      if (groupDelta !== 0) return groupDelta;
      const dueA = a.dueAt ?? Number.MAX_SAFE_INTEGER;
      const dueB = b.dueAt ?? Number.MAX_SAFE_INTEGER;
      if (dueA !== dueB) return dueA - dueB;
      const statusDelta = statusRank[a.status] - statusRank[b.status];
      if (statusDelta !== 0) return statusDelta;
      return a.title.localeCompare(b.title);
    });
  }, [activeReports, atRiskReportIds, reportActions, reportDetails]);

  const boardStatusCounts = useMemo(
    () =>
      implementationBoardActions.reduce(
        (acc, item) => {
          if (item.status === "Planned") acc.planned += 1;
          if (item.status === "In progress") acc.inProgress += 1;
          if (item.status === "Completed") acc.completed += 1;
          if (item.status === "Overdue") acc.overdue += 1;
          return acc;
        },
        { planned: 0, inProgress: 0, completed: 0, overdue: 0 },
      ),
    [implementationBoardActions],
  );

  const BOARD_ACTIONS_VISIBLE_COUNT = 6;
  const visibleBoardActions = useMemo(
    () => implementationBoardActions.slice(0, BOARD_ACTIONS_VISIBLE_COUNT),
    [implementationBoardActions],
  );

  const latestReadyReport = useMemo(
    () =>
      [...activeReports]
        .filter((report) => report.status === "ready")
        .sort((a, b) => (toApiTimestamp(b.created_at) || 0) - (toApiTimestamp(a.created_at) || 0))[0] ?? null,
    [activeReports],
  );
  const latestBriefAsOfLabel = useMemo(
    () => formatFreshnessLine("Last report created", latestReadyReport?.created_at ?? null),
    [latestReadyReport?.created_at],
  );
  const startWithTargetReport = useMemo(() => {
    const atRiskReports = activeReports
      .filter((report) => report.status === "ready" && atRiskReportIds.has(report.id))
      .sort((a, b) => (toApiTimestamp(b.created_at) || 0) - (toApiTimestamp(a.created_at) || 0));
    if (atRiskReports.length > 0) {
      return { report: atRiskReports[0], atRisk: true };
    }
    if (latestReadyReport) {
      return { report: latestReadyReport, atRisk: false };
    }
    return { report: null, atRisk: false };
  }, [activeReports, atRiskReportIds, latestReadyReport]);

  const setMatterLabel = useCallback((reportId: number, label: string) => {
    setMatterLabels((previous) => ({
      ...previous,
      [reportId]: label,
    }));
  }, []);

  useEffect(() => {
    const pendingFromStorage = Number(window.sessionStorage.getItem("pendingReportId") || 0);
    const shouldPoll = hasProcessingReports || pendingReportId !== null || pendingFromStorage > 0;
    if (!shouldPoll) {
      return;
    }

    let isCancelled = false;
    let isFetching = false;

    const pollReports = async () => {
      if (isCancelled || isFetching) return;
      isFetching = true;
      const result = await getReports(100);
      isFetching = false;
      if (isCancelled || !result.success || !result.reports) return;

      setReports(result.reports);

      const activePendingId = pendingReportId || Number(window.sessionStorage.getItem("pendingReportId") || 0) || null;
      if (!activePendingId) return;

      const pendingReport = result.reports.find((report) => report.id === activePendingId) || null;
      if (pendingReport && pendingReport.status !== "processing") {
        setPendingReportId(null);
        window.sessionStorage.removeItem("pendingReportId");
        if (pendingReport.status === "ready") {
          toast.success(`Report ready: ${pendingReport.name}`);
        }
        return;
      }

      const activeResultReports = result.reports.filter((report) => !deletedReportIds.has(report.id));
      if (!pendingReport && !activeResultReports.some((report) => report.status === "processing")) {
        setPendingReportId(null);
        window.sessionStorage.removeItem("pendingReportId");
      }
    };

    void pollReports();
    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== "visible") return;
      void pollReports();
    }, 2500);

    const onVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void pollReports();
      }
    };
    document.addEventListener("visibilitychange", onVisibilityChange);

    return () => {
      isCancelled = true;
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", onVisibilityChange);
    };
  }, [deletedReportIds, hasProcessingReports, pendingReportId]);

  useEffect(() => {
    if (!actionsWorkspaceMode) return;
    if (actionsWorkspaceView === "all") {
      setIsAllActionsDialogOpen(true);
    }
    window.requestAnimationFrame(() => {
      actionBoardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [actionsWorkspaceMode, actionsWorkspaceView]);

  const handleRestore = async (reportId: number) => {
    setRestoringId(reportId);
    const result = await restoreDeletedReport(reportId);
    if (result.success) {
      toast.success(result.report?.name ? `${result.report.name} restored.` : "Report restored.");
      await Promise.all([loadReports(), loadDeleted()]);
    } else {
      toast.error(result.error || "Unable to restore this report right now.");
    }
    setRestoringId(null);
  };

  // ── Status badge helper (shared by board + dialog) ──────────────
  const statusChipClass = (status: "Planned" | "In progress" | "Completed" | "Overdue") => {
    if (status === "Completed") return "border-emerald-500/35 bg-emerald-500/12 text-emerald-800 dark:text-emerald-200";
    if (status === "In progress") return "border-sky-400/45 bg-sky-500/12 text-sky-800 dark:text-sky-200";
    if (status === "Overdue") return "border-rose-500/35 bg-rose-500/12 text-rose-800 dark:text-rose-200";
    return "border-slate-400/35 bg-slate-500/10 text-slate-800 dark:text-slate-200";
  };

  return (
    <WorkspaceLayout>
      <section className="stage-sequence space-y-5">

        {/* ── Hero ─────────────────────────────────────────────── */}
        <div className="workspace-panel-card rounded-2xl border border-border/60 bg-background/60 p-6">
          {/* Title + controls row */}
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-foreground">Reports</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                Browse all reports, jump into details, and manage your firm's feedback history.
              </p>
            </div>
            <div className="flex shrink-0 flex-wrap items-center gap-2">
              <div className="inline-flex items-center gap-2 rounded border border-neutral-200 bg-white px-2.5 py-1.5 text-xs text-neutral-700">
                <span className="font-medium text-neutral-600">Start with:</span>
                <button
                  type="button"
                  className="font-semibold text-neutral-900 underline-offset-2 hover:underline disabled:text-neutral-400 disabled:no-underline"
                  disabled={!startWithTargetReport.report}
                  onClick={() => {
                    if (!startWithTargetReport.report) return;
                    navigate(`/dashboard/reports/${startWithTargetReport.report.id}`);
                  }}
                >
                  {startWithTargetReport.atRisk ? "Open an at-risk brief" : "Open latest brief"}
                </button>
              </div>
              <span className="text-xs text-muted-foreground">
                {lastUpdatedAt
                  ? `Updated ${lastUpdatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                  : "Loading…"}
              </span>
              <span data-testid="reports-brief-asof" className="text-xs text-neutral-600">
                {latestBriefAsOfLabel}
              </span>
              <button
                type="button"
                className="btn-secondary px-3 py-1.5 text-xs"
                onClick={() => void Promise.all([loadReports(), loadDeleted()])}
                disabled={isLoading}
              >
                Refresh
              </button>
              <Link to="/upload" className="btn-secondary px-3 py-1.5 text-xs">
                Open upload workspace
              </Link>
            </div>
          </div>

          {historyTruncated && historyNotice ? (
            <div className="mt-4 rounded-md border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-sm text-[#1E3A8A]">
              {historyNotice}
            </div>
          ) : null}

          {/* KPI tiles */}
          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-xl border border-border/70 bg-background/70 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Total</span>
                <Activity size={14} className="text-muted-foreground" />
              </div>
              {isLoading ? (
                <div className="mt-1.5 h-7 w-12 animate-pulse rounded bg-muted" />
              ) : (
                <p className="mt-1 text-2xl font-bold text-foreground">{activeReports.length}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">All reports in your library.</p>
            </div>

            <div className="rounded-xl border border-border/70 bg-background/70 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Ready</span>
                <Clock3 size={14} className="text-muted-foreground" />
              </div>
              {isLoading ? (
                <div className="mt-1.5 h-7 w-10 animate-pulse rounded bg-muted" />
              ) : (
                <p className="mt-1 text-2xl font-bold text-foreground">{statusCounts.ready}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">Available for review and export.</p>
            </div>

            <div className="rounded-xl border border-border/70 bg-background/70 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Processing</span>
                <AlertTriangle size={14} className="text-muted-foreground" />
              </div>
              {isLoading ? (
                <div className="mt-1.5 h-7 w-8 animate-pulse rounded bg-muted" />
              ) : (
                <p className="mt-1 text-2xl font-bold text-foreground">{statusCounts.processing}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">Currently in analysis pipeline.</p>
            </div>

            <div className="rounded-xl border border-border/70 bg-background/70 px-4 py-3">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Deleted</span>
                <Archive size={14} className="text-muted-foreground" />
              </div>
              {deletedLoading ? (
                <div className="mt-1.5 h-7 w-8 animate-pulse rounded bg-muted" />
              ) : (
                <p className="mt-1 text-2xl font-bold text-foreground">{deletedReports.length}</p>
              )}
              <p className="mt-1 text-xs text-muted-foreground">Retained {retentionDays} days before purge.</p>
            </div>
          </div>
          {deletedHistoryTruncated && deletedHistoryNotice ? (
            <div className="mt-4 rounded-md border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-sm text-[#1E3A8A]">
              {deletedHistoryNotice}
            </div>
          ) : null}
        </div>

        {/* ── Main 2-col grid ───────────────────────────────────── */}
        <section className="grid items-start gap-4 xl:grid-cols-[2fr_1fr]">
          <div className="space-y-4">

            {/* Filter bar + saved views */}
            <section className="workspace-panel-card rounded-xl border p-4">
              {/* Saved-view quick-filter chips — first workflow affordance */}
              <div className="mb-3 flex flex-wrap items-center gap-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">Quick views:</span>
                <button
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    statusFilter === "processing" && priorityFilter === "all"
                      ? "border-primary/45 bg-primary/12 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => {
                    setStatusFilter("processing");
                    setPriorityFilter("all");
                    setSearchQuery("");
                    setMatterFilter("all");
                  }}
                >
                  Processing queue ({statusCounts.processing})
                </button>
                <button
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    priorityFilter === "at_risk"
                      ? "border-amber-400/45 bg-amber-400/12 text-amber-900 dark:text-amber-200"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => {
                    setPriorityFilter("at_risk");
                    setStatusFilter("ready");
                    setSearchQuery("");
                    setMatterFilter("all");
                  }}
                >
                  At-risk ({atRiskReportIds.size})
                </button>
                <button
                  type="button"
                  className={`rounded-full border px-3 py-1 text-xs font-semibold transition-colors ${
                    matterFilter === "unassigned"
                      ? "border-primary/45 bg-primary/12 text-primary"
                      : "border-border text-muted-foreground hover:text-foreground"
                  }`}
                  onClick={() => {
                    setMatterFilter("unassigned");
                    setSearchQuery("");
                  }}
                >
                  Unassigned matters
                </button>
              </div>

              {/* Search + dropdowns */}
              <div className="flex flex-wrap items-end gap-3">
                <div className="min-w-[220px] flex-1">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground" htmlFor="report-search">
                    Search
                  </label>
                  <input
                    id="report-search"
                    type="search"
                    value={searchQuery}
                    onChange={(event) => setSearchQuery(event.target.value)}
                    placeholder="Search reports, themes, or actions…"
                    className="h-9 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  />
                </div>
                <div className="w-[160px]">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground" htmlFor="report-status-filter">
                    Status
                  </label>
                  <select
                    id="report-status-filter"
                    value={statusFilter}
                    onChange={(event) => setStatusFilter(event.target.value as "all" | "processing" | "ready" | "failed")}
                    className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    <option value="all">All statuses</option>
                    <option value="processing">Processing</option>
                    <option value="ready">Ready</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>
                <div className="w-[200px]">
                  <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-muted-foreground" htmlFor="report-matter-filter">
                    Matter
                  </label>
                  <select
                    id="report-matter-filter"
                    value={matterFilter}
                    onChange={(event) => setMatterFilter(event.target.value)}
                    className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
                  >
                    <option value="all">All matters</option>
                    <option value="unassigned">Unassigned</option>
                    {matterOptions.map((matter) => (
                      <option key={matter} value={matter}>
                        {matter}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  type="button"
                  className="btn-secondary h-9 px-4 py-0"
                  onClick={() => {
                    setSearchQuery("");
                    setStatusFilter("all");
                    setPriorityFilter("all");
                    setMatterFilter("all");
                  }}
                >
                  Clear filters
                </button>
              </div>

              {/* Priority toggle */}
              <div className="mt-3 inline-flex rounded-lg border border-border bg-background/70 p-1">
                {([
                  { id: "all", label: "All" },
                  { id: "at_risk", label: "At-risk" },
                  { id: "recent", label: "Recent (30 days)" },
                ] as const).map((option) => (
                  <button
                    key={option.id}
                    type="button"
                    onClick={() => setPriorityFilter(option.id)}
                    className={`rounded-md px-3 py-1.5 text-xs font-semibold ${
                      priorityFilter === option.id
                        ? "bg-primary/15 text-primary"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              <p className="mt-2 text-xs text-muted-foreground">
                Showing {filteredReports.length} of {activeReports.length} report{activeReports.length === 1 ? "" : "s"}.
                {" "}At-risk: satisfaction below 4.2 or complaint client issues outweigh praise.
              </p>
              {priorityFilter === "at_risk" && filteredReports.length === 0 && activeReports.some((r) => r.status === "ready") && (
                <p className="mt-1 text-xs text-muted-foreground">
                  No at-risk reports found in loaded client issues yet. Open a report for full detail.
                </p>
              )}
            </section>

            <ReportsPanel
              reports={filteredReports}
              isLoading={isLoading}
              error={error}
              pendingReportId={pendingReportId}
              showViewAll={false}
              showHeader={false}
              matterLabels={matterLabels}
              onMatterLabelChange={setMatterLabel}
              onReportDeleted={(reportId) => {
                setReports((previous) => previous.filter((report) => report.id !== reportId));
                setMatterLabels((previous) => {
                  const next = { ...previous };
                  delete next[reportId];
                  return next;
                });
                void loadDeleted();
              }}
              atRiskReportIds={atRiskReportIds}
              reportDetailsById={reportDetails}
            />            {!isLoading && activeReports.length === 0 && (
              <section className="workspace-panel-card rounded-xl border p-4">
                <h2 className="text-base font-semibold text-foreground">No reports yet</h2>
                <p className="mt-1 text-sm text-muted-foreground">
                  Your report library appears here after upload and analysis complete.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link to="/upload" className="btn-primary">
                    Upload your first CSV
                  </Link>
                  <Link to="/demo" className="btn-secondary">
                    Open read-only demo with sample data
                  </Link>
                </div>
              </section>
            )}
          </div>

          {/* ── Right rail ──────────────────────────────────────── */}
          <aside className="space-y-4">
            {/* Implementation action board */}
            <section id="implementation-action-board" ref={actionBoardRef} className="workspace-panel-card rounded-xl border p-5">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="text-base font-semibold text-foreground">Implementation actions</h2>
                  <p className="mt-0.5 text-xs text-muted-foreground">
                    Execution steps from client feedback, across all reports.
                  </p>
                </div>
                <Link to="/dashboard/actions" className="btn-secondary h-8 px-3 py-0 text-xs">
                  Open Actions workspace
                </Link>
              </div>

              {/* Status chips */}
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(
                  [
                    { label: "Planned", count: boardStatusCounts.planned, cls: "border-slate-400/35 bg-slate-500/10 text-slate-800 dark:text-slate-200" },
                    { label: "In progress", count: boardStatusCounts.inProgress, cls: "border-sky-400/45 bg-sky-500/12 text-sky-800 dark:text-sky-200" },
                    { label: "Completed", count: boardStatusCounts.completed, cls: "border-emerald-500/35 bg-emerald-500/12 text-emerald-800 dark:text-emerald-200" },
                    { label: "Overdue", count: boardStatusCounts.overdue, cls: "border-rose-500/35 bg-rose-500/12 text-rose-800 dark:text-rose-200" },
                  ] as const
                ).map(({ label, count, cls }) => (
                  <span key={label} className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-semibold ${cls}`}>
                    {label} <span className="font-bold">{count}</span>
                  </span>
                ))}
              </div>

              {/* Action rows */}
              <div className="mt-3 space-y-2">
                {visibleBoardActions.map((item) => {
                  const isFocusedItem =
                    actionsWorkspaceMode &&
                    focusedReportId === item.reportId &&
                    (focusedActionId ? item.actionId === focusedActionId : true);
                  return (
                    <div
                      key={item.id}
                      className={`w-full rounded-lg border border-border/70 bg-background/70 px-3 py-2.5 text-left transition-colors hover:border-primary/35 hover:bg-background ${
                        isFocusedItem ? "ring-1 ring-primary/55 border-primary/45" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-foreground">{item.title}</p>
                          <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                            <Link
                              to={`/dashboard/reports/${item.reportId}#implementation`}
                              className="text-xs font-medium text-primary hover:underline"
                            >
                              {item.reportName}
                            </Link>
                            <span className="text-xs text-muted-foreground">·</span>
                            <span className="text-xs text-muted-foreground">{item.owner}</span>
                            <span className="text-xs text-muted-foreground">·</span>
                            <span className="text-xs text-muted-foreground">{item.timeframe}</span>
                          </div>
                        </div>
                        <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusChipClass(item.status)}`}>
                          {item.status}
                        </span>
                      </div>
                    </div>
                  );
                })}

                {implementationBoardActions.length === 0 && (
                  <div className="rounded-md border border-border/70 bg-background/70 px-3 py-3">
                    <p className="text-sm text-muted-foreground">
                      {activeReports.length === 0
                        ? "Implementation actions appear once report plans are available."
                        : loadedDetailCount === 0
                          ? "Actions are still loading from your reports."
                          : "No implementation actions found in loaded reports."}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {activeReports.length === 0 ? (
                        <Link to="/upload" className="btn-secondary h-8 px-3 py-0 text-xs">
                          Upload your first CSV
                        </Link>
                      ) : (
                        <Link to="/dashboard/reports" className="btn-secondary h-8 px-3 py-0 text-xs">
                          Open reports library
                        </Link>
                      )}
                      <Link to="/demo" className="btn-secondary h-8 px-3 py-0 text-xs">
                        Open read-only demo with sample data
                      </Link>
                    </div>
                  </div>
                )}
              </div>

              {implementationBoardActions.length > BOARD_ACTIONS_VISIBLE_COUNT && (
                <button
                  type="button"
                  ref={allActionsDialogTriggerRef}
                  onClick={() => setIsAllActionsDialogOpen(true)}
                  className="mt-3 text-xs font-medium text-primary hover:underline"
                >
                  View all {implementationBoardActions.length} actions
                </button>
              )}
            </section>

            {/* Utilities card (replaces "Workspace controls" section) */}
            <section className="workspace-panel-card rounded-xl border p-4">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Utilities</h3>
              <div className="mt-2 space-y-1.5 text-xs text-muted-foreground">
                <p>
                  {activeReports.length} active · {matterOptions.length} matter label{matterOptions.length === 1 ? "" : "s"} · {deletedReports.length} deleted
                </p>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary h-8 px-3 py-0 text-xs"
                  onClick={() => {
                    setSearchQuery("");
                    setStatusFilter("all");
                    setPriorityFilter("all");
                    setMatterFilter("all");
                  }}
                >
                  Reset filters
                </button>
                <button
                  type="button"
                  className="btn-secondary h-8 px-3 py-0 text-xs"
                  onClick={() => setShowDeleted((prev) => !prev)}
                >
                  {showDeleted ? "Hide deleted" : "Show deleted"}
                </button>
              </div>
              {!canRestoreDeleted && (
                <Link to="/pricing" className="btn-secondary mt-2 inline-flex h-8 w-full items-center justify-center px-3 py-0 text-xs">
                  Upgrade to restore deleted
                </Link>
              )}
            </section>
          </aside>
        </section>

        {/* ── Recently Deleted ─────────────────────────────────── */}
        <section className="workspace-panel-card rounded-xl border p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">Recently deleted</h2>
              {!showDeleted && (
                <p className="mt-1 text-sm text-muted-foreground">
                  {deletedReports.length > 0
                    ? `${deletedReports.length} deleted report${deletedReports.length === 1 ? "" : "s"} retained for ${retentionDays} days.`
                    : `No deleted reports. Deleted reports are retained for ${retentionDays} days.`}
                </p>
              )}
              {showDeleted && (
                <p className="mt-1 text-sm text-muted-foreground">
                  Deleted reports stay here for {retentionDays} days before purge. Free workspaces cannot restore unless paid restore access is added during that window; Team and Firm can restore within current plan permissions and history limits.
                </p>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                className="btn-secondary h-8 px-3 py-0 text-xs"
                onClick={() => setShowDeleted((prev) => !prev)}
              >
                {showDeleted ? "Hide deleted reports" : "Show deleted reports"}
              </button>
              {!canRestoreDeleted && showDeleted && (
                <Link to="/pricing" className="btn-secondary h-8 px-3 py-0 text-xs">
                  Upgrade to restore
                </Link>
              )}
            </div>
          </div>

          {showDeleted && (
            <div className="mt-4">
              {deletedError && (
                <p className="mb-3 text-sm text-destructive">{deletedError}</p>
              )}

              {deletedLoading ? (
                /* Skeleton rows */
                <div className="space-y-2">
                  {[1, 2, 3].map((n) => (
                    <div key={n} className="flex items-center gap-3 rounded-lg border border-border/60 bg-background/60 px-3 py-2.5">
                      <div className="flex-1 space-y-1.5">
                        <div className="h-3.5 w-2/5 animate-pulse rounded bg-muted" />
                        <div className="h-2.5 w-1/4 animate-pulse rounded bg-muted/70" />
                      </div>
                      <div className="h-3.5 w-24 animate-pulse rounded bg-muted" />
                      <div className="h-3.5 w-24 animate-pulse rounded bg-muted" />
                      <div className="h-7 w-16 animate-pulse rounded-md bg-muted" />
                    </div>
                  ))}
                </div>
              ) : deletedReports.length === 0 ? (
                <div className="rounded-lg border border-border/60 bg-background/60 px-4 py-4">
                  <p className="text-sm text-muted-foreground">
                    No deleted reports in retention. Deleted items remain recoverable only during the {retentionDays}-day retention window and only for workspaces with restore access.
                  </p>
                  {!canRestoreDeleted && (
                    <Link to="/pricing" className="btn-secondary mt-3 inline-flex h-8 px-3 py-0 text-xs">
                      Upgrade to unlock restore
                    </Link>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full min-w-[700px] text-sm">
                    <thead className="border-b border-border text-left text-muted-foreground">
                      <tr>
                        <th className="py-2 pr-3 font-medium">Report</th>
                        <th className="py-2 pr-3 font-medium">Deleted</th>
                        <th className="py-2 pr-3 font-medium">Auto purge</th>
                        <th className="py-2 pr-3 font-medium">Reviews</th>
                        <th className="py-2 pr-3 font-medium">Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {deletedReports.map((report) => (
                        <tr key={report.id} className="border-b border-border/70 bg-amber-400/10 last:border-0 dark:bg-amber-500/5">
                          <td className="py-3 pr-3">
                            <div className="font-medium text-foreground">{report.name}</div>
                            <div className="text-xs text-muted-foreground">{report.plan_label}</div>
                          </td>
                          <td className="py-3 pr-3 text-muted-foreground">{formatDateTime(report.deleted_at)}</td>
                          <td className="py-3 pr-3 text-muted-foreground">{formatDateTime(report.purge_at)}</td>
                          <td className="py-3 pr-3 text-foreground">{report.total_reviews}</td>
                          <td className="py-3 pr-3">
                            {canRestoreDeleted ? (
                              <button
                                type="button"
                                disabled={restoringId === report.id}
                                onClick={() => void handleRestore(report.id)}
                                className="inline-flex items-center rounded-md border border-border px-3 py-1.5 text-xs font-medium text-foreground hover:bg-secondary disabled:opacity-60"
                              >
                                {restoringId === report.id ? "Restoring…" : "Restore"}
                              </button>
                            ) : (
                              <Link to="/pricing" className="text-xs font-medium text-primary hover:underline">
                                Upgrade to restore
                              </Link>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </section>

        {/* ── All-actions dialog ───────────────────────────────── */}
        <Dialog
          open={isAllActionsDialogOpen}
          onOpenChange={(open) => {
            setIsAllActionsDialogOpen(open);
            if (!open && allActionsDialogTriggerRef.current) {
              setTimeout(() => {
                allActionsDialogTriggerRef.current?.focus();
              }, 0);
            }
          }}
        >
          <DialogContent className="max-w-4xl">
            <DialogHeader>
              <DialogTitle>All implementation actions</DialogTitle>
              <DialogDescription>
                Sorted by priority: overdue first, then at-risk linked items, then soonest due.
              </DialogDescription>
            </DialogHeader>
            <div className="max-h-[65vh] space-y-2 overflow-y-auto pr-1">
              {implementationBoardActions.map((item) => {
                const isFocusedItem =
                  actionsWorkspaceMode &&
                  focusedReportId === item.reportId &&
                  (focusedActionId ? item.actionId === focusedActionId : true);
                return (
                  <div
                    key={`dialog-${item.id}`}
                    className={`rounded-lg border border-border/70 bg-background/70 px-3 py-2.5 ${
                      isFocusedItem ? "ring-1 ring-primary/55 border-primary/45" : ""
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-foreground">{item.title}</p>
                        <div className="mt-0.5 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
                          <Link
                            to={`/dashboard/reports/${item.reportId}#implementation`}
                            className="text-xs font-medium text-primary hover:underline"
                          >
                            {item.reportName}
                          </Link>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">{item.owner}</span>
                          <span className="text-xs text-muted-foreground">·</span>
                          <span className="text-xs text-muted-foreground">{item.timeframe}</span>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        {item.atRiskLinked && (
                          <span className="rounded-full border border-amber-400/45 bg-amber-400/12 px-2 py-0.5 text-[10px] font-semibold text-amber-900 dark:text-amber-200">
                            At-risk
                          </span>
                        )}
                        <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${statusChipClass(item.status)}`}>
                          {item.status}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </DialogContent>
        </Dialog>

      </section>
    </WorkspaceLayout>
  );
};

export default DashboardReports;





