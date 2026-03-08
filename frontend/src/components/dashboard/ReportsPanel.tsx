import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight, Download, MoreHorizontal, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { deleteReport, type ReportDetail, type ReportListItem } from "@/api/authService";
import { formatApiDateTime, toApiTimestamp } from "@/lib/dateTime";
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

interface ReportsPanelProps {
  reports: ReportListItem[];
  isLoading: boolean;
  error?: string;
  pendingReportId?: number | null;
  maxRows?: number;
  showViewAll?: boolean;
  onReportDeleted?: (reportId: number) => void;
  matterLabels?: Record<number, string>;
  onMatterLabelChange?: (reportId: number, label: string) => void;
  showHeader?: boolean;
  atRiskReportIds?: Set<number>;
  reportDetailsById?: Record<number, ReportDetail>;
}

const statusClassMap: Record<string, string> = {
  processing: "gov-chip-warn",
  ready: "gov-chip-muted",
  failed: "gov-chip-risk",
};

const formatDateTime = (value: string) => formatApiDateTime(value, undefined, value);

const ReportsPanel = ({
  reports,
  isLoading,
  error,
  pendingReportId = null,
  maxRows,
  showViewAll = true,
  onReportDeleted,
  matterLabels = {},
  onMatterLabelChange,
  showHeader = true,
  atRiskReportIds = new Set<number>(),
  reportDetailsById = {},
}: ReportsPanelProps) => {
  const navigate = useNavigate();
  const [localStatusFilter, setLocalStatusFilter] = useState<"all" | "processing" | "ready" | "failed">("all");
  const [localSearch, setLocalSearch] = useState("");
  const [sortField, setSortField] = useState<"name" | "matter" | "status" | "created_at" | "reviews">("created_at");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");
  const [deleteTarget, setDeleteTarget] = useState<ReportListItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [openRowMenuId, setOpenRowMenuId] = useState<number | null>(null);

  const deleteTargetRequiresUpgrade = !!deleteTarget && deleteTarget.plan_type === "free";
  const hasAnyReports = reports.length > 0;

  useEffect(() => {
    const handleClickOutside = () => setOpenRowMenuId(null);
    if (openRowMenuId === null) return undefined;
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [openRowMenuId]);

  const displayedReports = useMemo(
    () => (typeof maxRows === "number" ? reports.slice(0, maxRows) : reports),
    [maxRows, reports],
  );

  const normalizedSearch = localSearch.trim().toLowerCase();

  const filteredAndSortedReports = useMemo(() => {
    const effectiveStatusFilter = showHeader ? localStatusFilter : "all";
    const effectiveSearch = showHeader ? normalizedSearch : "";

    const filtered = displayedReports.filter((report) => {
      const status = report.id === pendingReportId ? "processing" : report.status;
      if (effectiveStatusFilter !== "all" && status !== effectiveStatusFilter) return false;
      if (!effectiveSearch) return true;
      const matterLabel = (matterLabels[report.id] || "").toLowerCase();
      return `${report.name} ${report.plan_label} ${matterLabel}`.toLowerCase().includes(effectiveSearch);
    });

    const sorted = [...filtered].sort((a, b) => {
      const aStatus = a.id === pendingReportId ? "processing" : a.status;
      const bStatus = b.id === pendingReportId ? "processing" : b.status;
      const aMatter = (matterLabels[a.id] || "").toLowerCase();
      const bMatter = (matterLabels[b.id] || "").toLowerCase();

      if (sortField === "name") return a.name.localeCompare(b.name);
      if (sortField === "matter") return aMatter.localeCompare(bMatter);
      if (sortField === "status") {
        const rank = { processing: 0, failed: 1, ready: 2 };
        return rank[aStatus] - rank[bStatus];
      }
      if (sortField === "reviews") return a.total_reviews - b.total_reviews;
      return (toApiTimestamp(a.created_at) || 0) - (toApiTimestamp(b.created_at) || 0);
    });

    return sortDirection === "desc" ? sorted.reverse() : sorted;
  }, [
    displayedReports,
    localStatusFilter,
    matterLabels,
    normalizedSearch,
    pendingReportId,
    showHeader,
    sortDirection,
    sortField,
  ]);

  const latestReportId = useMemo(() => {
    if (!reports.length) return null;
    return [...reports].sort((a, b) => (toApiTimestamp(b.created_at) || 0) - (toApiTimestamp(a.created_at) || 0))[0]?.id ?? null;
  }, [reports]);

  const knownMatterOptions = useMemo(
    () =>
      Array.from(
        new Set(
          Object.values(matterLabels)
            .map((value) => value.trim())
            .filter(Boolean),
        ),
      ).sort((a, b) => a.localeCompare(b)),
    [matterLabels],
  );

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    const result = await deleteReport(deleteTarget.id);
    if (result.success) {
      onReportDeleted?.(deleteTarget.id);
      toast.success(
        deleteTargetRequiresUpgrade
          ? "Report moved to Recently Deleted. Free workspaces cannot restore unless paid restore access is added within 30 days."
          : "Report moved to Recently Deleted. This workspace can restore it for up to 30 days, subject to plan history rules.",
      );
      setDeleteTarget(null);
    } else {
      toast.error(result.error || "We couldn't delete this report. Please try again.");
    }
    setIsDeleting(false);
  };

  const toggleSort = (field: "name" | "matter" | "status" | "created_at" | "reviews") => {
    if (sortField === field) {
      setSortDirection((previous) => (previous === "asc" ? "desc" : "asc"));
      return;
    }
    setSortField(field);
    setSortDirection(field === "name" || field === "matter" ? "asc" : "desc");
  };

  return (
    <>
      <section className="gov-level-2 p-6">
        {showHeader && (
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="gov-h2">Reports</h2>
              <p className="text-sm text-neutral-700">Generated outputs with status, preview, and export actions.</p>
            </div>
            {showViewAll && (
              <Link to="/dashboard/reports" className="gov-cta-secondary">
                View all reports
              </Link>
            )}
          </div>
        )}

        {error && <div className="mb-4 text-sm text-destructive">{error}</div>}

        {showHeader && (
          <div className="mb-4 grid gap-3 md:grid-cols-[1fr_auto]">
            <div className="flex flex-wrap gap-2">
              {(["all", "ready", "processing", "failed"] as const).map((status) => (
                <button
                  key={status}
                  type="button"
                  onClick={() => setLocalStatusFilter(status)}
                  className={`${localStatusFilter === status ? "gov-chip-warn" : "gov-chip-muted"}`}
                >
                  {status === "all" ? "All" : status}
                </button>
              ))}
            </div>
            <input
              type="search"
              value={localSearch}
              onChange={(event) => setLocalSearch(event.target.value)}
              placeholder="Search report name or matter label..."
              className="h-9 rounded border border-neutral-300 bg-white px-3 text-sm text-neutral-900 placeholder:text-neutral-500 focus:outline-none focus:ring-1 focus:ring-neutral-500"
            />
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="gov-table w-full min-w-[760px] text-sm"><thead><tr><th className="py-2 pr-3 font-medium"><button type="button" className="hover:text-neutral-900" onClick={() => toggleSort("name")}>Report</button></th><th className="py-2 pr-3 font-medium"><button type="button" className="hover:text-neutral-900" onClick={() => toggleSort("status")}>Status</button></th><th className="py-2 pr-3 font-medium"><button type="button" className="hover:text-neutral-900" onClick={() => toggleSort("created_at")}>Created</button></th><th className="py-2 pr-3 font-medium"><button type="button" className="hover:text-neutral-900" onClick={() => toggleSort("reviews")}>Reviews</button></th><th className="py-2 pr-3 font-medium">Actions</th></tr></thead><tbody>{isLoading ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-neutral-700">
                    Loading reports...
                  </td>
                </tr>
              ) : filteredAndSortedReports.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-6 text-center text-neutral-700">
                    {hasAnyReports
                      ? "No reports match your filters. Try clearing filters or switching to 'All'."
                      : "No reports yet. Upload your first CSV to create your first report."}
                  </td>
                </tr>
              ) : (
                filteredAndSortedReports.map((report, index) => {
                  const status = report.id === pendingReportId ? "processing" : report.status;
                  const isLatest = latestReportId === report.id;
                  const detail = reportDetailsById[report.id];
                  const delta = detail?.comparison?.overall_satisfaction?.delta;
                  const trendIndicator = typeof delta === "number" ? (delta > 0 ? "Increase" : delta < 0 ? "Decrease" : "No change") : null;
                  const riskLabel =
                    status !== "ready" ? "Pending" : atRiskReportIds.has(report.id) ? "At-risk" : "Stable";
                  const riskClass =
                    riskLabel === "At-risk"
                      ? "gov-chip-risk"
                      : riskLabel === "Stable"
                        ? "gov-chip-muted"
                        : "gov-chip-muted";

                  return (
                    <tr
                      key={report.id}
                      className={`gov-clickable border-b border-neutral-200 last:border-0 ${
                        index % 2 === 0 ? "bg-transparent" : "bg-neutral-50/50"
                      } ${isLatest ? "bg-neutral-100/70" : ""}`}
                      onClick={() => navigate(`/dashboard/reports/${report.id}`)}
                    >
                      <td className={`py-3 pr-3 ${isLatest ? "border-l-2 border-neutral-500 pl-2" : ""}`}>
                        <div className="gov-row-clickable -mx-2 rounded-md px-2 py-1">
                          <div className="flex min-w-0 items-center gap-2">
                            <div className={`truncate text-neutral-900 ${isLatest ? "font-semibold" : "font-medium"}`}>
                              {report.name}
                            </div>
                            {isLatest && <span className="gov-chip-muted">Latest</span>}
                          </div>
                          <span className="gov-row-chevron" aria-hidden="true">
                            <ChevronRight size={13} className="text-neutral-500" />
                          </span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-1.5">
                          <span className="text-xs text-neutral-700">{report.plan_label}</span>
                          <span className={riskClass}>{riskLabel}</span>
                          {trendIndicator && <span className="gov-chip-muted">Trend {trendIndicator}</span>}
                        </div>
                      </td>

                      <td className="py-3 pr-3">
                        <span className={statusClassMap[status] || statusClassMap.ready}>
                          {status.charAt(0).toUpperCase() + status.slice(1)}
                        </span>
                      </td>
                      <td className="py-3 pr-3 text-neutral-700">{formatDateTime(report.created_at)}</td>
                      <td className="py-3 pr-3 text-neutral-900">{report.total_reviews}</td>
                      <td className="py-3 pr-3">
                        <div className="relative flex flex-wrap items-center gap-2">
                          <a href={report.download_pdf_url} className="gov-cta-secondary">
                            <Download size={14} />
                            PDF
                            <ChevronRight size={13} />
                          </a>
                          <button
                            type="button"
                            onClick={(event) => {
                              event.stopPropagation();
                              setOpenRowMenuId((prev) => (prev === report.id ? null : report.id));
                            }}
                            className="gov-cta-secondary"
                            aria-label="More actions"
                          >
                            <MoreHorizontal size={14} />
                          </button>
                          {openRowMenuId === report.id && (
                            <div
                              className="absolute right-0 top-9 z-20 min-w-[140px] rounded-md border border-neutral-200 bg-white p-1 shadow-md"
                              onClick={(event) => event.stopPropagation()}
                            >
                              <button
                                type="button"
                                className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-xs text-neutral-800 hover:bg-neutral-50"
                                onClick={() => {
                                  setDeleteTarget(report);
                                  setOpenRowMenuId(null);
                                }}
                              >
                                <Trash2 size={13} />
                                Move to deleted
                              </button>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
               )}</tbody></table>

          {knownMatterOptions.length > 0 && (
            <datalist id="matter-label-options">
              {knownMatterOptions.map((label) => (
                <option key={label} value={label} />
              ))}
            </datalist>
          )}
        </div>

        {!isLoading && !hasAnyReports && (
          <div className="mt-4 rounded border border-neutral-200 bg-white p-3">
            <p className="text-sm text-neutral-700">
              Your first cycle starts with a CSV upload. Reports, status, and governance brief PDFs appear here once processing finishes.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Link to="/upload" className="gov-cta-primary">
                Upload your first CSV
              </Link>
              <Link to="/dashboard" className="gov-cta-secondary">
                Return to overview
              </Link>
            </div>
            <div className="mt-3">
              <Link to="/demo" className="text-sm text-neutral-600 underline underline-offset-4 transition-colors hover:text-neutral-900">
                Open read-only example cycle
              </Link>
            </div>
          </div>
        )}
      </section>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => (!open ? setDeleteTarget(null) : null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              {deleteTargetRequiresUpgrade ? (
                <span>
                  This report will move to Recently Deleted and stay available for 30 days. Free workspaces do not have
                  restore access unless the workspace adds paid restore access before the purge date.
                  <Link to="/pricing" className="ml-1 font-medium text-primary hover:underline">
                    Upgrade to unlock recovery.
                  </Link>
                </span>
              ) : (
                "This report will move to Recently Deleted for 30 days and be removed from your active dashboard metrics."
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                void handleConfirmDelete();
              }}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Move to recently deleted"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};

export default ReportsPanel;



