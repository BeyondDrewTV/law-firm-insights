import { Link, useParams } from "react-router-dom";
import { Download } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { defaultSampleReportId, sampleReportDetails } from "@/data/sampleFirmData";

const formatSigned = (value: number, suffix = "") => `${value >= 0 ? "+" : "-"}${Math.abs(value).toFixed(2)}${suffix}`;

const DemoReportDetail = () => {
  const { id } = useParams();
  const requestedId = Number(id);
  const reportId = Number.isFinite(requestedId) && requestedId > 0 ? requestedId : defaultSampleReportId;
  const report = sampleReportDetails[reportId];

  if (!report) {
    return (
      <PageLayout>
        <section className="section-container section-padding">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="gov-badge gov-badge-watch mb-3">Read-Only Demo Mode</p>
            <h1 className="text-2xl font-bold text-slate-900">Demo report unavailable</h1>
            <p className="mt-2 text-sm text-slate-600">This demo report could not be loaded.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/demo" className="gov-btn-secondary">
                Back to read-only demo
              </Link>
              <Link to="/signup" className="gov-btn-primary">
                Start real workspace
              </Link>
            </div>
          </article>
        </section>
      </PageLayout>
    );
  }

  const ratingDelta = report.avgRating - report.previousAvgRating;
  const positiveDelta = report.positiveShare - report.previousPositiveShare;
  const atRiskDelta = report.atRiskSignals - report.previousAtRiskSignals;

  return (
    <PageLayout>
      <section className="section-container section-padding space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="gov-badge gov-badge-watch mb-3">Read-Only Demo Mode</p>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Example cycle report</p>
              <h1 className="text-3xl font-bold text-slate-900">{report.name}</h1>
              <p className="mt-1 text-sm text-slate-600">
                Sample law-firm data for evaluation. This page shows what one completed cycle turns into once feedback
                has been grouped into client issues and follow-through.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link to="/demo" className="gov-btn-secondary">
                Back to example cycle
              </Link>
              <Link to={`/demo/reports/${report.id}/pdf`} className="gov-btn-primary inline-flex items-center gap-2">
                <Download size={15} /> Open read-only example brief
              </Link>
            </div>
          </div>
        </div>

        <section className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 shadow-sm">
          <p className="font-semibold">This report is part of the read-only example cycle, not your live workspace.</p>
          <p className="mt-1">
            Use it to inspect the structure, language, and action workflow. Start a real workspace to upload your own
            feedback and generate live reports.
          </p>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Review Count</p>
            <p className="mt-1 text-3xl font-bold text-slate-900">{report.totalReviews}</p>
            <p className="mt-1 text-xs text-slate-600">Records included in this snapshot.</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Overall Sentiment</p>
            <p className="mt-1 text-2xl font-bold text-slate-900">{report.avgRating.toFixed(2)} / 5</p>
            <p className="mt-1 text-xs text-slate-600">Current cycle rating.</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Top Theme</p>
            <p className="mt-1 text-sm font-semibold text-slate-900">{report.topTheme}</p>
            <p className="mt-1 text-xs text-slate-600">Most recurring issue area.</p>
          </article>
          <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <p className="text-xs uppercase tracking-wide text-slate-500">Top Issue</p>
            <p className="mt-1 line-clamp-2 text-sm font-semibold text-slate-900">{report.topIssue}</p>
            <p className="mt-1 text-xs text-slate-600">Most cited complaint summary.</p>
          </article>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">Cycle movement at a glance</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Overall satisfaction</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{formatSigned(ratingDelta)}</p>
              <p className="mt-1 text-sm text-slate-600">
                Current: {report.avgRating.toFixed(2)} / 5 vs {report.previousAvgRating.toFixed(2)} previously.
              </p>
            </article>
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">Positive share</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">{formatSigned(positiveDelta, " pts")}</p>
              <p className="mt-1 text-sm text-slate-600">
                Current: {report.positiveShare}% vs {report.previousPositiveShare}% previously.
              </p>
            </article>
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-xs uppercase tracking-wide text-slate-500">At-risk client issues</p>
              <p className="mt-2 text-2xl font-semibold text-slate-900">
                {atRiskDelta > 0 ? `+${atRiskDelta}` : `${atRiskDelta}`}
              </p>
              <p className="mt-1 text-sm text-slate-600">
                Current: {report.atRiskSignals} vs {report.previousAtRiskSignals} in the previous cycle.
              </p>
            </article>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">90-Day Implementation Plan (Read-only)</h3>
              <p className="text-sm text-slate-600">Theme-based actions with owners and success metrics.</p>
            </div>
            <button type="button" className="gov-btn-secondary cursor-not-allowed opacity-70" disabled>
              Add action item (read-only demo)
            </button>
          </div>
          <div className="mt-4 space-y-2">
            {report.implementationRoadmap.map((item) => (
              <article key={`${item.theme}-${item.timeline}`} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-900">{item.action}</p>
                <p className="mt-1 text-xs text-slate-600">Theme: {item.theme}</p>
                <p className="mt-2 text-sm text-slate-700">
                  {item.timeline} - Owner: {item.owner}
                </p>
                <p className="mt-1 text-sm text-slate-600">Success metric: {item.kpi}</p>
              </article>
            ))}
          </div>
        </section>
      </section>
    </PageLayout>
  );
};

export default DemoReportDetail;
