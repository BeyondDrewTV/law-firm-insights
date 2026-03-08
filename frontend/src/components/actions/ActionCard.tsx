import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { type ReportActionItem } from "@/api/authService";
import { formatApiDate, parseApiDate } from "@/lib/dateTime";

type ActionCardProps = {
  action: ReportActionItem;
};

const isOverdue = (action: ReportActionItem): boolean => {
  if (!action.due_date) return false;
  if (action.status === "done") return false;
  const dueDate = parseApiDate(action.due_date);
  return Boolean(dueDate && dueDate.getTime() < Date.now());
};

const statusLabel = (action: ReportActionItem): "Open" | "In Progress" | "Completed" | "Overdue" | "Blocked" => {
  if (action.status === "blocked") return "Blocked";
  if (isOverdue(action)) return "Overdue";
  if (action.status === "done") return "Completed";
  if (action.status === "in_progress") return "In Progress";
  return "Open";
};

const statusClass = (label: ReturnType<typeof statusLabel>) => {
  if (label === "Overdue" || label === "Blocked") return "bg-[#FEF2F2] text-[#DC2626]";
  if (label === "Completed") return "gov-chip-success";
  if (label === "In Progress") return "gov-chip-warn";
  return "gov-chip-muted";
};

const monthDay = (value?: string | null) => formatApiDate(value, { month: "short", day: "numeric" }, "Date unavailable");

const buildActivityLog = (action: ReportActionItem) => {
  const entries = Array.isArray(action.activity_log) ? [...action.activity_log] : [];
  if (entries.length === 0) {
    entries.push({ date: monthDay(action.created_at), description: "Action created" });
    const owner = (action.owner || "").trim();
    if (owner && owner.toLowerCase() !== "unassigned") {
      entries.push({ date: monthDay(action.updated_at || action.created_at), description: `Assigned to Partner ${owner}` });
    }
    if (action.status && action.status !== "open") {
      entries.push({
        date: monthDay(action.updated_at || action.created_at),
        description: `Status updated to ${statusLabel(action)}`,
      });
    }
  }
  return entries;
};

const ActionCard = ({ action }: ActionCardProps) => {
  const [showActivity, setShowActivity] = useState(false);
  const label = statusLabel(action);
  const owner = action.owner?.trim() || "";
  const dueDate = action.due_date ? formatApiDate(action.due_date, { month: "short", day: "numeric" }, "No due date") : "";
  const reportId = Number(action.report_id || 0) || null;
  const activity = useMemo(() => buildActivityLog(action), [action]);

  return (
    <article className="gov-level-2 p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="min-w-0 flex-1 line-clamp-2 text-sm font-semibold text-neutral-900">{action.title}</h3>
        <span className={`shrink-0 ${statusClass(label)}`}>{label}</span>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
        <p className={owner ? "text-[#374151]" : "text-[#9CA3AF]"}>{owner ? `Partner: ${owner}` : "Unassigned"}</p>
        <span className="text-neutral-300">|</span>
        <p className={action.due_date ? (isOverdue(action) ? "text-[#DC2626]" : "text-[#374151]") : "text-[#9CA3AF]"}>
          {action.due_date ? `Due ${dueDate}` : "No due date set"}
        </p>
      </div>

      <div className="mt-3">
        <button
          type="button"
          className="text-xs text-[#6B7280] underline underline-offset-4 transition-colors hover:text-slate-700"
          onClick={() => setShowActivity((prev) => !prev)}
        >
          {showActivity ? "Hide activity" : "Show activity"}
        </button>
        {showActivity ? (
          <ul className="mt-2 space-y-1">
            {activity.map((entry, index) => (
              <li key={`${entry.date}-${entry.description}-${index}`} className="text-[12px] text-[#6B7280]">
                {entry.date} - {entry.description}
              </li>
            ))}
          </ul>
        ) : null}
      </div>

      {reportId ? (
        <div className="mt-3">
          <Link className="gov-btn-quiet text-xs" to={`/dashboard/reports/${reportId}`}>
            Open report
          </Link>
        </div>
      ) : null}
    </article>
  );
};

export default ActionCard;
