import type { BillingPlan, PlanType } from "@/api/authService";

export type PricingPlanId = "free" | "team" | "firm";

export interface PricingPlan {
  id: PricingPlanId;
  planType: PlanType;
  name: string;
  audience: string;
  price: string;
  period: string;
  features: string[];
  cta: {
    default: string;
    current: string;
  };
}

export const pricingPlans: PricingPlan[] = [
  {
    id: "free",
    planType: "free",
    name: "Free",
    audience: "Start your first governance cycle",
    price: "$0",
    period: "",
    features: [
      "1 governance brief per month",
      "Up to 50 reviews per upload",
      "90 days of governance history",
      "Deleted reports retained 30 days (restore requires paid access)",
      "Theme and sentiment detection",
      "Dashboard workspace access",
      "Preview PDF export (watermarked)",
      "No credit card required",
    ],
    cta: {
      default: "Start Free",
      current: "Go to Dashboard",
    },
  },
  {
    id: "team",
    planType: "pro_monthly",
    name: "Team",
    audience: "Operational cadence for active firms",
    price: "$129",
    period: "/month",
    features: [
      "Upload up to 5,000 reviews per analysis",
      "Up to 10 governance briefs per month",
      "12 months of governance history",
      "Restore deleted reports within retention window",
      "Download Governance Brief PDF",
      "Plan usage dashboard",
    ],
    cta: {
      default: "Start Team",
      current: "Go to Dashboard",
    },
  },
  {
    id: "firm",
    planType: "pro_annual",
    audience: "Full governance coverage across practice groups",
    name: "Firm",
    price: "$1,290",
    period: "/year",
    features: [
      "Upload up to 5,000 reviews per analysis",
      "Single-workspace access",
      "Unlimited governance briefs",
      "Unlimited governance history",
      "Restore deleted reports within retention window",
      "Download Governance Brief PDF",
      "Full governance workflow access",
    ],
    cta: {
      default: "Start Firm",
      current: "Go to Dashboard",
    },
  },
];
