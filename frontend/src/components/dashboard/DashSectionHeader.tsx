type DashSectionHeaderProps = {
  title: string;
  /** Optional muted sub-line below the title */
  subtitle?: string;
};

/**
 * DashSectionHeader
 * Consistent heading for major content sections inside a dashboard tier.
 *
 * Typography:
 *   title    → gov-type-eyebrow  (11px / 700 / uppercase / #64748B)
 *   subtitle → gov-type-meta     (12px / 400 / #9CA3AF)
 *
 * Usage:
 *   <DashSectionHeader title="Priority follow-through" subtitle="Actions without clear ownership" />
 */
export default function DashSectionHeader({ title, subtitle }: DashSectionHeaderProps) {
  return (
    <div className="mb-3">
      <h2 className="gov-type-eyebrow">{title}</h2>
      {subtitle ? (
        <p className="gov-type-meta mt-0.5">{subtitle}</p>
      ) : null}
    </div>
  );
}
