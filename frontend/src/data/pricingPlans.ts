import type { BillingPlan, PlanType } from "@/api/authService";

export type PricingPlanId = "free" | "team" | "firm";

export interface PricingPlan {
  id: PricingPlanId;
  planType: PlanType;
  name: string;
  audience: string;
  /** Monthly price display string */
  price: string;
  period: string;
  /** Annual price display string */
  annualPrice: string;
  annualPeriod: string;
  /** e.g. "Save ~$358/year" */
  annualSavings: string | null;
  badge: string | null;
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
    audience: "Solo trial — validate your first governance cycle",
    price: "$0",
    period: "",
    annualPrice: "$0",
    annualPeriod: "",
    annualSavings: null,
    badge: null,
    features: [
      "50 reviews per upload",
      "1 governance brief per month",
      "90-day report history",
      "Governance signals & action tracking",
      "Watermarked PDF reports",
      "1 user (solo trial)",
      "No credit card required",
    ],
    cta: {
      default: "Start Free Trial",
      current: "Go to Dashboard",
    },
  },
  {
    id: "team",
    planType: "team",
    name: "Team",
    audience: "Recurring governance for active small firms",
    price: "$179",
    period: "/month",
    annualPrice: "$1,790",
    annualPeriod: "/year",
    annualSavings: "Save ~$358/year",
    badge: "Best for Small Firms",
    features: [
      "250 reviews per upload",
      "10 governance briefs per month",
      "1-year report history",
      "Professional PDF reports — no watermark",
      "Unlimited team members",
      "Team invite system",
      "Full governance workflow (signals, actions, briefs)",
      "Restore deleted reports within retention window",
    ],
    cta: {
      default: "Start Team Plan",
      current: "Go to Dashboard",
    },
  },
  {
    id: "firm",
    planType: "firm",
    name: "Firm",
    audience: "Full-platform coverage across practice groups",
    price: "$449",
    period: "/month",
    annualPrice: "$4,490",
    annualPeriod: "/year",
    annualSavings: "Save ~$898/year",
    badge: "Full Platform",
    features: [
      "1,000 reviews per upload",
      "Unlimited governance briefs",
      "Unlimited report history",
      "Professional PDF reports — no watermark",
      "Unlimited team members",
      "Scheduled governance brief delivery",
      "Custom branding & firm logo on reports",
      "Restore deleted reports within retention window",
      "Priority support",
    ],
    cta: {
      default: "Start Firm Plan",
      current: "Go to Dashboard",
    },
  },
];

// ---------------------------------------------------------------------------
// Comparison table rows — single source of truth for the feature matrix
// ---------------------------------------------------------------------------

export interface ComparisonRow {
  feature: string;
  category: string;
  free: string | boolean;
  team: string | boolean;
  firm: string | boolean;
  tooltip?: string;
}

export const comparisonRows: ComparisonRow[] = [
  // Upload capacity
  { feature: "Reviews per upload", category: "Capacity", free: "50", team: "250", firm: "1,000" },
  { feature: "Governance briefs per month", category: "Capacity", free: "1", team: "10", firm: "Unlimited" },
  { feature: "Report history", category: "Capacity", free: "90 days", team: "1 year", firm: "Unlimited" },
  // Core features
  { feature: "Governance signals & action tracking", category: "Governance", free: true, team: true, firm: true },
  { feature: "PDF report download", category: "Governance", free: "Watermarked", team: true, firm: true },
  { feature: "Restore deleted reports", category: "Governance", free: false, team: true, firm: true },
  // Team
  { feature: "Team members", category: "Team", free: "1 (solo)", team: "Unlimited", firm: "Unlimited" },
  { feature: "Team invite system", category: "Team", free: false, team: true, firm: true },
  // Firm features
  { feature: "Scheduled brief delivery", category: "Firm Features", free: false, team: false, firm: true },
  { feature: "Custom branding & logo", category: "Firm Features", free: false, team: false, firm: true },
  { feature: "Priority support", category: "Firm Features", free: false, team: false, firm: true },
];

// ---------------------------------------------------------------------------
// FAQ content
// ---------------------------------------------------------------------------

export interface FaqItem {
  value: string;
  question: string;
  answer: string;
}

export const pricingFaqs: FaqItem[] = [
  {
    value: "upgrade-downgrade",
    question: "Can we upgrade or downgrade at any time?",
    answer:
      "Yes. You can upgrade or downgrade your plan at any time. Changes take effect immediately and unused time is prorated.",
  },
  {
    value: "data-on-cancel",
    question: "What happens to our data if we cancel?",
    answer:
      "Your reports and governance history are retained for 90 days after cancellation. You can export or download briefs during that window. After 90 days, data is removed in accordance with our privacy policy.",
  },
  {
    value: "refunds",
    question: "Do you offer refunds?",
    answer:
      "Yes. We offer a full refund within 30 days of purchase if Clarion does not meet your needs. Contact support and we will process it promptly.",
  },
  {
    value: "free-vs-team-firm",
    question: "When should we use Free, Team, or Firm?",
    answer:
      "Free is designed for first-cycle validation — one upload, one brief, one user. Team is for firms running a recurring monthly governance rhythm. Firm is for year-round, cross-practice coverage with scheduled delivery and custom branding.",
  },
  {
    value: "team-to-firm",
    question: "Can we move from Team to Firm later?",
    answer:
      "Yes. You can upgrade from Team to Firm at any time. Your workspace, reports, and team settings carry over. Unused Team billing is prorated toward Firm.",
  },
];
