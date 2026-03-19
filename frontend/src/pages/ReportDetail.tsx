
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Maximize2,
  PencilLine,
  Printer,
  X,
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Lightbulb,
  Zap,
} from "lucide-react";
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
import BriefPresentMode from "@/components/governance/BriefPresentMode";
import GovStatusChip, {
  resolveChipVariantForActionStatus,
} from "@/components/governance/GovStatusChip";
import GovernanceCard from "@/components/governance/GovernanceCard";
import { formatApiDate, formatApiDateTime } from "@/lib/dateTime";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

// ─────────────────────────────────────────────────────────────────────────────
// Constants & pure helpers
// ─────────────────────────────────────────────────────────────────────────────

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

const isCompleted = (action: ReportActionItem): boolean =>
  normalizeStatus(action.status) === "done";

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
  return (
    (!ownerText || ownerText.toLowerCase() === "unassigned") &&
    (ownerUserId === null || ownerUserId === undefined)
  );
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
  formatApiDateTime(
    value,
    { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" },
    "-",
  );

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

const formatMonthDay = (value?: string | null): string => {
  if (!value)
    return new Date().toLocaleDateString([], { month: "long", day: "numeric" });
  const parsed = new Date(value);
  if (!Number.isFinite(parsed.getTime()))
    return new Date().toLocaleDateString([], { month: "long", day: "numeric" });
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
    activity_log: [
      ...existing,
      {
        date: formatMonthDay(timestamp || action.updated_at || action.created_at),
        description,
      },
    ],
  };
};

const isRateLimitMessage = (message: string | undefined): boolean => {
  const normalized = (message || "").toLowerCase();
  return (
    normalized.includes("rate limit") ||
    normalized.includes("too many") ||
    normalized.includes("429")
  );
};

// ─────────────────────────────────────────────────────────────────────────────
// Section header — shared between normal and present mode
// ─────────────────────────────────────────────────────────────────────────────

type PacketSectionProps = {
  eyebrow: string;
  title: string;
  presentMode?: boolean;
  children: React.ReactNode;
  className?: string;
};

function PacketSection({ eyebrow, title, presentMode, children, className = "" }: PacketSectionProps) {
  if (presentMode) {
    return (
      <section className={`brief-section ${className}`}>
        <p className="brief-section-eyebrow">{eyebrow}</p>
        <h2 className="brief-section-title">{title}</h2>
        <div className="mt-5">{children}</div>
      </section>
    );
  }
  return (
    <section
      className={[
        "rounded-[12px] border border-[#E5E7EB] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)]",
        className,
      ].join(" ")}
    >
      <p className="gov-type-eyebrow">
        {eyebrow}
      </p>
      <h2 className="mt-1 text-[17px] font-semibold text-[#0D1B2A]">{title}</h2>
      <div className="mt-5">{children}</div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page component
// ─────────────────────────────────────────────────────────────────────────────

const ReportDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const reportId = Number(id);

  // ── Present mode — driven by ?present=1 or internal state ─────────────────
  const [presentMode, setPresentMode] = useState(() => searchParams.get("present") === "1");

  const enterPresent = useCallback(() => {
    setPresentMode(true);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.set("present", "1");
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  const exitPresent = useCallback(() => {
    setPresentMode(false);
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("present");
      return next;
    }, { replace: true });
  }, [setSearchParams]);

  // ── Data loading state ─────────────────────────────────────────────────────
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

  const [renameMode, setRenameMode] = useState<
    "idle" | "editing" | "saving" | "saved" | "error"
  >("idle");
  const [renameDraft, setRenameDraft] = useState("");
  const [renameError, setRenameError] = useState("");

  const [actionFormMode, setActionFormMode] = useState<"create" | "edit" | null>(null);
  const [actionFormSubmitting, setActionFormSubmitting] = useState(false);
  const [actionFormError, setActionFormError] = useState("");
  const [editingActionId, setEditingActionId] = useState<number | null>(null);
  const [isSendingBrief, setIsSendingBrief] = useState(false);
  const [emailPreviewOpen, setEmailPreviewOpen] = useState(false);
  const [briefDeliveryStatus, setBriefDeliveryStatus] =
    useState<PartnerBriefDeliveryStatus | null>(null);
  const [briefDeliveryStatusLoading, setBriefDeliveryStatusLoading] = useState(false);

  const [evidenceOpen, setEvidenceOpen] = useState(false);

  // ── Data load ──────────────────────────────────────────────────────────────
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

      const detailRateLimited =
        !detailResult.success && isRateLimitMessage(detailResult.error);
      const actionsRateLimited =
        !actionsResult.success && isRateLimitMessage(actionsResult.error);
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

  // ── Derived data ──────────────────────────────────────────────────────────
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

  const overdueCount = useMemo(
    () => sortedActions.filter((row) => isOverdue(row)).length,
    [sortedActions],
  );
  const unassignedCount = useMemo(
    () => sortedActions.filter((row) => isUnassigned(row)).length,
    [sortedActions],
  );
  const completedCount = useMemo(
    () => sortedActions.filter((row) => isCompleted(row)).length,
    [sortedActions],
  );
  const activeActionCount = useMemo(
    () => sortedActions.filter((row) => !isCompleted(row)).length,
    [sortedActions],
  );

  const escalation = useMemo(() => {
    if (overdueCount > 0 && unassignedCount > 0)
      return { on: true, reason: "Overdue actions and unassigned owners." };
    if (overdueCount > 0) return { on: true, reason: "Overdue actions." };
    if (unassignedCount > 0) return { on: true, reason: "Unassigned owners." };
    return { on: false, reason: "" };
  }, [overdueCount, unassignedCount]);

  // Key signals — a curated 3-item summary for the "Signals this period" section
  const keySignals = useMemo(() => {
    if (!report) return [] as Array<{ label: string; value: string }>;
    const values: Array<{ label: string; value: string }> = [
      { label: "Satisfaction", value: `${report.avg_rating.toFixed(2)} / 5` },
      { label: "Reviews in brief", value: `${report.total_reviews || 0}` },
    ];
    if (report.themes.length > 0) {
      values.push({
        label: "Primary risk theme",
        value: `${report.themes[0].name} (${report.themes[0].mentions})`,
      });
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

  // "Decisions / Next steps" — derived from recommended changes
  const nextSteps = useMemo(() => {
    return (report?.recommended_changes || []).map((item) => ({
      theme: item.theme,
      recommendation: item.recommendation,
    }));
  }, [report?.recommended_changes]);
  const firstDecision = nextSteps[0] || null;

  const briefingBullets = useMemo(() => {
    if (!report) return [] as string[];
    if (report.executive_summary.length > 0) {
      return report.executive_summary.slice(0, 4);
    }
    const bullets = [
      `${report.name || report.title} is ready for partner review.`,
      `Top focus area: ${report.themes[0]?.name || "No dominant theme yet"}.`,
      `${report.total_reviews || 0} reviews analyzed with an average rating of ${report.avg_rating.toFixed(2)}.`,
    ];
    if (firstDecision?.recommendation) {
      bullets.push(firstDecision.recommendation);
    }
    return bullets;
  }, [firstDecision?.recommendation, report]);

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
    <title>Governance Brief Email</title>
  </head>
  <body style="margin:0;padding:24px;background:#f3f5f9;font-family:Segoe UI,Arial,sans-serif;color:#0D1B2A;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #E5E7EB;border-radius:10px;overflow:hidden;">
      <tr>
        <td style="padding:18px 20px;background:#0F2D57;color:#ffffff;">
          <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;opacity:.9;">Clarion</div>
          <div style="margin-top:8px;font-size:20px;font-weight:700;">Governance Brief Email</div>
          <div style="margin-top:6px;font-size:12px;opacity:.9;">${title} &bull; ${escapeHtml(generatedAt)}</div>
        </td>
      </tr>
      <tr><td style="padding:18px 20px;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Leadership Briefing</div><div style="margin-top:4px;font-size:16px;font-weight:600;color:#0D1B2A;">${avg}</div></td></tr>
      <tr><td style="padding:0 20px 16px 20px;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Signals That Matter Most</div><div style="margin-top:4px;font-size:16px;font-weight:600;color:#0D1B2A;">${issue}</div></td></tr>
      <tr><td style="padding:0 20px 16px 20px;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Decisions &amp; Next Steps</div><div style="margin-top:6px;padding:10px;border-left:3px solid #0EA5C2;background:#F8FAFC;color:#0D1B2A;font-size:14px;line-height:1.45;">${discussion}</div></td></tr>
      <tr><td style="padding:0 20px 20px 20px;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:#6B7280;">Supporting Client Evidence</div><div style="margin-top:6px;padding:10px;border-left:3px solid #EF4444;background:#F8FAFC;color:#0D1B2A;font-size:14px;line-height:1.45;">"${quote}"</div></td></tr>
    </table>
  </body>
</html>`;
  }, [
    emailSummaryFields.averageRating,
    emailSummaryFields.exampleQuote,
    emailSummaryFields.recommendedDiscussion,
    emailSummaryFields.topIssue,
    report,
  ]);

  // ── Action handlers ────────────────────────────────────────────────────────
  const openCreateAction = () => {
    setEditingActionId(null);
    setActionFormError("");
    setActionFormMode("create");
  };

  const handleSendPartnerBrief = async () => {
    if (isSendingBrief) return;
    if (!briefDeliveryStatus?.delivery_available) {
      toast.error(
        "Partner brief delivery is not configured for this deployment. No email was sent.",
      );
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
    return () => { active = false; };
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
          let created = appendActivity(
            result.action as ReportActionItem,
            "Action created",
            result.action?.created_at,
          );
          const createdOwner = (created.owner || "").trim();
          if (createdOwner && createdOwner.toLowerCase() !== "unassigned") {
            created = appendActivity(
              created,
              `Assigned to Partner ${createdOwner}`,
              created.updated_at || created.created_at,
            );
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
          updated = appendActivity(
            updated,
            `Assigned to Partner ${nextOwner}`,
            updated.updated_at || nextAction.updated_at,
          );
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
        const payload = (await response.json()) as {
          error?: string;
          message?: string;
        };
        if (payload.error === "Report outside plan history window") {
          toast.error(
            "This report is outside your plan's historical intelligence window. Upgrade your plan to access older governance history.",
          );
          return;
        }
        if (!response.ok) {
          toast.error(
            payload.message || payload.error || "Unable to open governance brief.",
          );
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

  // ── Loading / error shells ─────────────────────────────────────────────────
  if (loading) {
    return (
      <section className="gov-page">
        <div className="gov-level-2 p-6">
          <p className="text-sm text-neutral-700">Loading governance brief…</p>
          {isBusyRetrying && (
            <p className="mt-2 text-sm text-neutral-700">
              Busy right now. Retrying… (attempt {retryAttempt}/3)
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
                setReloadNonce((v) => v + 1);
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
            <button
              type="button"
              className="gov-btn-secondary"
              onClick={() => navigate("/dashboard/reports")}
            >
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
          <p className="mt-2 text-sm text-neutral-700">
            {error || "This report could not be loaded."}
          </p>
          {isHistoryWindowError ? (
            <div className="mt-3 rounded-md border border-[#BFDBFE] bg-[#EFF6FF] px-3 py-2 text-sm text-[#1E3A8A]">
              {historyNotice ||
                "Your current plan limits historical intelligence access. Upgrade to unlock older governance reports."}
            </div>
          ) : null}
          {showRateLimitRetryPrompt && (
            <div className="mt-3 rounded border border-neutral-300 bg-neutral-50 p-3 text-sm text-neutral-800">
              Busy right now. Please retry.
            </div>
          )}
          <button
            type="button"
            className="gov-btn-secondary mt-4"
            onClick={() => navigate("/dashboard/reports")}
          >
            Back to Briefs
          </button>
          {showRateLimitRetryPrompt && (
            <button
              type="button"
              className="gov-btn-secondary mt-2"
              onClick={() => {
                if (loading) return;
                setLoading(true);
                setReloadNonce((v) => v + 1);
              }}
            >
              Retry
            </button>
          )}
          {isHistoryWindowError && (
            <button
              type="button"
              className="gov-btn-secondary mt-2"
              onClick={() => navigate("/pricing")}
            >
              View plan options
            </button>
          )}
        </div>
      </section>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Packet sections — rendered both in normal mode and present mode
  // ─────────────────────────────────────────────────────────────────────────

  /** Section 1: Leadership briefing */
  const leadershipSection = (
    <PacketSection
      eyebrow="Section 1"
      title="Leadership Briefing"
      presentMode={presentMode}
    >
      <div className="grid gap-3 lg:grid-cols-3">
        <GovernanceCard
          title="Current cycle"
          accent={escalation.on ? "warn" : "success"}
          chip={
            <GovStatusChip
              label={escalation.on ? "Needs review" : "Ready for review"}
              variant={escalation.on ? "warn" : "success"}
              size="sm"
            />
          }
          summary={`Generated ${formatDateTime(report.created_at)} and ready for partner review.`}
        />
        <GovernanceCard
          title="Top signal"
          accent={report.themes.length > 0 ? "warn" : "neutral"}
          chip={
            report.themes.length > 0 ? (
              <GovStatusChip
                label={`${report.themes[0].mentions} mention${report.themes[0].mentions === 1 ? "" : "s"}`}
                variant="warn"
                size="sm"
              />
            ) : undefined
          }
          summary={
            report.themes[0]
              ? `${report.themes[0].name} is the strongest issue theme this cycle.`
              : report.top_complaints[0] || "No dominant signal is available yet."
          }
        />
        <GovernanceCard
          title="Follow-through"
          accent={escalation.on ? "risk" : activeActionCount > 0 ? "warn" : "success"}
          chip={
            <GovStatusChip
              label={escalation.on ? "Escalate" : activeActionCount > 0 ? "In motion" : "Clear"}
              variant={escalation.on ? "risk" : activeActionCount > 0 ? "warn" : "success"}
              size="sm"
            />
          }
          summary={`${activeActionCount} active, ${overdueCount} overdue, ${unassignedCount} unassigned, ${completedCount} completed.`}
        />
      </div>

      {firstDecision ? (
        <div className="mt-5 rounded-[10px] border border-[#D9E7F5] bg-[#F5F9FC] px-5 py-4">
          <p className="gov-type-eyebrow">Decision to bring into the meeting</p>
          <p className="mt-2 text-[15px] font-semibold text-[#0D1B2A]">{firstDecision.theme}</p>
          <p className="mt-1 text-[13px] leading-relaxed text-slate-700">
            {firstDecision.recommendation}
          </p>
        </div>
      ) : null}

      {briefingBullets.length > 0 ? (
        <div className="mt-5">
          <p className="mb-2 gov-type-eyebrow">What leadership needs to know now</p>
          <ul className="space-y-1">
            {briefingBullets.map((item, index) => (
              <li key={`briefing-${index}`} className="flex items-start gap-2">
                <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-slate-400" aria-hidden />
                <span className="text-[13px] leading-relaxed text-slate-700">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </PacketSection>
  );

  /** Section 2: Key Signals this period */
  const signalsSection = (
    <PacketSection
      eyebrow="Section 2"
      title="Signals That Matter Most"
      presentMode={presentMode}
    >
      {/* Metric tiles */}
      {keySignals.length > 0 ? (
        <div className="grid gap-3 sm:grid-cols-3">
          {keySignals.map((sig) => (
            <div
              key={sig.label}
              className="rounded-[8px] border border-[#E5E7EB] bg-[#F8FAFC] px-4 py-3"
            >
              <p className="gov-type-eyebrow">
                {sig.label}
              </p>
              <p className="mt-1 text-[17px] font-semibold text-[#0D1B2A]">{sig.value}</p>
            </div>
          ))}
        </div>
      ) : null}

      {/* Theme breakdown */}
      {report.themes.length > 0 ? (
        <div className="mt-5">
          <p className="mb-3 gov-type-eyebrow">
            Issue themes
          </p>
          <div className="space-y-2">
            {report.themes.slice(0, 6).map((theme) => (
              <div
                key={theme.name}
                className="flex items-center justify-between rounded-[6px] border border-[#E5E7EB] bg-white px-4 py-2.5"
              >
                <span className="text-[13px] font-medium text-[#0D1B2A]">{theme.name}</span>
                <span className="flex items-center gap-1.5 text-[12px] text-slate-500">
                  <Zap size={11} className="text-slate-400" aria-hidden />
                  {theme.mentions} mentions
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* Trend comparison */}
      {trendRows.length > 0 ? (
        <div className="mt-5">
          <p className="mb-3 gov-type-eyebrow">
            Trend vs. prior period
          </p>
          <div className="space-y-2">
            {trendRows.map((row) => {
              const trendLabel =
                row.change > 0 ? "↑" : row.change < 0 ? "↓" : "→";
              const tone =
                row.change > 0
                  ? "text-red-600"
                  : row.change < 0
                  ? "text-emerald-600"
                  : "text-slate-500";
              return (
                <div
                  key={`trend-${row.theme}`}
                  className="flex items-center justify-between rounded-[6px] border border-[#E5E7EB] bg-white px-4 py-2.5"
                >
                  <span className="text-[13px] text-[#0D1B2A]">{row.theme}</span>
                  <span className={`text-[12px] font-semibold ${tone}`}>
                    {trendLabel} {Math.abs(row.percent)}%
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-[13px] text-slate-500">
          No prior period available for trend comparison yet.
        </p>
      )}
    </PacketSection>
  );

  /** Section 3: Actions & owners */
  const actionsSection = (
    <PacketSection
      eyebrow="Section 3"
      title="Assigned Follow-Through"
      presentMode={presentMode}
    >
      <div className="mb-4 rounded-[10px] border border-[#E5E7EB] bg-[#F8FAFC] px-4 py-3">
        <p className="gov-type-eyebrow">Follow-through posture</p>
        <p className="mt-1 text-[13px] text-slate-700">
          Confirm ownership, due dates, and any blocked items before this brief goes into the next partner discussion.
        </p>
      </div>

      {/* Escalation callout */}
      {escalation.on ? (
        <div className="mb-4 flex items-start gap-3 rounded-[8px] border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle size={15} className="mt-0.5 shrink-0 text-amber-600" aria-hidden />
          <div>
            <p className="text-[13px] font-semibold text-amber-800">Escalation required</p>
            <p className="text-[12px] text-amber-700">{escalation.reason}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {overdueCount > 0 && (
                <GovStatusChip label={`${overdueCount} overdue`} variant="risk" size="sm" />
              )}
              {unassignedCount > 0 && (
                <GovStatusChip
                  label={`${unassignedCount} unassigned`}
                  variant="warn"
                  size="sm"
                />
              )}
            </div>
          </div>
        </div>
      ) : null}

      {/* Create action form trigger (hidden in present mode) */}
      {!presentMode ? (
        <>
          <ActionForm
            open={actionFormMode === "create"}
            mode="create"
            initialValues={
              searchParams.get("createAction") === "1"
                ? createActionPrefill
                : createFormInitialValues
            }
            ownerOptions={ownerOptions}
            submitting={actionFormSubmitting}
            serverError={actionFormError}
            onCancel={() => {
              setActionFormMode(null);
              setActionFormError("");
            }}
            onSubmit={handleActionFormSubmit}
          />
          {actionsError ? (
            <p className="mb-3 text-[12px] text-red-700">{actionsError}</p>
          ) : null}
        </>
      ) : null}

      {/* Actions list */}
      <div data-testid="report-actions-list" className="space-y-3">
        {sortedActions.length === 0 ? (
          <div className="rounded-[8px] border border-[#E5E7EB] bg-[#F8FAFC] px-5 py-5">
            <p className="text-[13px] text-slate-600">
              No actions have been assigned for this brief yet.
            </p>
            {!presentMode ? (
              <button
                type="button"
                className="gov-btn-secondary mt-3"
                onClick={openCreateAction}
              >
                Create first action
              </button>
            ) : null}
          </div>
        ) : (
          sortedActions.map((action) => (
            <article
              key={action.id}
              className={
                presentMode
                  ? "brief-action-row"
                  : "rounded-[8px] border border-[#E5E7EB] bg-white px-5 py-4"
              }
            >
              <div className="min-w-0 flex-1">
                <p
                  className={
                    presentMode
                      ? "text-[15px] font-semibold text-[#0D1B2A]"
                      : "text-[13px] font-semibold text-[#0D1B2A]"
                  }
                >
                  {action.title}
                </p>
                <p className="mt-1 text-[12px] text-slate-500">
                  Owner: {(action.owner || "Unassigned").trim() || "Unassigned"} ·
                  Due: {formatDate(action.due_date)} ·
                  Timeframe: {action.timeframe || "—"}
                </p>
                {action.kpi ? (
                  <p className="mt-1 text-[12px] text-slate-500">
                    Success measure: {action.kpi}
                  </p>
                ) : null}
                {action.notes && !presentMode ? (
                  <p className="mt-1 text-[12px] text-slate-500">
                    Notes: {action.notes}
                  </p>
                ) : null}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <GovStatusChip
                  label={statusLabel(action.status)}
                  variant={resolveChipVariantForActionStatus(
                    action.status,
                    isOverdue(action),
                  )}
                  size="sm"
                />
                {isOverdue(action) && (
                  <GovStatusChip label="Overdue" variant="risk" size="sm" />
                )}
                {!isOverdue(action) && isDueSoon(action) && (
                  <GovStatusChip label="Due soon" variant="warn" size="sm" />
                )}
                {isUnassigned(action) && (
                  <GovStatusChip label="Unassigned" variant="warn" size="sm" />
                )}
                {!presentMode ? (
                  <button
                    type="button"
                    className="gov-btn-ghost h-7 px-2 text-[11px]"
                    onClick={() => beginEditAction(action)}
                  >
                    Edit
                  </button>
                ) : null}
              </div>
              {!presentMode ? (
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
              ) : null}
            </article>
          ))
        )}
      </div>
    </PacketSection>
  );

  /** Section 5: Supporting client evidence */
  const exposureSection = (
    <PacketSection
      eyebrow="Section 5"
      title="Supporting Client Evidence"
      presentMode={presentMode}
    >
      {report.top_complaints.length === 0 ? (
        <p className="text-[13px] text-slate-500">No supporting client evidence for this period.</p>
      ) : (
        <div className="space-y-4">
          {report.top_complaints.slice(0, 4).map((quote, index) => (
            <ClientQuoteCard
              key={`complaint-${index}`}
              quote={quote}
              issue="Client Concern"
              sentiment="complaint"
              meta="Anonymized client feedback excerpt"
            />
          ))}
        </div>
      )}
      {report.top_praise.length > 0 && !presentMode ? (
        <div className="mt-5">
          <p className="mb-3 gov-type-eyebrow">
            Positive feedback
          </p>
          <div className="space-y-3">
            {report.top_praise.slice(0, 2).map((quote, index) => (
              <ClientQuoteCard
                key={`praise-${index}`}
                quote={quote}
                issue="Client Experience Strength"
                sentiment="praise"
                meta="Anonymized client feedback excerpt"
              />
            ))}
          </div>
        </div>
      ) : null}
    </PacketSection>
  );

  /** Section 4: Decisions made / Next steps */
  const decisionsSection = (
    <PacketSection
      eyebrow="Section 4"
      title="Decisions & Next Steps"
      presentMode={presentMode}
    >
      {nextSteps.length === 0 ? (
        <p className="text-[13px] text-slate-500">
          No recommended next steps for this period.
        </p>
      ) : (
        <div className="space-y-3">
          {nextSteps.map((step, index) => (
            <div
              key={`step-${index}`}
              className={
                presentMode
                  ? "border-l-[3px] border-l-[#0EA5C2] pl-4 py-1"
                  : "rounded-[8px] border border-[#E5E7EB] bg-white px-5 py-4"
              }
            >
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#0EA5C2]">
                {step.theme}
              </p>
              <p
                className={
                  presentMode
                    ? "mt-1 text-[15px] leading-relaxed text-[#0D1B2A]"
                    : "mt-1 text-[13px] leading-relaxed text-[#0D1B2A]"
                }
              >
                {step.recommendation}
              </p>
            </div>
          ))}
        </div>
      )}
    </PacketSection>
  );

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  return (
    <>
      {/* ── Present mode overlay ──────────────────────────────────────────── */}
      <BriefPresentMode active={presentMode} onExit={exitPresent}>
        {/* Present mode header */}
        <header className="brief-section" style={{ borderLeft: "4px solid #0D1B2A" }}>
          <p className="brief-section-eyebrow">Governance Brief</p>
          <h1
            style={{
              fontSize: "26px",
              fontWeight: 700,
              color: "#0D1B2A",
              lineHeight: 1.2,
              margin: 0,
            }}
          >
            {report.name || report.title}
          </h1>
          <p
            style={{
              marginTop: "6px",
              fontSize: "13px",
              color: "#64748B",
            }}
          >
            Generated {formatDateTime(report.created_at)}
          </p>
          <div
            style={{
              marginTop: "16px",
              display: "flex",
              gap: "12px",
              flexWrap: "wrap" as const,
            }}
          >
            <button
              type="button"
              onClick={() => window.print()}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 14px",
                borderRadius: "6px",
                border: "1px solid #CBD5E1",
                background: "white",
                fontSize: "12px",
                fontWeight: 500,
                color: "#0D1B2A",
                cursor: "pointer",
              }}
            >
              <Printer size={13} aria-hidden />
              Print / Export PDF
            </button>
          </div>
        </header>

        {leadershipSection}
        {signalsSection}
        {actionsSection}
        {decisionsSection}
        {exposureSection}
      </BriefPresentMode>

      {/* ── Normal page view ──────────────────────────────────────────────── */}
      <section className="px-8 py-8">
        <div className="mx-auto w-full max-w-[1100px] space-y-6">

          {/* Page header */}
          <header className="flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="workspace-shell-eyebrow">Current governance brief</p>
              {renameMode === "editing" ||
              renameMode === "saving" ||
              renameMode === "error" ? (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <input
                    data-testid="report-rename-input"
                    value={renameDraft}
                    onChange={(e) => setRenameDraft(e.target.value)}
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
                      <span className="inline-flex items-center gap-1">
                        <Loader2 size={14} className="animate-spin" /> Saving
                      </span>
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
                </div>
              ) : (
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <h1
                    className="text-[24px] font-semibold text-[#0D1B2A]"
                    data-testid="report-title"
                  >
                    {report.name || report.title}
                  </h1>
                  <button
                    type="button"
                    className="gov-btn-ghost h-8 px-2"
                    onClick={() => setRenameMode("editing")}
                  >
                    <PencilLine size={13} />
                    <span className="ml-1 text-[11px]">Rename</span>
                  </button>
                </div>
              )}
              <p className="mt-1.5 text-[13px] text-slate-500">
                Generated {formatDateTime(report.created_at)}
              </p>
              <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-slate-600">
                Use this packet for partner review, action decisions, and follow-through updates for the current cycle.
              </p>
              {renameMode === "saved" && (
                <p className="mt-1 text-[11px] text-emerald-700">Saved.</p>
              )}
              {renameMode === "error" && renameError && (
                <p className="mt-1 text-[11px] text-red-700">{renameError}</p>
              )}
            </div>

            {/* Toolbar */}
            <div className="flex flex-wrap items-center gap-2">
              {/* ★ Present mode button */}
              <button
                type="button"
                onClick={enterPresent}
                className="inline-flex items-center gap-1.5 rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-2 text-[12px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
                title="Open presentation mode (also via ?present=1)"
              >
                <Maximize2 size={13} aria-hidden />
                Present
              </button>
              <button
                type="button"
                className="gov-btn-secondary"
                onClick={() => setEmailPreviewOpen(true)}
                disabled={isSendingBrief}
              >
                Send partner brief
              </button>
              <button
                data-testid="report-view-brief"
                type="button"
                className="gov-btn-secondary"
                onClick={() => void openBrief()}
              >
                {report.plan_type === "free"
                  ? "Preview PDF (Watermarked)"
                  : "Download PDF"}
              </button>
              <button
                data-testid="report-create-action"
                type="button"
                className="inline-flex items-center gap-1.5 rounded-[6px] bg-[#0D1B2A] px-3 py-2 text-[12px] font-medium text-white transition-colors hover:bg-[#16263b]"
                onClick={openCreateAction}
              >
                + Add follow-through
              </button>
            </div>
          </header>

          {/* Notices */}
          {isBusyRetrying && (
            <div className="rounded-[8px] border border-neutral-200 bg-neutral-50 px-4 py-3 text-[13px] text-neutral-700">
              Busy right now. Retrying… (attempt {retryAttempt}/3)
            </div>
          )}
          {showRateLimitRetryPrompt && (
            <div className="flex flex-wrap items-center gap-3 rounded-[8px] border border-neutral-200 bg-neutral-50 px-4 py-3 text-[13px] text-neutral-800">
              <span>Busy right now. Please retry loading this brief.</span>
              <button
                type="button"
                className="gov-btn-secondary h-8 px-3 py-0 text-[11px]"
                onClick={() => {
                  if (loading) return;
                  setLoading(true);
                  setReloadNonce((v) => v + 1);
                }}
              >
                Retry
              </button>
            </div>
          )}
          {historyTruncated && historyNotice ? (
            <div className="rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-4 py-3 text-[13px] text-[#1E3A8A]">
              {historyNotice}
            </div>
          ) : null}

          {/* ── Four packet sections ─────────────────────────────────────── */}
          {leadershipSection}
          {signalsSection}
          {actionsSection}
          {decisionsSection}
          {exposureSection}

          {/* ── Evidence accordion (additional context, not in present mode) */}
          <section className="rounded-[12px] border border-[#E5E7EB] bg-white shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
            <button
              type="button"
              className="flex w-full items-center justify-between px-6 py-5 text-left"
              onClick={() => setEvidenceOpen((prev) => !prev)}
              aria-expanded={evidenceOpen}
            >
              <div>
                <p className="gov-type-eyebrow">
                  Supplementary
                </p>
                <p className="mt-0.5 text-[15px] font-semibold text-[#0D1B2A]">
                  Supporting Evidence
                </p>
                <p className="mt-1 text-[12px] text-slate-500">
                  Full traceability context. Not shown in present mode.
                </p>
              </div>
              {evidenceOpen ? (
                <ChevronDown size={16} className="text-slate-500" />
              ) : (
                <ChevronRight size={16} className="text-slate-500" />
              )}
            </button>
            {evidenceOpen && (
              <div className="border-t border-[#E5E7EB] px-6 pb-6 pt-5">
                <div className="space-y-4">
                  {(report.top_praise.length > 0
                    ? [
                        {
                          title: "Top Praise",
                          items: report.top_praise,
                          display: "quotes" as const,
                          sentiment: "praise" as const,
                        },
                      ]
                    : []
                  ).map((section) => (
                    <article key={section.title}>
                      <p className="mb-3 gov-type-eyebrow">
                        {section.title}
                      </p>
                      <div className="space-y-3">
                        {section.items.map((item, index) => (
                          <ClientQuoteCard
                            key={`${section.title}-${index}`}
                            quote={item}
                            issue="Client Experience Strength"
                            sentiment={section.sentiment}
                            meta="Anonymized client feedback excerpt"
                          />
                        ))}
                      </div>
                    </article>
                  ))}
                  {report.recommended_changes.length > 0 ? (
                    <article>
                      <p className="mb-3 gov-type-eyebrow">
                        All recommended changes
                      </p>
                      <ul className="space-y-2">
                        {report.recommended_changes.map((item, index) => (
                          <li
                            key={`rec-${index}`}
                            className="text-[13px] leading-relaxed text-slate-700"
                          >
                            <span className="font-medium text-[#0D1B2A]">{item.theme}:</span>{" "}
                            {item.recommendation}
                          </li>
                        ))}
                      </ul>
                    </article>
                  ) : null}
                </div>
              </div>
            )}
          </section>

          {/* Footer nav */}
          <div className="flex items-center justify-between pt-1">
            <Link to="/dashboard/reports" className="gov-btn-secondary">
              ← Back to Briefs
            </Link>
            <Link
              to={`/dashboard/brief-customization?reportId=${report.id}`}
              className="inline-flex items-center gap-1.5 rounded-[6px] border border-[#D1D5DB] bg-white px-3 py-2 text-[12px] font-medium text-[#0D1B2A] transition-colors hover:bg-slate-50"
            >
              Prepare brief & PDF →
            </Link>
          </div>
        </div>
      </section>

      {/* Email modal */}
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
    </>
  );
};

export default ReportDetail;
