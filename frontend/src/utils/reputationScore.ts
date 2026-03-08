export type ReputationIssuePercentages = {
  communication?: number | null;
  professionalism?: number | null;
  caseOutcome?: number | null;
  staffSupport?: number | null;
};

export type ReputationBreakdownItem = {
  label: "Communication" | "Professionalism" | "Case Outcomes" | "Staff Support";
  percentage: number;
  rating: "Strong" | "Moderate" | "Weak";
};

export type ReputationScoreResult = {
  score: number;
  colorClass: string;
  tier: "healthy" | "watch" | "risk";
  breakdown: ReputationBreakdownItem[];
};

const WEIGHTS: Array<{
  key: keyof ReputationIssuePercentages;
  label: ReputationBreakdownItem["label"];
  weight: number;
}> = [
  { key: "communication", label: "Communication", weight: 0.4 },
  { key: "professionalism", label: "Professionalism", weight: 0.3 },
  { key: "caseOutcome", label: "Case Outcomes", weight: 0.2 },
  { key: "staffSupport", label: "Staff Support", weight: 0.1 },
];

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value));

const toRating = (percentage: number): ReputationBreakdownItem["rating"] => {
  if (percentage >= 25) return "Weak";
  if (percentage >= 10) return "Moderate";
  return "Strong";
};

export const calculateReputationRiskScore = (
  percentages: ReputationIssuePercentages,
): ReputationScoreResult => {
  const present = WEIGHTS.filter(({ key }) => {
    const value = percentages[key];
    return typeof value === "number" && Number.isFinite(value);
  });

  if (present.length === 0) {
    return {
      score: 100,
      colorClass: "text-emerald-600",
      tier: "healthy",
      breakdown: [],
    };
  }

  const totalPresentWeight = present.reduce((sum, item) => sum + item.weight, 0);

  const weightedPenalty = present.reduce((sum, item) => {
    const raw = percentages[item.key] as number;
    const normalizedWeight = totalPresentWeight > 0 ? item.weight / totalPresentWeight : 0;
    return sum + raw * normalizedWeight;
  }, 0);

  const score = Math.round(clamp(100 - weightedPenalty, 0, 100));

  const tier = score >= 80 ? "healthy" : score >= 60 ? "watch" : "risk";
  const colorClass =
    tier === "healthy" ? "text-emerald-600" : tier === "watch" ? "text-amber-600" : "text-rose-600";

  const breakdown = present.map((item) => {
    const value = clamp(percentages[item.key] as number, 0, 100);
    return {
      label: item.label,
      percentage: Math.round(value),
      rating: toRating(value),
    };
  });

  return {
    score,
    colorClass,
    tier,
    breakdown,
  };
};
