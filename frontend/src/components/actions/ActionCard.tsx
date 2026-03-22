/**
 * ActionCard
 * Renders a single governance action using the shared GovernanceCard pattern.
 * Refactored from ad-hoc layout to GovernanceCard + GovStatusChip.
 *
 * Zones:
 *   header  -> action title + status chip
 *   meta    -> owner and due date
 *   detail  -> collapsible activity log
 *   actions -> "Open report" link + delete button
 */

import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Trash2 } from "lucide-react";

import { type ReportActionItem } from "@/api/authService";
import { formatApiDate, parseApiDate } from "@/lib/dateTime";
import GovernanceCard, { type GovernanceCardAccent } from "@/components/governance/GovernanceCard";
import GovStatusChip, { type GovStatusChipVariant } from "@/components/governance/GovStatusChip";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

type ActionCardProps = {
  action: ReportActionItem;
  onDelete?: (actionId: number) => Promise<void>;
};

const isOverdue = (action: ReportActionItem): boolean => {
  if (!action.due_date) return false;
  if (action.status === "done") return false;
  const dueDate = parseApiDate(action.due_date);
  return Boolean(dueDate && dueDate.getTime() < Date.now());
};

type StatusLabel = "Open" | "In Progress" | "Completed" | "Overdue" | "Blocked";

const resolveStatusLabel = (action: ReportActionItem): StatusLabel => {
  if (action.status === "blocked") return "Blocked";
  if (isOverdue(action)) return "Overdue";
  if (action.status === "done") return "Completed";
  if (action.status === "in_progress") return "In Progress";
  return "Open";
};

const statusToChipVariant: Record<StatusLabel, GovStatusChipVariant> = {
  Overdue: "risk",
  Blocked: "risk",
  "In Progress": "warn",
  Completed: "success",
  Open: "muted",
};

const statusToAccent: Record<StatusLabel, GovernanceCardAccent> = {
  Overdue: "risk",
  Blocked: "risk",
  "In Progress": "warn",
  Completed: "success",
  Open: "neutral",
};

const monthDay = (value?: string | null) =>
  formatApiDate(value, { month: "short", day: "numeric" }, "Date unavailable");

const buildActivityLog = (action: ReportActionItem) => {
  const entries = Array.isArray(action.activity_log) ? [...action.activity_log] : [];
  if (entries.length === 0) {
    entries.push({ date: monthDay(action.created_at), description: "Action created" });
    const owner = (action.owner || "").trim();
    if (owner && owner.toLowerCase() !== "unassigned") {
      entries.push({
        date: monthDay(action.updated_at || action.created_at),
        description: `Assigned to Partner ${owner}`,
      });
    }
    if (action.status && action.status !== "open") {
      entries.push({
        date: monthDay(action.updated_at || action.created_at),
        description: `Status updated to ${resolveStatusLabel(action)}`,
      });
    }
  }
  return entries;
};

const ActionCard = ({ action, onDelete }: ActionCardProps) => {
  const [showActivity, setShowActivity] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const label = resolveStatusLabel(action);
  const owner = action.owner?.trim() || "";
  const dueDate = action.due_date
    ? formatApiDate(action.due_date, { month: "short", day: "numeric" }, "No due date")
    : "";
  const reportId = Number(action.report_id || 0) || null;
  const activity = useMemo(() => buildActivityLog(action), [action]);

  const metaItems: string[] = [
    owner ? `Partner: ${owner}` : "Unassigned",
    action.due_date ? (isOverdue(action) ? `Due ${dueDate} - overdue` : `Due ${dueDate}`) : "No due date set",
  ];

  const handleConfirmDelete = async () => {
    if (!onDelete || deleting) return;
    setDeleting(true);
    try {
      await onDelete(action.id);
    } finally {
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  return (
    <>
      <GovernanceCard
        title={action.title}
        titleHref={`/dashboard/actions/${action.id}`}
        accent={statusToAccent[label]}
        chip={<GovStatusChip label={label} variant={statusToChipVariant[label]} />}
        meta={metaItems}
        detail={
          <div>
            <button
              type="button"
              className="text-[12px] text-[#9CA3AF] underline underline-offset-4 transition-colors hover:text-slate-700"
              onClick={() => setShowActivity((prev) => !prev)}
            >
              {showActivity ? "Hide activity" : "Show activity"}
            </button>
            {showActivity ? (
              <ul className="mt-2 space-y-1">
                {activity.map((entry, index) => (
                  <li
                    key={`${entry.date}-${entry.description}-${index}`}
                    className="text-[12px] text-[#9CA3AF]"
                  >
                    {entry.date} - {entry.description}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        }
        actions={
          <div className="flex items-center justify-between gap-2">
            {reportId ? (
              <Link
                className="text-[12px] text-[#6B7280] underline underline-offset-4 transition-colors hover:text-slate-700"
                to={`/dashboard/reports/${reportId}`}
              >
                Open report
              </Link>
            ) : (
              <span />
            )}
            {onDelete ? (
              <button
                type="button"
                aria-label="Delete action"
                disabled={deleting}
                className="rounded p-1 text-[#9CA3AF] transition-colors hover:bg-red-50 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-40"
                onClick={() => setConfirmOpen(true)}
              >
                <Trash2 size={14} strokeWidth={1.75} />
              </button>
            ) : null}
          </div>
        }
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this action?</AlertDialogTitle>
            <AlertDialogDescription>
              This cannot be undone. The action will be permanently removed from the workspace.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleting}
              className="bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
              onClick={(e) => {
                e.preventDefault();
                void handleConfirmDelete();
              }}
            >
              {deleting ? "Deleting..." : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default ActionCard;
