import { Link, useParams } from "react-router-dom";
import PageLayout from "@/components/PageLayout";
import { defaultSampleReportId, sampleReportDetails } from "@/data/sampleFirmData";
import PdfDeckPreview from "@/components/pdf/PdfDeckPreview";

const DemoPdfPreview = () => {
  const { id } = useParams();
  const requestedId = Number(id);
  const reportId = Number.isFinite(requestedId) && requestedId > 0 ? requestedId : defaultSampleReportId;
  const report = sampleReportDetails[reportId];

  if (!report) {
    return (
      <PageLayout>
        <section className="section-container section-padding">
          <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <p className="gov-badge gov-badge-watch mb-3">Sample Workspace</p>
            <h1 className="text-2xl font-bold text-slate-900">Sample brief unavailable</h1>
            <p className="mt-2 text-sm text-slate-600">This sample brief preview could not be loaded.</p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Link to="/demo" className="gov-btn-secondary">Back to sample workspace</Link>
              <Link to="/signup" className="gov-btn-primary">Start workspace</Link>
            </div>
          </article>
        </section>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <section className="section-container section-padding space-y-6">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="gov-badge gov-badge-watch mb-3">Sample Brief</p>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">PDF view of the canonical sample artifact</p>
              <h1 className="text-3xl font-bold text-slate-900">Sample governance brief preview</h1>
              <p className="mt-1 text-sm text-slate-600">
                This is the PDF-facing view of the same sample governance brief. It uses sample law-firm data and
                shows the structure and pacing of the live governance brief, but download stays disabled in sample
                mode.
              </p>
            </div>
            <div className="flex gap-2">
              <Link to={`/demo/reports/${report.id}`} className="gov-btn-secondary">Back to sample brief</Link>
              <button type="button" className="gov-btn-secondary cursor-not-allowed opacity-70" disabled>
                Download PDF (disabled)
              </button>
            </div>
          </div>
        </div>

        <article className="rounded-2xl border border-blue-200 bg-blue-50 p-4 text-sm text-blue-950 shadow-sm">
          <p className="font-semibold">This PDF preview uses sample data and stays read-only.</p>
          <p className="mt-1">
            It is part of the sample proof layer only. The live product creates files and delivery actions only from
            your own uploaded feedback inside a live workspace.
          </p>
        </article>

        <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <PdfDeckPreview
            firmName="Sample Firm LLP"
            reportTitle={report.name}
            generatedAt={report.createdAt}
            avgRating={report.avgRating}
            totalReviews={report.totalReviews}
            positiveShare={report.positiveShare}
            atRiskSignals={report.atRiskSignals}
            previousAvgRating={report.previousAvgRating}
            previousPositiveShare={report.previousPositiveShare}
            previousAtRiskSignals={report.previousAtRiskSignals}
            themes={report.themes}
            actions={report.implementationRoadmap.map((item) => ({
              action: item.action,
              owner: item.owner,
              timeframe: item.timeline,
              kpi: item.kpi,
            }))}
            positiveComments={report.comments.filter((item) => item.sentiment === "Positive").map((item) => item.text)}
            negativeComments={report.comments.filter((item) => item.sentiment === "Negative").map((item) => item.text)}
          />
        </article>
      </section>
    </PageLayout>
  );
};

export default DemoPdfPreview;
