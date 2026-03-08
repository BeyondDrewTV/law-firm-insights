import { formatApiDate } from "@/lib/dateTime";

type PdfPreviewTheme = { name: string; mentions?: number };
type PdfPreviewAction = { action: string; owner: string; timeframe: string; kpi: string };

type PdfDeckPreviewProps = {
  firmName: string;
  logoUrl?: string | null;
  reportTitle: string;
  generatedAt?: string | null;
  avgRating?: number | null;
  totalReviews?: number;
  positiveShare?: number | null;
  atRiskSignals?: number | null;
  previousAvgRating?: number | null;
  previousPositiveShare?: number | null;
  previousAtRiskSignals?: number | null;
  themes?: PdfPreviewTheme[];
  actions?: PdfPreviewAction[];
  positiveComments?: string[];
  negativeComments?: string[];
  compact?: boolean;
};

const formatDate = (value?: string | null) =>
  formatApiDate(value, { month: "short", day: "numeric", year: "numeric" }, "No date");

const formatDelta = (current?: number | null, previous?: number | null, suffix = "") => {
  if (typeof current !== "number" || typeof previous !== "number") return "No previous comparison";
  const delta = current - previous;
  if (delta === 0) return `no change${suffix ? ` ${suffix}` : ""}`;
  const verb = delta > 0 ? "up" : "down";
  return `${verb} ${Math.abs(delta).toFixed(2)}${suffix} vs last report`;
};

const formatMetric = (value?: number | null, suffix = "") => {
  if (typeof value !== "number" || Number.isNaN(value)) return "--";
  return `${value.toFixed(suffix ? 0 : 2)}${suffix}`;
};

const PdfDeckPreview = ({
  firmName,
  logoUrl,
  reportTitle,
  generatedAt,
  avgRating,
  totalReviews,
  positiveShare,
  atRiskSignals,
  previousAvgRating,
  previousPositiveShare,
  previousAtRiskSignals,
  themes = [],
  actions = [],
  positiveComments = [],
  negativeComments = [],
  compact = false,
}: PdfDeckPreviewProps) => {
  const previewThemes = themes.slice(0, compact ? 3 : 5);
  const previewActions = actions.slice(0, compact ? 2 : 3);
  const positiveComment = positiveComments[0];
  const negativeComment = negativeComments[0];
  const leadTheme = previewThemes[0];
  const reviewVolume = typeof totalReviews === "number" ? `${totalReviews} review${totalReviews === 1 ? "" : "s"}` : "this review cycle";
  const summaryLines = [
    typeof avgRating === "number"
      ? `Overall satisfaction is ${avgRating.toFixed(2)} / 5 across ${reviewVolume}.`
      : `Overall satisfaction will appear here once scoring is available for ${reviewVolume}.`,
    leadTheme
      ? `${leadTheme.name} is the main client issue in this cycle${typeof leadTheme.mentions === "number" ? `, appearing ${leadTheme.mentions} times` : ""}.`
      : "Recurring client issues will appear here once the report is generated.",
    previewActions.length > 0
      ? `${previewActions.length} action ${previewActions.length === 1 ? "priority is" : "priorities are"} listed for owner follow-through in the next review cycle.`
      : "Action ownership and follow-through appear here once the implementation plan is generated.",
  ];

  return (
    <article className="overflow-hidden rounded-[24px] border border-slate-300 bg-white shadow-[0_20px_40px_rgba(15,23,42,0.06)]">
      <header className="border-b border-slate-200 bg-[linear-gradient(180deg,#f8fafc_0%,#ffffff_100%)] px-5 py-4">
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Governance brief preview</p>
            <p className="mt-1 truncate text-base font-semibold text-slate-950">{reportTitle}</p>
          </div>
          {logoUrl ? (
            <img
              src={logoUrl}
              alt="Firm logo"
              className="h-9 w-auto max-w-[110px] rounded-md border border-slate-200 bg-white px-2 py-1"
            />
          ) : null}
        </div>
        <p className="mt-2 text-xs text-slate-600">{firmName} | Generated {formatDate(generatedAt)}</p>
      </header>

      <div className="space-y-4 px-5 py-5">
        <section className="rounded-[20px] border border-slate-200 bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Leadership summary</p>
              <p className="mt-2 max-w-2xl text-sm font-medium leading-6 text-slate-900">{summaryLines[0]}</p>
            </div>
            <div className="rounded-full border border-slate-200 bg-white px-3 py-1 text-[11px] font-medium text-slate-600">
              Preview of current report structure
            </div>
          </div>
          <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-700">
            {summaryLines.slice(1).map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </section>

        <section className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Satisfaction</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">
              {typeof avgRating === "number" ? `${avgRating.toFixed(2)} / 5` : "--"}
            </p>
            <p className="text-[11px] text-slate-600">{formatDelta(avgRating, previousAvgRating)}</p>
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">Positive share</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{formatMetric(positiveShare, "%")}</p>
            <p className="text-[11px] text-slate-600">{formatDelta(positiveShare, previousPositiveShare, " pts")}</p>
          </div>
          <div className="rounded-[18px] border border-slate-200 bg-slate-50 px-4 py-3">
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-500">At-risk client issues</p>
            <p className="mt-1 text-xs text-slate-600">Patterns requiring leadership attention.</p>
            <p className="mt-1 text-lg font-semibold text-slate-950">{formatMetric(atRiskSignals)}</p>
            <p className="text-[11px] text-slate-600">{formatDelta(atRiskSignals, previousAtRiskSignals)}</p>
          </div>
        </section>

        <section className="grid gap-3 lg:grid-cols-[1fr_1.15fr]">
          <div className="rounded-[20px] border border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">Recurring client issues</p>
            <div className="mt-3 space-y-2 text-sm text-slate-900">
              {previewThemes.length > 0 ? (
                previewThemes.map((theme) => (
                  <div key={theme.name} className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
                    <span className="truncate font-medium">{theme.name}</span>
                    <span className="text-xs text-slate-500">
                      {typeof theme.mentions === "number" ? `${theme.mentions} mentions` : ""}
                    </span>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-600">Issue detail appears here once the report is generated.</p>
              )}
            </div>
          </div>
          <div className="rounded-[20px] border border-slate-200 bg-white p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">90-day governance plan</p>
            <div className="mt-3 space-y-2 text-sm">
              {previewActions.length > 0 ? (
                previewActions.map((action, index) => (
                  <div key={`${action.action}-${index}`} className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <p className="line-clamp-2 font-medium text-slate-950">{action.action}</p>
                      <span className="shrink-0 rounded-full border border-slate-200 bg-white px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.12em] text-slate-500">
                        {action.timeframe}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-600">Owner: {action.owner}</p>
                    <p className="mt-1 text-xs text-slate-600">KPI: {action.kpi}</p>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-600">Action rows appear here after roadmap generation.</p>
              )}
            </div>
          </div>
        </section>

        {!compact && (positiveComment || negativeComment) ? (
          <section className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-[20px] border border-emerald-200 bg-emerald-50/80 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-900">Representative praise</p>
              <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-800">
                {positiveComment || "No representative positive comment."}
              </p>
            </div>
            <div className="rounded-[20px] border border-rose-200 bg-rose-50/80 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-rose-900">Representative concern</p>
              <p className="mt-2 line-clamp-4 text-sm leading-6 text-slate-800">
                {negativeComment || "No representative negative comment."}
              </p>
            </div>
          </section>
        ) : null}
      </div>
    </article>
  );
};

export default PdfDeckPreview;
