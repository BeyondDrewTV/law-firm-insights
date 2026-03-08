import type { ReputationIssuePercentages } from "@/utils/reputationScore";

export type TrendAlert = {
  key: keyof ReputationIssuePercentages;
  label: "Communication" | "Professionalism" | "Case Outcomes" | "Staff Support";
  previous: number;
  current: number;
  delta: number;
  direction: "up" | "down" | "flat";
  message: string;
};

const LABELS: Record<keyof ReputationIssuePercentages, TrendAlert["label"]> = {
  communication: "Communication",
  professionalism: "Professionalism",
  caseOutcome: "Case Outcomes",
  staffSupport: "Staff Support",
};

export const analyzeTrendAlerts = (
  current: ReputationIssuePercentages,
  previous: ReputationIssuePercentages | null | undefined,
): TrendAlert[] => {
  if (!previous) return [];

  const keys = Object.keys(LABELS) as Array<keyof ReputationIssuePercentages>;

  const alerts = keys
    .map((key) => {
      const currentValue = current[key];
      const previousValue = previous[key];
      if (typeof currentValue !== "number" || typeof previousValue !== "number") return null;
      if (!Number.isFinite(currentValue) || !Number.isFinite(previousValue)) return null;

      const delta = Math.round(currentValue - previousValue);
      const direction = delta > 0 ? "up" : delta < 0 ? "down" : "flat";
      const verb =
        direction === "up" ? "increased" : direction === "down" ? "decreased" : "remained unchanged";
      const message =
        direction === "flat"
          ? `${LABELS[key]} complaints remained unchanged at ${currentValue}% since last review.`
          : `${LABELS[key]} complaints ${verb} from ${previousValue}% -> ${currentValue}% since last review.`;

      return {
        key,
        label: LABELS[key],
        previous: previousValue,
        current: currentValue,
        delta,
        direction,
        message,
      } satisfies TrendAlert;
    })
    .filter((item): item is TrendAlert => item !== null)
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta));

  return alerts.slice(0, 3);
};
