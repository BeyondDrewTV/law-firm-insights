export type SampleTrendPoint = {
  label: string;
  score: number;
  reviews: number;
  createdAt: string;
};

export type SampleReportSummary = {
  id: number;
  name: string;
  createdAt: string;
  totalReviews: number;
  avgRating: number;
  status: "ready";
};

export type SampleImplementationRow = {
  theme: string;
  action: string;
  timeline: string;
  owner: string;
  kpi: string;
};

export type SampleComment = {
  sentiment: "Positive" | "Neutral" | "Negative";
  text: string;
};

export type SampleReportDetail = {
  id: number;
  name: string;
  createdAt: string;
  totalReviews: number;
  avgRating: number;
  planLabel: string;
  topTheme: string;
  topIssue: string;
  positiveShare: number;
  atRiskSignals: number;
  previousAvgRating: number;
  previousPositiveShare: number;
  previousAtRiskSignals: number;
  themes: Array<{ name: string; mentions: number }>;
  implementationRoadmap: SampleImplementationRow[];
  comments: SampleComment[];
};

export const defaultSampleReportId = 26;
export const defaultSampleBriefPath = `/demo/reports/${defaultSampleReportId}`;
export const defaultSampleBriefPdfPath = `${defaultSampleBriefPath}/pdf`;

export const sampleTrend: SampleTrendPoint[] = [
  { label: "Nov", score: 3.92, reviews: 286, createdAt: "2025-11-15T10:00:00Z" },
  { label: "Dec", score: 4.01, reviews: 312, createdAt: "2025-12-18T10:00:00Z" },
  { label: "Jan", score: 4.07, reviews: 348, createdAt: "2026-01-20T10:00:00Z" },
  { label: "Feb", score: 4.18, reviews: 462, createdAt: "2026-02-24T10:00:00Z" },
];

export const sampleReports: SampleReportSummary[] = [
  {
    id: 26,
    name: "Monthly Client Feedback Governance Brief - Feb 24 (#26)",
    createdAt: "2026-02-24T10:00:00Z",
    totalReviews: 462,
    avgRating: 4.18,
    status: "ready",
  },
  {
    id: 24,
    name: "Monthly Client Feedback Governance Brief - Jan 20 (#24)",
    createdAt: "2026-01-20T10:00:00Z",
    totalReviews: 348,
    avgRating: 4.07,
    status: "ready",
  },
  {
    id: 21,
    name: "Monthly Client Feedback Governance Brief - Dec 18 (#21)",
    createdAt: "2025-12-18T10:00:00Z",
    totalReviews: 312,
    avgRating: 4.01,
    status: "ready",
  },
];

export const sampleReportDetails: Record<number, SampleReportDetail> = {
  26: {
    id: 26,
    name: "Monthly Client Feedback Governance Brief - Feb 24 (#26)",
    createdAt: "2026-02-24T10:00:00Z",
    totalReviews: 462,
    avgRating: 4.18,
    planLabel: "Team",
    topTheme: "Communication (145)",
    topIssue: "Communication delays created uncertainty and repeated follow-up.",
    positiveShare: 84,
    atRiskSignals: 3,
    previousAvgRating: 4.07,
    previousPositiveShare: 81,
    previousAtRiskSignals: 5,
    themes: [
      { name: "Case Outcome", mentions: 173 },
      { name: "Communication", mentions: 145 },
      { name: "Professionalism", mentions: 119 },
      { name: "Legal Expertise", mentions: 111 },
      { name: "Staff Support", mentions: 85 },
    ],
    implementationRoadmap: [
      {
        theme: "Communication",
        action: "Introduce a standard weekly case status email template for active matters.",
        timeline: "0-30 days",
        owner: "Client service partner",
        kpi: "Weekly status updates sent on at least 90% of active matters.",
      },
      {
        theme: "Cost/Value",
        action: "Provide written fee estimates at intake with scope and assumption notes.",
        timeline: "31-60 days",
        owner: "Billing manager",
        kpi: "Billing surprise complaints fall by 20% in the next reporting cycle.",
      },
      {
        theme: "Responsiveness",
        action: "Set a 24-hour response SLA for client calls and emails on business days.",
        timeline: "61-90 days",
        owner: "Intake team lead",
        kpi: "Meet SLA on at least 90% of tracked client messages.",
      },
    ],
    comments: [
      {
        sentiment: "Negative",
        text: "While the legal outcome was decent, I was disappointed with communication and repeated follow-ups.",
      },
      {
        sentiment: "Positive",
        text: "Outstanding legal representation and clear explanations throughout the matter lifecycle.",
      },
      {
        sentiment: "Neutral",
        text: "Overall experience was acceptable, but billing updates could be more proactive.",
      },
    ],
  },
};
