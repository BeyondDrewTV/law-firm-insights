import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Activity, Zap, ClipboardList } from "lucide-react";
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

const ExecutionPage = () => {
  const navigate = useNavigate();
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

  // ── Workflow tab: "firm-wide" | "my-actions" | "overdue" ─────────────────
  const [actionsTab, setActionsTab] = useState<"firm-wide" | "my-actions" | "overdue">("firm-wide");

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [ownerFilter, setOwnerFilter] = useState<string>("all");
  const [reportFilter, setReportFilter] = useState<string>("all");
  const isOverdueOnlyFilter = searchParams.get("filter") === "overdue";
  const readyReports = useMemo(
    () => reports.filter((report) => report.status === "ready"),
    [reports],
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
        setActions(actionsResult.actions);
        setError("");
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
      .filter((report) => report.status === "ready")
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

  const grouped = useMemo(() => {
    const open: ReportActionItem[] = [];
    const inProgress: ReportActionItem[] = [];
    const blocked: ReportActionItem[] = [];
    const completed: ReportActionItem[] = [];
    filteredActions.forEach((action) => {
      if (action.status === "done") completed.push(action);
      else if (action.status === "blocked") blocked.push(action);
      else if (action.status === "in_progress") inProgress.push(action);
      else open.push(action);
    });
    return { open, inProgress, blocked, completed };
  }, [filteredActions]);

  const summary = useMemo(
    () => ({
      total: filteredActions.length,
      open: grouped.open.length,
      overdue: filteredActions.filter((action) => isOverdue(action)).length,
    }),
    [filteredActions, grouped.open.length],
  );

  // ── Tab-aware action list ─────────────────────────────────────────────────
  // "Firm-wide"  → existing filteredActions (all)
  // "My Actions" → filtered to the current user's name/email match
  // "Overdue"    → uses existing isOverdue helper
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
    if (actionsTab === "overdue")    return overdueActionsSet;
    return filteredActions;
  }, [actionsTab, filteredActions, myActionsSet, overdueActionsSet]);

  const tabGrouped = useMemo(() => {
    const open: ReportActionItem[] = [];
    const inProgress: ReportActionItem[] = [];
    const blocked: ReportActionItem[] = [];
    const completed: ReportActionItem[] = [];
    tabActions.forEach((action) => {
      if (action.status === "done") completed.push(action);
      else if (action.status === "blocked") blocked.push(action);
      else if (action.status === "in_progress") inProgress.push(action);
      else open.push(action);
    });
    return { open, inProgress, blocked, completed };
  }, [tabActions]);

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

  const handleResetFilters = () => {
    resetFilters();
    if (isOverdueOnlyFilter) {
      clearUrlFilter();
    }
  };

  const clearUrlFilter = () => {
    const next = new URLSearchParams(searchParams);
    next.delete("filter");
    setSearchParams(next);
  };

  const openCreateActionModal = () => {
    if (!hasReadyCycle || !targetReportId) {
      toast.message("Create actions after the first report is ready.");
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
      setCreateActionError("No governance brief is available yet. Generate a report first, then create actions.");
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
    toast.success("Governance action created.");
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
    toast.success("Action deleted.");
  };

  return (
      <PageWrapper
        eyebrow="Follow-through"
        title="Action Workspace"
        description="Track ownership and execution of governance responses."
        contentClassName="stage-sequence"
        actions={
          <>
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-[8px] border border-[#D1D5DB] bg-transparent px-4 py-2 text-sm font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:text-slate-400 disabled:hover:bg-transparent"
              onClick={handleResetFilters}
              disabled={!hasActiveFilters}
            >
              Reset filters
            </button>
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
              {hasReadyCycle ? "Create Action" : "Create Action After First Cycle"}
            </Link>
          </>
        }
      >
        {!hasReadyCycle ? (
          <section className="rounded-xl border border-blue-100 bg-blue-50/70 p-5 shadow-sm">
            <p className="gov-label text-blue-700">Action Workspace</p>
            <h2 className="gov-section-intro mt-2">Actions open after a report is ready</h2>
            <p className="gov-body mt-2 max-w-3xl">
              Clarion uses this workspace for follow-through after the first governance cycle exists: upload feedback,
              review recurring {DISPLAY_LABELS.clientIssuePlural.toLowerCase()}, then assign owners and due dates here.
            </p>
          </section>
        ) : null}

        <section className="rounded-[12px] border border-[#E3E8EF] bg-white px-6 py-5 shadow-sm">
          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <div>
              <p className="gov-label">Current queue</p>
              <h2 className="gov-section-intro mt-2">Keep ownership visible, then narrow the list only when you need to.</h2>
              <p className="gov-body mt-3 max-w-xl">
                This workspace is primarily for assigning and finishing follow-through. Filters are available, but the main job is keeping the current action queue clear and credible.
              </p>
              <div className="mt-4 workspace-inline-stats">
                <div className="workspace-inline-stat">
                  <p className="gov-label">Visible</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.total}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">Open</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.open}</p>
                </div>
                <div className="workspace-inline-stat">
                  <p className="gov-label">Overdue</p>
                  <p className="mt-1 text-[20px] font-semibold text-slate-900">{loading ? "..." : summary.overdue}</p>
                </div>
              </div>
            </div>
            <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="gov-label">Narrow the workspace</p>
                  <p className="gov-body-sm mt-1">Use one filter pass when you need a cleaner execution list.</p>
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
                      <option value="all">All Statuses</option>
                      <option value="open">Open</option>
                      <option value="in_progress">In Progress</option>
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
                      <option value="all">All Owners</option>
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
                      <option value="all">All Reports</option>
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

        {/* ── Workflow tabs ─────────────────────────────────────────────── */}
        {!loading && hasReadyCycle ? (
          <PageTabs
            value={actionsTab}
            onValueChange={(v) => {
              setActionsTab(v as typeof actionsTab);
              // Sync: if URL has overdue filter and user switches away, clear it
              if (v !== "overdue" && isOverdueOnlyFilter) clearUrlFilter();
            }}
            tabs={[
              { value: "firm-wide",  label: "Firm-wide" },
              { value: "my-actions", label: "My Actions", badgeCount: myActionsSet.length > 0 ? myActionsSet.length : undefined },
              { value: "overdue",    label: "Overdue", badgeCount: overdueActionsSet.length, badgeUrgent: overdueActionsSet.length > 0 },
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
              title="No governance actions yet"
              description={
                !hasAnyCycle
                  ? "The first cycle starts with a CSV upload. Once the report is ready, review client issues and assign ownership here."
                  : !hasReadyCycle
                    ? "Your first governance cycle is still being prepared. Actions become available once the report is ready for issue review."
                    : `Actions are created after reviewing client issues. Confirm what needs ownership, then assign due dates and partners here.`
              }
              primaryAction={
                !hasAnyCycle
                  ? { label: "Upload feedback CSV", href: "/upload" }
                  : !hasReadyCycle
                    ? { label: "Check report status", href: "/dashboard/reports" }
                    : { label: "Review client issues", href: "/dashboard/signals" }
              }
              secondaryAction={
                hasReadyCycle && !(!hasAnyCycle) && !(!hasReadyCycle)
                  ? { label: "Create action manually", onClick: openCreateActionModal }
                  : { label: "Return to dashboard", href: "/dashboard" }
              }
              footer={
                <Link to="/demo" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-700">
                  Open read-only example cycle
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
                  ? "No governance actions assigned to you"
                  : "No overdue actions — all within due dates"
              }
              description={
                actionsTab === "my-actions"
                  ? "Review firm-wide actions to see where ownership is missing and assign yourself to any that need a named partner."
                  : "All current actions are within their due dates. Good standing — review firm-wide actions to stay ahead of upcoming deadlines."
              }
              primaryAction={{ label: "View firm-wide actions", onClick: () => setActionsTab("firm-wide") }}
            />
          </section>
        ) : (
          <section className="space-y-4">
            <div>
              <p className="gov-type-eyebrow">
                {actionsTab === "overdue" ? "Overdue actions" : actionsTab === "my-actions" ? "My assigned actions" : "By status"}
              </p>
              <p className="mt-1 text-sm text-slate-700">
                {actionsTab === "overdue"
                  ? "These actions have passed their due date and require immediate partner review."
                  : actionsTab === "my-actions"
                    ? "Actions where you are listed as the owner. Keep these current before the next review."
                    : "Open work stays first. Completed items remain visible without competing with the active queue."}
              </p>
            </div>
            <div className="grid gap-6 lg:grid-cols-4">
              <div className="space-y-4">
                <h2 className="text-lg font-medium text-neutral-900">Open Actions</h2>
                {tabGrouped.open.map((action) => (
                  <ActionCard key={`open-${action.id}`} action={action} onDelete={handleDeleteAction} />
                ))}
              </div>
              <div className="space-y-4">
                <h2 className="text-lg font-medium text-neutral-900">In Progress</h2>
                {tabGrouped.inProgress.map((action) => (
                  <ActionCard key={`progress-${action.id}`} action={action} onDelete={handleDeleteAction} />
                ))}
              </div>
              <div className="space-y-4">
                <h2 className="text-lg font-medium text-neutral-900">Blocked</h2>
                {tabGrouped.blocked.map((action) => (
                  <ActionCard key={`blocked-${action.id}`} action={action} onDelete={handleDeleteAction} />
                ))}
              </div>
              <div className="space-y-4">
                <h2 className="text-lg font-medium text-neutral-900">Completed</h2>
                {tabGrouped.completed.map((action) => (
                  <ActionCard key={`done-${action.id}`} action={action} onDelete={handleDeleteAction} />
                ))}
              </div>
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
              <DialogTitle>Create Governance Action</DialogTitle>
              <DialogDescription>
                Create an action with clear ownership, due date, and success metric.
              </DialogDescription>
            </DialogHeader>
            <ActionForm
              open={createModalOpen}
              mode="create"
              initialValues={createActionInitialValues}
              ownerOptions={ownerSuggestions}
              submitting={creatingAction}
              submitLabel="Create Action"
              submittingLabel="Creating..."
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
