import { useCallback, useEffect, useMemo, useState, type ChangeEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Download, Eye, RefreshCcw } from "lucide-react";
import { toast } from "sonner";

import {
  deleteAccountBrandingLogo,
  getAccountBranding,
  getReportDetail,
  getReports,
  updateAccountBrandingTheme,
  updateAccountProfile,
  uploadAccountBrandingLogo,
  type AccountBranding,
  type ReportDetail,
  type ReportListItem,
} from "@/api/authService";
import PdfDeckPreview from "@/components/pdf/PdfDeckPreview";
import { useAuth } from "@/contexts/AuthContext";
import { resolvePlanLimits } from "@/config/planLimits";
import { formatApiDate, toApiTimestamp } from "@/lib/dateTime";

const DashboardPdfPreview = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { user, currentPlan, refreshUser } = useAuth();
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [selectedReportId, setSelectedReportId] = useState<number | null>(null);
  const [reportDetails, setReportDetails] = useState<Record<number, ReportDetail>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [branding, setBranding] = useState<AccountBranding | null>(null);
  const [brandingLoading, setBrandingLoading] = useState(true);
  const [isUploadingPreviewLogo, setIsUploadingPreviewLogo] = useState(false);
  const [isRemovingLogo, setIsRemovingLogo] = useState(false);
  const [isSavingTheme, setIsSavingTheme] = useState(false);
  const [firmNameDraft, setFirmNameDraft] = useState("");
  const [isSavingFirmName, setIsSavingFirmName] = useState(false);
  const [isActualPdfLoading, setIsActualPdfLoading] = useState(false);
  const [actualPdfObjectUrl, setActualPdfObjectUrl] = useState<string | null>(null);
  const [actualPdfPreviewError, setActualPdfPreviewError] = useState("");
  const preferredReportId = useMemo(() => {
    const raw = Number(searchParams.get("reportId"));
    return Number.isFinite(raw) && raw > 0 ? raw : null;
  }, [searchParams]);

  useEffect(() => {
    let active = true;

    const loadInitial = async () => {
      setLoading(true);
      const [reportsResult, brandingResult] = await Promise.all([getReports(100), getAccountBranding()]);
      if (!active) return;

      if (reportsResult.success && reportsResult.reports) {
        const sortedReady = reportsResult.reports
          .filter((report) => report.status === "ready")
          .sort((a, b) => (toApiTimestamp(b.created_at) || 0) - (toApiTimestamp(a.created_at) || 0));

        setReports(sortedReady);
        setSelectedReportId((previous) => {
          if (previous && sortedReady.some((report) => report.id === previous)) return previous;
          if (preferredReportId && sortedReady.some((report) => report.id === preferredReportId)) return preferredReportId;
          return sortedReady[0]?.id ?? null;
        });
        setError("");
      } else {
        setReports([]);
        setSelectedReportId(null);
        setError(reportsResult.error || "Unable to load reports for governance brief preview.");
      }

      if (brandingResult.success && brandingResult.branding) {
        setBranding(brandingResult.branding);
      }

      setBrandingLoading(false);
      setLoading(false);
    };

    void loadInitial();
    return () => {
      active = false;
    };
  }, [preferredReportId]);

  useEffect(() => {
    setFirmNameDraft(user?.firm_name?.trim() || "");
  }, [user?.firm_name]);

  useEffect(() => {
    if (!selectedReportId || reportDetails[selectedReportId]) return;
    let active = true;

    const loadDetail = async () => {
      const result = await getReportDetail(selectedReportId);
      if (!active) return;
      if (!result.success || !result.report) {
        toast.error(result.error || "Unable to load the selected report.");
        return;
      }
      setReportDetails((previous) => ({
        ...previous,
        [result.report!.id]: result.report!,
      }));
    };

    void loadDetail();
    return () => {
      active = false;
    };
  }, [reportDetails, selectedReportId]);

  const selectedReport = useMemo(
    () => reports.find((report) => report.id === selectedReportId) || null,
    [reports, selectedReportId],
  );

  const previewDetail = selectedReport ? reportDetails[selectedReport.id] : undefined;

  const loadActualPdfPreview = useCallback(async (report: ReportListItem | null) => {
    if (!report?.download_pdf_url) {
      setActualPdfObjectUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return null;
      });
      setActualPdfPreviewError("This report does not currently have a downloadable governance brief.");
      return;
    }

    setIsActualPdfLoading(true);
    setActualPdfPreviewError("");

    try {
      const response = await fetch(report.download_pdf_url, {
        method: "GET",
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Failed to load PDF preview (${response.status}).`);
      }

      const blob = await response.blob();
      if (!blob || blob.size === 0) {
        throw new Error("PDF preview returned an empty file.");
      }

      const nextUrl = URL.createObjectURL(blob);
      setActualPdfObjectUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return nextUrl;
      });
    } catch (loadError) {
      console.error("[DashboardPdfPreview] Unable to load PDF preview blob:", loadError);
      setActualPdfObjectUrl((previous) => {
        if (previous) URL.revokeObjectURL(previous);
        return null;
      });
      setActualPdfPreviewError(
        "Clarion could not render the embedded brief preview. Download the PDF to verify the final file.",
      );
    } finally {
      setIsActualPdfLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadActualPdfPreview(selectedReport);
  }, [loadActualPdfPreview, selectedReport]);

  useEffect(() => {
    return () => {
      if (actualPdfObjectUrl) {
        URL.revokeObjectURL(actualPdfObjectUrl);
      }
    };
  }, [actualPdfObjectUrl]);

  const handlePreviewLogoUpload = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      toast.error("Please upload a PNG, JPG, or SVG logo file.");
      event.target.value = "";
      return;
    }

    setIsUploadingPreviewLogo(true);
    const result = await uploadAccountBrandingLogo(file);

    if (result.success && result.branding) {
      setBranding(result.branding);
      toast.success("Logo updated. New governance brief PDFs will use this branding.");
      void loadActualPdfPreview(selectedReport);
    } else {
      toast.error(result.error || "Unable to upload logo.");
    }

    setIsUploadingPreviewLogo(false);
    event.target.value = "";
  };

  const handleLogoRemove = async () => {
    if (!branding?.hasLogo || isRemovingLogo) return;

    setIsRemovingLogo(true);
    const result = await deleteAccountBrandingLogo();

    if (result.success && result.branding) {
      setBranding(result.branding);
      toast.success("Logo removed. Governance briefs now use firm-name text branding.");
      void loadActualPdfPreview(selectedReport);
    } else {
      toast.error(result.error || "Unable to remove logo.");
    }

    setIsRemovingLogo(false);
  };

  const handleThemeChange = async (themeId: string) => {
    if (!branding || isSavingTheme || branding.accentTheme === themeId) return;

    setIsSavingTheme(true);
    const result = await updateAccountBrandingTheme(themeId);

    if (result.success && result.branding) {
      setBranding(result.branding);
      toast.success("Governance brief accent theme updated.");
      void loadActualPdfPreview(selectedReport);
    } else {
      toast.error(result.error || "Unable to update accent theme.");
    }

    setIsSavingTheme(false);
  };

  const handleSaveFirmName = async () => {
    const nextFirmName = firmNameDraft.trim();
    if (nextFirmName.length < 2 || nextFirmName.length > 120) {
      toast.error("Firm name must be 2-120 characters.");
      return;
    }
    if (nextFirmName === (user?.firm_name || "").trim()) return;

    setIsSavingFirmName(true);
    const result = await updateAccountProfile({ firm_name: nextFirmName });

    if (result.success) {
      await refreshUser();
      toast.success("Firm name updated. Preview and downloaded briefs are now aligned.");
      void loadActualPdfPreview(selectedReport);
    } else {
      toast.error(result.error || "Unable to update firm name.");
    }

    setIsSavingFirmName(false);
  };

  const savedFirmName = (user?.firm_name || "").trim();
  const hasFirmNameChanges = firmNameDraft.trim() !== savedFirmName;
  const previewLogoUrl = useMemo(() => {
    if (!branding?.logoUrl) return null;
    const version = branding.logoUpdatedAt ? Date.parse(branding.logoUpdatedAt) || Date.now() : Date.now();
    return `${branding.logoUrl}?v=${version}`;
  }, [branding?.logoUpdatedAt, branding?.logoUrl]);
  const pdfWatermarked = resolvePlanLimits(currentPlan).pdfWatermark;

  const reportDateLabel = useMemo(
    () =>
      selectedReport
        ? formatApiDate(selectedReport.created_at, { month: "long", day: "numeric", year: "numeric" }, "No date")
        : "No report selected",
    [selectedReport],
  );

  const topThemeLabel = useMemo(() => {
    const theme = previewDetail?.themes?.[0];
    if (!theme) return "Not available yet";
    return `${theme.name}${typeof theme.mentions === "number" ? ` (${theme.mentions})` : ""}`;
  }, [previewDetail?.themes]);

  return (
      <section className="gov-page">
        <div className="stage-sequence mx-auto w-full max-w-[1200px] space-y-6">
          <header className="rounded-[24px] border border-[#E2E8F0] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-6 shadow-[0_18px_50px_rgba(15,23,42,0.06)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="max-w-3xl">
                <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Governance Brief Preparation
                </p>
                <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">
                  Prepare the brief leadership will review.
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                  Align the firm logo, accent treatment, and final PDF presentation before you print, download, or
                  circulate the governance brief. This page changes presentation only. Report findings and action
                  content stay tied to the selected report.
                </p>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">Logo upload</span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">
                    {branding?.themeOptions?.length ?? 3} accent themes
                  </span>
                  <span className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1">Preview before print</span>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Link to="/dashboard/reports" className="gov-btn-secondary px-3 py-1.5 text-xs">
                  Back to briefs
                </Link>
                {selectedReport ? (
                  <button
                    type="button"
                    onClick={() => navigate(`/dashboard/reports/${selectedReport.id}`)}
                    className="gov-btn-secondary px-3 py-1.5 text-xs"
                  >
                    Open report detail
                  </button>
                ) : null}
              </div>
            </div>
          </header>

          {error ? (
            <div className="rounded-xl border border-destructive/35 bg-destructive/10 p-4 text-sm text-destructive">
              {error}
            </div>
          ) : null}

          {loading ? (
            <section className="gov-level-2 rounded-2xl p-5">
              <p className="text-sm text-muted-foreground">Loading governance brief preview...</p>
            </section>
          ) : reports.length === 0 ? (
            <section className="gov-level-2 rounded-2xl p-6">
              <h2 className="text-lg font-semibold text-slate-900">No governance brief is ready yet</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                Upload a client feedback CSV and let Clarion generate a report first. Once a report is ready, you can
                review the brief layout, branding, and final PDF here.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Link to="/upload" className="gov-btn-primary px-3 py-1.5 text-xs">
                  Upload your first CSV
                </Link>
                <Link to="/demo/reports/26/pdf" className="gov-btn-secondary px-3 py-1.5 text-xs">
                  Open read-only demo brief
                </Link>
              </div>
            </section>
          ) : (
            <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
              <aside className="space-y-4 rounded-[24px] border border-[#E2E8F0] bg-white p-5 shadow-[0_16px_40px_rgba(15,23,42,0.05)]">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Brief controls</p>
                  <h2 className="mt-2 text-lg font-semibold text-slate-950">Branding and preview preparation</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    These settings control the visible brief presentation only: firm name, logo, and accent theme.
                    They do not rewrite report findings or action recommendations.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <label
                    htmlFor="pdf-preview-report"
                    className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500"
                  >
                    Choose the brief to prepare
                  </label>
                  <select
                    id="pdf-preview-report"
                    value={selectedReportId ?? ""}
                    onChange={(event) => setSelectedReportId(Number(event.target.value) || null)}
                    className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/25"
                  >
                    {reports.map((report) => (
                      <option key={report.id} value={report.id}>
                        {report.name}
                      </option>
                    ))}
                  </select>

                  {selectedReport ? (
                    <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
                      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Generated</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{reportDateLabel}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">Reviews</p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{selectedReport.total_reviews || 0}</p>
                      </div>
                      <div className="rounded-xl border border-slate-200 bg-white px-3 py-2">
                        <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                          Top client issue
                        </p>
                        <p className="mt-1 text-sm font-medium text-slate-900">{topThemeLabel}</p>
                      </div>
                    </div>
                  ) : null}
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <label className="block text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                    Firm identity
                  </label>
                  <input
                    type="text"
                    value={firmNameDraft}
                    onChange={(event) => setFirmNameDraft(event.target.value)}
                    className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/25"
                    placeholder="Firm name"
                    maxLength={120}
                  />
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <button
                      type="button"
                      onClick={() => void handleSaveFirmName()}
                      disabled={isSavingFirmName || !hasFirmNameChanges}
                      className="gov-btn-primary px-3 py-1.5 text-xs disabled:opacity-50"
                    >
                      {isSavingFirmName ? "Saving..." : "Save firm name"}
                    </button>
                    {hasFirmNameChanges ? (
                      <p className="text-[11px] text-slate-500">Save to sync the preview header and downloaded PDF.</p>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Firm logo</p>
                  {previewLogoUrl ? (
                    <div className="mt-3 flex h-20 items-center justify-center rounded-xl border border-slate-200 bg-white px-3">
                      <img src={previewLogoUrl} alt="Firm logo preview" className="max-h-12 max-w-full object-contain" />
                    </div>
                  ) : (
                    <div className="mt-3 flex h-20 items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white text-xs text-slate-500">
                      No logo uploaded
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-2">
                    <label className="gov-btn-secondary cursor-pointer px-3 py-1.5 text-xs">
                      {isUploadingPreviewLogo ? "Uploading..." : "Upload logo"}
                      <input
                        type="file"
                        accept=".png,.jpg,.jpeg,.svg,image/png,image/jpeg,image/svg+xml"
                        className="hidden"
                        onChange={(event) => void handlePreviewLogoUpload(event)}
                        disabled={isUploadingPreviewLogo}
                      />
                    </label>
                    {branding?.hasLogo ? (
                      <button
                        type="button"
                        className="gov-btn-secondary px-3 py-1.5 text-xs"
                        onClick={() => void handleLogoRemove()}
                        disabled={isRemovingLogo}
                      >
                        {isRemovingLogo ? "Removing..." : "Remove logo"}
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Accent treatment</p>
                  <p className="mt-2 text-xs leading-5 text-slate-600">
                    Choose the color treatment used across the governance brief cover, highlights, and section accents.
                  </p>
                  <div className="mt-3 space-y-2">
                    {branding?.themeOptions?.map((option) => {
                      const active = branding.accentTheme === option.id;
                      return (
                        <button
                          key={option.id}
                          type="button"
                          disabled={isSavingTheme}
                          onClick={() => void handleThemeChange(option.id)}
                          className={`w-full rounded-xl border px-3 py-2 text-left text-xs transition ${
                            active
                              ? "border-amber-300 bg-amber-50 text-slate-900"
                              : "border-slate-200 bg-white text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          <span className="flex items-center justify-between gap-2">
                            <span>{option.label}</span>
                            <span className="flex items-center gap-1.5">
                              <span
                                className="h-2.5 w-2.5 rounded-full border border-black/20"
                                style={{ backgroundColor: option.primary_hex }}
                              />
                              <span
                                className="h-2.5 w-2.5 rounded-full border border-black/20"
                                style={{ backgroundColor: option.accent_hex }}
                              />
                            </span>
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="rounded-2xl border border-[#DBEAFE] bg-[#F8FBFF] p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#466183]">Preview notes</p>
                  <ul className="mt-2 space-y-2 text-sm leading-6 text-slate-600">
                    <li>The embedded viewer uses the same generated PDF file Clarion downloads for this report.</li>
                    <li>
                      Branding updates apply to governance brief presentation. They do not change the underlying report
                      data.
                    </li>
                    <li>
                      {brandingLoading
                        ? "Loading branding settings..."
                        : "Branding settings are saved to your account for future governance brief exports."}
                    </li>
                    <li>
                      {pdfWatermarked
                        ? "Your current plan previews the full brief with a watermark. Upgrading unlocks the same file without the watermark."
                        : "Your current plan downloads the final governance brief without a watermark."}
                    </li>
                  </ul>
                </div>
              </aside>

              <div className="space-y-5">
                <section className="rounded-[24px] border border-[#E2E8F0] bg-white p-5 shadow-[0_16px_40px_rgba(15,23,42,0.05)]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div className="max-w-2xl">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                        Final brief preview
                      </p>
                      <h2 className="mt-2 text-xl font-semibold text-slate-950">
                        Embedded view of the governance brief PDF
                      </h2>
                      <p className="mt-2 text-sm leading-6 text-slate-600">
                        Use this view to confirm hierarchy, branding, and meeting-readiness before download or print.
                        If the embed fails, the PDF itself may still download normally.
                      </p>
                      <p className="mt-2 text-xs text-slate-500">
                        {pdfWatermarked
                          ? "Free-plan downloads stay watermarked. The layout, branding, and content still reflect the real governance brief structure."
                          : "This view reflects the final governance brief file your firm can download and circulate."}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={() => void loadActualPdfPreview(selectedReport)}
                        className="gov-btn-secondary px-3 py-1.5 text-xs"
                      >
                        <RefreshCcw size={13} className="mr-1 inline-block" />
                        Refresh embedded preview
                      </button>
                      {selectedReport?.download_pdf_url ? (
                        <a href={selectedReport.download_pdf_url} className="gov-btn-primary px-3 py-1.5 text-xs">
                          <Download size={14} className="mr-1 inline-block" />
                          {pdfWatermarked ? "Preview governance brief PDF (watermarked)" : "Download governance brief PDF"}
                        </a>
                      ) : (
                        <button type="button" disabled className="gov-btn-primary px-3 py-1.5 text-xs opacity-60">
                          Download governance brief PDF
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                        <Eye size={14} />
                        Final brief preview
                      </div>
                      {isActualPdfLoading ? <p className="text-[11px] text-slate-500">Refreshing file...</p> : null}
                    </div>
                    <div className="relative h-[640px] overflow-hidden rounded-[18px] border border-slate-200 bg-white">
                      {actualPdfObjectUrl ? (
                        <iframe
                          key={actualPdfObjectUrl}
                          title="Actual PDF preview"
                          src={`${actualPdfObjectUrl}#toolbar=0&navpanes=0`}
                          className="h-full w-full"
                        />
                      ) : (
                        <div className="flex h-full flex-col items-center justify-center px-6 text-center">
                          <p className="text-sm font-medium text-slate-900">
                            {actualPdfPreviewError || "PDF preview unavailable for this report."}
                          </p>
                          <p className="mt-2 max-w-md text-sm text-slate-500">
                            Download the governance brief to inspect the file directly if the embedded viewer is not
                            available in this browser.
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                </section>

                <section className="rounded-[24px] border border-[#E2E8F0] bg-white p-5 shadow-[0_16px_40px_rgba(15,23,42,0.05)]">
                  <div className="max-w-2xl">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                      Layout reference
                    </p>
                    <h2 className="mt-2 text-xl font-semibold text-slate-950">Structure guide for the brief layout</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      This reference view helps you review hierarchy and pacing at a glance. The embedded PDF above
                      remains the source of truth for the final file.
                    </p>
                  </div>

                  <div className="mt-4">
                    <PdfDeckPreview
                      firmName={savedFirmName || "Your Firm"}
                      logoUrl={previewLogoUrl}
                      reportTitle={selectedReport?.name || "Governance Brief"}
                      generatedAt={selectedReport?.created_at}
                      avgRating={previewDetail?.avg_rating ?? previewDetail?.comparison?.overall_satisfaction.current ?? null}
                      totalReviews={selectedReport?.total_reviews}
                      positiveShare={previewDetail?.comparison?.positive_share.current ?? null}
                      atRiskSignals={previewDetail?.comparison?.at_risk_signals.current ?? null}
                      previousAvgRating={previewDetail?.comparison?.overall_satisfaction.previous ?? null}
                      previousPositiveShare={previewDetail?.comparison?.positive_share.previous ?? null}
                      previousAtRiskSignals={previewDetail?.comparison?.at_risk_signals.previous ?? null}
                      themes={(previewDetail?.themes || []).map((theme) => ({
                        name: theme.name,
                        mentions: theme.mentions,
                      }))}
                      actions={(previewDetail?.implementation_roadmap || []).map((item) => ({
                        action: item.action || `${item.theme}: ${item.kpi}`,
                        owner: item.owner || "Operations",
                        timeframe: item.timeline || "0-30 days",
                        kpi: item.kpi,
                      }))}
                      positiveComments={previewDetail?.top_praise || []}
                      negativeComments={previewDetail?.top_complaints || []}
                    />
                  </div>
                </section>
              </div>
            </section>
          )}
        </div>
      </section>
  );
};

export default DashboardPdfPreview;
