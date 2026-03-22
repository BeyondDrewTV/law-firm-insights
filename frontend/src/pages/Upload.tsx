import { useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import {
  getCredits,
  getReportDetail,
  getReports,
  uploadCsv,
  type CreditsState,
  type ReportDetail as ReportDetailData,
  type ReportListItem,
} from "@/api/authService";
import GovSectionCard from "@/components/governance/GovSectionCard";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/AuthContext";
import { formatFreshnessLine } from "@/utils/freshnessStamp";
import { resolvePlanLimits } from "@/config/planLimits";
import UploadUsageBar from "@/components/billing/UploadUsageBar";
import { formatApiDate } from "@/lib/dateTime";

type HeaderPreview = {
  detectedHeaders: string[];
  mapping: {
    date?: string;
    rating?: string;
    review_text?: string;
  };
  isCompatible: boolean;
  message: string;
};

const headerAliases = {
  date: ["review date", "review_date", "date", "created_at", "submitted_at", "time", "timestamp", "published_at", "publish_time", "at"],
  rating: ["rating (1-5)", "rating (1-5)", "rating_1_5", "rating", "score", "stars", "star_rating", "review_rating", "review_score"],
  review_text: ["client comment", "client_comment", "review_text", "review", "review_body", "comment", "comments", "feedback", "text", "content", "message"],
};

const normalizeHeader = (value: string) =>
  value
    .replace(/^\ufeff/, "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");

const splitCsvLine = (line: string) => {
  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < line.length; i += 1) {
    const char = line[i];
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      result.push(current.trim());
      current = "";
      continue;
    }

    current += char;
  }

  result.push(current.trim());
  return result.filter((header) => header.length > 0);
};

const resolveHeaderMapping = (headers: string[]) => {
  const normalizedMap = new Map<string, string>();
  headers.forEach((header) => {
    const normalized = normalizeHeader(header);
    if (normalized && !normalizedMap.has(normalized)) {
      normalizedMap.set(normalized, header);
    }
  });

  const mapping: HeaderPreview["mapping"] = {};

  (Object.keys(headerAliases) as Array<keyof typeof headerAliases>).forEach((key) => {
    const aliases = headerAliases[key];
    for (const alias of aliases) {
      const found = normalizedMap.get(normalizeHeader(alias));
      if (found) {
        mapping[key] = found;
        break;
      }
    }
  });

  return mapping;
};

const formatResetDate = (value: string | null | undefined) => {
  if (!value) {
    return "start of next month";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "start of next month";
  }
  return date.toLocaleDateString();
};

const formatCycleLabel = (
  report: Pick<ReportDetailData, "review_date_label" | "review_date_start" | "review_date_end" | "created_at"> | null,
) => {
  if (!report) {
    return "Current review period";
  }

  if (report.review_date_label?.trim()) {
    return report.review_date_label;
  }

  const start = report.review_date_start ? new Date(report.review_date_start) : null;
  const end = report.review_date_end ? new Date(report.review_date_end) : null;
  const validStart = Boolean(start && Number.isFinite(start.getTime()));
  const validEnd = Boolean(end && Number.isFinite(end.getTime()));

  if (validStart && validEnd && start && end) {
    const sameYear = start.getFullYear() === end.getFullYear();
    const sameMonth = sameYear && start.getMonth() === end.getMonth();

    if (sameMonth) {
      return start.toLocaleDateString([], { month: "long", year: "numeric" });
    }

    if (sameYear) {
      return `${start.toLocaleDateString([], { month: "short" })} - ${end.toLocaleDateString([], {
        month: "short",
        year: "numeric",
      })}`;
    }

    return `${start.toLocaleDateString([], { month: "short", year: "numeric" })} - ${end.toLocaleDateString([], {
      month: "short",
      year: "numeric",
    })}`;
  }

  if (report.created_at) {
    const created = new Date(report.created_at);
    if (Number.isFinite(created.getTime())) {
      return created.toLocaleDateString([], { month: "long", year: "numeric" });
    }
  }

  return "Current review period";
};

type CollapsibleCardProps = {
  title: string;
  summary: string;
  children: React.ReactNode;
};

const CollapsibleCard = ({ title, summary, children }: CollapsibleCardProps) => (
  <details className="gov-level-2 overflow-hidden">
    <summary className="cursor-pointer list-none px-4 py-3">
      <p className="text-sm font-semibold text-neutral-900">{title}</p>
      <p className="mt-1 text-xs text-neutral-700">{summary}</p>
    </summary>
    <div className="border-t border-neutral-200 px-4 py-3 text-sm text-neutral-800">{children}</div>
  </details>
);

const Upload = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentPlan, refreshPlan, refreshUser } = useAuth();
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [successMessage, setSuccessMessage] = useState("");
  const [reportId, setReportId] = useState<number | null>(null);
  const [uploadAsOfTimestamp, setUploadAsOfTimestamp] = useState<string | null>(null);
  const [usageMessage, setUsageMessage] = useState("");
  const [wasTruncatedForPlan, setWasTruncatedForPlan] = useState(false);
  const [latestUploadedReport, setLatestUploadedReport] = useState<ReportDetailData | null>(null);
  const [headerPreviews, setHeaderPreviews] = useState<Record<string, HeaderPreview>>({});
  const [credits, setCredits] = useState<CreditsState | null>(null);
  const [creditsLoading, setCreditsLoading] = useState(true);
  const [recentReports, setRecentReports] = useState<ReportListItem[]>([]);
  const [reportsUsedThisMonth, setReportsUsedThisMonth] = useState(0);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const fileChooserCardRef = useRef<HTMLDivElement | null>(null);
  const uploadAbortRef = useRef<AbortController | null>(null);
  const uploadCancelledRef = useRef(false);
  const isPaidPlan = (currentPlan?.planType || "free") !== "free";
  const planLimits = resolvePlanLimits(currentPlan);
  const maxReviewsPerUpload = planLimits.maxReviewsPerUpload;
  const maxReportsPerMonth = planLimits.maxReportsPerMonth;
  // Human-readable reset date for the usage bar, e.g. "April 1, 2026"
  const resetLabel = credits?.next_reset
    ? formatApiDate(credits.next_reset, { month: "long", day: "numeric", year: "numeric" }, "")
    : "";

  const getFileKey = (file: File) => `${file.name}:${file.size}:${file.lastModified}`;

  useEffect(() => {
    let isMounted = true;
    const loadBootstrapData = async () => {
      setCreditsLoading(true);
      if (!isMounted) {
        return;
      }
      const [creditsResult, reportsResult] = await Promise.all([getCredits(), getReports(300)]);
      if (creditsResult.success && creditsResult.credits) {
        setCredits(creditsResult.credits);
      } else {
        setCredits(null);
      }
      if (reportsResult.success && reportsResult.reports) {
        const allReports = [...reportsResult.reports];
        const now = new Date();
        const monthUsage = allReports.filter((report) => {
          const parsed = new Date(report.created_at || "");
          return (
            Number.isFinite(parsed.getTime()) &&
            parsed.getFullYear() === now.getFullYear() &&
            parsed.getMonth() === now.getMonth()
          );
        }).length;
        setReportsUsedThisMonth(monthUsage);
        const readyFirst = allReports
          .filter((report) => report.status !== "failed")
          .sort((a, b) => Date.parse(b.created_at || "") - Date.parse(a.created_at || ""))
          .slice(0, 3);
        setRecentReports(readyFirst);
      } else {
        setRecentReports([]);
        setReportsUsedThisMonth(0);
      }
      setCreditsLoading(false);
    };
    void loadBootstrapData();
    return () => {
      isMounted = false;
    };
  }, []);

  const noReportCredits =
    !!credits &&
    !credits.has_active_subscription &&
    credits.paid_reports_remaining <= 0 &&
    credits.free_reports_remaining <= 0;

  const fileMeta = useMemo(() => {
    if (files.length === 0) {
      return null;
    }
    const totalBytes = files.reduce((sum, item) => sum + item.size, 0);
    const sizeMb = (totalBytes / (1024 * 1024)).toFixed(2);
    return `${files.length} file${files.length === 1 ? "" : "s"} selected (${sizeMb} MB total)`;
  }, [files]);

  const firstFile = files[0] || null;
  const headerPreview = firstFile ? headerPreviews[getFileKey(firstFile)] || null : null;
  const shouldAutoStart = searchParams.get("start") === "true";
  const uploadedCycleLabel = useMemo(() => formatCycleLabel(latestUploadedReport), [latestUploadedReport]);
  const uploadedReviewCountLabel = latestUploadedReport
    ? `${latestUploadedReport.total_reviews} review${latestUploadedReport.total_reviews === 1 ? "" : "s"} analyzed`
    : "Report packet ready";
  const uploadedBriefAccessLabel = latestUploadedReport
    ? latestUploadedReport.plan_type === "free"
      ? "Preview the PDF from the report packet."
      : "Download the PDF from the report packet."
    : "Brief controls are available from the report packet.";

  useEffect(() => {
    if (!shouldAutoStart || isUploading || files.length > 0 || successMessage) {
      return;
    }

    const clearStartIntent = () => {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.delete("start");
      setSearchParams(nextParams, { replace: true });
    };

    const timer = window.setTimeout(() => {
      fileChooserCardRef.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      fileInputRef.current?.click();
      clearStartIntent();
    }, 120);

    return () => window.clearTimeout(timer);
  }, [files.length, isUploading, searchParams, setSearchParams, shouldAutoStart, successMessage]);

  const inspectHeaders = async (nextFile: File): Promise<HeaderPreview> => {
    try {
      const sample = await nextFile.slice(0, 64 * 1024).text();
      const firstLine = sample
        .split(/\r?\n/)
        .map((line) => line.trim())
        .find((line) => line.length > 0);

      if (!firstLine) {
        return {
          detectedHeaders: [],
          mapping: {},
          isCompatible: false,
          message: "We couldn't detect CSV headers. Add a header row and try again.",
        };
      }

      const detectedHeaders = splitCsvLine(firstLine);
      const mapping = resolveHeaderMapping(detectedHeaders);
      const hasRequired = Boolean(mapping.date && mapping.rating && mapping.review_text);
      const missing: string[] = [];
      if (!mapping.date) {
        missing.push("Review date");
      }
      if (!mapping.rating) {
        missing.push("Rating (1-5)");
      }
      if (!mapping.review_text) {
        missing.push("Client comment");
      }

      return {
        detectedHeaders,
        mapping,
        isCompatible: hasRequired,
        message: hasRequired
          ? "Great. We detected the needed columns and can process this file."
          : `Looks like your file is missing ${missing.join(" and ")}. Check the template and try again.`,
      };
    } catch {
      return {
        detectedHeaders: [],
        mapping: {},
        isCompatible: false,
        message: "We couldn't inspect this file locally. You can still try upload.",
      };
    }
  };

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFiles = Array.from(event.target.files || []);
    setError("");
    setSuccessMessage("");
    setReportId(null);
    setUploadAsOfTimestamp(null);
    setUsageMessage("");
    setWasTruncatedForPlan(false);
    setLatestUploadedReport(null);
    setProgress(0);
    setHeaderPreviews({});

    if (nextFiles.length === 0) {
      setFiles([]);
      return;
    }

    const invalidFile = nextFiles.find((item) => !item.name.toLowerCase().endsWith(".csv"));
    if (invalidFile) {
      setFiles([]);
      setError("Please select a .csv file.");
      return;
    }

    setFiles(nextFiles);
    void Promise.all(nextFiles.map(async (nextFile) => ({ key: getFileKey(nextFile), preview: await inspectHeaders(nextFile) }))).then(
      (results) => {
        const next: Record<string, HeaderPreview> = {};
        results.forEach((entry) => {
          next[entry.key] = entry.preview;
        });
        setHeaderPreviews(next);
      },
    );
  };

  const downloadTemplate = () => {
    const template = [
      "Review date,Rating (1-5),Client comment",
      '2026-02-01,5,"Clear communication and fast follow-up."',
      '2026-02-03,4,"Good experience overall. Billing explanation could be clearer."',
    ].join("\n");

    const blob = new Blob([template], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "clarion-upload-template.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setSuccessMessage("");
    setReportId(null);
    setUploadAsOfTimestamp(null);
    setUsageMessage("");
    setWasTruncatedForPlan(false);
    setLatestUploadedReport(null);

    if (files.length === 0) {
      setError("Choose at least one CSV file before uploading.");
      return;
    }
    if (noReportCredits) {
      const message = "You have reached your monthly report limit for this plan. Upgrade to continue.";
      setError(message);
      toast.error(message);
      return;
    }

    setIsUploading(true);
    setProgress(0);
    uploadCancelledRef.current = false;

    let successCount = 0;
    let failureCount = 0;
    let lastReportId: number | null = null;
    let lastUsageMessage = "";
    let truncatedDetected = false;
    let latestError = "";
    let consumedOneTimeCredit = false;

    for (let index = 0; index < files.length; index += 1) {
      if (uploadCancelledRef.current) {
        break;
      }
      const currentFile = files[index];
      const controller = new AbortController();
      uploadAbortRef.current = controller;
      const result = await uploadCsv(
        currentFile,
        (value) => {
          const nextProgress = ((index + value / 100) / files.length) * 100;
          setProgress(Math.round(nextProgress));
        },
        controller.signal,
      );
      uploadAbortRef.current = null;

      if (result.error === "Aborted") {
        uploadCancelledRef.current = true;
        break;
      }

      if (result.success && result.data) {
        successCount += 1;
        lastReportId = result.data.summary.report_id;
        truncatedDetected = truncatedDetected || Boolean(result.data.summary.truncated_for_plan);
        if ((currentPlan?.planType || "free") === "one_time" && result.data.usage.one_time_reports_remaining <= 0) {
          consumedOneTimeCredit = true;
        }
        const apiSubscriptionType = result.data.usage.subscription_type;
        lastUsageMessage =
          apiSubscriptionType === "monthly" || apiSubscriptionType === "annual"
            ? "Subscription reports: unlimited."
            : `Reports used this month: ${reportsUsedThisMonth}/${maxReportsPerMonth ?? "Unlimited"} | One-time remaining: ${result.data.usage.one_time_reports_remaining}`;

        if (result.data.summary.report_id) {
          window.sessionStorage.setItem("pendingReportId", String(result.data.summary.report_id));
        }

      const creditsResult = await getCredits();
      if (creditsResult.success && creditsResult.credits) {
        setCredits(creditsResult.credits);
          lastUsageMessage = creditsResult.credits.has_active_subscription
            ? "Subscription reports: unlimited."
            : `Reports used this month: ${reportsUsedThisMonth}/${maxReportsPerMonth ?? "Unlimited"}. Resets ${formatResetDate(creditsResult.credits.next_reset)}.`;
          const exhausted =
            !creditsResult.credits.has_active_subscription &&
            creditsResult.credits.paid_reports_remaining <= 0 &&
            creditsResult.credits.free_reports_remaining <= 0;
          if (exhausted && index < files.length - 1) {
            latestError = "Uploads stopped because your monthly report limit was reached.";
            failureCount += files.length - index - 1;
            break;
          }
        }
      } else {
        failureCount += 1;
        const backendError = result.error || "Upload failed. Please verify your CSV and try again.";
        const normalized = backendError.toLowerCase();
        latestError = normalized.includes("identical to an existing report")
          ? "This file matches a report you've already uploaded. If you need a new analysis, upload a different date range or dataset."
          : normalized.includes("plan allows up to")
            ? "This upload exceeded your current plan limits. Reduce rows or upgrade your plan."
          : normalized.includes("review date")
            ? "Looks like your file is missing a Review date column. Check the template and try again."
          : normalized.includes("rating") && normalized.includes("column")
            ? "Looks like your file is missing a Rating (1-5) column. Check the template and try again."
            : normalized.includes("review_text") || normalized.includes("review text") || normalized.includes("client comment")
              ? "Looks like your file is missing a Client comment column. Check the template and try again."
          : normalized.includes("required columns") || normalized.includes("no valid review rows")
            ? "We couldn't read this export yet. Make sure it includes Review date, Rating (1-5), and Client comment, or use the template below."
            : backendError;
      }
    }

    uploadAbortRef.current = null;

    if (uploadCancelledRef.current) {
      setIsUploading(false);
      setProgress(0);
      setError("");
      setSuccessMessage("");
      setReportId(null);
      setUploadAsOfTimestamp(null);
      setUsageMessage("");
      setWasTruncatedForPlan(false);
      setLatestUploadedReport(null);
      setFiles([]);
      setHeaderPreviews({});
      toast.info("Upload canceled.");
      return;
    }

    setProgress(100);
    setIsUploading(false);

    if (successCount > 0) {
      setSuccessMessage(
        successCount === 1
          ? "CSV uploaded and analyzed successfully."
          : `${successCount} CSV files uploaded and analyzed successfully.`,
      );
      setReportId(lastReportId);
      if (lastReportId) {
        const detailResult = await getReportDetail(lastReportId);
        if (detailResult.success && detailResult.report) {
          setLatestUploadedReport(detailResult.report);
          setUploadAsOfTimestamp(detailResult.report.created_at || null);
        } else {
          setUploadAsOfTimestamp(null);
          setLatestUploadedReport(null);
        }
      } else {
        setUploadAsOfTimestamp(null);
        setLatestUploadedReport(null);
      }
      setWasTruncatedForPlan(truncatedDetected);
      setUsageMessage(lastUsageMessage);
      toast.success(
        successCount === 1 ? "CSV uploaded and analyzed successfully." : `${successCount} files uploaded successfully.`,
      );
      setFiles([]);
      setHeaderPreviews({});
      const refreshedReports = await getReports(300);
      if (refreshedReports.success && refreshedReports.reports) {
        const allReports = [...refreshedReports.reports];
        const now = new Date();
        const monthUsage = allReports.filter((report) => {
          const parsed = new Date(report.created_at || "");
          return (
            Number.isFinite(parsed.getTime()) &&
            parsed.getFullYear() === now.getFullYear() &&
            parsed.getMonth() === now.getMonth()
          );
        }).length;
        setReportsUsedThisMonth(monthUsage);
        const readyFirst = allReports
          .filter((report) => report.status !== "failed")
          .sort((a, b) => Date.parse(b.created_at || "") - Date.parse(a.created_at || ""))
          .slice(0, 3);
        setRecentReports(readyFirst);
      }
      window.dispatchEvent(new Event("credits:refresh"));
      window.dispatchEvent(new Event("reports:uploaded"));
      await Promise.all([refreshUser(), refreshPlan()]);
      if (lastReportId && consumedOneTimeCredit) {
        window.sessionStorage.setItem("showOneTimeUpsell", "1");
      }
    }

    if (failureCount > 0 || latestError) {
      const finalError =
        latestError || `${failureCount} file${failureCount === 1 ? "" : "s"} could not be processed.`;
      setError(finalError);
      toast.error(finalError);
    }
  };

  const handleCancelUpload = () => {
    if (!isUploading) {
      return;
    }
    uploadCancelledRef.current = true;
    uploadAbortRef.current?.abort();
    uploadAbortRef.current = null;
  };

  const mappingRows = [
    { label: "Review date", value: headerPreview?.mapping.date || "Not found" },
    { label: "Rating (1-5)", value: headerPreview?.mapping.rating || "Not found" },
    { label: "Client comment", value: headerPreview?.mapping.review_text || "Not found" },
  ];
  const startAnotherUpload = () => {
    setSuccessMessage("");
    setReportId(null);
    setUsageMessage("");
    setWasTruncatedForPlan(false);
    setLatestUploadedReport(null);
    setError("");
    setProgress(0);
    setFiles([]);
    setHeaderPreviews({});
    fileInputRef.current?.click();
  };

  return (
      <section className="gov-page">
        <div className="stage-sequence mx-auto w-full max-w-[1200px]">
          <div className="grid gap-4 lg:grid-cols-[minmax(0,1.65fr)_minmax(280px,1fr)]">
          <GovSectionCard accent="none" padding="sm" className="space-y-4">
            <header className="space-y-2">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h1 className="gov-h1 text-balance">Start or continue a review cycle</h1>
                  <p className="mt-1 text-sm text-neutral-600">
                    Bring in one review-period export, let Clarion confirm the structure, and turn it into the current report packet, follow-through list, and brief.
                  </p>
                </div>
                <p data-testid="upload-asof" className="text-xs text-neutral-700">
                  {formatFreshnessLine("Last Report Created", uploadAsOfTimestamp)}
                </p>
              </div>
            </header>

            <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-neutral-700">
                <span className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 font-medium">One CSV for one review period</span>
                <span className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 font-medium">Header check before analysis</span>
                <span className="rounded-full border border-neutral-200 bg-white px-2.5 py-1 font-medium">Report, actions, and brief created after upload</span>
              </div>
              <div className="mt-4 grid gap-3 rounded-md border border-neutral-200 bg-white px-4 py-4 lg:grid-cols-[1.2fr_0.8fr_0.8fr]">
                <div>
                  <p className="gov-type-eyebrow">Step 1</p>
                  <p className="mt-1 text-sm font-medium text-neutral-900">Choose one clean export.</p>
                  <p className="mt-1 text-xs leading-5 text-neutral-700">Start with one CSV from the current review period rather than several files at once.</p>
                </div>
                <div>
                  <p className="gov-type-eyebrow">Step 2</p>
                  <p className="mt-1 text-sm font-medium text-neutral-900">Confirm the header check.</p>
                  <p className="mt-1 text-xs leading-5 text-neutral-700">Clarion reads the header row first so you can catch structure issues before processing.</p>
                </div>
                <div>
                  <p className="gov-type-eyebrow">Step 3</p>
                  <p className="mt-1 text-sm font-medium text-neutral-900">Open the current report packet.</p>
                  <p className="mt-1 text-xs leading-5 text-neutral-700">Start review in the report packet first, then move into follow-through and the partner-ready brief.</p>
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-3 text-sm">
                <Link to="/demo" className="gov-text-link">
                  Review the sample workspace first
                </Link>
                <span className="text-neutral-600">
                  Use the sample workspace if you want to see the workflow before preparing your own export.
                </span>
              </div>
            </div>

            <input
              ref={fileInputRef}
              id="csv-file"
              type="file"
              accept=".csv,text/csv"
              multiple
              onChange={handleFileChange}
              disabled={isUploading}
              className="sr-only"
            />

            {error && <div className="rounded border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-800">{error}</div>}
            {!creditsLoading && noReportCredits && (
              <div className="rounded border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-800">
                You have reached your monthly report limit on this plan. Upgrade before uploading to generate a new report.
                <Link to="/pricing" className="ml-1 font-semibold underline underline-offset-2">
                  View plans
                </Link>
              </div>
            )}

            <form className="space-y-3" onSubmit={handleSubmit}>
              <div ref={fileChooserCardRef} className="rounded-md border border-neutral-200 bg-white px-4 py-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="gov-type-eyebrow">Start this cycle</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900">Choose the review export for this cycle</p>
                    <p className="mt-1 text-xs leading-5 text-neutral-700">
                      Clarion detects common header names, checks the required fields before full analysis, and points you into the current report packet after processing. There is no manual column-mapping step in this version.
                    </p>
                    {shouldAutoStart ? (
                      <p className="mt-2 text-xs text-neutral-600">
                        Starting the file picker for your first upload.
                      </p>
                    ) : null}
                  </div>
                  <button
                    type="button"
                    className={files.length > 0 ? "gov-cta-secondary" : "gov-cta-primary"}
                    disabled={isUploading}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {files.length > 0 ? "Change file" : "Choose file"}
                  </button>
                </div>
                <div className="mt-4 rounded-md border border-dashed border-neutral-300 bg-neutral-50 px-4 py-4">
                  <span className="min-w-0 truncate text-sm font-medium text-neutral-900">{fileMeta || "No file selected yet"}</span>
                  {firstFile ? (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs text-neutral-700">
                        Selected file: <span className="font-medium text-neutral-900">{firstFile.name}</span>
                      </p>
                      <p className="text-xs text-neutral-600">
                        Clarion will inspect the header row immediately, then run full validation during upload.
                      </p>
                    </div>
                  ) : (
                    <div className="mt-2 space-y-1">
                      <p className="text-xs text-neutral-700">
                        Recommended: one clean CSV export for a single review period.
                      </p>
                      <p className="text-xs text-neutral-600">
                        If the file matches the required structure, Clarion will turn it into the current report packet and the first brief-ready cycle.
                      </p>
                    </div>
                  )}
                </div>
                {!isPaidPlan && files.length > 1 && (
                  <p className="mt-2 text-xs text-neutral-700">Free plans: each file consumes one report slot.</p>
                )}
                {!successMessage ? (
                  <div className="mt-4 flex flex-wrap items-center gap-3">
                    <button
                      type="submit"
                      disabled={isUploading || files.length === 0 || noReportCredits}
                      className="gov-cta-primary disabled:opacity-50"
                    >
                      {isUploading
                        ? "Uploading..."
                        : noReportCredits
                          ? "Upgrade required"
                          : files.length > 1
                            ? `Upload and analyze ${files.length} files`
                            : "Upload and analyze"}
                    </button>
                    {files.length === 0 ? (
                      <span className="text-xs text-neutral-600">Choose a file to enable analysis.</span>
                    ) : headerPreview?.isCompatible ? (
                      <span className="text-xs text-emerald-700">Header check passed. Ready to analyze.</span>
                    ) : headerPreview ? (
                      <span className="text-xs text-amber-700">Review the detected columns before starting analysis.</span>
                    ) : (
                      <span className="text-xs text-neutral-600">Header check will appear here before analysis starts.</span>
                    )}
                  </div>
                ) : null}
              </div>

              {headerPreview && (
                <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="gov-type-eyebrow">Pre-upload check</p>
                      <p className="mt-1 text-sm font-semibold text-neutral-900">
                        {headerPreview.isCompatible ? "File structure looks ready" : "Review the file structure before analysis"}
                      </p>
                      <p className="mt-1 text-sm text-neutral-700">
                        {headerPreview.isCompatible ? "Required columns found. Ready to analyze." : headerPreview.message}
                      </p>
                      <p className="mt-1 text-xs text-neutral-600">
                        Clarion checks the header row locally first, then runs full validation again during upload.
                      </p>
                    </div>
                    <span className={headerPreview.isCompatible ? "gov-chip-muted" : "gov-chip-warn"}>
                      {headerPreview.isCompatible ? "Ready" : "Check headers"}
                    </span>
                  </div>

                  <div className="mt-3 overflow-hidden rounded-md border border-neutral-200 bg-white">
                    <div className="grid grid-cols-2 bg-neutral-50 text-[11px] font-semibold uppercase tracking-wide text-neutral-700">
                      <div className="px-3 py-1.5">Required column</div>
                      <div className="px-3 py-1.5">Detected mapping</div>
                    </div>
                    <div className="divide-y divide-neutral-200">
                      {mappingRows.map((row) => (
                        <div key={row.label} className="grid grid-cols-2 text-sm">
                          <div className="px-3 py-1.5 text-neutral-800">{row.label}</div>
                          <div className="px-3 py-1.5 text-neutral-900">{row.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {headerPreview.detectedHeaders.length > 0 && (
                    <details className="mt-2 rounded-md border border-neutral-200 bg-white">
                      <summary className="cursor-pointer list-none px-3 py-2 text-sm font-medium text-neutral-800">Show detected headers</summary>
                      <div className="border-t border-neutral-200 px-3 py-2">
                        <div className="max-h-20 overflow-y-auto rounded border border-neutral-200 bg-neutral-50 px-2 py-1 text-xs text-neutral-700">
                          {headerPreview.detectedHeaders.join(", ")}
                        </div>
                      </div>
                    </details>
                  )}
                </div>
              )}

              {isUploading && (
                <div className="rounded-md border border-neutral-200 bg-white px-3 py-3">
                  <Progress value={progress} />
                  <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-xs text-neutral-700">Uploading and processing... {progress}%</p>
                    <button type="button" onClick={handleCancelUpload} className="gov-cta-secondary">
                      Cancel upload
                    </button>
                  </div>
                </div>
              )}

              {successMessage ? (
                <div className="rounded-md border border-neutral-200 bg-neutral-50 px-4 py-4 text-sm text-neutral-800">
                  <p className="gov-type-eyebrow">Upload complete</p>
                  <p className="mt-1 font-semibold text-neutral-900">The current report packet is ready.</p>
                  <p className="mt-1">{successMessage}</p>
                  <p className="mt-1 text-xs text-neutral-700">
                    Clarion finished the upload and created the report packet, action list, and brief path from this dataset. Start with the report packet first, then move into follow-through and the partner brief.
                  </p>
                  <div className="mt-4 grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
                    <div className="rounded-md border border-neutral-200 bg-white px-4 py-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-700">Current cycle created</p>
                      <p className="mt-1 text-sm font-semibold text-neutral-900">
                        {latestUploadedReport?.name || (reportId ? `Report #${reportId}` : "Current report packet")}
                      </p>
                      <div className="mt-3 grid gap-3 sm:grid-cols-3">
                        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">Review period</p>
                          <p className="mt-1 text-sm font-medium text-neutral-900">{uploadedCycleLabel}</p>
                        </div>
                        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">Cycle output</p>
                          <p className="mt-1 text-sm font-medium text-neutral-900">{uploadedReviewCountLabel}</p>
                        </div>
                        <div className="rounded-md border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="text-[11px] font-semibold uppercase tracking-wide text-neutral-600">Brief access</p>
                          <p className="mt-1 text-sm font-medium text-neutral-900">{uploadedBriefAccessLabel}</p>
                        </div>
                      </div>
                      {reportId ? <p className="mt-3 text-xs text-neutral-700">Report snapshot ID: #{reportId}</p> : null}
                    </div>

                    <div className="rounded-md border border-neutral-200 bg-white px-4 py-4">
                      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-700">Review this first</p>
                      <ol className="mt-3 space-y-3">
                        {[
                          {
                            step: "01",
                            title: "Open the current report packet",
                            detail: "Review the leadership briefing, the signals that matter most, and the next decisions for this cycle.",
                          },
                          {
                            step: "02",
                            title: "Check follow-through",
                            detail: "Confirm ownership, due dates, and anything overdue before the next partner discussion.",
                          },
                          {
                            step: "03",
                            title: "Use the brief controls",
                            detail: "Send the partner brief or open the PDF from the report packet once the cycle reads clearly.",
                          },
                        ].map((item) => (
                          <li key={item.step} className="flex gap-3">
                            <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-neutral-200 bg-neutral-50 text-[11px] font-semibold text-neutral-700">
                              {item.step}
                            </span>
                            <div>
                              <p className="text-sm font-medium text-neutral-900">{item.title}</p>
                              <p className="mt-1 text-xs leading-5 text-neutral-700">{item.detail}</p>
                            </div>
                          </li>
                        ))}
                      </ol>
                    </div>
                  </div>
                  {usageMessage && <p className="mt-1 text-xs text-neutral-700">{usageMessage}</p>}
                  {wasTruncatedForPlan && (
                    <div className="mt-3 rounded border border-amber-200 bg-amber-50 px-4 py-3">
                      <div className="flex items-start gap-2.5">
                        {/* amber indicator dot */}
                        <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-amber-400" />
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-amber-900">
                            Some reviews were skipped.
                          </p>
                          <p className="mt-1 text-sm text-amber-800">
                            This file had more reviews than your{" "}
                            {currentPlan?.firmPlan === "team" || currentPlan?.firmPlan === "professional"
                              ? "Team"
                              : currentPlan?.firmPlan === "firm" || currentPlan?.firmPlan === "leadership"
                              ? "Firm"
                              : "Free"}{" "}
                            plan allows. Clarion analyzed the first{" "}
                            <span className="font-semibold">
                              {maxReviewsPerUpload ?? "allowed"}
                            </span>{" "}
                            reviews — the rest were not included. Upgrade to Team (250/upload) or
                            Firm (1,000/upload) to process larger exports.
                          </p>
                          <div className="mt-3">
                            <Link
                              to="/pricing"
                              className="inline-flex items-center rounded border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 hover:bg-amber-100 transition-colors"
                            >
                              View upgrade options →
                            </Link>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                  <div className="mt-4 rounded-md border border-neutral-200 bg-white px-4 py-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-neutral-700">What to do next</p>
                    <p className="mt-1 text-xs text-neutral-700">
                      Open the report packet first. It is the fastest way into signals, assigned follow-through, partner-ready decisions, and the brief controls for this cycle.
                    </p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <Link to={reportId ? `/dashboard/reports/${reportId}` : "/dashboard/reports"} className="gov-cta-primary">
                        Open current report
                      </Link>
                      <Link to="/dashboard" className="gov-cta-secondary">
                        Open workspace home
                      </Link>
                      <Link to="/dashboard/actions" className="gov-cta-secondary">
                        Open follow-through
                      </Link>
                      <button type="button" className="gov-btn-quiet px-2.5 py-1.5 text-xs" onClick={startAnotherUpload}>
                        Upload another file
                      </button>
                    </div>
                  </div>
                </div>
              ) : null}
            </form>
          </GovSectionCard>

            <aside className="space-y-3">
              <GovSectionCard accent="watch" padding="sm" className="space-y-3">
                <h2 className="text-sm font-semibold text-neutral-900">Cycle reference</h2>
                <p className="text-xs text-neutral-700">Use the template if you need a clean starter format, then confirm current plan limits before upload.</p>
                <button type="button" onClick={downloadTemplate} className="gov-cta-secondary w-full">
                  Download CSV Template
                </button>

                {/* ── Plan usage bar (replaces raw plan/limit text) ── */}
                <UploadUsageBar
                  firmPlan={currentPlan?.firmPlan}
                  used={reportsUsedThisMonth}
                  cap={maxReportsPerMonth}
                  isSubscription={Boolean(credits?.has_active_subscription)}
                  resetLabel={resetLabel}
                  isLoading={creditsLoading}
                />

                {/* Upload limit line — kept as static reference */}
                <div className="rounded border border-neutral-200 bg-white px-3 py-2 text-xs text-neutral-800">
                  <span className="font-semibold text-neutral-900">Reviews per upload:</span>{" "}
                  {maxReviewsPerUpload ?? "Unlimited"}
                </div>
              </GovSectionCard>

              <CollapsibleCard title="Before you upload" summary="A quick checklist for a smoother first pass.">
                <ul className="list-disc space-y-1 pl-5 text-sm text-neutral-800">
                  <li>Export one CSV from your source system for a defined review period.</li>
                  <li>Include review date, rating (1-5), and comment text in the export.</li>
                  <li>Use the template if your source export needs column cleanup before upload.</li>
                  <li>Review the detected columns here before starting analysis.</li>
                </ul>
              </CollapsibleCard>

              <CollapsibleCard title="Recent cycles" summary="Open the latest report packets if you need to continue an earlier cycle first.">
                <div className="space-y-2">
                  {recentReports.length === 0 ? (
                    <p className="rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700">
                      No recent cycles yet. Your first completed upload will appear here.
                    </p>
                  ) : (
                    recentReports.map((report) => (
                      <Link
                        key={report.id}
                        to={`/dashboard/reports/${report.id}`}
                        className="flex items-center justify-between rounded border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-800 hover:bg-neutral-50"
                      >
                        <span className="truncate pr-3">{report.name}</span>
                        <span className="text-xs text-neutral-700">{report.created_at ? new Date(report.created_at).toLocaleDateString() : "--"}</span>
                      </Link>
                    ))
                  )}
                </div>
              </CollapsibleCard>

              <CollapsibleCard title="Accepted structure" summary="Required fields, current limits, and version boundaries.">
                <ul className="list-disc space-y-1 pl-5 text-sm text-neutral-800">
                  <li>Required: Review date, Rating (1-5), Client comment.</li>
                  <li>Maximum file size: 10 MB.</li>
                  <li>Current plan upload limit: {maxReviewsPerUpload ?? "Unlimited"} valid reviews per upload.</li>
                  <li>Current plan monthly report limit: {maxReportsPerMonth ?? "Unlimited"} reports.</li>
                  <li>Clarion matches common header names automatically, but there is no manual column-mapping flow in this version.</li>
                  {!isPaidPlan && <li>PDF export: preview mode with watermark on Free plan.</li>}
                </ul>
              </CollapsibleCard>
            </aside>
          </div>
        </div>
      </section>
  );
};

export default Upload;

