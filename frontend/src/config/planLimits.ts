export type UiFirmPlan = "free" | "team" | "firm";

export type UiPlanLimits = {
  maxReviewsPerUpload: number | null;
  maxReportsPerMonth: number | null;
  maxUsers: number | null;
  pdfWatermark: boolean;
  historyDays?: number | null;
};

export function normalizeFirmPlan(plan?: string | null): UiFirmPlan {
  const value = (plan || "").toLowerCase();
  if (value === "team" || value === "professional") return "team";
  if (value === "firm" || value === "leadership") return "firm";
  return "free";
}

export function resolvePlanLimits(currentPlan?: {
  firmPlan?: string | null;
  planLimits?: Partial<UiPlanLimits> | null;
} | null): UiPlanLimits {
  const serverLimits = currentPlan?.planLimits;
  return {
    maxReviewsPerUpload:
      typeof serverLimits?.maxReviewsPerUpload === "number" ? serverLimits.maxReviewsPerUpload : null,
    maxReportsPerMonth:
      typeof serverLimits?.maxReportsPerMonth === "number" ? serverLimits.maxReportsPerMonth : null,
    maxUsers: typeof serverLimits?.maxUsers === "number" ? serverLimits.maxUsers : null,
    pdfWatermark: Boolean(serverLimits?.pdfWatermark),
    historyDays: typeof serverLimits?.historyDays === "number" ? serverLimits.historyDays : null,
  };
}
