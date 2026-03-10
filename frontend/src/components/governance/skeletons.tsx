/**
 * Governance skeleton components — Task 8.2
 *
 * All skeletons share the same card border/background/padding as their real
 * counterparts so layout shifts are eliminated. The inner blocks use
 * `.gov-skel-shimmer` for the two-stop gradient shimmer defined in index.css.
 *
 * Exports
 * ───────
 * SignalCardSkeleton      — 3-col grid card (SignalsPage loading list)
 * BriefCardSkeleton       — single-column row card (ReportsPage loading list)
 * ActionColumnSkeleton    — 4-col kanban column (ExecutionPage loading list)
 * DashboardCardSkeleton   — generic DashboardCard shell with 1–4 row stubs
 */

// ─────────────────────────────────────────────────────────────────────────────
// SignalCardSkeleton
// Mirrors: <article class="rounded-xl border p-6"> inside the 3-col grid
// ─────────────────────────────────────────────────────────────────────────────
export function SignalCardSkeleton() {
  return (
    <article
      aria-hidden="true"
      className="rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm"
    >
      {/* Title row — matches h-4 text block */}
      <div className="gov-skel-shimmer h-4 w-40 rounded" />
      {/* Sub-label — severity chip */}
      <div className="mt-3 h-3 w-20 rounded gov-skel-shimmer" />
      {/* Badge / CTA stand-in */}
      <div className="mt-4 h-7 w-16 rounded gov-skel-shimmer" />
    </article>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// BriefCardSkeleton
// Mirrors: <article class="rounded-xl border p-6"> in Reports list rows
// ─────────────────────────────────────────────────────────────────────────────
export function BriefCardSkeleton() {
  return (
    <article
      aria-hidden="true"
      className="rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm"
    >
      {/* Title */}
      <div className="gov-skel-shimmer h-4 w-36 rounded" />
      {/* Date + review period */}
      <div className="mt-3 gov-skel-shimmer h-3 w-48 rounded" />
      <div className="mt-2 gov-skel-shimmer h-3 w-32 rounded" />
      {/* View button stand-in */}
      <div className="mt-6 gov-skel-shimmer h-8 w-28 rounded" />
    </article>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ActionColumnSkeleton
// Mirrors: <article class="rounded-xl border p-6"> in the 4-col kanban view
// Contains 3 nested card stubs matching the real action card rows.
// ─────────────────────────────────────────────────────────────────────────────
export function ActionColumnSkeleton() {
  return (
    <article
      aria-hidden="true"
      className="rounded-xl border border-[#E3E8EF] bg-white p-6 shadow-sm"
    >
      {/* Column header */}
      <div className="gov-skel-shimmer h-4 w-28 rounded" />
      <div className="mt-4 space-y-3">
        {[0, 1, 2].map((i) => (
          <div
            key={`action-card-stub-${i}`}
            className="rounded-lg border border-neutral-200 p-3"
          >
            {/* Action title */}
            <div className="gov-skel-shimmer h-3 w-40 rounded" />
            {/* Owner / due-date meta */}
            <div className="mt-2 gov-skel-shimmer h-3 w-28 rounded" />
          </div>
        ))}
      </div>
    </article>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DashboardCardSkeleton
// Drop-in for any DashboardCard section that should show structure while
// loading. Pass `rows` (1–4) to control how many stub lines appear.
// ─────────────────────────────────────────────────────────────────────────────
type DashboardCardSkeletonProps = {
  /** Number of content row stubs to render (default: 3) */
  rows?: number;
  /** Optional extra class on the outer article */
  className?: string;
};

export function DashboardCardSkeleton({
  rows = 3,
  className = "",
}: DashboardCardSkeletonProps) {
  return (
    <section
      aria-hidden="true"
      className={`rounded-[10px] border border-[#E5E7EB] bg-white p-6 shadow-[0_1px_3px_rgba(0,0,0,0.06)] ${className}`.trim()}
    >
      {/* Card header */}
      <div className="mb-4">
        <div className="gov-skel-shimmer h-4 w-44 rounded" />
        <div className="mt-1.5 gov-skel-shimmer h-3 w-64 rounded" />
      </div>
      {/* Content rows */}
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={`dash-card-stub-${i}`} className="flex items-center gap-3">
            <div className="gov-skel-shimmer h-3 rounded" style={{ width: `${55 + (i % 3) * 15}%` }} />
            <div className="gov-skel-shimmer h-3 w-14 rounded" />
          </div>
        ))}
      </div>
    </section>
  );
}
