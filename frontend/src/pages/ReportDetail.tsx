
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { ChevronDown, ChevronRight, Loader2, PencilLine, X } from "lucide-react";
import { toast } from "sonner";
import {
  createReportAction,
  getPartnerBriefDeliveryStatus,
  getReportActions,
  getReportDetail,
  sendPartnerBriefEmail,
  updateReportAction,
  updateReportName,
  type PartnerBriefDeliveryStatus,
  type ReportActionItem,
  type ReportDetail as ReportDetailData,
} from "@/api/authService";
import ActionForm, { type ActionFormValues, type ActionStatus } from "@/components/actions/ActionForm";
import ClientQuoteCard from "@/components/ClientQuoteCard";
import EmailBriefPreviewModal from "@/components/reports/EmailBriefPreviewModal";
import { formatApiDate, formatApiDateTime } from "@/lib/dateTime";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

const STATUS_OPTIONS: Array<{ value: ActionStatus; label: string }> = [
  { value: "open", label: "Planned" },
  { value: "in_progress", label: "In Progress" },
  { value: "blocked", label: "Blocked" },
  { value: "done", label: "Completed" },
];

const normalizeStatus = (value: string | null | undefined): ActionStatus => {
  if (value === "in_progress") return "in_progress";
  if (value === "blocked") return "blocked";
  if (value === "done") return "done";
  return "open";
};

const startOfToday = (): Date => {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d;
};

const asDayDate = (value: string | null | undefined): Date | null => {
  if (!value) return null;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return null;
  parsed.setHours(0, 0, 0, 0);
  return parsed;
};

const isCompleted = (action: ReportActionItem): boolean => normalizeStatus(action.status) === "done";
const isOverdue = (action: ReportActionItem): boolean => {
  if (isCompleted(action)) return false;
  const due = asDayDate(action.due_date);
  return !!due && due.getTime() < startOfToday().getTime();
};
const isDueSoon = (action: ReportActionItem): boolean => {
  if (isCompleted(action)) return false;
  const due = asDayDate(action.due_date);
  if (!due) return false;
  const today = startOfToday();
  const soon = new Date(today);
  soon.setDate(soon.getDate() + 7);
  return due.getTime() >= today.getTime() && due.getTime() <= soon.getTime();
};
const isUnassigned = (action: ReportActionItem): boolean => {
  if (isCompleted(action)) return false;
  const ownerText = (action.owner || "").trim();
  const ownerUserId = action.owner_user_id;
  return (!ownerText || ownerText.toLowerCase() === "unassigned") && (ownerUserId === null || ownerUserId === undefined);
};

const compareActions = (a: ReportActionItem, b: ReportActionItem): number => {
  const bucket = (item: ReportActionItem): number => {
    if (isOverdue(item)) return 0;
    if (isDueSoon(item)) return 1;
    if (!isCompleted(item)) return 2;
    return 3;
  };
  const delta = bucket(a) - bucket(b);
  if (delta !== 0) return delta;
  const aDue = asDayDate(a.due_date)?.getTime() ?? Number.MAX_SAFE_INTEGER;
  const bDue = asDayDate(b.due_date)?.getTime() ?? Number.MAX_SAFE_INTEGER;
  return aDue - bDue;
};

const formatDate = (value?: string | null): string =>
  formatApiDate(value, { month: "short", day: "numeric", year: "numeric" }, "-");
const formatDateTime = (value?: string | null): string =>
  formatApiDateTime(value, { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }, "-");
const escapeHtml = (value: string): string =>
  value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
const statusLabel = (status: string | null | undefined): string => {
  const normalized = normalizeStatus(status);
  return STATUS_OPTIONS.find((row) => row.value === normalized)?.label || "Planned";
};
const statusBadgeClass = (status: string | null | undefined): string => {
  const normalized = normalizeStatus(status);
  if (normalized === "done") return "gov-badge gov-badge-controlled";
  if (normalized === "blocked") return "gov-badge gov-badge-critical";
  if (normalized === "in_progress") return "gov-badge gov-badge-watch";
  return "gov-badge";
};

const formatMonthDay = (value?: string | null): string => {
  if (!value) return new Date().toLocaleDateString([], { month: "long", day: "numeric" });
  const parsed = new Date(value);
  if (!Number.isFinite(parsed.getTime())) return new Date().toLocaleDateString([], { month: "long", day: "numeric" });
  return parsed.toLocaleDateString([], { month: "long", day: "numeric" });
};

const appendActivity = (
  action: ReportActionItem,
  description: string,
  timestamp?: string | null,
): ReportActionItem => {
  const existing = Array.isArray(action.activity_log) ? action.activity_log : [];
  return {
    ...action,
    activity_log: [...existing, { date: formatMonthDay(timestamp || action.updated_at || action.created_at), description }],
  };
};

const isRateLimitMessage = (message: string | undefined): boolean => {
  const normalized = (message || "").toLowerCase();
  return normalized.includes("rate limit") || normalized.includes("too many") || normalized.includes("429");
};

const ReportDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const reportId = Number(id);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [historyNotice, setHistoryNotice] = useState<string | null>(null);
  const [historyTruncated, setHistoryTruncated] = useState(false);
  const [report, setReport] = useState<ReportDetailData | null>(null);
  const [actions, setActions] = useState<ReportActionItem[]>([]);
  const [actionsError, setActionsError] = useState("");
  const [isBusyRetrying, setIsBusyRetrying] = useState(false);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const [showRateLimitRetryPrompt, setShowRateLimitRetryPrompt] = useState(false);
  const [reloadNonce, setReloadNonce] = useState(0);

  const [renameMode, setRenameMode] = useState<"idle" | "editing" | "saving" | "saved" | "error">("idle");
  const [renameDraft, setRenameDraft] = useState("");
  const [renameError, setRenameError] = useState("");

  const [actionFormMode, setActionFormMode] = useState<"create" | "edit" | null>(null);
  const [actionFormSubmitting, setActionFormSubmitting] = useState(false);
  const [actionFormError, setActionFormError] = useState("");
  const [editingActionId, setEditingActionId] = useState<number | null>(null);
  const [isSendingBrief, setIsSendingBrief] = useState(false);
  const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);
  const [briefDeliveryStatus, setBriefDeliveryStatus] = useState<PartnerBriefDeliveryStatus | null>(null);
  const [briefDeliveryStatusLoading, setBriefDeliveryStatusLoading] = useState(false);

  const [detailsOpen, setDetailsOpen] = useState(false);

  useEffect(() => {
    if (!reportId || Number.isNaN(reportId)) {
      setError("Invalid report identifier.");
      setLoading(false);
      return;
    }

    const detailController = new AbortController();
    const actionsController = new AbortController();
    let active = true;
    let timedOut = false;
    const loadTimeout = window.setTimeout(() => {
      timedOut = true;
      detailController.abort();
      actionsController.abort();
    }, 9000);

    const load = async () => {
      setLoading(true);
      setError("");
      setActionsError("");
      setIsBusyRetrying(false);
      setRetryAttempt(0);
      setShowRateLimitRetryPrompt(false);
      const retryNotice = (meta: { attempt: number }) => {
        setIsBusyRetrying(true);
        setRetryAttempt(meta.attempt);
      };
      const [detailResult, actionsResult] = await Promise.all([
        getReportDetail(reportId, detailController.signal, { onRetry: retryNotice }),
        getReportActions(reportId, actionsController.signal, { onRetry: retryNotice }),
      ]);
      window.clearTimeout(loadTimeout);

      if (!active) return;
      setIsBusyRetrying(false);

      if (timedOut) {
        setShowRateLimitRetryPrompt(true);
        setError("");
        setActionsError("");
        setLoading(false);
        return;
      }

      const detailRateLimited = !detailResult.success && isRateLimitMessage(detailResult.error);
      const actionsRateLimited = !actionsResult.success && isRateLimitMessage(actionsResult.error);
      const isRateLimited = detailRateLimited || actionsRateLimited;

      if (detailResult.success && detailResult.report) {
        setReport(detailResult.report);
        setRenameDraft(detailResult.report.name || detailResult.report.title || "");
        setHistoryNotice(detailResult.history_notice || null);
        setHistoryTruncated(Boolean(detailResult.history_truncated));
      } else if (detailResult.error !== "Aborted") {
        if (!detailRateLimited) {
          setReport(null);
          setError(detailResult.error || "Unable to load report detail.");
          setHistoryNotice(detailResult.history_notice || null);
          setHistoryTruncated(Boolean(detailResult.history_truncated));
        }
      }

      if (actionsResult.success) {
        setActions(actionsResult.actions || []);
      } else if (actionsResult.error !== "Aborted") {
        if (!actionsRateLimited) {
          setActions([]);
          setActionsError(actionsResult.error || "Unable to load actions.");
        }
      }

      if (isRateLimited) {
        setShowRateLimitRetryPrompt(true);
        setError("");
        setActionsError("");
        setHistoryNotice(detailResult.history_notice || null);
        setHistoryTruncated(Boolean(detailResult.history_truncated));
      } else {
        setShowRateLimitRetryPrompt(false);
      }

      setLoading(false);
    };

    void load();
    return () => {
      active = false;
      window.clearTimeout(loadTimeout);
      detailController.abort();
      actionsController.abort();
    };
  }, [reportId, reloadNonce]);

  const sortedActions = useMemo(() => [...actions].sort(compareActions), [actions]);

  const ownerOptions = useMemo(() => {
    const set = new Set<string>();
    for (const action of actions) {
      const owner = (action.owner || "").trim();
      if (owner && owner.toLowerCase() !== "unassigned") set.add(owner);
    }
    for (const row of report?.implementation_roadmap || []) {
      const owner = (row.owner || "").trim();
      if (owner && owner.toLowerCase() !== "unassigned") set.add(owner);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [actions, report?.implementation_roadmap]);

  const overdueCount = useMemo(() => sortedActions.filter((row) => isOverdue(row)).length, [sortedActions]);
  const unassignedCount = useMemo(() => sortedActions.filter((row) => isUnassigned(row)).length, [sortedActions]);

  const escalation = useMemo(() => {
    if (overdueCount > 0 && unassignedCount > 0) return { on: true, reason: "Overdue actions and unassigned owners." };
    if (overdueCount > 0) return { on: true, reason: "Overdue actions." };
    if (unassignedCount > 0) return { on: true, reason: "Unassigned owners." };
    return { on: false, reason: "" };
  }, [overdueCount, unassignedCount]);

  const keySignals = useMemo(() => {
    if (!report) return [] as Array<{ label: string; value: string }>;
    const values: Array<{ label: string; value: string }> = [
      { label: "Satisfaction", value: `${report.avg_rating.toFixed(2)} / 5` },
      { label: "Reviews in brief", value: `${report.total_reviews || 0}` },
    ];
    if (report.themes.length > 0) {
      values.push({ label: "Primary risk theme", value: `${report.themes[0].name} (${report.themes[0].mentions})` });
    } else if (report.top_complaints.length > 0) {
      values.push({ label: "Top client concern", value: report.top_complaints[0] });
    }
    return values.slice(0, 3);
  }, [report]);

  const trendRows = useMemo(() => {
    const trendMap = report?.theme_trends || {};
    return Object.entries(trendMap)
      .map(([theme, value]) => ({
        theme,
        current: Number(value?.current || 0),
        previous: Number(value?.previous || 0),
        change: Number(value?.change || 0),
        percent: Number(value?.percent || 0),
      }))
      .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
      .slice(0, 8);
  }, [report?.theme_trends]);

  const emailSummaryFields = useMemo(() => {
    const averageRating = `${report?.avg_rating?.toFixed(2) || "0.00"} / 5`;
    const topIssue = report?.themes?.[0]
      ? `${report.themes[0].name} (${report.themes[0].mentions})`
      : report?.top_complaints?.[0] || "No top issue identified yet";
    const exampleQuote =
      report?.top_complaints?.[0] ||
      report?.top_praise?.[0] ||
      "No client quote available yet.";
    const recommendedDiscussion =
      report?.recommended_changes?.[0]?.recommendation ||
      "Review current client issues and confirm assigned action ownership.";
    return { averageRating, topIssue, exampleQuote, recommendedDiscussion };
  }, [report]);

  const emailHtmlSummary = useMemo(() => {
    if (!report) return "";
    const generatedAt = formatDateTime(report.created_at);
    const title = escapeHtml(report.name || report.title || "Governance Brief");
    const avg = escapeHtml(emailSummaryFields.averageRating);
    const issue = escapeHtml(emailSummaryFields.topIssue);
    const quote = escapeHtml(emailSummaryFields.exampleQuote);
    const discussion = escapeHtml(emailSummaryFields.recommendedDiscussion);
    return `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Partner Brief Summary</title>
  </head>
  <body style="margin:0;padding:24px;background:#f3f5f9;font-family:Segoe UI,Arial,sans-serif;color:#0D1B2A;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden;">
      <tr>
        <td style="padding:18px 20px;background:#0F2D57;color:#ffffff;">
          <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.9;">Clarion</div>
          <div style="margin-top:8px;font-size:20px;font-weight:700;">Partner Brief Summary</div>
          <div style="margin-top:6px;font-size:12px;opacity:.9;">${title} &bull; ${escapeHtml(generatedAt)}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:18px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Average Rating</div>
          <div style="margin-top:4px;font-size:16px;font-weight:600;color:#0D1B2A;">${avg}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:0 20px 16px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Top Issue</div>
          <div style="margin-top:4px;font-size:16px;font-weight:600;color:#0D1B2A;">${issue}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:0 20px 16px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Example Client Quote</div>
          <div style="margin-top:6px;padding:10px;border-left:3px solid #EF4444;background:#F8FAFC;color:#0D1B2A;font-size:14px;line-height:1.45;">"${quote}"</div>
        </td>
      </tr>
      <tr>
        <td style="padding:0 20px 20px 20px;">
          <div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Recommended Partner Discussion</div>
          <div style="margin-top:6px;padding:10px;border-left:3px solid #0EA5C2;background:#F8FAFC;color:#0D1B2A;font-size:14px;line-height:1.45;">${discussion}</div>
        </td>
      </tr>
    </table>
  </body>
</html>`;
  }, [emailSummaryFields.averageRating, emailSummaryFields.exampleQuote, emailSummaryFields.recommendedDiscussion, emailSummaryFields.topIssue, report]);

  const openCreateAction = () => {
    setEditingActionId(null);
    setActionFormError("");
    setActionFormMode("create");
  };

  const handleSendPartnerBrief = async () => {
    if (isSendingBrief) return;
    if (!briefDeliveryStatus?.delivery_available) {
      toast.error("Partner brief delivery is not configured for this deployment. No email was sent.");
      return;
    }
    setIsSendingBrief(true);
    const result = await sendPartnerBriefEmail(emailHtmlSummary);
    if (result.success) {
      setEmailPreviewOpen(false);
      toast.success(
        result.recipient_count && result.recipient_count > 0
          ? `Partner brief delivered to ${result.recipient_count} configured recipient${result.recipient_count === 1 ? "" : "s"}.`
          : "Partner brief delivered.",
      );
    } else {
      toast.error(result.error || "Partner brief was not delivered.");
    }
    setIsSendingBrief(false);
  };

  useEffect(() => {
    if (!emailPreviewOpen) return;
    let active = true;
    const loadDeliveryStatus = async () => {
      setBriefDeliveryStatusLoading(true);
      const result = await getPartnerBriefDeliveryStatus();
      if (!active) return;
      if (result.success && result.status) {
        setBriefDeliveryStatus(result.status);
      } else {
        setBriefDeliveryStatus(null);
      }
      setBriefDeliveryStatusLoading(false);
    };
    void loadDeliveryStatus();
    return () => {
      active = false;
    };
  }, [emailPreviewOpen]);

  const beginEditAction = (action: ReportActionItem) => {
    setEditingActionId(action.id);
    setActionFormError("");
    setActionFormMode("edit");
  };

  const createFormInitialValues = useMemo<ActionFormValues>(
    () => ({
      title: "",
      owner: "",
      owner_user_id: null,
      due_date: "",
      status: "open",
      timeframe: "Days 1-30",
      kpi: "",
      notes: "",
    }),
    [],
  );

  const createActionPrefill = useMemo<ActionFormValues>(() => {
    const title = (searchParams.get("actionTitle") || "").trim();
    const owner = (searchParams.get("actionOwner") || "").trim();
    const priority = (searchParams.get("actionPriority") || "medium").toLowerCase();
    const due = new Date();
    due.setDate(due.getDate() + (priority === "high" ? 7 : priority === "low" ? 30 : 14));
    const dueDate = due.toISOString().slice(0, 10);
    const timeframe: ActionFormValues["timeframe"] =
      priority === "high" ? "Days 1-30" : priority === "low" ? "Days 61-90" : "Days 31-60";

    return {
      title,
      owner,
      owner_user_id: null,
      due_date: dueDate,
      status: "open",
      timeframe,
      kpi: title ? `Address: ${title}` : "",
      notes: "",
    };
  }, [searchParams]);

  useEffect(() => {
    if (searchParams.get("createAction") !== "1") return;
    setEditingActionId(null);
    setActionFormError("");
    setActionFormMode("create");
  }, [searchParams]);

  const editFormInitialValues = useMemo<ActionFormValues>(() => {
    const target = actions.find((row) => row.id === editingActionId);
    return {
      title: target?.title || "",
      owner: target?.owner || "",
      owner_user_id: target?.owner_user_id ?? null,
      due_date: target?.due_date || "",
      status: normalizeStatus(target?.status),
      timeframe: (target?.timeframe as ActionFormValues["timeframe"]) || "Days 1-30",
      kpi: target?.kpi || "",
      notes: target?.notes || "",
    };
  }, [actions, editingActionId]);

  const handleActionFormSubmit = async (values: ActionFormValues) => {
    if (!reportId || Number.isNaN(reportId) || !actionFormMode) return;
    setActionFormSubmitting(true);
    setActionFormError("");

    if (actionFormMode === "create") {
      const result = await createReportAction(
        reportId,
        {
          title: values.title,
          owner: values.owner,
          owner_user_id: values.owner_user_id,
          status: values.status,
          due_date: values.due_date || null,
          timeframe: values.timeframe,
          kpi: values.kpi,
          notes: values.notes,
        },
        { onRetry: () => setActionFormError("Busy, retrying...") },
      );
      if (result.success && result.action) {
        setActions((prev) => {
          let created = appendActivity(result.action as ReportActionItem, "Action created", result.action?.created_at);
          const createdOwner = (created.owner || "").trim();
          if (createdOwner && createdOwner.toLowerCase() !== "unassigned") {
            created = appendActivity(created, `Assigned to Partner ${createdOwner}`, created.updated_at || created.created_at);
          }
          if (normalizeStatus(created.status) !== "open") {
            created = appendActivity(
              created,
              `Status updated to ${statusLabel(created.status)}`,
              created.updated_at || created.created_at,
            );
          }
          return [created, ...prev];
        });
        setActionFormMode(null);
        toast.success("Action created.");
      } else {
        setActionFormError(result.error || "Unable to create action.");
      }
      setActionFormSubmitting(false);
      return;
    }

    if (!editingActionId) {
      setActionFormSubmitting(false);
      setActionFormError("Unable to identify the action to update.");
      return;
    }
    const result = await updateReportAction(
      reportId,
      editingActionId,
      {
        title: values.title,
        owner: values.owner,
        owner_user_id: values.owner_user_id,
        status: values.status,
        due_date: values.due_date || null,
        timeframe: values.timeframe,
        kpi: values.kpi,
        notes: values.notes,
      },
      { onRetry: () => setActionFormError("Busy, retrying...") },
    );
    if (!result.success) {
      setActionFormError(result.error || "Unable to save action updates.");
      setActionFormSubmitting(false);
      return;
    }

    const nextAction = result.action
      ? (result.action as ReportActionItem)
      : ({
          id: editingActionId,
          title: values.title,
          owner: values.owner,
          owner_user_id: values.owner_user_id,
          status: values.status,
          due_date: values.due_date || null,
          timeframe: values.timeframe,
          kpi: values.kpi,
          notes: values.notes,
        } as ReportActionItem);

    setActions((prev) =>
      prev.map((row) => {
        if (row.id !== editingActionId) return row;
        let updated = { ...row, ...nextAction };
        const previousOwner = (row.owner || "").trim().toLowerCase();
        const nextOwner = (updated.owner || "").trim();
        if ((nextOwner || "").toLowerCase() !== previousOwner && nextOwner) {
          updated = appendActivity(updated, `Assigned to Partner ${nextOwner}`, updated.updated_at || nextAction.updated_at);
        }
        if (normalizeStatus(row.status) !== normalizeStatus(updated.status)) {
          updated = appendActivity(
            updated,
            `Status updated to ${statusLabel(updated.status)}`,
            updated.updated_at || nextAction.updated_at,
          );
        }
        return updated;
      }),
    );
    setActionFormSubmitting(false);
    setActionFormMode(null);
    setEditingActionId(null);
    toast.success("Action updated.");
  };

  const handleRenameSave = async () => {
    if (!reportId || Number.isNaN(reportId) || !report) return;
    const nextName = renameDraft.trim();
    if (!nextName) {
      setRenameError("Report title is required.");
      setRenameMode("error");
      return;
    }
    setRenameMode("saving");
    setRenameError("");
    const result = await updateReportName(reportId, nextName);
    if (!result.success) {
      setRenameError(result.error || "Unable to rename report.");
      setRenameMode("error");
      setRenameDraft(report.name || report.title || "");
      return;
    }
    setReport((prev) => (prev ? { ...prev, name: nextName } : prev));
    setRenameMode("saved");
    setTimeout(() => setRenameMode("idle"), 1500);
  };

  const openBrief = async () => {
    if (!report?.download_pdf_url) {
      toast.error("Brief preview is unavailable for this report.");
      return;
    }
    const sep = report.download_pdf_url.includes("?") ? "&" : "?";
    const url = `${report.download_pdf_url}${sep}v=${Date.now()}`;
    try {
      const response = await fetch(url, { credentials: "include" });
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as { error?: string; message?: string };
        if (payload.error === "Report outside plan history window") {
          toast.error(
            "This report is outside your plan’s historical intelligence window. Upgrade your plan to access older governance history.",
          );
          return;
        }
        if (!response.ok) {
          toast.error(payload.message || payload.error || "Unable to open governance brief.");
          return;
        }
      }
      if (!response.ok) {
        toast.error("Unable to open governance brief.");
        return;
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch {
      toast.error("Unable to open governance brief.");
    }
  };

  if (loading) {
    return (
      <section className="gov-page">
          <div className="gov-level-2 p-6">
            <p className="text-sm text-neutral-700">Loading governance brief...</p>
            {isBusyRetrying && (
              <p className="mt-2 text-sm text-neutral-700">
                Busy right now. Retrying… (attempt {retryAttempt}/{3})
              </p>
            )}
          </div>
        </section>
    );
  }

  if (!report && showRateLimitRetryPrompt) {
    return (
      <section className="gov-page">
          <div className="gov-level-2 p-6">
            <h1 className="gov-h1">Governance Brief</h1>
            <p className="mt-2 text-sm text-neutral-700">
              Busy right now. Please retry loading this brief.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="gov-btn-secondary"
                onClick={() => {
                  if (loading) return;
                  setLoading(true);
                  setReloadNonce((value) => value + 1);
                }}
              >
                Retry
              </button>
              <button
                type="button"
                className="gov-btn-quiet"
                onClick={() => {
                  setShowRateLimitRetryPrompt(false);
                  setError("Report load was stopped.");
                }}
              >
                Stop
              </button>
              <button type="button" className="gov-btn-secondary" onClick={() => navigate("/dashboard/reports")}>
                Back to Briefs
              </button>
            </div>
          </div>
        </section>
    );
  }

  if (error || !report) {
    const isHistoryWindowError = error === "Report outside plan history window";
    return (
      <section className="gov-page">
          <div className="gov-level-2 p-6">
            <h1 className="gov-h1">Report unavailable</h1>
            <p className="mt-2 text-sm text-neutral-700">{error || "This report could not be loaded."}</p>
            {isHistoryWindowError ? (
              <div className="mt-3 rounded-md border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-sm text-[#1E3A8A]">
                {historyNotice ||
                  "Your current plan limits historical intelligence access. Upgrade to unlock older governance reports."}
              </div>
            ) : null}
            {showRateLimitRetryPrompt && (
              <div className="mt-3 rounded border border-neutral-300 bg-neutral-50 p-3 text-sm text-neutral-800">
                Busy right now. Please retry loading this brief.
              </div>
            )}
            {isBusyRetrying && (
              <div className="mt-3 rounded border border-neutral-300 bg-neutral-50 p-3 text-sm text-neutral-700">
                Busy, retrying...
              </div>
            )}
            <button type="button" className="gov-btn-secondary mt-4" onClick={() => navigate("/dashboard/reports")}>
              Back to Briefs
            </button>
            {showRateLimitRetryPrompt && (
              <button
                type="button"
                className="gov-btn-secondary mt-2"
                onClick={() => {
                  if (loading) return;
                  setLoading(true);
                  setReloadNonce((value) => value + 1);
                }}
              >
                Retry
              </button>
            )}
            {isHistoryWindowError ? (
              <button
                type="button"
                className="gov-btn-secondary mt-2"
                onClick={() => navigate("/pricing")}
              >
                View plan options
              </button>
            ) : null}
          </div>
        </section>
    );
  }

  return (
    <section className="gov-page space-y-4">
        <section className="gov-level-2 p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-[280px] flex-1">
              <p className="gov-micro-label">Governance Brief</p>
              <div className="mt-1 flex flex-wrap items-center gap-2">
                {renameMode === "editing" || renameMode === "saving" || renameMode === "error" ? (
                  <>
                    <input
                      data-testid="report-rename-input"
                      value={renameDraft}
                      onChange={(event) => setRenameDraft(event.target.value)}
                      className="gov-field h-10 min-w-[280px] text-base"
                      disabled={renameMode === "saving"}
                    />
                    <button
                      data-testid="report-rename-save"
                      type="button"
                      className="gov-btn-secondary h-10 px-3"
                      disabled={renameMode === "saving"}
                      onClick={() => void handleRenameSave()}
                    >
                      {renameMode === "saving" ? (
                        <span className="inline-flex items-center gap-1"><Loader2 size={14} className="animate-spin" /> Saving</span>
                      ) : (
                        "Save"
                      )}
                    </button>
                    <button
                      type="button"
                      className="gov-btn-ghost h-10 px-3"
                      disabled={renameMode === "saving"}
                      onClick={() => {
                        setRenameMode("idle");
                        setRenameDraft(report.name || report.title || "");
                        setRenameError("");
                      }}
                      aria-label="Cancel rename"
                    >
                      <X size={14} />
                    </button>
                  </>
                ) : (
                  <>
                    <h1 className="gov-h1" data-testid="report-title">{report.name || report.title}</h1>
                    <button type="button" className="gov-btn-ghost h-8 px-2" onClick={() => setRenameMode("editing")}>
                      <PencilLine size={14} />
                      <span className="ml-1 text-xs">Rename</span>
                    </button>
                  </>
                )}
              </div>
              <p className="mt-2 text-sm text-neutral-700">Created {formatDateTime(report.created_at)}</p>
              <div className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 px-3 py-2">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-700">{DISPLAY_LABELS.clientIssueSingular}</p>
                <p className="mt-1 text-sm text-neutral-700">
                  A recurring pattern in client feedback that may require leadership attention.
                </p>
                <p className="mt-1 text-xs text-neutral-600">
                  Examples include communication breakdowns, billing confusion, or responsiveness issues.
                </p>
              </div>
              {renameMode === "saved" && <p className="mt-1 text-xs text-green-700">Saved.</p>}
              {renameMode === "error" && renameError && <p className="mt-1 text-xs text-red-700">{renameError}</p>}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <button data-testid="report-create-action" type="button" className="gov-btn-primary" onClick={openCreateAction}>
                Create Action
              </button>
              <button
                type="button"
                className="gov-btn-secondary"
                onClick={() => setEmailPreviewOpen(true)}
                disabled={isSendingBrief}
              >
                Email Brief to Partners
              </button>
              <button data-testid="report-view-brief" type="button" className="gov-btn-secondary" onClick={() => void openBrief()}>
                {report.plan_type === "free"
                  ? "Preview Governance Brief (Watermarked)"
                  : "Download Governance Brief PDF"}
              </button>
              <Link to={`/dashboard/brief-customization?reportId=${report.id}`} className="gov-btn-secondary">
                Prepare Brief & Preview PDF
              </Link>
            </div>
          </div>
          <p className="mt-3 text-xs text-neutral-600">
            Apply your firm logo and accent theme before print or download.
          </p>
          {isBusyRetrying && (
            <div className="mt-3 rounded border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
              Busy right now. Retrying… (attempt {retryAttempt}/{3})
            </div>
          )}
          {showRateLimitRetryPrompt && (
            <div className="mt-3 flex flex-wrap items-center gap-2 rounded border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-800">
              <span>Busy right now. Please retry loading this brief.</span>
              <button
                type="button"
                className="gov-btn-secondary h-8 px-3 py-0 text-xs"
                onClick={() => {
                  if (loading) return;
                  setLoading(true);
                  setReloadNonce((value) => value + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          {historyTruncated && historyNotice ? (
            <div className="mt-3 rounded-md border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-sm text-[#1E3A8A]">
              {historyNotice}
            </div>
          ) : null}
        </section>

        <section className="grid gap-4 lg:grid-cols-2">
          <article className="gov-level-2 p-5">
            <h2 className="gov-h2">Key Client Issues</h2>
            {keySignals.length === 0 ? (
              <p className="mt-2 text-sm text-neutral-700">No key client issues yet.</p>
            ) : (
              <ul className="mt-3 space-y-2">
                {keySignals.map((signal) => (
                  <li key={signal.label} className="gov-level-2-soft px-3 py-2">
                    <p className="gov-micro-label">{signal.label}</p>
                    <p className="mt-1 text-sm text-neutral-900">{signal.value}</p>
                  </li>
                ))}
              </ul>
            )}
          </article>

          {escalation.on && (
            <article className="gov-level-2 border-red-200 p-5">
              <h2 className="gov-h2 text-neutral-900">Escalation required</h2>
              <p className="mt-2 text-sm text-neutral-800">{escalation.reason}</p>
              <div className="mt-3 flex flex-wrap gap-2 text-xs text-neutral-700">
                {overdueCount > 0 && <span className="gov-badge gov-badge-critical">{overdueCount} overdue</span>}
                {unassignedCount > 0 && <span className="gov-badge gov-badge-watch">{unassignedCount} unassigned</span>}
              </div>
            </article>
          )}
        </section>

        <section className="gov-level-2 p-5">
          <h2 className="gov-h2">Trend Since Last Report</h2>
          {trendRows.length === 0 ? (
            <p className="mt-2 text-sm text-neutral-700">No previous report available for trend comparison yet.</p>
          ) : (
            <ul className="mt-3 space-y-2">
              {trendRows.map((row) => {
                const trendLabel = row.change > 0 ? "Increase" : row.change < 0 ? "Decrease" : "No change";
                const tone =
                  row.change > 0 ? "text-red-700" : row.change < 0 ? "text-emerald-700" : "text-neutral-700";
                return (
                  <li key={`trend-${row.theme}`} className="gov-level-2-soft px-3 py-2">
                    <p className="text-sm text-neutral-900">
                      {row.theme} <span className={tone}>{trendLabel} {Math.abs(row.percent)}%</span> since last report
                    </p>
                    <p className="mt-1 text-xs text-neutral-600">
                      Current: {row.current} · Previous: {row.previous} · Change: {row.change > 0 ? "+" : ""}
                      {row.change}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </section>

        <section className="gov-level-2 p-5">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="gov-h2">Actions</h2>
              <p className="mt-1 text-sm text-neutral-700">Assign and track execution with canonical governance fields.</p>
            </div>
            <p className="text-xs text-neutral-600">{sortedActions.length} total</p>
          </div>

          <ActionForm
            open={actionFormMode === "create"}
            mode="create"
            initialValues={searchParams.get("createAction") === "1" ? createActionPrefill : createFormInitialValues}
            ownerOptions={ownerOptions}
            submitting={actionFormSubmitting}
            serverError={actionFormError}
            onCancel={() => {
              setActionFormMode(null);
              setActionFormError("");
            }}
            onSubmit={handleActionFormSubmit}
          />

          {actionsError && <p className="mt-3 text-xs text-red-700">{actionsError}</p>}
          <div className="mt-4" data-testid="report-actions-list">
            {sortedActions.length === 0 ? (
              <div className="gov-level-2-soft px-4 py-4"><p className="text-sm text-neutral-800">No actions have been assigned for this brief yet.</p><button type="button" className="gov-btn-secondary mt-3" onClick={openCreateAction}>Create first action</button></div>
            ) : (
              <div className="space-y-3">
                {sortedActions.map((action) => {
                  return (
                    <article key={action.id} className="gov-level-2-soft p-4">
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div className="min-w-[260px] flex-1">
                          <p className="text-sm font-semibold text-neutral-900">{action.title}</p>
                          <p className="mt-1 text-xs text-neutral-700">
                            Owner: {(action.owner || "Unassigned").trim() || "Unassigned"} | Due: {formatDate(action.due_date)} | Timeframe:{" "}
                            {action.timeframe || "-"}
                          </p>
                          <p className="mt-1 text-xs text-neutral-700">Success measure: {action.kpi || "-"}</p>
                          {action.notes && <p className="mt-1 text-xs text-neutral-700">Notes: {action.notes}</p>}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className={statusBadgeClass(action.status)}>{statusLabel(action.status)}</span>
                          {isOverdue(action) && <span className="gov-badge gov-badge-critical">Overdue</span>}
                          {!isOverdue(action) && isDueSoon(action) && <span className="gov-badge gov-badge-watch">Due soon</span>}
                          {isUnassigned(action) && <span className="gov-badge gov-badge-watch">Unassigned</span>}
                          <button type="button" className="gov-btn-ghost h-8 px-2" onClick={() => beginEditAction(action)}>
                            Edit
                          </button>
                        </div>
                      </div>
                      <ActionForm
                        open={actionFormMode === "edit" && editingActionId === action.id}
                        mode="edit"
                        initialValues={editFormInitialValues}
                        ownerOptions={ownerOptions}
                        submitting={actionFormSubmitting}
                        submitLabel="Save"
                        serverError={actionFormError}
                        onCancel={() => {
                          setActionFormMode(null);
                          setEditingActionId(null);
                          setActionFormError("");
                        }}
                        onSubmit={handleActionFormSubmit}
                      />
                    </article>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        <section className="gov-level-2 p-5">
          <button type="button" className="flex w-full items-center justify-between text-left" onClick={() => setDetailsOpen((prev) => !prev)} aria-expanded={detailsOpen}>
            <div><p className="gov-h2">Evidence / Details</p><p className="mt-1 text-xs text-neutral-700">Expanded context for briefing and traceability.</p></div>
            {detailsOpen ? <ChevronDown size={16} className="text-neutral-600" /> : <ChevronRight size={16} className="text-neutral-600" />}
          </button>
          {detailsOpen && (
            <div className="mt-4 space-y-4">
              {[
                { title: "Executive Summary", items: report.executive_summary || [], display: "list" as const },
                { title: "Top Complaints", items: report.top_complaints || [], display: "quotes" as const, sentiment: "complaint" as const },
                { title: "Top Praise", items: report.top_praise || [], display: "quotes" as const, sentiment: "praise" as const },
                {
                  title: "Recommended Changes",
                  items: (report.recommended_changes || []).map((item) => `${item.theme}: ${item.recommendation}`),
                  display: "list" as const,
                },
              ].map((section) => (
                <article key={section.title} className="gov-level-2-soft p-4">
                  <p className="gov-micro-label">{section.title}</p>
                  {section.items.length === 0 ? (
                    <p className="mt-2 text-sm text-neutral-700">No records available.</p>
                  ) : section.display === "quotes" ? (
                    <div className="mt-3 space-y-3">
                      {section.items.map((item, index) => (
                        <ClientQuoteCard
                          key={`${section.title}-${index}`}
                          quote={item}
                          issue={section.title === "Top Complaints" ? "Top Client Concern" : "Client Experience Strength"}
                          sentiment={section.sentiment}
                          meta="Anonymized client feedback excerpt"
                        />
                      ))}
                    </div>
                  ) : (
                    <ul className="mt-2 space-y-1">
                      {section.items.map((item, index) => (
                        <li key={`${section.title}-${index}`} className="text-sm text-neutral-800">
                          {item}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}
        </section>

        <div className="flex justify-end"><Link to="/dashboard/reports" className="gov-btn-secondary">Back to Briefs</Link></div>
        <EmailBriefPreviewModal
          open={emailPreviewOpen}
          onOpenChange={setEmailPreviewOpen}
          averageRating={emailSummaryFields.averageRating}
          topIssue={emailSummaryFields.topIssue}
          exampleQuote={emailSummaryFields.exampleQuote}
          recommendedDiscussion={emailSummaryFields.recommendedDiscussion}
          htmlSummary={emailHtmlSummary}
          onSend={() => void handleSendPartnerBrief()}
          isSending={isSendingBrief}
          deliveryStatus={briefDeliveryStatus}
          deliveryStatusLoading={briefDeliveryStatusLoading}
        />
      </section>
  );
};

export default ReportDetail;


