/**
 * PageTabs
 * ─────────────────────────────────────────────────────────────────────────────
 * Calm, governance-appropriate tab bar for workflow segmentation on key pages.
 *
 * Design:
 *   - Sits below the PageWrapper header, above the content area
 *   - Active tab: dark text (#0D1B2A) + 2px bottom border in Clarion teal (#0EA5C2)
 *   - Inactive tabs: muted slate text, no border, subtle hover
 *   - Badge count optional — small numeric indicator for urgency (overdue, triage)
 *   - No pill/card background; the tab bar itself has a single bottom border
 *   - Keyboard accessible via Radix Tabs primitive
 *
 * Usage:
 *   <PageTabs
 *     value={activeTab}
 *     onValueChange={setActiveTab}
 *     tabs={[
 *       { value: "triage", label: "Triage", badgeCount: 3 },
 *       { value: "all",    label: "All Signals" },
 *       { value: "briefs", label: "In Briefs" },
 *     ]}
 *   />
 *
 * Note: This component is purely the tab bar. Content switching is managed
 * by the parent page via the `value` / `onValueChange` pattern.
 * ─────────────────────────────────────────────────────────────────────────────
 */

import * as TabsPrimitive from "@radix-ui/react-tabs";

export type PageTabItem = {
  value: string;
  label: string;
  /** Optional count badge — shown when > 0 */
  badgeCount?: number;
  /** Amber tint on badge when true (used for urgency: overdue, triage) */
  badgeUrgent?: boolean;
};

type PageTabsProps = {
  value: string;
  onValueChange: (value: string) => void;
  tabs: PageTabItem[];
  className?: string;
};

export function PageTabs({ value, onValueChange, tabs, className = "" }: PageTabsProps) {
  return (
    <TabsPrimitive.Root value={value} onValueChange={onValueChange}>
      <TabsPrimitive.List
        className={[
          "flex items-end gap-0 border-b border-[#E5E7EB] bg-transparent",
          className,
        ].join(" ")}
        aria-label="Page workflow tabs"
      >
        {tabs.map((tab) => (
          <TabsPrimitive.Trigger
            key={tab.value}
            value={tab.value}
            className={[
              // Layout
              "group relative flex items-center gap-2 px-4 pb-3 pt-1",
              // Typography
              "text-[13px] font-medium leading-none whitespace-nowrap",
              // Default (inactive) state — smooth color + opacity transition
              "text-slate-400 transition-[color,opacity] duration-150 ease-out",
              // Hover — darkens text to near-active weight without committing to active
              "hover:text-slate-700",
              // Active state — full ink weight
              "data-[state=active]:text-[#0D1B2A]",
              // Active bottom border — slide-in via scaleX so it feels intentional
              "after:absolute after:bottom-[-1px] after:left-0 after:right-0 after:h-[2px] after:rounded-t-[1px] after:bg-[#0EA5C2]",
              "after:origin-left after:transition-[transform,opacity] after:duration-150 after:ease-out",
              "after:scale-x-0 after:opacity-0",
              "data-[state=active]:after:scale-x-100 data-[state=active]:after:opacity-100",
              // Focus ring — teal, only on keyboard nav
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0EA5C2] focus-visible:ring-offset-1 rounded-sm",
              "outline-none",
            ].join(" ")}
          >
            {tab.label}
            {typeof tab.badgeCount === "number" && tab.badgeCount > 0 ? (
              <span
                className={[
                  "inline-flex min-w-[18px] items-center justify-center rounded-full border px-1.5 py-[1px] text-[10px] font-semibold tabular-nums leading-none",
                  tab.badgeUrgent
                    ? "border-amber-300/60 bg-amber-100 text-amber-800"
                    : "border-slate-200 bg-slate-100 text-slate-600",
                ].join(" ")}
              >
                {tab.badgeCount}
              </span>
            ) : null}
          </TabsPrimitive.Trigger>
        ))}
      </TabsPrimitive.List>
    </TabsPrimitive.Root>
  );
}
