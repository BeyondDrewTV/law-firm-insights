
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, AlertTriangle, Info, Loader2, X, ClipboardList, ShieldAlert } from "lucide-react";
import GovernanceEmptyState from "@/components/governance/GovernanceEmptyState";
import { toast } from "sonner";
import {
  emitPlanLimitError,
  getDashboardStats,
  getGovernanceAlerts,
  getFirmActions,
  getLatestExposure,
  getPartnerBriefDeliveryStatus,
  getRecentGovernanceActions,
  getReportGovernanceSignals,
  getReports,
  sendPartnerBriefEmail,
  type DashboardStats,
  type ExposureSnapshot,
  type GovernanceAlert,
  type GovernanceSignal,
  type RecentGovernanceAction,
  type ReportActionItem,
  type ReportListItem,
} from "@/api/authService";
import FirmGovernanceStatus from "@/components/dashboard/FirmGovernanceStatus";
import SinceLastReview from "@/components/dashboard/SinceLastReview";
import GovernanceGuidance from "@/components/dashboard/GovernanceGuidance";
import RecentGovernanceBriefs from "@/components/dashboard/RecentGovernanceBriefs";
import PlanBadge from "@/components/dashboard/PlanBadge";
import PartnerBriefPanel from "@/components/dashboard/PartnerBriefPanel";
import DashboardSectionDivider from "@/components/dashboard/DashboardSectionDivider";
import DashSectionHeader from "@/components/dashboard/DashSectionHeader";
import GovernanceLoop from "@/components/dashboard/GovernanceLoop";
import OversightBand from "@/components/dashboard/OversightBand";
import GovernanceNarrativeRail from "@/components/dashboard/GovernanceNarrativeRail";
import { DashboardCard } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { resolvePlanLimits } from "@/config/planLimits";
import { DISPLAY_LABELS } from "@/constants/displayLabels";
import type { ReputationIssuePercentages } from "@/utils/reputationScore";

const toTimestamp = (value: string | null | undefined) => {
  if (!value) return 0;
  const ts = Date.parse(value);
  return Number.isFinite(ts) ? ts : 0;
};

const formatDateTime = (value: string | null | undefined) => {
  if (!value) return "Not available";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Not available";
  return date.toLocaleString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const formatDateOnly = (value: string | null | undefined) => {
  if (!value) return "Not available";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "Not available";
  return date.toLocaleDateString([], {
    month: "long",
    day: "numeric",
    year: "numeric",
  });
};

const formatMonthYear = (value: string | null | undefined) => {
  if (!value) return "";
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return "";
  return date.toLocaleDateString([], {
    month: "long",
    year: "numeric",
  });
};

const formatReviewPeriod = (report: ReportListItem | null) => {
  if (!report) return "Not available";
  const start = report.review_date_start ? new Date(report.review_date_start) : null;
  const end = report.review_date_end ? new Date(report.review_date_end) : null;

  const validStart = Boolean(start && Number.isFinite(start.getTime()));
  const validEnd = Boolean(end && Number.isFinite(end.getTime()));

  if (validStart && validEnd && start && end) {
    const sameYear = start.getFullYear() === end.getFullYear();
    const sameMonth = sameYear && start.getMonth() === end.getMonth();
    if (sameMonth) return start.toLocaleDateString([], { month: "long", year: "numeric" });
    if (sameYear) {
      return `${start.toLocaleDateString([], { month: "long" })} - ${end.toLocaleDateString([], {
        month: "long",
        year: "numeric",
      })}`;
    }
    return `${start.toLocaleDateString([], { month: "short", year: "numeric" })} - ${end.toLocaleDateString([], {
      month: "short",
      year: "numeric",
    })}`;
  }

  const cycleMonthYear = formatMonthYear(report.created_at);
  return cycleMonthYear ? `${cycleMonthYear} (current cycle)` : "Not available";
};

const isOverdue = (action: ReportActionItem) => {
  if (!action.due_date || action.status === "done") return false;
  const due = Date.parse(action.due_date);
  if (!Number.isFinite(due)) return false;
  return due < Date.now();
};

const signalCategory = (signal: GovernanceSignal) => {
  const title = (signal.title || "").trim();
  if (!title) return "uncategorized";
  return title.split(":")[0].trim().toLowerCase();
};

const signalLabel = (signal: GovernanceSignal) => {
  const title = (signal.title || "").trim();
  if (!title) return "service quality";
  return title.split(":")[0].trim();
};

const recommendationForSignal = (label: string) => {
  const lower = label.toLowerCase();
  if (lower.includes("communication")) return "Review firm communication response standards.";
  if (lower.includes("billing")) return "Review billing explanation standards and escalation script.";
  if (lower.includes("intake")) return "Review intake callback standards and ownership.";
  if (lower.includes("timeline") || lower.includes("delay")) return "Review case timeline update protocol.";
  return `Review ${label.toLowerCase()} response standards.`;
};

const buildIssuePercentagesFromSignals = (
  signals: GovernanceSignal[],
): ReputationIssuePercentages => {
  if (signals.length === 0) return {};

  const counts = new Map<string, number>();
  signals.forEach((signal) => {
    const label = signalLabel(signal).toLowerCase();
    counts.set(label, (counts.get(label) || 0) + 1);
  });

  const countFor = (matcher: (category: string) => boolean) => {
    let total = 0;
    counts.forEach((count, category) => {
      if (matcher(category)) total += count;
    });
    return total;
  };

  const toPercent = (count: number) => Math.round((count / signals.length) * 100);

  const communication = countFor((category) => category.includes("communication"));
  const professionalism = countFor((category) => category.includes("professionalism"));
  const caseOutcome = countFor(
    (category) =>
      category.includes("case outcome") ||
      category.includes("outcome") ||
      category.includes("result") ||
      category.includes("timeline") ||
      category.includes("delay"),
  );
  const staffSupport = countFor(
    (category) =>
      category.includes("staff support") ||
      category.includes("support staff") ||
      category.includes("staff"),
  );

  const percentages: ReputationIssuePercentages = {};
  if (communication > 0) percentages.communication = toPercent(communication);
  if (professionalism > 0) percentages.professionalism = toPercent(professionalism);
  if (caseOutcome > 0) percentages.caseOutcome = toPercent(caseOutcome);
  if (staffSupport > 0) percentages.staffSupport = toPercent(staffSupport);
  return percentages;
};

const Dashboard = () => {
  const navigate = useNavigate();
  const { currentPlan, user } = useAuth();

  const fetchTeamSeatsUsed = useCallback(async (): Promise<number | null> => {
    try {
      const response = await fetch("/api/team/members", { credentials: "include" });
      const payload = (await response.json()) as {
        success?: boolean;
        members?: Array<{ status?: string }>;
      };
      if (!response.ok || payload.success === false || !Array.isArray(payload.members)) return null;
      return payload.members.filter((member) => member.status === "active" || member.status === "invited").length;
    } catch {
      return null;
    }
  }, []);

  const [loading, setLoading] = useState(true);
  const [exposure, setExposure] = useState<ExposureSnapshot | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [historyNotice, setHistoryNotice] = useState<string | null>(null);
  const [historyTruncated, setHistoryTruncated] = useState(false);
  const [actions, setActions] = useState<ReportActionItem[]>([]);
  const [latestSignals, setLatestSignals] = useState<GovernanceSignal[]>([]);
  const [previousSignals, setPreviousSignals] = useState<GovernanceSignal[]>([]);
  const [alerts, setAlerts] = useState<GovernanceAlert[]>([]);
  const [recentGovernanceActions, setRecentGovernanceActions] = useState<RecentGovernanceAction[]>([]);
  const [teamSeatsUsed, setTeamSeatsUsed] = useState<number | null>(null);
  const [loadError, setLoadError] = useState("");
  const [baselineDismissed, setBaselineDismissed] = useState(false);
  const [partnerMode, setPartnerMode] = useState(false);
  const [isSendingBrief, setIsSendingBrief] = useState(false);

  const baselineDismissKey = useMemo(
    () => `baseline-analysis-dismissed:${user?.firm_id ?? user?.email ?? "unknown"}`,
    [user?.email, user?.firm_id],
  );

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [exposureResult, statsResult, reportsResult, actionsResult, seatsResult, alertsResult, recentActionsResult] = await Promise.all([
        getLatestExposure(),
        getDashboardStats(),
        getReports(100),
        getFirmActions(),
        fetchTeamSeatsUsed(),
        getGovernanceAlerts(),
        getRecentGovernanceActions(),
      ]);

      setExposure(exposureResult.success && exposureResult.exposure ? exposureResult.exposure : null);
      setStats(statsResult.success && statsResult.stats ? statsResult.stats : null);

      const sortedReports = reportsResult.success && reportsResult.reports
        ? [...reportsResult.reports].sort((a, b) => toTimestamp(b.created_at) - toTimestamp(a.created_at))
        : [];

      setReports(sortedReports);
      setHistoryNotice(reportsResult.success ? reportsResult.history_notice || null : null);
      setHistoryTruncated(Boolean(reportsResult.success && reportsResult.history_truncated));
      setActions(actionsResult.success && actionsResult.actions ? actionsResult.actions : []);
      setTeamSeatsUsed(typeof seatsResult === "number" ? seatsResult : null);
      setAlerts(alertsResult.success && alertsResult.alerts ? alertsResult.alerts : []);
      setRecentGovernanceActions(recentActionsResult.success && recentActionsResult.actions ? recentActionsResult.actions : []);

      const readyReports = sortedReports.filter((report) => report.status === "ready");
      const latestReady = readyReports[0];
      const previousReady = readyReports[1];

      if (latestReady?.id) {
        const latestResult = await getReportGovernanceSignals(latestReady.id);
        setLatestSignals(latestResult.success && latestResult.signals ? latestResult.signals : []);
      } else {
        setLatestSignals([]);
      }

      if (previousReady?.id) {
        const previousResult = await getReportGovernanceSignals(previousReady.id);
        setPreviousSignals(previousResult.success && previousResult.signals ? previousResult.signals : []);
      } else {
        setPreviousSignals([]);
      }
    } catch {
      setLoadError("Unable to load executive overview right now.");
      setExposure(null);
      setStats(null);
      setReports([]);
      setHistoryNotice(null);
      setHistoryTruncated(false);
      setActions([]);
      setLatestSignals([]);
      setPreviousSignals([]);
      setAlerts([]);
      setRecentGovernanceActions([]);
      setTeamSeatsUsed(null);
    } finally {
      setLoading(false);
    }
  }, [fetchTeamSeatsUsed]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  useEffect(() => {
    const onUploaded = () => {
      void loadDashboard();
    };
    window.addEventListener("reports:uploaded", onUploaded as EventListener);
    return () => {
      window.removeEventListener("reports:uploaded", onUploaded as EventListener);
    };
  }, [loadDashboard]);

  useEffect(() => {
    const dismissed = window.localStorage.getItem(baselineDismissKey) === "1";
    setBaselineDismissed(dismissed);
  }, [baselineDismissKey]);

  useEffect(() => {
    const saved = window.localStorage.getItem("dashboard-partner-mode") === "1";
    setPartnerMode(saved);
  }, []);

  const latestReadyBrief = useMemo(
    () => reports.find((report) => report.status === "ready" && report.download_pdf_url) || null,
    [reports],
  );
  const recentReadyBriefs = useMemo(
    () => reports.filter((report) => report.status === "ready" && report.download_pdf_url).slice(0, 3),
    [reports],
  );
  const latestProcessedReport = useMemo(() => reports.find((report) => report.status === "ready") || null, [reports]);
  const reviewPeriodLabel = useMemo(() => formatReviewPeriod(latestProcessedReport), [latestProcessedReport]);
  const reviewsAnalyzed = latestProcessedReport?.total_reviews ?? 0;
  const lastProcessedLabel = formatDateOnly(latestProcessedReport?.created_at);
  const lastProcessedDateTime = formatDateTime(latestProcessedReport?.created_at);
  const readyReportCount = useMemo(() => reports.filter((report) => report.status === "ready").length, [reports]);
  const showBaselineNotice = readyReportCount === 1 && !baselineDismissed;
  const isFirstRunWorkspace = !loading && !loadError && readyReportCount === 0;

  const overdueActions = useMemo(() => actions.filter((action) => isOverdue(action)), [actions]);
  const openActions = useMemo(() => actions.filter((action) => action.status !== "done"), [actions]);
  const inProgressActions = useMemo(() => actions.filter((action) => action.status === "in_progress"), [actions]);
  const unownedActionsCount = useMemo(
    () => openActions.filter((action) => !action.owner || String(action.owner).trim() === "").length,
    [openActions],
  );
  const highSeveritySignalsCount = useMemo(
    () => latestSignals.filter((signal) => String(signal.severity || "").toLowerCase() === "high").length,
    [latestSignals],
  );

  const newSignalsCount = useMemo(() => {
    if (previousSignals.length === 0) return latestSignals.length;
    return Math.max(0, latestSignals.length - previousSignals.length);
  }, [latestSignals.length, previousSignals.length]);

  const newExposureCategories = useMemo(() => {
    const previousCategories = new Set(previousSignals.map(signalCategory));
    const latestCategories = new Set(latestSignals.map(signalCategory));
    let created = 0;
    latestCategories.forEach((category) => {
      if (!previousCategories.has(category)) created += 1;
    });
    return created;
  }, [latestSignals, previousSignals]);

  const exposureLabel = (exposure?.exposure_label || "Baseline").toLowerCase();
  const exposureRisk = exposureLabel.includes("high") || exposureLabel.includes("elevated")
    ? "High"
    : exposureLabel.includes("watch")
      ? "Moderate"
      : "Low";

  const guidance = useMemo(() => {
    if (overdueActions.length > 0) {
      return {
        directive: `${overdueActions.length} overdue action${overdueActions.length === 1 ? "" : "s"} require immediate partner review.`,
        recommendation: "Assign partner review and confirm owner + due date updates today.",
      };
    }
    if (newSignalsCount > 0) {
      return {
        directive: `${newSignalsCount} new ${newSignalsCount === 1 ? DISPLAY_LABELS.clientIssueSingular.toLowerCase() : DISPLAY_LABELS.clientIssuePlural.toLowerCase()} detected since last review.`,
        recommendation: "Assign partner review.",
      };
    }
    if (latestSignals.length > 0 && openActions.length === 0) {
      return {
        directive: "Client issues exist without corresponding open actions.",
        recommendation: "Create action owners for each high-priority client issue.",
      };
    }
    return {
      directive: "Client issues and actions are currently aligned.",
      recommendation: "Proceed to generate the next governance brief.",
    };
  }, [latestSignals.length, newSignalsCount, openActions.length, overdueActions.length]);

  const signalCategoryCounts = useMemo(() => {
    const counts = new Map<string, { label: string; count: number }>();
    latestSignals.forEach((signal) => {
      const key = signalCategory(signal);
      const label = signalLabel(signal);
      const existing = counts.get(key);
      if (existing) {
        existing.count += 1;
      } else {
        counts.set(key, { label, count: 1 });
      }
    });
    return Array.from(counts.values()).sort((a, b) => b.count - a.count);
  }, [latestSignals]);

  const issuePercentages = useMemo<ReputationIssuePercentages>(
    () => buildIssuePercentagesFromSignals(latestSignals),
    [latestSignals],
  );
  const previousIssuePercentages = useMemo<ReputationIssuePercentages>(
    () => buildIssuePercentagesFromSignals(previousSignals),
    [previousSignals],
  );

  const topIssue = signalCategoryCounts[0] || null;
  const topIssueShare = topIssue && latestSignals.length > 0 ? Math.round((topIssue.count / latestSignals.length) * 100) : 0;

  const briefDeltas = useMemo(() => {
    const items: string[] = [];
    items.push(newSignalsCount > 0 ? `${newSignalsCount} new client issues detected.` : "No net-new client issues detected in this cycle.");
    if (newExposureCategories > 0) {
      items.push(`${newExposureCategories} new exposure categories emerged.`);
    }
    items.push(
      overdueActions.length > 0
        ? `${overdueActions.length} overdue actions now require partner attention.`
        : "No overdue actions at this time.",
    );
    return items;
  }, [newExposureCategories, newSignalsCount, overdueActions.length]);

  const briefFeedbackQuotes = useMemo(
    () => latestSignals.map((signal) => signal.description?.trim()).filter((value): value is string => Boolean(value)).slice(0, 2),
    [latestSignals],
  );

  const estimatedImpact = useMemo(() => {
    if (!topIssue) return null;
    const modeledReduction = Math.max(1, Math.round(topIssue.count * 0.1));
    return `A 10% reduction in ${topIssue.label.toLowerCase()} themes would reduce approximately ${modeledReduction} flagged client issues in the next cycle.`;
  }, [topIssue]);

  const suggestedActions = useMemo(() => {
    return latestSignals
      .filter((signal) => String(signal.severity || "").toLowerCase() === "high")
      .map((signal) => {
        const label = signalLabel(signal);
        const categoryKey = signalCategory(signal);
        const hasAssignedAction = actions.some((action) => {
          const haystack = `${action.title} ${action.notes || ""} ${action.kpi || ""}`.toLowerCase();
          return haystack.includes(categoryKey);
        });
        return {
          id: signal.id,
          hasAssignedAction,
          context: `High-severity ${label.toLowerCase()} client issue detected in this cycle.`,
          recommendation: recommendationForSignal(label),
        };
      })
      .filter((item) => !item.hasAssignedAction);
  }, [actions, latestSignals]);

  const cycleAttentionSummary = useMemo(() => {
    if (overdueActions.length > 0) {
      return `${overdueActions.length} overdue follow-through item${overdueActions.length === 1 ? "" : "s"} need partner review before the current brief is meeting-ready.`;
    }
    if (unownedActionsCount > 0) {
      return `${unownedActionsCount} open follow-through item${unownedActionsCount === 1 ? "" : "s"} still need clear ownership before the brief can carry clean follow-through into the room.`;
    }
    if (highSeveritySignalsCount > 0) {
      return `${highSeveritySignalsCount} high-severity client issue${highSeveritySignalsCount === 1 ? "" : "s"} are active in the current cycle and should be reviewed in the brief first.`;
    }
    if (latestReadyBrief) {
      return "The latest brief is ready to review and current follow-through is in a healthy state.";
    }
    return "This cycle is active, but the latest brief is still being prepared.";
  }, [highSeveritySignalsCount, latestReadyBrief, overdueActions.length, unownedActionsCount]);

  const handleExportBrief = useCallback(async (targetBrief?: ReportListItem | null) => {
    const brief = targetBrief || latestReadyBrief;
    if (!brief?.download_pdf_url) {
      navigate("/dashboard/reports");
      return;
    }

    const exportUrl = brief.download_pdf_url.includes("?")
      ? `${brief.download_pdf_url}&export=1`
      : `${brief.download_pdf_url}?export=1`;

    try {
      const response = await fetch(exportUrl, { credentials: "include" });
      const contentType = response.headers.get("content-type") || "";

      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as { error?: string; message?: string };
        if (payload.error === "plan_limit") {
          emitPlanLimitError(payload.message || "Trial limit reached");
          return;
        }
        if (payload.error === "Report outside plan history window") {
          toast.error("This report is outside your plan's historical intelligence window. Upgrade your plan to access older governance history.");
          return;
        }
        if (!response.ok) {
          toast.error(payload.message || payload.error || "Unable to generate governance brief.");
          return;
        }
      }

      if (!response.ok) {
        toast.error("Unable to generate governance brief.");
        return;
      }

      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, "_blank", "noopener,noreferrer");
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
    } catch {
      toast.error("Unable to generate governance brief.");
    }
  }, [latestReadyBrief, navigate]);

  const planUsage = useMemo(() => {
    const limits = resolvePlanLimits(currentPlan);
    const now = new Date();
    const reportsUsedThisMonth = reports.filter((report) => {
      const parsed = new Date(report.created_at || "");
      return Number.isFinite(parsed.getTime()) && parsed.getFullYear() === now.getFullYear() && parsed.getMonth() === now.getMonth();
    }).length;
    return {
      reportsUsedThisMonth,
      reportsLimitPerMonth: limits?.maxReportsPerMonth ?? null,
      seatsUsed: teamSeatsUsed,
      seatsLimit: limits?.maxUsers ?? null,
      reviewUploadLimit: limits?.maxReviewsPerUpload ?? null,
      pdfWatermark: Boolean(limits.pdfWatermark),
    };
  }, [currentPlan, reports, teamSeatsUsed]);

  const dismissBaselineNotice = () => {
    window.localStorage.setItem(baselineDismissKey, "1");
    setBaselineDismissed(true);
  };

  const togglePartnerMode = () => {
    setPartnerMode((prev) => {
      const next = !prev;
      window.localStorage.setItem("dashboard-partner-mode", next ? "1" : "0");
      return next;
    });
  };

  const handleEmailBrief = async () => {
    if (isSendingBrief) return;
    if (!latestProcessedReport) {
      toast.error("Upload feedback to generate the first governance brief before sending partner delivery.");
      return;
    }
    const statusResult = await getPartnerBriefDeliveryStatus();
    if (!statusResult.success || !statusResult.status) {
      toast.error("Partner brief delivery status could not be confirmed. Please try again.");
      return;
    }
    if (!statusResult.status.delivery_available) {
      toast.error("Partner brief delivery is not configured for this deployment. No email was sent.");
      return;
    }
    const topIssueText = topIssue ? `${topIssue.label} (${topIssueShare}%)` : "No dominant issue identified";
    const quote = briefFeedbackQuotes[0] || "No client quote available yet.";
    const htmlContent = `<!doctype html>
<html>
  <body style="font-family:Arial,sans-serif;line-height:1.5;color:#0D1B2A;">
    <h2>Clarion Client Experience Brief</h2>
    <p><strong>Reporting Period:</strong> ${reviewPeriodLabel}</p>
    <p><strong>Overall Reputation Risk:</strong> ${exposureRisk}</p>
    <p><strong>Top Client Issue:</strong> ${topIssueText}</p>
    <p><strong>Example Client Feedback:</strong> "${quote}"</p>
    <p><strong>Recommended Partner Discussion:</strong> ${guidance.recommendation}</p>
  </body>
</html>`;
    setIsSendingBrief(true);
    const result = await sendPartnerBriefEmail(htmlContent);
    if (result.success) {
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

  return (
      <section
        className="bg-[#F0F2F5]"
        style={{
          padding: "var(--space-page-y) var(--space-page-x)",
        }}
      >
        <div
          className="stage-sequence dash-override mx-auto w-full"
          style={{ maxWidth: "var(--content-max-w)" }}
        >
          <header
            className="flex flex-wrap items-center justify-between gap-3"
            style={{ marginBottom: "var(--space-section)" }}
          >
            <div className="max-w-3xl">
              <p className="text-xs uppercase tracking-wide text-neutral-500">
                {isFirstRunWorkspace ? "First governance cycle" : "Current governance cycle"}
              </p>
              <h1 className="gov-h1">
                {isFirstRunWorkspace ? "Start the first client-feedback review cycle." : "Current client-feedback review cycle"}
              </h1>
              <p className="mt-1 text-sm text-neutral-600">
                {isFirstRunWorkspace
                  ? "Upload one CSV to generate recurring client issues, assign follow-through, and prepare the first governance brief."
                  : "Use workspace home to see what needs attention now, whether the latest brief is ready, and which follow-through items still need partner review."}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-neutral-500">
                <GovernanceLoop />
                {latestProcessedReport ? <span>Last processed {lastProcessedDateTime}</span> : null}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {isFirstRunWorkspace ? (
                <>
                  <Link to="/upload?start=true" className="gov-btn-primary">
                    Upload feedback CSV
                  </Link>
                  <Link to="/demo" className="gov-text-link">
                    Review sample workspace
                  </Link>
                </>
              ) : (
                <>
                  <button
                    type="button"
                    onClick={togglePartnerMode}
                    disabled={readyReportCount === 0}
                    className={[
                      "inline-flex items-center gap-2 rounded-[8px] border px-3 py-2 text-xs font-semibold uppercase tracking-[0.06em] transition-colors",
                      partnerMode
                        ? "border-[#0D1B2A] bg-[#0D1B2A] text-white hover:bg-[#16263b]"
                        : "border-[#D1D5DB] bg-white text-[#0D1B2A] hover:bg-slate-50 disabled:cursor-not-allowed disabled:border-slate-200 disabled:bg-slate-100 disabled:text-slate-400 disabled:hover:bg-slate-100",
                    ].join(" ")}
                    aria-pressed={partnerMode}
                    title={readyReportCount === 0 ? "Meeting view becomes available after the first completed review cycle." : undefined}
                  >
                    <span
                      className={[
                        "h-2.5 w-2.5 rounded-full",
                        partnerMode ? "bg-emerald-300" : "bg-slate-300",
                      ].join(" ")}
                    />
                    Meeting view
                  </button>
                  <button
                    id="emailBriefBtn"
                    type="button"
                    className="gov-btn-secondary"
                    onClick={() => void handleEmailBrief()}
                    disabled={isSendingBrief || !latestProcessedReport}
                  >
                    {isSendingBrief ? "Sending brief..." : latestProcessedReport ? "Email latest brief" : "Brief unavailable"}
                  </button>
                </>
              )}
              <PlanBadge plan={currentPlan?.firmPlan} />
              <Button type="button" variant="secondary" onClick={() => void loadDashboard()}>Refresh</Button>
            </div>
          </header>

          {/* ════════════════════════════════════
              MEETING VIEW — partner mode active
              Brief-first, no workspace chrome
              ════════════════════════════════════ */}
          {partnerMode ? (
            <section className="space-y-6">
              {/* Primary: the current governance brief */}
              <div className="rounded-[12px] border border-[#D9E2EC] bg-white px-6 py-6 shadow-[0_1px_4px_rgba(0,0,0,0.07)]">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.08em] text-neutral-500">
                      Meeting view · current governance brief
                    </p>
                    <h2 className="mt-1 text-[22px] font-semibold text-[#0D1B2A]">
                      {latestProcessedReport
                        ? `${reviewPeriodLabel}`
                        : "No brief ready yet"}
                    </h2>
                    {latestProcessedReport && (
                      <p className="mt-1 text-sm text-neutral-500">
                        {reviewsAnalyzed} reviews analyzed · last processed {lastProcessedDateTime}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {latestProcessedReport && (
                      <Button
                        type="button"
                        variant="primary"
                        onClick={() => navigate(`/dashboard/reports/${latestProcessedReport.id}`)}
                      >
                        Open governance brief
                        <ChevronRight size={14} />
                      </Button>
                    )}
                    {latestReadyBrief && (
                      <Button type="button" variant="secondary" onClick={() => void handleExportBrief()}>
                        {planUsage.pdfWatermark ? "Preview brief PDF" : "Download brief PDF"}
                        <ChevronRight size={14} />
                      </Button>
                    )}
                  </div>
                </div>

                {latestProcessedReport ? (
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Cycle period</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">{reviewPeriodLabel}</p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Client issues</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">
                        {latestSignals.length} active
                        <span className="ml-1 font-normal text-neutral-600">({highSeveritySignalsCount} high severity)</span>
                      </p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Posture</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">{exposureRisk} exposure</p>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-neutral-600">
                    Upload a CSV to generate the first governance brief before using meeting view.
                  </p>
                )}
              </div>

              {/* Secondary: cycle attention summary */}
              {latestProcessedReport && (
                <div className="rounded-[12px] border border-[#D9E2EC] bg-white px-6 py-5 shadow-[0_1px_3px_rgba(0,0,0,0.05)]">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500 mb-2">
                    Cycle attention
                  </p>
                  <p className="text-sm leading-6 text-neutral-700">{cycleAttentionSummary}</p>
                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Open actions</p>
                      <p className="mt-1 text-2xl font-semibold text-[#0D1B2A]">{openActions.length}</p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Overdue</p>
                      <p className={`mt-1 text-2xl font-semibold ${overdueActions.length > 0 ? "text-red-600" : "text-[#0D1B2A]"}`}>
                        {overdueActions.length}
                      </p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">High-severity signals</p>
                      <p className={`mt-1 text-2xl font-semibold ${highSeveritySignalsCount > 0 ? "text-amber-600" : "text-[#0D1B2A]"}`}>
                        {highSeveritySignalsCount}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              <div className="flex justify-end">
                <button
                  type="button"
                  onClick={togglePartnerMode}
                  className="text-xs text-neutral-400 underline underline-offset-4 hover:text-neutral-600"
                >
                  Exit meeting view
                </button>
              </div>
            </section>
          ) : null}

          {!partnerMode && isFirstRunWorkspace ? (
            <>
              <section className="mb-8 rounded-[12px] border border-[#D9E2EC] bg-white px-6 py-6 shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
                <div className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.08em] text-neutral-500">First review cycle</p>
                    <h2 className="mt-2 text-[24px] font-semibold text-[#0D1B2A]">The workspace is intentionally quiet until the first upload starts the cycle.</h2>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
                      Bring in one CSV from the current review period. Clarion will validate the file, generate the first report,
                      and open the issue, action, and governance brief workflow from there.
                    </p>

                    <div className="mt-5 rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC]">
                      <div className="border-b border-[#E5E7EB] px-5 py-4">
                        <p className="gov-type-eyebrow">What happens next</p>
                        <p className="mt-1 text-sm text-neutral-700">The first upload creates the structure the rest of the workspace depends on.</p>
                      </div>
                      <div className="divide-y divide-[#E5E7EB]">
                        <div className="flex gap-4 px-5 py-4">
                          <div className="gov-type-eyebrow">01</div>
                          <div>
                            <h3 className="text-[15px] font-semibold text-[#0D1B2A]">Upload feedback</h3>
                            <p className="mt-1 text-sm text-neutral-700">Use one CSV from the current review period to establish the first live cycle.</p>
                          </div>
                        </div>
                        <div className="flex gap-4 px-5 py-4">
                          <div className="gov-type-eyebrow">02</div>
                          <div>
                            <h3 className="text-[15px] font-semibold text-[#0D1B2A]">Review the recurring client issues</h3>
                            <p className="mt-1 text-sm text-neutral-700">Clarion groups the feedback into patterns leadership can review in one pass.</p>
                          </div>
                        </div>
                        <div className="flex gap-4 px-5 py-4">
                          <div className="gov-type-eyebrow">03</div>
                          <div>
                            <h3 className="text-[15px] font-semibold text-[#0D1B2A]">Assign follow-through and open the brief packet</h3>
                            <p className="mt-1 text-sm text-neutral-700">Turn the highest-priority issues into owned actions and a leadership-ready governance brief.</p>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-6 flex flex-wrap items-center gap-3">
                      <Link to="/upload?start=true" className="gov-btn-primary">
                        Upload feedback CSV
                      </Link>
                      <Link to="/demo" className="gov-text-link">
                        Review sample workspace
                      </Link>
                    </div>
                  </div>

                  <aside className="space-y-4">
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
                      <p className="gov-type-eyebrow">What you need</p>
                      <p className="mt-2 text-sm text-neutral-700">
                        One CSV export from the current review period. Clarion checks structure first, then runs full upload validation.
                      </p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] p-4">
                      <p className="gov-type-eyebrow">What Clarion creates</p>
                      <p className="mt-2 text-sm text-neutral-700">
                        The first upload creates the report packet, action list, and governance brief the rest of the workspace is built around.
                      </p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
                      <p className="gov-type-eyebrow">Sample workspace</p>
                      <p className="mt-2 text-sm text-neutral-700">
                        The sample workspace uses law-firm example data. Your live workspace remains unchanged until you upload your own feedback.
                      </p>
                    </div>
                  </aside>
                </div>
              </section>
            </>
          ) : null}

          {!partnerMode && showBaselineNotice ? (
            <section className="relative mb-8 rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-[18px] py-[14px]">
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
                  <h2 className="text-[14px] font-semibold text-[#1E40AF]">Cycle baseline</h2>
                </div>
                <p className="mt-1 text-[13px] leading-relaxed text-[#374151]">
                  This is your first review cycle. Future uploads will allow the system to detect trends and changes over time. Your client issues reflect patterns from this upload only.
                </p>
              </div>
            </section>
          ) : null}

          {!partnerMode && historyTruncated && historyNotice ? (
            <section className="mb-8 rounded-[8px] border border-[#BFDBFE] bg-[#EFF6FF] px-[18px] py-[12px] text-[13px] text-[#1E3A8A]">
              {historyNotice}
            </section>
          ) : null}

          {/* Anchored-to strip: suppressed from primary view — data is surfaced in the brief card itself */}

          {!partnerMode && loadError ? (
            <div className="mb-8">
              <DashboardCard title="Dashboard status" subtitle="Connection">
                <p className="text-sm text-red-700">{loadError}</p>
              </DashboardCard>
            </div>
          ) : null}

          {!partnerMode && !isFirstRunWorkspace ? (
          <section className="dash-tier">
            <div className="grid gap-[var(--dash-section-gap)] xl:grid-cols-[1.1fr_0.9fr]">
              <DashboardCard
                title="Current governance brief"
                subtitle={latestProcessedReport ? `${reviewPeriodLabel} · ${reviewsAnalyzed} reviews analyzed` : "Awaiting the first completed cycle"}
                actions={
                  <div className="flex flex-wrap items-center gap-2">
                    {latestProcessedReport ? (
                      <Button
                        type="button"
                        variant="primary"
                        onClick={() => navigate(`/dashboard/reports/${latestProcessedReport.id}`)}
                      >
                        Open current brief
                        <ChevronRight size={14} />
                      </Button>
                    ) : null}
                    {latestReadyBrief ? (
                      <Button type="button" variant="secondary" onClick={() => void handleExportBrief()}>
                        {loading ? (
                          <>
                            <Loader2 size={14} className="animate-spin" />
                            Loading
                          </>
                        ) : (
                          <>
                            {planUsage.pdfWatermark ? "Preview latest brief PDF" : "Download latest brief PDF"}
                            <ChevronRight size={14} />
                          </>
                        )}
                      </Button>
                    ) : (
                      <Button type="button" variant="primary" onClick={() => navigate("/upload")}>
                        Upload to generate brief
                        <ChevronRight size={14} />
                      </Button>
                    )}
                  </div>
                }
              >
                <div className="space-y-4">
                  <p className="text-sm leading-6 text-neutral-700">{cycleAttentionSummary}</p>

                  <div className="grid gap-3 sm:grid-cols-3">
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Cycle period</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">{reviewPeriodLabel}</p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Client issues</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">
                        {latestSignals.length} active
                        <span className="ml-1 font-normal text-neutral-600">({highSeveritySignalsCount} high severity)</span>
                      </p>
                    </div>
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-[#FAFBFC] px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Follow-through</p>
                      <p className="mt-2 text-sm font-semibold text-[#0D1B2A]">
                        {openActions.length} open
                        <span className="ml-1 font-normal text-neutral-600">({overdueActions.length} overdue)</span>
                      </p>
                    </div>
                  </div>

                  {latestProcessedReport ? (
                    <div className="rounded-[10px] border border-[#E5E7EB] bg-white px-4 py-3">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-neutral-500">Brief status</p>
                      <p className="mt-2 text-sm text-neutral-700">
                        Ready for partner review. Open the full brief packet for the five-section governance summary,
                        assigned follow-through, and decisions record.
                      </p>
                    </div>
                  ) : null}
                </div>
              </DashboardCard>

              <FirmGovernanceStatus
                status={exposureRisk}
                reviewPeriodLabel={reviewPeriodLabel}
                reviewsAnalyzed={reviewsAnalyzed}
                metrics={{
                  signals: latestSignals.length,
                  newSignals: newSignalsCount,
                  openActions: openActions.length,
                  overdueActions: overdueActions.length,
                }}
                loading={loading}
                onOpenSignals={() => navigate("/dashboard/signals")}
                onOpenNewSignals={() => navigate("/dashboard/signals?filter=new")}
                onOpenOpenActions={() => navigate("/dashboard/actions")}
                onOpenOverdueActions={() => navigate("/dashboard/actions?filter=overdue")}
              />
            </div>

            <div>
              <div className="dash-tier-gap" />
              <DashboardSectionDivider
                label="Attention now"
                description="What still needs follow-through before the next partner review"
              />
            </div>

            <div className="dash-tier">
              <GovernanceGuidance
                directive={guidance.directive}
                recommendedAction={guidance.recommendation}
                onOpenActions={() => navigate("/dashboard/actions")}
              />

              {suggestedActions.length > 0 ? (
                <div>
                  <DashSectionHeader
                    title="Follow-through to assign now"
                    subtitle="Recommended responses where current client issues still do not have clear ownership."
                  />
                  <div className="space-y-3">
                    {suggestedActions.map((item) => (
                      <article key={`suggested-action-${item.id}`} className="rounded-[10px] border border-[#E5E7EB] border-l-[3px] border-l-[#F59E0B] bg-white px-5 py-[18px]">
                        <p className="text-[13px] text-[#6B7280]">{item.context}</p>
                        <p className="mt-2 text-[11px] uppercase tracking-[0.08em] text-[#9CA3AF]">Suggested Governance Action</p>
                        <p className="mt-1 text-[15px] font-semibold text-[#0D1B2A]">{item.recommendation}</p>
                        <div className="mt-3 flex justify-end">
                          <button
                            type="button"
                            onClick={() => navigate(`/dashboard/signals/${item.id}`)}
                            className="rounded-[6px] bg-[#0D1B2A] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#16263b]"
                          >
                            Create Governance Action
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              <DashboardCard
                title="Follow-through to review"
                subtitle="Ownership gaps and due-state tied to the current governance brief."
                actions={
                  <Button type="button" variant="primary" onClick={() => navigate("/dashboard/actions")}>
                    Open follow-through
                    <ChevronRight size={14} />
                  </Button>
                }
              >
                <div className="workspace-inline-stats">
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">Open</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">
                      {loading ? <span className="inline-block h-8 w-10 rounded gov-skel-shimmer" /> : openActions.length}
                    </p>
                  </div>
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">In Progress</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">
                      {loading ? <span className="inline-block h-8 w-10 rounded gov-skel-shimmer" /> : inProgressActions.length}
                    </p>
                  </div>
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">Overdue</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">
                      {loading ? <span className="inline-block h-8 w-10 rounded gov-skel-shimmer" /> : overdueActions.length}
                    </p>
                  </div>
                </div>

                {latestProcessedReport ? (
                  <div className="mt-4 rounded-[10px] border border-[#E5E7EB] bg-white px-4 py-3 text-sm text-neutral-700">
                    These items are reflected in{" "}
                    <button
                      type="button"
                      onClick={() => navigate(`/dashboard/reports/${latestProcessedReport.id}`)}
                      className="font-semibold text-[#0D1B2A] underline underline-offset-4"
                    >
                      the current governance brief
                    </button>
                    {" "}and should be reviewed there before partner discussion.
                  </div>
                ) : null}
              </DashboardCard>

              <DashboardCard title="Recent follow-through" subtitle="Latest issue response, owner, and current status">
                {loading ? (
                  <ul aria-label="Loading recent actions" className="space-y-3">
                    {(["w-44", "w-56", "w-36"] as const).map((wCls, i) => (
                      <li key={`recent-action-skel-${i}`} className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
                        <div className={`gov-skel-shimmer h-3 rounded ${wCls}`} />
                        <div className="mt-2 gov-skel-shimmer h-3 w-52 rounded" />
                        <div className="mt-1.5 gov-skel-shimmer h-2.5 w-36 rounded" />
                      </li>
                    ))}
                  </ul>
                ) : recentGovernanceActions.length === 0 ? (
                  <GovernanceEmptyState
                    size="sm"
                    icon={<ClipboardList size={18} />}
                    title="No governance actions assigned yet"
                    description="Actions are created after reviewing client issues. Assign ownership and due dates — they will appear here."
                    primaryAction={{ label: "Review client issues", href: "/dashboard/signals" }}
                  />
                ) : (
                  <ul className="space-y-3">
                    {recentGovernanceActions.map((item) => (
                      <li key={item.id} className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
                        <p className="text-sm text-neutral-800"><span className="font-semibold">Issue:</span> {item.issue}</p>
                        <p className="mt-1 text-sm text-neutral-800"><span className="font-semibold">Action:</span> {item.action}</p>
                        <p className="mt-1 text-xs text-neutral-600">Owner: {item.owner || "Unassigned"} - Status: {item.status || "open"}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </DashboardCard>

            </div>

            {/* ════════════════════════════════════
                TIER 3 — Supporting context
                Governance posture, history, brief prep
                ════════════════════════════════════ */}
            <div>
              <div className="dash-tier-gap" />
              <DashboardSectionDivider
                label="Supporting cycle context"
                description="Change, history, and broader brief context after the immediate review work"
              />
            </div>

            <div className="dash-tier">
              <div className="grid gap-[var(--dash-section-gap)] xl:grid-cols-[1.2fr_0.8fr]">
                <SinceLastReview
                  isLoading={loading}
                  newFeedbackSignals={newSignalsCount}
                  newExposureCategories={newExposureCategories}
                  overdueActionsCreated={overdueActions.length}
                />
              </div>

              <RecentGovernanceBriefs
                briefs={recentReadyBriefs}
                escalationReportId={exposure?.report_id}
                hasEscalation={exposure?.partner_escalation_required}
                onView={(reportId) => navigate(`/dashboard/reports/${reportId}`)}
                onDownload={handleExportBrief}
              />

              <OversightBand
                loading={loading}
                metrics={[
                  {
                    label: "High-risk signals",
                    value: highSeveritySignalsCount,
                    sub: `of ${latestSignals.length} total client issues`,
                    risk: true,
                    route: "/dashboard/signals",
                    routeQuery: "filter=high",
                  },
                  {
                    label: "Unowned actions",
                    value: unownedActionsCount,
                    sub: `${openActions.length} open actions total`,
                    warn: true,
                    route: "/dashboard/actions",
                  },
                  {
                    label: "Briefs ready",
                    value: readyReportCount,
                    sub: readyReportCount === 1 ? "1 completed review cycle" : `${readyReportCount} completed cycles`,
                    success: readyReportCount > 0,
                    route: "/dashboard/reports",
                  },
                  {
                    label: "Overdue actions",
                    value: overdueActions.length,
                    sub: overdueActions.length === 0 ? "No overdue items" : "Require immediate attention",
                    risk: true,
                    route: "/dashboard/actions",
                    routeQuery: "filter=overdue",
                  },
                ]}
              />

              <GovernanceNarrativeRail
                loading={loading}
                cards={[
                  {
                    stage: "Evidence",
                    description: "Raw client feedback uploaded and processed into this review cycle.",
                    statusLines: [
                      `${reviewsAnalyzed} reviews analyzed`,
                      latestProcessedReport ? `Last cycle: ${reviewPeriodLabel}` : "No cycle yet",
                    ],
                    route: "/upload",
                  },
                  {
                    stage: "Signals",
                    description: "Recurring patterns and client issues extracted from evidence.",
                    statusLines: [
                      `${latestSignals.length} client issue${latestSignals.length === 1 ? "" : "s"} detected`,
                      newSignalsCount > 0 ? `${newSignalsCount} new since last review` : "No net-new signals",
                    ],
                    route: "/dashboard/signals",
                  },
                  {
                    stage: "Follow-Through" as never,
                    description: "Owner-assigned follow-through tied to active client issues.",
                    statusLines: [
                      `${openActions.length} open action${openActions.length === 1 ? "" : "s"}`,
                      overdueActions.length > 0 ? `${overdueActions.length} overdue` : "No overdue actions",
                    ],
                    route: "/dashboard/actions",
                  },
                  {
                    stage: "Briefs" as never,
                    description: "Leadership-ready summaries prepared for partner review.",
                    statusLines: [
                      `${readyReportCount} brief${readyReportCount === 1 ? "" : "s"} ready`,
                      latestReadyBrief ? `Latest: ${formatDateOnly(latestReadyBrief.created_at)}` : "Awaiting first cycle",
                    ],
                    route: "/dashboard/reports",
                  },
                ]}
              />

              {/* PartnerBriefPanel (80/100 reputation score) deferred:
                  score framing conflicts with exposure posture label — needs engine/label audit before showing publicly */}

              <DashboardCard title="Escalations and watchpoints" subtitle="Client issues that intensified or need leadership attention.">
                {alerts.length === 0 ? (
                  <GovernanceEmptyState
                    size="sm"
                    icon={<ShieldAlert size={18} />}
                    title="No active escalations this cycle"
                    description="Issues that intensify across review periods or require partner escalation will be flagged here."
                  />
                ) : (
                  <ul className="space-y-3">
                    {alerts.map((alert) => (
                      <li key={alert.id} className="rounded-[10px] border border-[#E5E7EB] bg-white p-4">
                        <p className="text-sm font-medium text-neutral-900">{alert.message}</p>
                        <p className="mt-1 text-xs text-neutral-600">
                          Appeared in {alert.occurrences} new review{alert.occurrences === 1 ? "" : "s"} this week
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </DashboardCard>
            </div>

            {/* ════════════════════════════════════
                TIER 4 — Workspace information / admin
                Capacity, plan limits, usage
                ════════════════════════════════════ */}
            <div>
              <div className="dash-tier-gap" />
              <DashboardSectionDivider
                label="Workspace reference"
                description="Secondary plan, seat, and capacity details"
              />
            </div>

            <div>
              <DashboardCard title="Plan and capacity" subtitle="Current month usage and seat coverage for this workspace.">
                <div className="workspace-inline-stats">
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">Reports this month</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">
                      {planUsage.reportsUsedThisMonth}
                      <span className="ml-1 text-sm font-medium text-neutral-600">/ {planUsage.reportsLimitPerMonth ?? "Unlimited"}</span>
                    </p>
                  </div>
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">Team seats</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">
                      {planUsage.seatsUsed ?? "-"}
                      <span className="ml-1 text-sm font-medium text-neutral-600">/ {planUsage.seatsLimit ?? "Unlimited"}</span>
                    </p>
                  </div>
                  <div className="workspace-inline-stat">
                    <p className="text-xs uppercase tracking-wide text-neutral-500">Review upload limit</p>
                    <p className="mt-2 text-3xl font-semibold text-neutral-900">{planUsage.reviewUploadLimit ?? "Unlimited"}</p>
                  </div>
                </div>
              </DashboardCard>
            </div>
          </section>
          ) : null}
        </div>
      </section>
  );
};

export default Dashboard;
