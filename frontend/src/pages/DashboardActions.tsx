import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowRight, CheckCircle2, ChevronRight, Clock3, Filter, ShieldAlert } from "lucide-react";
import {
  getFirmActions,
  getDeletedReports,
  getReports,
  type ReportActionItem,
  type ReportListItem,
} from "@/api/authService";
import GovPageHeader from "@/components/governance/GovPageHeader";
import GovSectionCard from "@/components/governance/GovSectionCard";
import GovStatCard from "@/components/governance/GovStatCard";
import WorkspaceLayout from "@/components/WorkspaceLayout";
import { formatApiDate, parseApiDate, toApiTimestamp } from "@/lib/dateTime";

type ActionStatus = "Planned" | "In progress" | "Completed" | "Overdue";
type CanonicalTimeframe = "Days 1-30" | "Days 31-60" | "Days 61-90" | null;
type ActionTypeLabel = "Suggested action" | "Tracked action";
type GroupKey = "needs_attention" | "in_progress" | "planned" | "completed";
type StatusFilter = "all" | "planned" | "in_progress" | "completed" | "overdue";
type TimeframeFilter = "all" | "Days 1-30" | "Days 31-60" | "Days 61-90" | "none";

type ActionWorkspaceRow = {
  id: string;
  reportId: number;
  actionId: number | null;
  reportName: string;
  reportCreatedAt: string;
  title: string;
  owner: string;
  ownerUserId: number | null;
  ownerKey: string;
  timeframeLabel: string;
  timeframeValue: CanonicalTimeframe;
  status: ActionStatus;
  actionType: ActionTypeLabel;
  atRiskLinked: boolean;
  theme: string | null;
  duplicateCount: number;
  crossReportCount: number;
};

const REFRESH_COOLDOWN_MS = 30_000;

const normalizeText = (value: string) =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();

const statusChipClass: Record<ActionStatus, string> = {
  Planned: "gov-chip-muted",
  "In progress": "gov-chip-warn",
  Completed: "gov-chip-success",
  Overdue: "gov-chip-risk",
};

const timeframeRank = (timeframe: CanonicalTimeframe) => {
  if (timeframe === "Days 1-30") return 0;
  if (timeframe === "Days 31-60") return 1;
  if (timeframe === "Days 61-90") return 2;
  return 3;
};

const resolveCanonicalTimeframe = (timeline: string | null | undefined): CanonicalTimeframe => {
  const normalized = (timeline || "").toLowerCase();
  if (normalized.includes("days 1-30") || normalized.includes("days 1–30")) return "Days 1-30";
  if (normalized.includes("days 31-60") || normalized.includes("days 31–60")) return "Days 31-60";
  if (normalized.includes("days 61-90") || normalized.includes("days 61–90")) return "Days 61-90";
  return null;
};

/** Normalize legacy/unexpected DB status values to the canonical enum. */
const normalizeRawStatus = (raw: string | undefined | null): "open" | "in_progress" | "done" => {
  const s = (raw || "").toLowerCase();
  if (s.includes("progress")) return "in_progress";
  if (s.includes("done") || s.includes("complete")) return "done";
  return "open";
};

const statusFromTrackedAction = (action: ReportActionItem): ActionStatus => {
  const normalized = normalizeRawStatus(action.status);
  const due = parseApiDate(action.due_date);
  const isOverdue = normalized !== "done" && !!due && due.getTime() < Date.now();
  if (isOverdue) return "Overdue";
  if (normalized === "done") return "Completed";
  if (normalized === "in_progress") return "In progress";
  return "Planned";
};

const mapStatusFilterValue = (value: string | null): StatusFilter => {
  if (!value) return "all";
  const normalized = value.toLowerCase();
  if (normalized === "planned") return "planned";
  if (normalized === "in progress" || normalized === "in_progress") return "in_progress";
  if (normalized === "completed") return "completed";
  if (normalized === "overdue") return "overdue";
  return "all";
};

const groupForRow = (row: ActionWorkspaceRow): GroupKey => {
  if (row.status === "Overdue" || (row.status === "Planned" && row.timeframeValue === "Days 1-30")) {
    return "needs_attention";
  }
  if (row.status === "In progress") return "in_progress";
  if (row.status === "Planned") return "planned";
  return "completed";
};

const DashboardActions = () => {
  const [searchParams] = useSearchParams();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [reportActions, setReportActions] = useState<ReportActionItem[]>([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [initialLoadingActions, setInitialLoadingActions] = useState(true);
  const [refreshingActions, setRefreshingActions] = useState(false);
  const [error, setError] = useState("");

  const [statusFilter, setStatusFilter] = useState<StatusFilter>(mapStatusFilterValue(searchParams.get("status")));
  const [ownerFilter, setOwnerFilter] = useState<string>("all");
  const [reportFilter, setReportFilter] = useState<string>(searchParams.get("reportId") || "all");
  const [timeframeFilter, setTimeframeFilter] = useState<TimeframeFilter>("all");
  const [selectedActionId, setSelectedActionId] = useState<string | null>(null);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const lastRefreshAtRef = useRef(0);
  const hasLoadedActionsRef = useRef(false);

  useEffect(() => {
    const nextStatusFilter = mapStatusFilterValue(searchParams.get("status"));
    const nextReportFilter = searchParams.get("reportId") || "all";
    setStatusFilter(nextStatusFilter);
    setReportFilter(nextReportFilter);
  }, [searchParams]);

  useEffect(() => {
    const triggerRefresh = () => {
      const now = Date.now();
      if (now - lastRefreshAtRef.current < REFRESH_COOLDOWN_MS) return;
      lastRefreshAtRef.current = now;
      setRefreshNonce((prev) => prev + 1);
    };
    const onVisibility = () => {
      if (document.visibilityState === "visible") triggerRefresh();
    };
    window.addEventListener("focus", triggerRefresh);
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      window.removeEventListener("focus", triggerRefresh);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoadingReports(true);
      const [reportsResult, deletedResult] = await Promise.all([getReports(120), getDeletedReports(120)]);
      if (!active) return;

      if (!reportsResult.success || !reportsResult.reports) {
        setReports([]);
        setError(reportsResult.error || "Unable to load actions workspace.");
        setLoadingReports(false);
        return;
      }

      const deletedIds = new Set((deletedResult.reports || []).map((row) => row.id));
      const readyReports = reportsResult.reports
        .filter((report) => report.status === "ready" && !deletedIds.has(report.id))
        .sort((a, b) => (toApiTimestamp(b.created_at) || 0) - (toApiTimestamp(a.created_at) || 0));

      setReports(readyReports);
      setError("");
      setLoadingReports(false);
    };

    void load();
    return () => {
      active = false;
    };
  }, [refreshNonce]);

  // Stable primitive dep: same IDs produce same string, so the effect does not re-run.
  // reportDetails and reportActions produce new object refs on every completed
  // fetch, which is exactly what caused the storm when they were in the dep
  // array — each write re-triggered the effect which issued more fetches.
  useEffect(() => {
  const controller = new AbortController();
  const { signal } = controller;

  const loadActions = async () => {
    if (!reports.length) {
      setReportActions([]);
      setInitialLoadingActions(false);
      setRefreshingActions(false);
      return;
    }

    const isInitialLoad = !hasLoadedActionsRef.current;
    if (isInitialLoad) {
      setInitialLoadingActions(true);
    } else {
      setRefreshingActions(true);
    }

    const actionsResult = await getFirmActions(signal);
    if (signal.aborted) return;

    if (actionsResult.success && actionsResult.actions) {
      const activeReportIds = new Set(reports.map((report) => report.id));
      setReportActions(actionsResult.actions.filter((action) => activeReportIds.has(Number(action.report_id || 0))));
      hasLoadedActionsRef.current = true;
    } else if (!actionsResult.success && actionsResult.error !== "Aborted") {
      setError(actionsResult.error || "Unable to load actions workspace.");
    }

    setInitialLoadingActions(false);
    setRefreshingActions(false);
  };

  void loadActions();
  return () => {
    controller.abort();
  };
}, [reports, refreshNonce]);

const atRiskReportIds = useMemo(() => new Set<number>(), []);

  const actionRows = useMemo<ActionWorkspaceRow[]>(() => {
  const rawRows: ActionWorkspaceRow[] = [];

  reportActions.forEach((action) => {
    const reportId = Number(action.report_id || 0);
    if (!reportId) return;
    const report = reports.find((item) => item.id === reportId);
    const reportName = action.report_name || report?.name || `Report #${reportId}`;
    const reportCreatedAt = action.report_created_at || report?.created_at || "";
    const timeframeValue = resolveCanonicalTimeframe(action.timeframe);
    const ownerText = action.owner || "Unassigned";

    rawRows.push({
      id: `tracked-${reportId}-${action.id}`,
      reportId,
      actionId: action.id,
      reportName,
      reportCreatedAt,
      title: action.title,
      owner: ownerText,
      ownerUserId: typeof action.owner_user_id === "number" ? action.owner_user_id : null,
      ownerKey:
        typeof action.owner_user_id === "number"
          ? `user:${action.owner_user_id}`
          : `name:${ownerText.trim().toLowerCase()}`,
      timeframeLabel: action.due_date ? `Due ${formatApiDate(action.due_date)}` : "No due date",
      timeframeValue,
      status: statusFromTrackedAction(action),
      actionType: "Tracked action",
      atRiskLinked: false,
      theme: null,
      duplicateCount: 1,
      crossReportCount: 1,
    });
  });

  const dedupedByReportKey = new Map<string, ActionWorkspaceRow>();
  rawRows.forEach((row) => {
    const dedupeKey = `${row.reportId}|${normalizeText(row.title)}|${normalizeText(row.owner)}|${row.timeframeValue || "none"}`;
    const existing = dedupedByReportKey.get(dedupeKey);
    if (existing) {
      existing.duplicateCount += 1;
    } else {
      dedupedByReportKey.set(dedupeKey, { ...row });
    }
  });

  const dedupedRows = [...dedupedByReportKey.values()];
  const crossReportKeyCounts = dedupedRows.reduce<Record<string, number>>((acc, row) => {
    const crossKey = `${normalizeText(row.title)}|${normalizeText(row.owner)}|${row.timeframeValue || "none"}`;
    acc[crossKey] = (acc[crossKey] || 0) + 1;
    return acc;
  }, {});

  return dedupedRows
    .map((row) => {
      const crossKey = `${normalizeText(row.title)}|${normalizeText(row.owner)}|${row.timeframeValue || "none"}`;
      return {
        ...row,
        crossReportCount: crossReportKeyCounts[crossKey] || 1,
      };
    })
    .sort((a, b) => {
      const overdueRank = (row: ActionWorkspaceRow) => (row.status === "Overdue" ? 0 : 1);
      const overdueDelta = overdueRank(a) - overdueRank(b);
      if (overdueDelta !== 0) return overdueDelta;

      const timeframeDelta = timeframeRank(a.timeframeValue) - timeframeRank(b.timeframeValue);
      if (timeframeDelta !== 0) return timeframeDelta;

      return (toApiTimestamp(b.reportCreatedAt) || 0) - (toApiTimestamp(a.reportCreatedAt) || 0);
    });
}, [reportActions, reports]);

  const ownerOptions = useMemo(() => {
    const byValue = new Map<string, { value: string; label: string }>();
    let hasUnassigned = false;

    actionRows.forEach((row) => {
      const ownerName = (row.owner || "").trim();
      if (row.ownerUserId) {
        const value = row.ownerKey;
        if (!byValue.has(value)) {
          byValue.set(value, { value, label: ownerName || `User ${row.ownerUserId}` });
        }
        return;
      }

      if (!ownerName || ownerName.toLowerCase() === "unassigned") {
        hasUnassigned = true;
        return;
      }

      const value = row.ownerKey;
      if (!byValue.has(value)) {
        byValue.set(value, { value, label: ownerName });
      }
    });

    const sorted = [...byValue.values()].sort((a, b) => a.label.localeCompare(b.label));
    if (hasUnassigned) {
      sorted.push({ value: "unassigned", label: "Unassigned" });
    }
    return sorted;
  }, [actionRows]);
  const reportOptions = useMemo(
    () => [...new Set(actionRows.map((item) => `${item.reportId}|${item.reportName}`))],
    [actionRows],
  );
  const resetFilters = () => {
    setStatusFilter("all");
    setOwnerFilter("all");
    setReportFilter("all");
    setTimeframeFilter("all");
  };

  const filteredRows = useMemo(() => {
    const isRowUnassigned = (row: ActionWorkspaceRow) =>
      !row.ownerUserId && (!row.owner || row.owner.trim().length === 0 || row.owner.toLowerCase() === "unassigned");

    const matchesOwnerFilter = (row: ActionWorkspaceRow) => {
      if (ownerFilter === "all") return true;
      if (ownerFilter === "unassigned") return isRowUnassigned(row);
      if (ownerFilter.startsWith("user:")) {
        return String(row.ownerUserId || "") === ownerFilter.slice("user:".length);
      }
      if (ownerFilter.startsWith("name:")) {
        return row.ownerKey === ownerFilter;
      }
      return true;
    };

    return actionRows.filter((row) => {
      if (statusFilter !== "all") {
        const statusKey =
          row.status === "In progress"
            ? "in_progress"
            : row.status === "Completed"
              ? "completed"
              : row.status === "Overdue"
                ? "overdue"
                : "planned";
        if (statusFilter !== statusKey) return false;
      }
      if (!matchesOwnerFilter(row)) return false;
      if (reportFilter !== "all" && String(row.reportId) !== reportFilter) return false;
      if (timeframeFilter !== "all") {
        const rowTimeframe = row.timeframeValue || "none";
        if (rowTimeframe !== timeframeFilter) return false;
      }
      return true;
    });
  }, [actionRows, ownerFilter, reportFilter, statusFilter, timeframeFilter]);
  const hasAnyActions = actionRows.length > 0;

  const groupedRows = useMemo(() => {
    const groups: Record<GroupKey, ActionWorkspaceRow[]> = {
      needs_attention: [],
      in_progress: [],
      planned: [],
      completed: [],
    };
    filteredRows.forEach((row) => {
      groups[groupForRow(row)].push(row);
    });
    return groups;
  }, [filteredRows]);

  useEffect(() => {
    if (!filteredRows.length) {
      setSelectedActionId(null);
      return;
    }

    const current = filteredRows.find((row) => row.id === selectedActionId);
    if (current) return;

    const targetReportId = Number(searchParams.get("reportId") || 0) || null;
    const targetActionId = Number(searchParams.get("actionId") || 0) || null;
    if (targetReportId) {
      const found = filteredRows.find(
        (row) => row.reportId === targetReportId && (targetActionId ? row.actionId === targetActionId : true),
      );
      if (found) {
        setSelectedActionId(found.id);
        return;
      }
    }

    const preferred =
      groupedRows.needs_attention[0] ||
      groupedRows.in_progress[0] ||
      groupedRows.planned[0] ||
      groupedRows.completed[0] ||
      filteredRows[0];

    // Guard: only write if the value is actually changing. Without this,
    // setting the same string re-renders the component, which recomputes
    // filteredRows (a useMemo), which re-triggers this effect — a render
    // loop that does not fetch but does thrash the main thread.
    // React bails out of useState writes only for primitive state when the
    // value is strictly equal, so this explicit check is required here
    // because preferred.id is computed each render and may be a new string
    // reference even when the logical value hasn't changed.
    if (preferred.id !== selectedActionId) {
      setSelectedActionId(preferred.id);
    }
  }, [filteredRows, groupedRows, searchParams, selectedActionId]);

  const selectedRow = useMemo(
    () => filteredRows.find((row) => row.id === selectedActionId) || null,
    [filteredRows, selectedActionId],
  );
  const whyThisMatters = useMemo(() => {
  if (!selectedRow) return [];
  const lines: string[] = [];
  if (selectedRow.atRiskLinked) {
    lines.push("This action is linked to a report currently flagged with at-risk client issues.");
  }
  if (selectedRow.status === "Overdue") {
    lines.push("This action is overdue and should be reviewed in the next governance session.");
  }
  if (selectedRow.owner.toLowerCase() === "unassigned") {
    lines.push("Owner is unassigned. Assign ownership to keep execution accountable.");
  }
  if (!lines.length) {
    lines.push("This recommendation comes from tracked report actions and supports service consistency.");
  }
  return lines.slice(0, 2);
}, [selectedRow]);

  return (
    <WorkspaceLayout>
      <section className="gov-page stage-sequence">
        <GovPageHeader
          title="Execution"
          subtitle="Filter and prioritize implementation actions across reports, then open the related report to execute."
          actions={
            <>
              <Link to="/dashboard/reports" className="gov-cta-primary">
                Open briefs
              </Link>
              <Link to="/upload" className="gov-cta-secondary">
                Upload feedback
              </Link>
            </>
          }
        />

        {error && (
          <div className="rounded-lg border border-destructive/35 bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        <GovSectionCard accent="watch" padding="sm">
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Filters</h2>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-700">Status</label>
              <select
                value={statusFilter}
                onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                className="gov-field"
              >
                <option value="all">All statuses</option>
                <option value="planned">Planned</option>
                <option value="in_progress">In progress</option>
                <option value="completed">Completed</option>
                <option value="overdue">Overdue</option>
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-700">Owner</label>
              <select
                value={ownerFilter}
                onChange={(event) => setOwnerFilter(event.target.value)}
                className="gov-field"
              >
                <option value="all">All owners</option>
                {ownerOptions.map((owner) => (
                  <option key={owner.value} value={owner.value}>
                    {owner.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-700">Report</label>
              <select
                value={reportFilter}
                onChange={(event) => setReportFilter(event.target.value)}
                className="gov-field"
              >
                <option value="all">All reports</option>
                {reportOptions.map((entry) => {
                  const [id, name] = entry.split("|");
                  return (
                    <option key={entry} value={id}>
                      {name}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-neutral-700">Timeframe</label>
              <select
                value={timeframeFilter}
                onChange={(event) => setTimeframeFilter(event.target.value as TimeframeFilter)}
                className="gov-field"
              >
                <option value="all">All timeframes</option>
                <option value="Days 1-30">Days 1-30</option>
                <option value="Days 31-60">Days 31-60</option>
                <option value="Days 61-90">Days 61-90</option>
                <option value="none">No timeframe</option>
              </select>
            </div>
          </div>
          <div className="mt-3 flex justify-end">
            <button type="button" className="gov-cta-secondary" onClick={resetFilters}>
              Reset filters
            </button>
          </div>
        </GovSectionCard>

        <section className="grid items-start gap-4 xl:grid-cols-[1.75fr_1fr]">
          <GovSectionCard accent="attention" padding="sm" className="!m-0">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-base font-semibold text-foreground">Implementation actions</h2>
              <span className="text-xs text-neutral-700">{filteredRows.length} actions shown</span>
            </div>

            {(refreshingActions || (loadingReports && reports.length > 0)) && (
              <p className="text-xs text-neutral-700">Refreshing…</p>
            )}

          {initialLoadingActions ? (
              <p className="mt-3 text-sm text-neutral-700">Loading actions...</p>
            ) : filteredRows.length === 0 ? (
              <div className="mt-3 gov-level-2-soft px-3 py-3 text-sm text-neutral-700">
                {hasAnyActions ? (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>No actions match current filters.</span>
                    <button type="button" className="gov-cta-secondary" onClick={resetFilters}>
                      Reset filters
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span>No actions yet.</span>
                    <Link to="/dashboard/reports" className="gov-cta-secondary">
                      Open briefs
                    </Link>
                  </div>
                )}
              </div>
            ) : (
              <div className="mt-3 space-y-4">
                {([
                  { key: "needs_attention", label: "Needs attention", hint: "Overdue and near-term planned items." },
                  { key: "in_progress", label: "In progress", hint: "Actions currently being executed." },
                  { key: "planned", label: "Planned", hint: "Queued actions not yet started." },
                  { key: "completed", label: "Completed", hint: "Closed actions for audit trail." },
                ] as const).map((group) =>
                  groupedRows[group.key].length > 0 ? (
                    <section key={group.key} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-foreground">{group.label}</h3>
                          <p className="text-xs text-neutral-700">{group.hint}</p>
                        </div>
                        <span className="gov-chip-muted min-w-8 justify-center px-2 py-0 text-[11px] font-semibold">
                          {groupedRows[group.key].length}
                        </span>
                      </div>
                      <div className="space-y-2">
                        {groupedRows[group.key].map((row) => (
                          <button
                            key={row.id}
                            type="button"
                            onClick={() => setSelectedActionId(row.id)}
                            className={`gov-clickable gov-row-clickable w-full rounded-lg border px-3 py-2 text-left ${
                              selectedActionId === row.id
                                ? "border-primary/45 bg-primary/10"
                                : "border-neutral-200 bg-white"
                            }`}
                          >
                            <div className="flex items-center justify-between gap-3">
                              <p className="truncate text-sm font-medium text-foreground">{row.title}</p>
                              <div className="flex items-center gap-2">
                                <span className={statusChipClass[row.status]}>
                                  {row.status}
                                </span>
                                <span className="gov-row-chevron" aria-hidden="true">
                                  <ChevronRight size={14} className="text-neutral-700" />
                                </span>
                              </div>
                            </div>
                            <p className="mt-1 text-xs text-neutral-700">
                              Report: {row.reportName} | Owner: {row.owner} | Timeframe: {row.timeframeValue || "No timeframe"} | Type: {row.actionType}
                            </p>
                          </button>
                        ))}
                      </div>
                    </section>
                  ) : null,
                )}
              </div>
            )}
          </GovSectionCard>

          <GovSectionCard accent="neutral" padding="sm" className="!m-0">
            <h2 className="text-base font-semibold text-foreground">Action details</h2>
            {!selectedRow ? (
              <p className="mt-3 text-sm text-neutral-700">Select an action to view context and open the related report.</p>
            ) : (
              <div className="mt-3 space-y-3">
                <div>
                  <p className="text-sm font-semibold text-foreground">{selectedRow.title}</p>
                  <p className="mt-1 text-xs text-neutral-700">
                    {selectedRow.reportName} | {selectedRow.actionType}
                  </p>
                </div>

                <div className="gov-level-2-soft px-3 py-2">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-700">Why this matters</p>
                  <div className="mt-1 space-y-1">
                    {whyThisMatters.map((line, index) => (
                      <p key={`${selectedRow.id}-why-${index}`} className="text-xs text-foreground">
                        {line}
                      </p>
                    ))}
                  </div>
                </div>

                <div className="gov-level-2-soft px-3 py-2 text-xs text-foreground">
                  <p>Owner: {selectedRow.owner}</p>
                  <p className="mt-1">Timeframe: {selectedRow.timeframeLabel}</p>
                  <div className="mt-1 flex flex-wrap items-center gap-1.5">
                    <span className={statusChipClass[selectedRow.status]}>
                      {selectedRow.status}
                    </span>
                    {selectedRow.atRiskLinked && (
                      <span className="gov-chip-warn">
                        At-risk linked
                      </span>
                    )}
                    {selectedRow.theme && (
                      <span className="rounded-full border border-border bg-background px-2 py-0.5 text-[10px] font-semibold text-neutral-700">
                        Theme: {selectedRow.theme}
                      </span>
                    )}
                  </div>
                </div>

                {(selectedRow.duplicateCount > 1 || selectedRow.crossReportCount > 1) && (
                  <div className="gov-level-2-soft px-3 py-2 text-xs text-neutral-700">
                    {selectedRow.duplicateCount > 1 && (
                      <p>Consolidated {selectedRow.duplicateCount} duplicate recommendations in this report.</p>
                    )}
                    {selectedRow.crossReportCount > 1 && (
                      <p>Appears in multiple reports ({selectedRow.crossReportCount}).</p>
                    )}
                  </div>
                )}

                <div className="flex flex-wrap gap-2 pt-1">
                  <Link to={`/dashboard/reports/${selectedRow.reportId}#implementation`} className="gov-cta-primary px-3 py-1.5 text-xs">
                    Open related report
                    <ArrowRight size={13} className="ml-1 inline-block" />
                  </Link>
                  <Link to="/dashboard/reports" className="gov-cta-secondary px-3 py-1.5 text-xs">
                    Open briefs
                  </Link>
                </div>
              </div>
            )}
          </GovSectionCard>
        </section>

        <section className="grid gap-3 sm:grid-cols-3">
          <GovStatCard
            label="Needs attention"
            value={groupedRows.needs_attention.length}
            icon={<ShieldAlert size={14} />}
          />
          <GovStatCard
            label="In progress"
            value={groupedRows.in_progress.length}
            icon={<Clock3 size={14} />}
          />
          <GovStatCard
            label="Completed"
            value={groupedRows.completed.length}
            icon={<CheckCircle2 size={14} />}
          />
        </section>
      </section>
    </WorkspaceLayout>
  );
};

export default DashboardActions;




