import type { ReactNode } from "react";

type GovBadgeTone = "neutral" | "watch" | "critical" | "controlled";

type GovBadgeProps = {
  children: ReactNode;
  tone?: GovBadgeTone;
  className?: string;
};

const toneClass: Record<GovBadgeTone, string> = {
  neutral: "gov-badge gov-badge-neutral",
  watch: "gov-badge gov-badge-watch",
  critical: "gov-badge gov-badge-critical",
  controlled: "gov-badge gov-badge-controlled",
};

const GovBadge = ({ children, tone = "neutral", className = "" }: GovBadgeProps) => {
  return <span className={[toneClass[tone], className].join(" ")}>{children}</span>;
};

export default GovBadge;
