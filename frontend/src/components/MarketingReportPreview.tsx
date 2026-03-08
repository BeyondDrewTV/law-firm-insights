import PdfDeckPreview from "@/components/pdf/PdfDeckPreview";
import { defaultSampleReportId, sampleReportDetails } from "@/data/sampleFirmData";

interface MarketingReportPreviewProps {
  compact?: boolean;
}

const MarketingReportPreview = ({ compact = true }: MarketingReportPreviewProps) => {
  const report = sampleReportDetails[defaultSampleReportId];

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
        <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-600">Demo report state</p>
        <p className="text-[11px] text-slate-500">Read-only demo with sample law-firm data. No live workspace changes happen here.</p>
      </div>
      <PdfDeckPreview
        compact={compact}
        firmName="Clarion Sample Firm"
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
    </div>
  );
};

export default MarketingReportPreview;
