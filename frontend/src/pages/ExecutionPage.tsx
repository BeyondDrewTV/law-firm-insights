import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ClipboardList } from "lucide-react";
import { toast } from "sonner";

import GovernanceEmptyState from "@/components/governance/GovernanceEmptyState";
import { ActionColumnSkeleton } from "@/components/governance/skeletons";
import {
  createReportAction,
  deleteReportAction,
  getFirmActions,
  getReports,
  type ReportActionItem,
  type ReportListItem,
} from "@/api/authService";
import ActionForm, { type ActionFormValues } from "@/components/actions/ActionForm";
import ActionCard from "@/components/actions/ActionCard";
import PageWrapper from "@/components/governance/PageWrapper";
import { PageTabs } from "@/components/governance/PageTabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { DISPLAY_LABELS } from "@/constants/displayLabels";
import { useAuth } from "@/contexts/AuthContext";

type StatusFilter = "all" | "open" | "in_progress" | "blocked" | "done" | "overdue";

const isOverdue = (action: ReportActionItem): boolean => {
  if (!action.due_date) return false;
  if (action.status === "done") return false;
  const due = new Date(action.due_date).getTime();
  return Number.isFinite(due) && due < Date.now();
};

const actionMatchesStatus = (action: ReportActionItem, status: StatusFilter) => {
  if (status === "all") return true;
  if (status === "overdue") return isOverdue(action);
  if (status === "blocked") return action.status === "blocked";
  if (status === "open") return action.status === "open" && !isOverdue(action);
  return action.status === status;
};

const normalizeOwnerKey = (action: ReportActionItem): string => {
  if (typeof action.owner_user_id === "number") return `user:${action.owner_user_id}`;
  const owner = (action.owner || "").trim().toLowerCase();
  return owner ? `name:${owner}` : "unassigned";
};

const ownerLabel = (action: ReportActionItem): string => {
  const owner = (action.owner || "").trim();
  return owner || "Unassigned";
};

const hasOwner = (action: ReportActionItem): boolean => Boolean((action.owner || "").trim());

const ExecutionPage = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [actions, setActions] = useState<ReportActionItem[]>([]);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [creatingAction, setCreatingAction] = useState(false);
  const [createActionError, setCreateActionError] = useState("");
  const [targetReportId, setTargetReportId] = useState<number | null>(null);
  const [actionsTab, setActionsTab] = useState<"firm-wide" | "my-actions" | "overdue">("firm-wide");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [ownerFilter, setOwnerFilter] = useState<string>("all");
  const [reportFilter, setReportFilter] = useState<string>("all");

  const isOverdueOnlyFilter = searchParams.get("filter") === "overdue";
  const readyReports = useMemo(
    () => reports.filter((report) => report.status === "ready"),
    [reports],
  );
  const latestReadyReport = useMemo(
    () =>
      readyReports
        .slice()
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0] || null,
    [readyReports],
  );
  const hasReadyCycle = readyReports.length > 0;
  const hasAnyCycle = reports.length > 0;

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      const [actionsResult, reportsResult] = await Promise.all([getFirmActions(), getReports(120)]);
      if (!mounted) return;

      if (!actionsResult.success || !actionsResult.actions) {
        setError(actionsResult.error || "Unable to load actions.");
        setActions([]);
      } else {
        setError("");
        setActions(actionsResult.actions);
      }

      if (reportsResult.success && reportsResult.reports) {
        setReports(reportsResult.reports);
      } else {
        setReports([]);
      }

      setLoading(false);
    };

    void load();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (targetReportId) return;
    const ready = readyReports
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
    const fallback = reports
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0];
    const preferred = ready || fallback;
    setTargetReportId(preferred?.id ?? null);
  }, [readyReports, reports, targetReportId]);

  const ownerOptions = useMemo(() => {
    const options = new Map<string, string>();
    actions.forEach((action) => {
      options.set(normalizeOwnerKey(action), ownerLabel(action));
    });
    return [...options.entries()]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [actions]);

  const ownerSuggestions = useMemo(
    () => ownerOptions.map((option) => option.label).filter((label) => label !== "Unassigned"),
    [ownerOptions],
  );

  const reportOptions = useMemo(() => {
    const byId = new Map<number, string>();
    actions.forEach((action) => {
      const reportId = Number(action.report_id || 0);
      if (!reportId) return;
      const reportName = action.report_name || reports.find((r) => r.id === reportId)?.name || `Report #${reportId}`;
      byId.set(reportId, reportName);
    });
    return [...byId.entries()]
      .map(([id, name]) => ({ id, name }))
      .sort((a, b) => b.id - a.id);
  }, [actions, reports]);

  const filteredActions = useMemo(() => {
    return actions.filter((action) => {
      if (isOverdueOnlyFilter && !isOverdue(action)) return false;
      if (!actionMatchesStatus(action, statusFilter)) return false;
      if (ownerFilter !== "all" && normalizeOwnerKey(action) !== ownerFilter) return false;
      if (reportFilter !== "all" && String(action.report_id || "") !== reportFilter) return false;
      return true;
    });
  }, [actions, isOverdueOnlyFilter, ownerFilter, reportFilter, statusFilter]);

  const myActionsSet = useMemo(() => {
    if (!user) return filteredActions;
    const myName = (user.name || "").trim().toLowerCase();
    const myEmail = (user.email || "").trim().toLowerCase();
    return filteredActions.filter((action) => {
      const owner = (action.owner || "").trim().toLowerCase();
      return (myName && owner === myName) || (myEmail && owner === myEmail);
    });
  }, [filteredActions, user]);

  const overdueActionsSet = useMemo(
    () => filteredActions.filter((action) => isOverdue(action)),
    [filteredActions],
  );

  const tabActions = useMemo(() => {
    if (actionsTab === "my-actions") return myActionsSet;
    if (actionsTab === "overdue") return overdueActionsSet;
    return filteredActions;
  }, [actionsTab, filteredActions, myActionsSet, overdueActionsSet]);

  const overdueNow = useMemo(() => tabActions.filter((action) => isOverdue(action)), [tabActions]);
  const blockedNow = useMemo(
    () => tabActions.filter((action) => action.status === "blocked" && !isOverdue(action)),
    [tabActions],
  );
  const unownedNow = useMemo(
    () =>
      tabActions.filter(
        (action) =>
          action.status !== "done" &&
          action.status !== "blocked" &&
          !isOverdue(action) &&
          !hasOwner(action),
      ),
    [tabActions],
  );
  const openReview = useMemo(
    () =>
      tabActions.filter(
        (action) => action.status === "open" && !isOverdue(action) && hasOwner(action),
      ),
    [tabActions],
  );
  const inProgressReview = useMemo(
    () =>
      tabActions.filter(
        (action) => action.status === "in_progress" && !isOverdue(action) && hasOwner(action),
      ),
    [tabActions],
  );
  const completedActions = useMemo(
    () => tabActions.filter((action) => action.status === "done"),
    [tabActions],
  );

  const summary = useMemo(
    () => ({
      overdue: overdueNow.length,
      unowned: tabActions.filter((action) => action.status !== "done" && !hasOwner(action)).length,
      blocked: tabActions.filter((action) => action.status === "blocked").length,
      needsReview: tabActions.filter((action) => action.status !== "done").length,
    }),
    [overdueNow.length, tabActions],
  );

  const accountabilityDirective = useMemo(() => {
    if (summary.overdue > 0) {
      return `${summary.overdue} overdue follow-through item${summary.overdue === 1 ? "" : "s"} need partner review now.`;
    }
    if (summary.unowned > 0) {
      return `${summary.unowned} follow-through item${summary.unowned === 1 ? "" : "s"} still need a named owner before the next discussion.`;
    }
    if (summary.blocked > 0) {
      return `${summary.blocked} blocked item${summary.blocked === 1 ? "" : "s"} may stall the current governance cycle.`;
    }
    if (summary.needsReview > 0) {
      return `${summary.needsReview} active follow-through item${summary.needsReview === 1 ? " is" : "s are"} moving without immediate risk.`;
    }
    return "Current follow-through is clear. Completed items remain available as cycle history.";
  }, [summary.blocked, summary.needsReview, summary.overdue, summary.unowned]);

  const resetFilters = () => {
    setStatusFilter("all");
    setOwnerFilter("all");
    setReportFilter("all");
  };

  const hasActiveFilters =
    statusFilter !== "all" ||
    ownerFilter !== "all" ||
    reportFilter !== "all" ||
    isOverdueOnlyFilter;

  const clearUrlFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("filter");
    setSearchParams(next);
  };

  const handleResetFilters = () => {
    resetFilters();
    if (isOverdueOnlyFilter) {
      clearUrlFilter();
    }
  };

  const openCreateActionModal = () => {
    if (!hasReadyCycle || !targetReportId) {
      toast.message("Add follow-through after the first brief is ready.");
      return;
    }
    setCreateActionError("");
    setCreateModalOpen(true);
  };

  const closeCreateActionModal = () => {
    setCreateActionError("");
    setCreateModalOpen(false);
  };

  const createActionInitialValues: ActionFormValues = {
    title: "",
    owner: "",
    owner_user_id: null,
    due_date: "",
    status: "open",
    timeframe: "Days 1-30",
    kpi: "",
    notes: "",
  };

  const handleCreateAction = async (values: ActionFormValues) => {
    if (!targetReportId) {
      setCreateActionError("No governance brief is available yet. Generate a report first, then add follow-through.");
      return;
    }

    setCreatingAction(true);
    setCreateActionError("");
    const result = await createReportAction(targetReportId, {
      title: values.title,
      owner: values.owner || undefined,
      owner_user_id: values.owner_user_id,
      status: values.status,
      due_date: values.due_date || null,
      timeframe: values.timeframe,
      kpi: values.kpi,
      notes: values.notes,
    });
    setCreatingAction(false);

    if (!result.success || !result.action) {
      setCreateActionError(result.error || "Unable to create action.");
      return;
    }

    setActions((prev) => [result.action as ReportActionItem, ...prev]);
    toast.success("Follow-through item created.");
    closeCreateActionModal();
  };

  const handleDeleteAction = async (actionId: number) => {
    const target = actions.find((a) => a.id === actionId);
    if (!target) return;
    const reportId = Number(target.report_id || 0);
    if (!reportId) {
      toast.error("Unable to delete: action has no linked report.");
      return;
    }
    const result = await deleteReportAction(reportId, actionId);
    if (!result.success) {
      toast.error(result.error || "Unable to delete action.");
      return;
    }
    setActions((prev) => prev.filter((a) => a.id !== actionId));
    toast.success("Follow-through item deleted.");
  };

  const renderActionGroup = (
    title: string,
    description: string,
    actionsForGroup: ReportActionItem[],
    emptyTitle: string,
    emptyDescription: string,
    accent: "risk" | "warn" | "neutral" | "success" = "neutral",
  ) => (
    <div className="space-y-4 rounded-[12px] border border-[#E3E8EF] bg-white p-5 shadow-sm">
      <div>
        <p className="gov-label">{title}</p>
        <p className="gov-body mt-2">{description}</p>
      </div>
      {actionsForGroup.length > 0 ? (
        <div className="space-y-4">
          {actionsForGroup.map((action) => (
            <ActionCard key={`${title}-${action.id}`} action={action} onDelete={handleDeleteAction} />
          ))}
        </div>
      ) : (
        <GovernanceEmptyState
          size="sm"
          icon={<ClipboardList size={18} />}
          title={emptyTitle}
          description={emptyDescription}
          className={
            accent === "risk"
              ? "rounded-[10px] border border-red-100 bg-red-50/50"
              : accent === "warn"
                ? "rounded-[10px] border border-amber-100 bg-amber-50/50"
                : accent === "success"
                  ? "rounded-[10px] border border-emerald-100 bg-emerald-50/40"
                  : "rounded-[10px] border border-slate-200 bg-slate-50/70"
          }
        />
      )}
    </div>
  );

  return (
    <PageWrapper
      eyebrow="Assigned Follow-Through"
      title="Follow-through for the current brief"
      description="The assigned follow-through record for the current governance brief. Review ownership, due-state, and blockers before the next partner discussion."
      contentClassName="stage-sequence"
      actions={
        <>
          <button
            type="button"
            className="inline-flex items-center justify-center rounded-[8px] border border-[#D1D5DB] bg-transparent px-4 py-2 text-sm font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400 disabled:hover:bg-transparent"
            onClick={handleResetFilters}
            disabled={!hasActiveFilters}
          >
            Reset view
          </button>
          {latestReadyReport ? (
            <Link
              className="inline-flex items-center justify-center rounded-[8px] border border-[#D1D5DB] bg-white px-4 py-2 text-sm font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
              to={`/dashboard/reports/${latestReadyReport.id}`}
            >
              Open current brief
            </Link>
          ) : null}
          <Link
            className={[
              "inline-flex items-center justify-center rounded-[8px] px-4 py-2 text-sm font-semibold transition-colors",
              hasReadyCycle
                ? "bg-[#0D1B2A] text-white hover:bg-[#16263b]"
                : "cursor-not-allowed border border-[#D1D5DB] bg-white text-slate-400 hover:bg-white",
            ].join(" ")}
            to={hasReadyCycle ? "#" : "/dashboard"}
            aria-disabled={!hasReadyCycle}
            onClick={(event) => {
              if (!hasReadyCycle) {
                event.preventDefault();
                return;
              }
              event.preventDefault();
              openCreateActionModal();
            }}
          >
            {hasReadyCycle ? "Add follow-through" : "Add follow-through after first cycle"}
          </Link>
        </>
      }
    >
      {!hasReadyCycle ? (
        <section className="rounded-xl border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
          <p className="gov-label text-blue-700">Follow-through</p>
          <h2 className="gov-section-intro mt-2">Follow-through opens after the first brief is ready</h2>
          <p className="gov-body mt-2 max-w-3xl">
            Clarion uses this workspace once the first governance cycle is ready: upload feedback, review recurring{" "}
            {DISPLAY_LABELS.clientIssuePlural.toLowerCase()}, then assign owners and due dates here before the next
            partner discussion.
          </p>
        </section>
      ) : null}

      <section className="rounded-[12px] border border-[#E3E8EF] bg-white px-6 py-5 shadow-sm">
        <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
          <div>
            <p className="gov-label">Follow-through posture for this cycle</p>
            <h2 className="gov-section-intro mt-2">What needs partner attention before the brief goes into a meeting.</h2>
            <p className="gov-body mt-3 max-w-xl">
              {accountabilityDirective}{" "}
              {latestReadyReport
                ? `Review and resolve these items in the current brief packet before the next partner discussion.`
                : "Upload feedback and generate the first brief to begin tracking follow-through here."}
            </p>
            <div className="mt-4 workspace-inline-stats">
              <div className="workspace-inline-stat">
                <p className="gov-label">Overdue</p>
                <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.overdue}</p>
              </div>
              <div className="workspace-inline-stat">
                <p className="gov-label">Unowned</p>
                <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.unowned}</p>
              </div>
              <div className="workspace-inline-stat">
                <p className="gov-label">Blocked</p>
                <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.blocked}</p>
              </div>
              <div className="workspace-inline-stat">
                <p className="gov-label">Needs review</p>
                <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.needsReview}</p>
              </div>
            </div>
            {latestReadyReport ? (
              <div className="mt-4 rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                <p className="gov-label">Current governance brief</p>
                <p className="mt-2 text-sm font-semibold text-slate-900">
                  {latestReadyReport.name || `Report #${latestReadyReport.id}`}
                </p>
                <p className="mt-1 text-xs leading-5 text-slate-600">
                  Follow-through status here feeds directly into the brief. Confirm ownership and due-state before
                  opening the brief for partner review.
                </p>
                <div className="mt-3">
                  <Link
                    to={`/dashboard/reports/${latestReadyReport.id}`}
                    className="inline-flex items-center rounded-[8px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-xs font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                  >
                    Open current brief
                  </Link>
                </div>
              </div>
            ) : null}
          </div>
          <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="gov-label">Refine only when needed</p>
                <p className="gov-body-sm mt-1">Use filters after you review the at-risk work first.</p>
              </div>
              {isOverdueOnlyFilter ? (
                <button type="button" className="gov-btn-secondary" onClick={clearUrlFilter}>
                  Clear overdue view
                </button>
              ) : null}
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-3">
              <div>
                <label className="gov-label mb-1 block">Status</label>
                <div className="relative">
                  <select
                    className="h-[40px] w-full appearance-none rounded-[8px] border border-[#D1D5DB] bg-white px-3 pr-8 text-[14px] text-[#0D1B2A] outline-none transition-colors focus:border-[#0EA5C2]"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                  >
                    <option value="all">All statuses</option>
                    <option value="open">Open</option>
                    <option value="in_progress">In progress</option>
                    <option value="blocked">Blocked</option>
                    <option value="done">Completed</option>
                    <option value="overdue">Overdue</option>
                  </select>
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">v</span>
                </div>
              </div>
              <div>
                <label className="gov-label mb-1 block">Owner</label>
                <div className="relative">
                  <select
                    className="h-[40px] w-full appearance-none rounded-[8px] border border-[#D1D5DB] bg-white px-3 pr-8 text-[14px] text-[#0D1B2A] outline-none transition-colors focus:border-[#0EA5C2]"
                    value={ownerFilter}
                    onChange={(e) => setOwnerFilter(e.target.value)}
                  >
                    <option value="all">All owners</option>
                    {ownerOptions.map((owner) => (
                      <option key={owner.value} value={owner.value}>
                        {owner.label}
                      </option>
                    ))}
                  </select>
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">v</span>
                </div>
              </div>
              <div>
                <label className="gov-label mb-1 block">Report</label>
                <div className="relative">
                  <select
                    className="h-[40px] w-full appearance-none rounded-[8px] border border-[#D1D5DB] bg-white px-3 pr-8 text-[14px] text-[#0D1B2A] outline-none transition-colors focus:border-[#0EA5C2]"
                    value={reportFilter}
                    onChange={(e) => setReportFilter(e.target.value)}
                  >
                    <option value="all">All reports</option>
                    {reportOptions.map((report) => (
                      <option key={report.id} value={String(report.id)}>
                        {report.name}
                      </option>
                    ))}
                  </select>
                  <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-500">v</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {error ? (
        <div className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">{error}</div>
      ) : null}

      {!loading && hasReadyCycle ? (
        <PageTabs
          value={actionsTab}
          onValueChange={(value) => {
            setActionsTab(value as typeof actionsTab);
            if (value !== "overdue" && isOverdueOnlyFilter) clearUrlFilter();
          }}
          tabs={[
            { value: "firm-wide", label: "Brief record" },
            {
              value: "my-actions",
              label: "Assigned to me",
              badgeCount: myActionsSet.length > 0 ? myActionsSet.length : undefined,
            },
            {
              value: "overdue",
              label: "Overdue now",
              badgeCount: overdueActionsSet.length,
              badgeUrgent: overdueActionsSet.length > 0,
            },
          ]}
        />
      ) : null}

      {loading ? (
        <section aria-label="Loading governance actions" className="grid gap-6 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, col) => (
            <ActionColumnSkeleton key={`exec-skeleton-${col}`} />
          ))}
        </section>
      ) : filteredActions.length === 0 ? (
        <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
          <GovernanceEmptyState
            size="lg"
            icon={<ClipboardList size={20} />}
            title="No follow-through created yet"
            description={
              !hasAnyCycle
                ? "The first cycle starts with a CSV upload. Once the report is ready, review client issues and assign ownership here."
                : !hasReadyCycle
                  ? "Your first governance cycle is still being prepared. Follow-through becomes available once the report is ready for issue review."
                  : "Follow-through opens after reviewing client issues. Confirm what needs ownership, then assign due dates and partners here."
            }
            primaryAction={
              !hasAnyCycle
                ? { label: "Upload feedback CSV", href: "/upload" }
                : !hasReadyCycle
                  ? { label: "Check report status", href: "/dashboard/reports" }
                  : { label: "Review client issues", href: "/dashboard/signals" }
            }
            secondaryAction={
              hasReadyCycle
                ? { label: "Add follow-through manually", onClick: openCreateActionModal }
                : { label: "Return to dashboard", href: "/dashboard" }
            }
            footer={
              <Link
                to="/demo"
                className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-700"
              >
                Open sample workspace
              </Link>
            }
          />
        </section>
      ) : tabActions.length === 0 && actionsTab !== "firm-wide" ? (
        <section className="rounded-xl border border-[#E3E8EF] bg-white shadow-sm">
          <GovernanceEmptyState
            size="md"
            icon={<ClipboardList size={20} />}
            title={
              actionsTab === "my-actions"
                ? "No follow-through assigned to you"
                : "No overdue follow-through - all within due dates"
            }
            description={
              actionsTab === "my-actions"
                ? "Review firm-wide follow-through to see where ownership is missing and assign yourself to the items that need a named lead."
                : "All current follow-through is within due dates. Review the firm-wide view to stay ahead of the next discussion."
            }
            primaryAction={{ label: "View all follow-through", onClick: () => setActionsTab("firm-wide") }}
          />
        </section>
      ) : (
        <section className="space-y-6">
          <div className="rounded-[12px] border border-[#E3E8EF] bg-white px-5 py-4 shadow-sm">
            <p className="gov-type-eyebrow">
              {actionsTab === "overdue"
                ? "Overdue follow-through"
                : actionsTab === "my-actions"
                  ? "Assigned follow-through"
                  : "Firm-wide follow-through"}
            </p>
            <p className="mt-1 text-sm text-slate-700">
              {actionsTab === "overdue"
                ? "These items have passed their due date and require immediate partner review."
                : actionsTab === "my-actions"
                  ? "This view keeps your owned follow-through visible before the next leadership discussion."
                  : "This is the complete follow-through record for the current brief. Review at-risk items first, then confirm what is moving cleanly."}
            </p>
          </div>

          <div className="space-y-5">
            <div>
              <p className="gov-type-eyebrow">At risk now</p>
              <p className="mt-1 text-sm text-slate-700">
                These items are the clearest threats to a credible partner-ready review cycle.
              </p>
            </div>
            <div className="grid gap-6 xl:grid-cols-3">
              {renderActionGroup(
                "Overdue",
                "Due dates have passed and need immediate review.",
                overdueNow,
                "No overdue follow-through",
                "Everything currently in view is still within due date.",
                "risk",
              )}
              {renderActionGroup(
                "Unowned",
                "These items still need a named owner before the next discussion.",
                unownedNow,
                "No unowned follow-through",
                "Visible items already have ownership assigned.",
                "warn",
              )}
              {renderActionGroup(
                "Blocked",
                "These items are stalled and may keep the current cycle from closing cleanly.",
                blockedNow,
                "No blocked follow-through",
                "Nothing in view is currently marked blocked.",
                "warn",
              )}
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <p className="gov-type-eyebrow">Needs review before the next partner discussion</p>
              <p className="mt-1 text-sm text-slate-700">
                Confirm ownership, progress, and due dates before these items roll into the next brief.
              </p>
            </div>
            <div className="grid gap-6 xl:grid-cols-2">
              {renderActionGroup(
                "Ready to start",
                "Owned items that still need visible movement.",
                openReview,
                "No ready-to-start follow-through",
                "There are no owned open items in the current view.",
              )}
              {renderActionGroup(
                "In progress",
                "Work already underway that should stay visible until it closes.",
                inProgressReview,
                "No in-progress follow-through",
                "There are no actively moving items in the current view.",
              )}
            </div>
          </div>

          <div className="space-y-5">
            <div>
              <p className="gov-type-eyebrow">Progressing cleanly</p>
              <p className="mt-1 text-sm text-slate-700">
                Completed follow-through stays visible as cycle history without competing with active review.
              </p>
            </div>
            {renderActionGroup(
              "Completed",
              "Closed items remain available as a record of follow-through.",
              completedActions,
              "No completed follow-through in view",
              "Completed items will appear here as the cycle progresses.",
              "success",
            )}
          </div>
        </section>
      )}

      <Dialog
        open={createModalOpen}
        onOpenChange={(open) => {
          if (!open) {
            closeCreateActionModal();
            return;
          }
          setCreateModalOpen(true);
        }}
      >
        <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create follow-through item</DialogTitle>
            <DialogDescription>
              Create an item with clear ownership, due date, and success metric.
            </DialogDescription>
          </DialogHeader>
          <ActionForm
            open={createModalOpen}
            mode="create"
            initialValues={createActionInitialValues}
            ownerOptions={ownerSuggestions}
            submitting={creatingAction}
            submitLabel="Add follow-through"
            submittingLabel="Adding..."
            serverError={createActionError}
            onCancel={closeCreateActionModal}
            onSubmit={handleCreateAction}
          />
        </DialogContent>
      </Dialog>
    </PageWrapper>
  );
};

export default ExecutionPage;
