/**
 * ActionDetail — Accountability Hub Layout
 * ─────────────────────────────────────────────────────────────────────────────
 * Answers "Who owns this, by when, and why does it matter?" at a glance.
 *
 * Structure:
 *   ┌────────────────────────────────────────────────────────────────────────┐
 *   │  ACCOUNTABILITY HEADER  title · status chip · Edit/View-Report CTAs   │
 *   ├────────────────────────────────┬───────────────────────────────────────┤
 *   │  LEFT — Context                │  RIGHT — Accountability sidebar       │
 *   │  Notes / KPI / Timeframe       │  Owner · Due date · Status            │
 *   │  Originating signal context    │  Linked governance brief              │
 *   │  Evidence excerpt              │  Activity timeline                    │
 *   └────────────────────────────────┴───────────────────────────────────────┘
 *
 * Mobile order: sidebar (owner panel) → left content → briefs → timeline
 *
 * Data: loaded from getFirmActions() + getReportDetail() for evidence.
 * No new API shapes — uses existing updateReportAction for inline edits.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import {
  getFirmActions,
  getReportDetail,
  updateReportAction,
  type ReportActionItem,
  type ReportDetail,
} from "@/api/authService";
import ActionForm, { type ActionFormValues } from "@/components/actions/ActionForm";
import GovStatusChip, {
  resolveChipVariantForActionStatus,
} from "@/components/governance/GovStatusChip";
import PageWrapper from "@/components/governance/PageWrapper";
import { formatApiDate } from "@/lib/dateTime";

// ── Helpers ───────────────────────────────────────────────────────────────────

const isOverdue = (action: ReportActionItem): boolean => {
  if (!action.due_date) return false;
  if (action.status === "done") return false;
  const due = Date.parse(action.due_date);
  return Number.isFinite(due) && due < Date.now();
};

type StatusLabel = "Open" | "In Progress" | "Completed" | "Overdue" | "Blocked";

const resolveStatusLabel = (action: ReportActionItem): StatusLabel => {
  if (action.status === "blocked") return "Blocked";
  if (isOverdue(action)) return "Overdue";
  if (action.status === "done") return "Completed";
  if (action.status === "in_progress") return "In Progress";
  return "Open";
};

const fmtLong = (value?: string | null) =>
  formatApiDate(value, { month: "long", day: "numeric", year: "numeric" }, "Not set");

const fmtShort = (value?: string | null) =>
  formatApiDate(value, { month: "short", day: "numeric" }, "Not set");

const buildActivityLog = (action: ReportActionItem) => {
  const entries = Array.isArray(action.activity_log) ? [...action.activity_log] : [];
  if (entries.length === 0) {
    entries.push({ date: fmtShort(action.created_at), description: "Action created" });
    const owner = (action.owner || "").trim();
    if (owner && owner.toLowerCase() !== "unassigned") {
      entries.push({
        date: fmtShort(action.updated_at || action.created_at),
        description: `Assigned to ${owner}`,
      });
    }
    if (action.status && action.status !== "open") {
      entries.push({
        date: fmtShort(action.updated_at || action.created_at),
        description: `Status updated to ${resolveStatusLabel(action)}`,
      });
    }
  }
  return entries;
};

const toFormValues = (action: ReportActionItem): ActionFormValues => ({
  title: action.title || "",
  owner: action.owner || "",
  owner_user_id: action.owner_user_id ?? null,
  due_date: action.due_date || "",
  status: (action.status as ActionFormValues["status"]) || "open",
  timeframe: (action.timeframe as ActionFormValues["timeframe"]) || "Days 1-30",
  kpi: action.kpi || "",
  notes: action.notes || "",
});

// ── Component ─────────────────────────────────────────────────────────────────

const ActionDetail = () => {
  const { actionId } = useParams<{ actionId: string }>();
  const parsedId = Number(actionId);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [action, setAction] = useState<ReportActionItem | null>(null);
  const [reportDetail, setReportDetail] = useState<ReportDetail | null>(null);
  const [allOwners, setAllOwners] = useState<string[]>([]);
  const [showEditForm, setShowEditForm] = useState(false);
  const [submittingEdit, setSubmittingEdit] = useState(false);
  const [editError, setEditError] = useState("");

  const loadAction = useCallback(async () => {
    const result = await getFirmActions();
    if (!result.success || !result.actions) return null;
    // Collect all owner names for the form datalist
    const owners = Array.from(
      new Set(result.actions.map((a) => (a.owner || "").trim()).filter(Boolean))
    );
    setAllOwners(owners);
    return result.actions.find((a) => a.id === parsedId) ?? null;
  }, [parsedId]);

  useEffect(() => {
    if (!Number.isFinite(parsedId) || parsedId <= 0) {
      setError("Invalid action ID.");
      setLoading(false);
      return;
    }

    let active = true;
    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const found = await loadAction();
        if (!active) return;
        if (!found) {
          setError("Action not found. It may have been deleted or you may not have access.");
          setLoading(false);
          return;
        }
        setAction(found);

        // Load report detail for evidence excerpts (best-effort)
        const reportId = Number(found.report_id || 0);
        if (reportId > 0) {
          const rResult = await getReportDetail(reportId);
          if (active && rResult.success && rResult.report) {
            setReportDetail(rResult.report);
          }
        }
      } catch {
        if (active) setError("Unable to load action detail right now.");
      } finally {
        if (active) setLoading(false);
      }
    };

    void load();
    return () => { active = false; };
  }, [loadAction, parsedId]);

  const handleSaveEdit = async (values: ActionFormValues) => {
    if (!action) return;
    const reportId = Number(action.report_id || 0);
    if (!reportId) {
      setEditError("This action is not linked to a report and cannot be updated.");
      return;
    }
    setSubmittingEdit(true);
    setEditError("");
    try {
      const result = await updateReportAction(reportId, action.id, {
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
        const msg = result.error || "Unable to save changes.";
        setEditError(msg);
        toast.error(msg);
        return;
      }
      // Merge update into local state
      setAction((prev) =>
        prev
          ? {
              ...prev,
              title: values.title,
              owner: values.owner,
              owner_user_id: values.owner_user_id,
              status: values.status,
              due_date: values.due_date || null,
              timeframe: values.timeframe,
              kpi: values.kpi,
              notes: values.notes,
              updated_at: new Date().toISOString(),
            }
          : prev,
      );
      toast.success("Action updated");
      setShowEditForm(false);
    } finally {
      setSubmittingEdit(false);
    }
  };

  const statusLabel = useMemo(() => (action ? resolveStatusLabel(action) : "Open"), [action]);
  const overdueFlag = useMemo(() => (action ? isOverdue(action) : false), [action]);
  const activityLog = useMemo(() => (action ? buildActivityLog(action) : []), [action]);
  const reportId = action ? Number(action.report_id || 0) || null : null;

  // Evidence: up to 2 complaint excerpts from the linked report
  const evidenceExcerpts = useMemo(() => {
    if (!reportDetail) return [];
    const complaints = Array.isArray(reportDetail.top_complaints) ? reportDetail.top_complaints : [];
    return complaints.slice(0, 2).map((text, idx) => ({ id: idx, text: String(text || "").trim() })).filter((e) => e.text);
  }, [reportDetail]);

  // Derive which signal this action relates to (best-effort from title/notes)
  const signalHint = useMemo(() => {
    if (!action) return null;
    const text = [action.title, action.notes || ""].join(" ").trim();
    return text.length > 0 ? text.split(/[:.]/)[0].trim() : null;
  }, [action]);


  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <PageWrapper
      title="Action Detail"
      description="Who owns this, by when, and why does it matter?"
      contentClassName="stage-sequence"
    >
      {/* Back nav */}
      <div>
        <Link to="/dashboard/actions" className="text-[13px] font-medium text-[#0EA5C2] hover:text-[#0b8ca7]">
          ← Back to Actions
        </Link>
      </div>

      {/* Error state */}
      {error ? (
        <section className="rounded-xl border border-destructive/35 bg-destructive/10 p-6 text-sm text-destructive">
          {error}
        </section>
      ) : null}

      {/* Skeleton loader */}
      {loading ? (
        <section className="space-y-4">
          <div className="h-28 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
          <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
            <div className="space-y-4">
              <div className="h-40 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
              <div className="h-28 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
            </div>
            <div className="h-56 animate-pulse rounded-xl border border-[#E5E7EB] bg-white" />
          </div>
        </section>
      ) : action ? (
        <div className="space-y-6">

          {/* ── Accountability header ──────────────────────────────── */}
          <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <GovStatusChip
                    label={statusLabel}
                    variant={resolveChipVariantForActionStatus(action.status, overdueFlag)}
                  />
                  {overdueFlag ? (
                    <span className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#DC2626]">
                      Overdue
                    </span>
                  ) : null}
                  <span className="gov-type-eyebrow">
                    Governance Action
                  </span>
                </div>
                <h1 className="mt-2 text-[22px] font-bold leading-snug text-[#0D1B2A]">{action.title}</h1>
                <p className="mt-1 text-[13px] text-slate-500">
                  {action.timeframe ? `Timeframe: ${action.timeframe}` : "No timeframe set"}
                  {reportDetail?.name ? ` · ${reportDetail.name}` : ""}
                </p>
              </div>
              {/* Primary CTAs */}
              <div className="flex shrink-0 flex-wrap items-center gap-2 pt-1">
                {!showEditForm ? (
                  <button
                    type="button"
                    className="inline-flex items-center rounded-[8px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#16263b]"
                    onClick={() => { setEditError(""); setShowEditForm(true); }}
                  >
                    Edit Action
                  </button>
                ) : null}
                {reportId ? (
                  <Link
                    to={`/dashboard/reports/${reportId}`}
                    className="inline-flex items-center rounded-[8px] border border-[#D1D5DB] bg-white px-4 py-2 text-[13px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                  >
                    View Report
                  </Link>
                ) : null}
              </div>
            </div>

            {/* Inline edit form */}
            {showEditForm ? (
              <div className="mt-5 rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
                <p className="mb-3 gov-type-eyebrow">
                  Edit action
                </p>
                <ActionForm
                  open
                  mode="edit"
                  initialValues={toFormValues(action)}
                  ownerOptions={allOwners}
                  submitting={submittingEdit}
                  submitLabel="Save changes"
                  submittingLabel="Saving..."
                  serverError={editError}
                  onCancel={() => { if (submittingEdit) return; setEditError(""); setShowEditForm(false); }}
                  onSubmit={handleSaveEdit}
                />
              </div>
            ) : null}
          </section>


          {/* ── Two-column accountability hub ──────────────────────── */}
          <div className="grid gap-6 lg:grid-cols-[1fr_340px] lg:items-start">

            {/* ═══════════════════════════════════════════════════════
                LEFT — Context column
                Mobile: order-2 (below owner panel)
                ═══════════════════════════════════════════════════════ */}
            <div className="order-2 space-y-5 lg:order-1">

              {/* Action details: KPI + notes */}
              <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <p className="gov-type-eyebrow">
                  Action Details
                </p>

                {action.kpi ? (
                  <div className="mt-4">
                    <p className="gov-type-eyebrow">
                      Success Measure
                    </p>
                    <p className="mt-1 text-[14px] leading-relaxed text-[#0D1B2A]">{action.kpi}</p>
                  </div>
                ) : null}

                {action.notes ? (
                  <div className="mt-4">
                    <p className="gov-type-eyebrow">
                      Notes
                    </p>
                    <p className="mt-1 text-[14px] leading-relaxed text-[#374151] whitespace-pre-wrap">{action.notes}</p>
                  </div>
                ) : null}

                {!action.kpi && !action.notes ? (
                  <p className="mt-3 text-[13px] text-slate-400">No description or notes have been added yet.</p>
                ) : null}
              </section>

              {/* Originating signal context */}
              <section className="rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <p className="gov-type-eyebrow">
                  Context
                </p>
                <h2 className="mt-1 text-[16px] font-semibold text-[#0D1B2A]">
                  Originating signal
                </h2>
                <p className="mt-2 text-[13px] leading-relaxed text-[#374151]">
                  {signalHint
                    ? `This action was created in response to the "${signalHint}" signal.`
                    : "This action was created in response to a recurring client feedback signal."}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Link
                    to="/dashboard/signals"
                    className="inline-flex items-center rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                  >
                    View all signals →
                  </Link>
                  {reportId ? (
                    <Link
                      to={`/dashboard/reports/${reportId}`}
                      className="inline-flex items-center rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-1.5 text-[12px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                    >
                      Open source report →
                    </Link>
                  ) : null}
                </div>

                {/* Evidence excerpts */}
                {evidenceExcerpts.length > 0 ? (
                  <div className="mt-4 space-y-2">
                    <p className="gov-type-eyebrow">
                      Representative client feedback
                    </p>
                    {evidenceExcerpts.map((excerpt) => (
                      <blockquote
                        key={excerpt.id}
                        className="rounded-[8px] border border-[#E5E7EB] border-l-[3px] border-l-rose-400 bg-rose-50/40 px-4 py-3"
                      >
                        <p className="text-[13px] italic leading-relaxed text-[#374151]">
                          &quot;{excerpt.text}&quot;
                        </p>
                        <p className="mt-1.5 text-[11px] text-slate-400">Anonymous client feedback</p>
                      </blockquote>
                    ))}
                  </div>
                ) : null}
              </section>
            </div>


            {/* ═══════════════════════════════════════════════════════
                RIGHT — Accountability sidebar
                Mobile: order-1 (above context, answers "who/when/why" first)
                ═══════════════════════════════════════════════════════ */}
            <div className="order-1 space-y-4 lg:order-2">

              {/* Accountability panel — owner, due date, status */}
              <aside className="rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <p className="gov-type-eyebrow">
                  Accountability
                </p>
                <dl className="mt-3 space-y-4">

                  {/* Owner */}
                  <div>
                    <dt className="gov-type-eyebrow">Owner</dt>
                    <dd className="mt-1 flex items-center gap-2">
                      {action.owner ? (
                        <>
                          <span className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-[#0D1B2A] text-[11px] font-bold text-white">
                            {action.owner.trim().charAt(0).toUpperCase()}
                          </span>
                          <span className="text-[14px] font-semibold text-[#0D1B2A]">{action.owner}</span>
                        </>
                      ) : (
                        <GovStatusChip label="Unassigned" variant="warn" size="sm" />
                      )}
                    </dd>
                  </div>

                  {/* Due date */}
                  <div>
                    <dt className="gov-type-eyebrow">Due date</dt>
                    <dd className="mt-1">
                      {action.due_date ? (
                        <span
                          className={[
                            "text-[14px] font-semibold",
                            overdueFlag ? "text-[#DC2626]" : "text-[#0D1B2A]",
                          ].join(" ")}
                        >
                          {fmtLong(action.due_date)}
                          {overdueFlag ? " — overdue" : ""}
                        </span>
                      ) : (
                        <GovStatusChip label="No due date" variant="muted" size="sm" />
                      )}
                    </dd>
                  </div>

                  {/* Status */}
                  <div>
                    <dt className="gov-type-eyebrow">Status</dt>
                    <dd className="mt-1">
                      <GovStatusChip
                        label={statusLabel}
                        variant={resolveChipVariantForActionStatus(action.status, overdueFlag)}
                      />
                    </dd>
                  </div>

                  {/* Timeframe */}
                  {action.timeframe ? (
                    <div>
                      <dt className="gov-type-eyebrow">Timeframe</dt>
                      <dd className="mt-1 text-[13px] text-[#374151]">{action.timeframe}</dd>
                    </div>
                  ) : null}

                </dl>
              </aside>

              {/* Linked governance brief */}
              {reportId ? (
                <aside className="order-3 rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] lg:order-none">
                  <p className="gov-type-eyebrow">
                    Governance Brief
                  </p>
                  <Link
                    to={`/dashboard/reports/${reportId}`}
                    className="mt-3 flex items-center justify-between gap-2 rounded-[8px] border border-[#E5E7EB] bg-[#FAFBFC] px-3 py-2.5 transition-colors hover:bg-slate-50"
                  >
                    <div>
                      <p className="text-[13px] font-medium text-[#0D1B2A]">
                        {reportDetail?.name || `Report #${reportId}`}
                      </p>
                      {reportDetail?.created_at ? (
                        <p className="text-[11px] text-slate-400">{fmtLong(reportDetail.created_at)}</p>
                      ) : null}
                    </div>
                    <span className="shrink-0 text-[11px] font-medium text-[#0EA5C2]">View →</span>
                  </Link>
                </aside>
              ) : null}

              {/* Activity timeline */}
              <aside className="order-4 rounded-[12px] border border-[#E5E7EB] bg-white px-5 py-4 shadow-[0_1px_3px_rgba(0,0,0,0.06)] lg:order-none">
                <p className="gov-type-eyebrow">
                  Activity Timeline
                </p>
                {activityLog.length > 0 ? (
                  <ol className="relative mt-3 ml-2 space-y-4 border-l border-[#E5E7EB] pl-4">
                    {activityLog.map((entry, idx) => (
                      <li key={`tl-${idx}`} className="relative">
                        <span className="absolute -left-[21px] top-[3px] h-2 w-2 rounded-full border-2 border-[#0EA5C2] bg-white" />
                        <p className="text-[13px] font-medium text-[#0D1B2A]">{entry.description}</p>
                        <p className="text-[11px] text-slate-400">{entry.date}</p>
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

export default ActionDetail;
