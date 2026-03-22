import { defaultSampleReportId, sampleReportDetails } from "@/data/sampleFirmData";
import {
  landingAccountabilityRows,
  landingPreviewIssueRows,
  landingPreviewMeetingAgenda,
} from "@/content/landingV3";

type LandingOperatingPreviewProps = {
  compact?: boolean;
  mode?: "hero" | "outputs";
};

const toneClassByLabel: Record<string, string> = {
  Watch: "border-[#D9C78C] bg-[#FFF9E8] text-[#775E1F]",
  "Needs action": "border-[#E5C6B8] bg-[#FFF2EA] text-[#8C4A33]",
  Escalate: "border-[#E3C2C2] bg-[#FFF1F1] text-[#7F2F2F]",
  "In Progress": "border-[#D9C78C] bg-[#FFF9E8] text-[#775E1F]",
  Planned: "border-[#D7D0C3] bg-[#F5F1EA] text-[#585A63]",
};

const LandingOperatingPreview = ({
  compact = false,
  mode = "hero",
}: LandingOperatingPreviewProps) => {
  const report = sampleReportDetails[defaultSampleReportId];
  const previewTitle = "Monthly client feedback governance review";
  const actions = compact ? landingAccountabilityRows.slice(0, 2) : landingAccountabilityRows;
  const issues = compact ? landingPreviewIssueRows.slice(0, 2) : landingPreviewIssueRows;

  return (
    <article className={`landing-preview-sheet ${compact ? "landing-preview-sheet-compact" : ""}`}>
      <header className="landing-preview-header">
        <div>
          <p className="landing-preview-label">Partner review brief</p>
          <h3 className="landing-preview-title">{previewTitle}</h3>
          <p className="landing-preview-subtitle">
            {report.totalReviews} reviews analyzed. Prepared for monthly partner review.
          </p>
        </div>
        <div className="landing-preview-header-badges">
          <span className="landing-preview-pill">Governance brief</span>
          <span className="landing-preview-pill">PDF and email ready</span>
        </div>
      </header>

      <div className="landing-preview-grid">
        <section className="landing-preview-panel">
          <p className="landing-preview-label">Attention now</p>
          <p className="mt-3 text-sm leading-7 text-[#1F2937]">
            Communication delays and billing confusion remain the clearest service risks. Outcome sentiment is still
            strong, but the firm is losing confidence between milestones.
          </p>
          <div className="mt-5 space-y-3">
            {issues.map((issue) => (
              <div key={issue.label} className="landing-preview-row">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold text-[#111827]">{issue.label}</p>
                  <span className={`landing-preview-chip ${toneClassByLabel[issue.tone]}`}>{issue.tone}</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-[#4B5563]">{issue.summary}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="landing-preview-panel landing-preview-panel-soft">
          <p className="landing-preview-label">Action ownership</p>
          <div className="mt-4 space-y-3">
            {actions.map((row) => (
              <div key={row.action} className="landing-preview-action-row">
                <div className="flex items-start justify-between gap-3">
                  <p className="text-sm font-semibold leading-6 text-[#111827]">{row.action}</p>
                  <span className={`landing-preview-chip ${toneClassByLabel[row.status] || toneClassByLabel.Planned}`}>
                    {row.status}
                  </span>
                </div>
                <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[#5F6470]">
                  <span>Owner: {row.owner}</span>
                  <span>Due: {row.due}</span>
                </div>
                {!compact && <p className="mt-2 text-sm leading-6 text-[#4B5563]">{row.note}</p>}
              </div>
            ))}
          </div>
        </section>
      </div>

      <footer className="landing-preview-footer">
        <div>
          <p className="landing-preview-label">Meeting agenda</p>
          <ul className="mt-3 space-y-2">
            {landingPreviewMeetingAgenda.map((point) => (
              <li key={point} className="landing-preview-bullet">
                {point}
              </li>
            ))}
          </ul>
        </div>

        {mode === "outputs" && !compact && (
          <div className="landing-preview-output-strip">
            <div>
              <p className="landing-preview-label">Use in the room</p>
              <p className="mt-2 text-sm leading-6 text-[#1F2937]">
                Bring the brief into partner review, then keep the same cycle alive in the workspace.
              </p>
            </div>
            <div className="landing-preview-output-badges">
              <span className="landing-preview-pill">Workspace</span>
              <span className="landing-preview-pill">PDF brief</span>
              <span className="landing-preview-pill">Email summary</span>
            </div>
          </div>
        )}
      </footer>
    </article>
  );
};

export default LandingOperatingPreview;
