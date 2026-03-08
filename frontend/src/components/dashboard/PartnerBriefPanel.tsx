import { DashboardCard } from "@/components/ui/card";
import ClientQuoteCard from "@/components/ClientQuoteCard";
import {
  calculateReputationRiskScore,
  type ReputationIssuePercentages,
} from "@/utils/reputationScore";
import { analyzeTrendAlerts } from "@/utils/trendAnalysis";

type PartnerBriefPanelProps = {
  reportingPeriod: string;
  overallRisk: "Low" | "Moderate" | "High";
  deltas: string[];
  topClientIssue: {
    name: string;
    percentage: number;
    context: string;
  } | null;
  issuePercentages: ReputationIssuePercentages;
  previousIssuePercentages?: ReputationIssuePercentages | null;
  exampleFeedback: string[];
  recommendedDiscussion: string;
  estimatedImpact?: string | null;
  loading?: boolean;
};

const riskBadgeClass = (risk: "Low" | "Moderate" | "High") => {
  if (risk === "High") return "border-rose-300 bg-rose-50 text-rose-800";
  if (risk === "Moderate") return "border-amber-300 bg-amber-50 text-amber-800";
  return "border-emerald-300 bg-emerald-50 text-emerald-800";
};

export default function PartnerBriefPanel({
  reportingPeriod,
  overallRisk,
  deltas,
  topClientIssue,
  issuePercentages,
  previousIssuePercentages,
  exampleFeedback,
  recommendedDiscussion,
  estimatedImpact,
  loading = false,
}: PartnerBriefPanelProps) {
  const reputationScore = calculateReputationRiskScore(issuePercentages);
  const trendAlerts = analyzeTrendAlerts(issuePercentages, previousIssuePercentages);
  const hasPreviousPeriod = Boolean(
    previousIssuePercentages &&
      Object.values(previousIssuePercentages).some((value) => typeof value === "number" && Number.isFinite(value)),
  );

  return (
    <DashboardCard
      title="CLIENT EXPERIENCE BRIEF"
      subtitle={`Current reporting period: ${reportingPeriod}`}
      className="animate-slide-up"
    >
      <div className="grid gap-6 md:grid-cols-2">
        <section className="space-y-4">
          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Overall Reputation Risk</p>
            <div className="mt-3">
              <span
                className={[
                  "inline-flex rounded-full border px-3 py-1 text-sm font-semibold",
                  riskBadgeClass(overallRisk),
                ].join(" ")}
              >
                {loading ? "Loading..." : `${overallRisk} Risk`}
              </span>
            </div>
          </div>

          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Firm Reputation Risk Score</p>
            <div className="mt-3 flex items-end gap-2">
              <span className={["text-3xl font-semibold", reputationScore.colorClass].join(" ")}>
                {loading ? "--" : reputationScore.score}
              </span>
              <span className="pb-1 text-sm text-neutral-600">/ 100</span>
            </div>
            <div className="mt-3">
              <p className="text-xs uppercase tracking-wide text-neutral-500">Breakdown</p>
              {reputationScore.breakdown.length > 0 ? (
                <ul className="mt-2 space-y-1 text-sm text-neutral-800">
                  {reputationScore.breakdown.map((item) => (
                    <li key={item.label}>
                      {item.label}: {item.rating}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-neutral-700">Insufficient data for category breakdown.</p>
              )}
            </div>
          </div>

          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">What Changed Since Last Review</p>
            <ul className="mt-3 space-y-2 text-sm text-neutral-800">
              {(loading ? [] : deltas).map((delta, index) => (
                <li key={`${delta}-${index}`} className="flex items-start gap-2">
                  <span className="mt-1 inline-block h-1.5 w-1.5 rounded-full bg-neutral-500" />
                  <span>{delta}</span>
                </li>
              ))}
              {!loading && deltas.length === 0 ? <li>No material changes detected in this cycle.</li> : null}
            </ul>
          </div>

          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Top Client Issue</p>
            {topClientIssue ? (
              <div className="mt-3">
                <p className="text-base font-semibold text-neutral-900">{topClientIssue.name}</p>
                <p className="mt-1 text-sm text-neutral-700">
                  {topClientIssue.percentage}% {topClientIssue.context}
                </p>
              </div>
            ) : (
              <p className="mt-3 text-sm text-neutral-700">No recurring issue identified yet.</p>
            )}
          </div>

          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Trend Alerts</p>
            {!hasPreviousPeriod ? (
              <p className="mt-3 text-sm text-neutral-700">No prior reporting period available.</p>
            ) : trendAlerts.length > 0 ? (
              <ul className="mt-3 space-y-2 text-sm text-neutral-800">
                {trendAlerts.map((alert) => (
                  <li key={alert.key}>{alert.message}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-neutral-700">No material trend changes since last review.</p>
            )}
          </div>
        </section>

        <section className="space-y-4">
          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Example Client Feedback</p>
            <div className="mt-3 space-y-3">
              {exampleFeedback.slice(0, 2).map((quote, index) => (
                <ClientQuoteCard
                  key={`${quote}-${index}`}
                  quote={quote}
                  issue={topClientIssue?.name || "Client Experience"}
                  sentiment="complaint"
                  meta="Anonymized client feedback excerpt"
                  className="bg-neutral-50"
                />
              ))}
              {exampleFeedback.length === 0 ? (
                <p className="text-sm text-neutral-700">No anonymized excerpts available for this cycle yet.</p>
              ) : null}
            </div>
          </div>

          <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
            <p className="text-xs uppercase tracking-wide text-neutral-500">Recommended Partner Discussion</p>
            <p className="mt-3 text-sm text-neutral-800">{recommendedDiscussion}</p>
          </div>

          {estimatedImpact ? (
            <div className="rounded-[10px] border border-[#E5E7EB] bg-white p-5">
              <p className="text-xs uppercase tracking-wide text-neutral-500">Estimated Impact if Improved</p>
              <p className="mt-3 text-sm text-neutral-800">{estimatedImpact}</p>
            </div>
          ) : null}
        </section>
      </div>
    </DashboardCard>
  );
}
