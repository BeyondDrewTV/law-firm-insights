import type { CSSProperties, HTMLAttributes, ReactNode } from "react";

type GovCardAccent = "none" | "attention" | "watch" | "success" | "neutral";

type GovSectionCardProps = {
  children: ReactNode;
  className?: string;
  accent?: GovCardAccent;
  padding?: "sm" | "md" | "lg";
} & Omit<HTMLAttributes<HTMLElement>, "className">;

const accentClass: Record<GovCardAccent, string> = {
  none: "",
  attention: "gov-accent-attention",
  watch: "gov-accent-watch",
  success: "gov-accent-success",
  neutral: "gov-accent-neutral",
};

const paddingClass = {
  sm: "p-4",
  md: "p-5",
  lg: "p-6",
} as const;

const accentStyle: Record<GovCardAccent, CSSProperties> = {
  none: {},
  attention: { borderLeftWidth: 5, borderLeftColor: "#d97706" },
  watch: { borderLeftWidth: 5, borderLeftColor: "#2563eb" },
  success: { borderLeftWidth: 5, borderLeftColor: "#059669" },
  neutral: { borderLeftWidth: 5, borderLeftColor: "#64748b" },
};

const GovSectionCard = ({
  children,
  className = "",
  accent = "neutral",
  padding = "md",
  style,
  ...props
}: GovSectionCardProps) => {
  return (
    <section
      className={["gov-level-2", accentClass[accent], paddingClass[padding], className].join(" ")}
      style={{ ...accentStyle[accent], ...style }}
      {...props}
    >
      {children}
    </section>
  );
};

export default GovSectionCard;
