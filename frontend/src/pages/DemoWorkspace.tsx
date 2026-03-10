import { Link } from "react-router-dom";
import { Download, FileText } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { defaultSampleReportId, sampleReports, sampleReportDetails } from "@/data/sampleFirmData";

const formatDate = (value: string) => {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric" });
};

const DemoWorkspace = () => {
  const report = sampleReportDetails[defaultSampleReportId];

  if (!report) {
    return (
      <PageLayout>
        <section className="section-container section-padding">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h1 className="text-2xl font-bold text-slate-900">Demo workspace unavailable</h1>
            <p className="mt-2 text-sm text-slate-600">The demo data is temporarily unavailable.</p>
            <div className="mt-4 flex gap-2">
              <Link to="/" className="gov-btn-secondary">
                Back to Home
              </Link>
              <Link to="/signup" className="gov-btn-primary">
                Start your workspace
              </Link>
            </div>
          </article>
        </section>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-4">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Read-Only Demo Mode
          </p>
          <h1 className="marketing-hero-title">Review one example cycle before you upload your own feedback</h1>
          <p className="max-w-3xl marketing-hero-body">
            This is a read-only example cycle using sample law-firm data. It mirrors the same workflow surfaces used in
            the live product, but nothing here writes to your real workspace.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={`/demo/reports/${defaultSampleReportId}`} className="gov-btn-primary">
              Open example report
            </Link>
            <Link to="/signup" className="gov-btn-secondary">
              Start real workspace
            </Link>
          </div>
        </div>
      </section>

      <section className="section-container section-padding space-y-6">
        <article className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 shadow-sm">
          <p className="font-semibold">You are viewing one example cycle with sample data in read-only mode.</p>
          <p className="mt-1">
            Use it to see what one completed upload turns into: recurring client issues, assigned actions, and a
            governance brief. Uploads and live changes happen only in a real workspace.
          </p>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Example cycle map</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">See the full workflow before you prepare your CSV.</h2>
              <p className="mt-1 max-w-2xl text-sm text-slate-600">
                This example shows the same sequence your live workspace will follow after upload: overview, client
                issues, owner follow-through, and the final governance brief.
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 md:grid-cols-3">
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="gov-type-eyebrow">Step 1</p>
              <h3 className="mt-2 text-base font-semibold text-slate-900">Overview posture</h3>
              <p className="mt-2 text-sm text-slate-600">
                See how one review cycle is summarized once feedback has been processed.
              </p>
            </article>
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="gov-type-eyebrow">Step 2</p>
              <h3 className="mt-2 text-base font-semibold text-slate-900">Issue and action detail</h3>
              <p className="mt-2 text-sm text-slate-600">
                Open the example report to inspect recurring client issues, movement over time, and assigned follow-through.
              </p>
              <Link
                to={`/demo/reports/${defaultSampleReportId}`}
                className="mt-3 inline-flex text-sm font-medium text-slate-900 underline underline-offset-4"
              >
                Open example report
              </Link>
            </article>
            <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="gov-type-eyebrow">Step 3</p>
              <h3 className="mt-2 text-base font-semibold text-slate-900">Leadership brief output</h3>
              <p className="mt-2 text-sm text-slate-600">
                Open the example governance brief to see the partner-ready output produced from that cycle.
              </p>
              <Link
                to={`/demo/reports/${defaultSampleReportId}/pdf`}
                className="mt-3 inline-flex text-sm font-medium text-slate-900 underline underline-offset-4"
              >
                Open example brief
              </Link>
            </article>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Workspace overview</p>
              <h2 className="mt-1 text-xl font-semibold text-slate-900">Firm Governance Status</h2>
              <p className="mt-1 text-sm text-slate-600">Review period: January - March 2026</p>
            </div>
            <span className="inline-flex rounded-full border border-amber-300 bg-amber-100 px-3 py-1 text-sm font-semibold text-amber-800">
              Moderate Exposure
            </span>
          </div>

          <div className="mt-4 grid gap-3 sm:grid-cols-3 lg:grid-cols-6">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Reviews</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{report.totalReviews}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Client Issues</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{report.atRiskSignals}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Open Actions</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">5</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Overdue</p>
              <p className="mt-1 text-2xl font-semibold text-red-600">1</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Avg Rating</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{report.avgRating.toFixed(2)}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <p className="text-xs uppercase tracking-wide text-slate-500">Positive Share</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{report.positiveShare}%</p>
            </div>
          </div>
        </article>

        <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-slate-700" />
              <h3 className="text-lg font-semibold text-slate-900">Continue through the example cycle</h3>
            </div>
            <Link
              to={`/demo/reports/${defaultSampleReportId}`}
              className="gov-btn-primary inline-flex items-center gap-2"
            >
              <FileText size={15} />
              Open example report
            </Link>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            From here, inspect one report in detail or jump straight to the brief that leadership would review.
          </p>
          <div className="mt-4">
            <Link
              to={`/demo/reports/${defaultSampleReportId}/pdf`}
              className="gov-btn-secondary inline-flex items-center gap-2"
            >
              <Download size={15} />
              Open read-only example brief
            </Link>
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[680px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="px-3 py-2 font-semibold text-slate-900">Report</th>
                  <th className="px-3 py-2 font-semibold text-slate-900">Created</th>
                  <th className="px-3 py-2 font-semibold text-slate-900">Reviews</th>
                  <th className="px-3 py-2 font-semibold text-slate-900">Avg rating</th>
                  <th className="px-3 py-2 font-semibold text-slate-900">Action</th>
                </tr>
              </thead>
              <tbody>
                {sampleReports.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="px-3 py-2 text-slate-800">{row.name}</td>
                    <td className="px-3 py-2 text-slate-600">{formatDate(row.createdAt)}</td>
                    <td className="px-3 py-2 text-slate-600">{row.totalReviews}</td>
                    <td className="px-3 py-2 text-slate-600">{row.avgRating.toFixed(2)} / 5</td>
                    <td className="px-3 py-2">
                      <Link to={`/demo/reports/${row.id}`} className="gov-btn-secondary">
                        Open example report
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <div className="supporting-cta-strip">
          <p className="text-sm text-slate-600">
            If the example cycle matches what you need, move from proof to a live workspace when you are ready.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link to="/signup" className="gov-btn-primary">
              Start real workspace
            </Link>
            <Link to="/pricing" className="gov-btn-secondary">
              See plans
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default DemoWorkspace;
