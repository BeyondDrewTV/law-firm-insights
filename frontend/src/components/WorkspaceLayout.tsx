/**
 * WorkspaceLayout
 * ─────────────────────────────────────────────────────────────────────────────
 * Global shell for all authenticated workspace routes.
 *
 * Navigation Information Architecture (Phase 3 Task 3.1)
 * ── PRIMARY (governance narrative order) ─────────────────────────────────────
 *   Overview          /dashboard              Home          — entry point, KPI strip
 *   Evidence          /upload                 Database      — source data ingestion
 *   Signals           /dashboard/signals      ScanLine      — detected client issues
 *   Actions           /dashboard/actions      ClipboardList — follow-through execution
 *   Governance Briefs /dashboard/reports      FileText      — leadership artifacts
 * ── SETTINGS (below divider) ─────────────────────────────────────────────────
 *   Account           /dashboard/account      Users
 *   Team              /dashboard/team         UserPlus
 *   Billing           /dashboard/billing      CreditCard
 * ─────────────────────────────────────────────────────────────────────────────
 *
 * Icon rationale:
 *   Database      → raw source material being loaded into the system
 *   ScanLine      → scanning/detecting patterns in evidence (not generic activity)
 *   ClipboardList → structured follow-through checklist (not an arbitrary "Zap")
 *   FileText      → formal printed artifact ✅ already correct
 *   CreditCard    → billing/subscription management
 *
 * No route changes. No API contract changes.
 */

import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  ClipboardList,
  CreditCard,
  Database,
  FileText,
  Home,
  ScanLine,
  UserPlus,
  Users,
  CheckSquare,
} from "lucide-react";
import { getLatestExposure } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";

// ── Navigation Items ──────────────────────────────────────────────────────────

const PRIMARY_NAV = [
  {
    to: "/dashboard",
    label: "Overview",
    Icon: Home,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/upload",
    label: "Evidence",
    Icon: Database,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/signals",
    label: "Signals",
    Icon: ScanLine,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/actions",
    label: "Actions",
    Icon: ClipboardList,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/reports",
    label: "Governance Briefs",
    Icon: FileText,
    badgeKey: "briefs" as const,
    badgeLabel: "Escalation-required briefs",
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/approval-queue",
    label: "Approval Queue",
    Icon: CheckSquare,
    badgeKey: "queue" as const,
    badgeLabel: "Items pending approval",
    iconClass: "text-amber-300/70",
    iconActiveClass: "text-amber-300",
  },
] as const;

const SETTINGS_NAV = [
  {
    to: "/dashboard/account",
    label: "Account",
    Icon: Users,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/team",
    label: "Team",
    Icon: UserPlus,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/billing",
    label: "Billing",
    Icon: CreditCard,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
] as const;

// Union type for badge key across both nav arrays
type BadgeKey = "briefs" | "queue";


// ── NavItem Component ─────────────────────────────────────────────────────────

function NavItem({
  to,
  label,
  Icon,
  isActive,
  badgeCount,
  urgent = false,
  iconClass,
  iconActiveClass,
  badgeLabel,
}: {
  to: string;
  label: string;
  Icon: React.ComponentType<{ size?: number; className?: string }>;
  isActive: boolean;
  badgeCount?: number;
  urgent?: boolean;
  iconClass?: string;
  iconActiveClass?: string;
  badgeLabel?: string;
}) {
  return (
    <Link
      to={to}
      aria-current={isActive ? "page" : undefined}
      className={[
        "group flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
        isActive
          ? "border-l-[3px] border-l-[#0EA5C2] bg-[#0EA5C2]/14 pl-[9px] text-white"
          : "border border-transparent text-slate-100 hover:bg-[#1E293B] hover:text-white",
      ].join(" ")}
    >
      <Icon
        size={16}
        className={[
          "shrink-0 transition-colors duration-150",
          isActive ? (iconActiveClass || "text-white") : (iconClass || "text-[#E2E8F0]"),
          !isActive ? "group-hover:text-white" : "",
        ].join(" ")}
      />
      <span className="flex-1 text-[14px] leading-none">{label}</span>
      {typeof badgeCount === "number" ? (
        <span
          title={badgeLabel ? `${badgeLabel}: ${badgeCount}` : String(badgeCount)}
          aria-label={badgeLabel ? `${badgeLabel}: ${badgeCount}` : String(badgeCount)}
          className={[
            "inline-flex min-w-5 items-center justify-center rounded border px-1.5 py-0.5 text-[10px] font-semibold tabular-nums",
            urgent && badgeCount > 0
              ? "border-amber-300/50 bg-amber-200/20 text-amber-100"
              : "border-white/30 bg-white/10 text-slate-100",
          ].join(" ")}
        >
          {badgeCount}
        </span>
      ) : null}
    </Link>
  );
}


// ── WorkspaceLayout ───────────────────────────────────────────────────────────

/** Maps a pathname to a human-readable page label for the topbar and document title. */
const resolvePageLabel = (pathname: string): string => {
  // Detail routes first (more specific)
  if (pathname.startsWith("/dashboard/brief-customization")) return "Brief Customization";
  if (pathname.startsWith("/dashboard/signals/"))             return "Signal Detail";
  if (pathname.startsWith("/dashboard/reports/"))             return "Governance Brief";

  // Primary nav exact / prefix matches
  for (const item of PRIMARY_NAV) {
    if (item.to === "/dashboard" && pathname === "/dashboard") return item.label;
    if (item.to !== "/dashboard" && (pathname === item.to || pathname.startsWith(`${item.to}/`))) return item.label;
  }
  // Upload is a top-level route outside /dashboard
  if (pathname === "/upload") return "Evidence";

  // Settings nav
  for (const item of SETTINGS_NAV) {
    if (pathname === item.to || pathname.startsWith(`${item.to}/`)) return item.label;
  }

  return "Overview";
};

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const { logOut, user, currentPlan } = useAuth();
  const location = useLocation();
  const { pathname } = location;
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const [briefsBadgeCount, setBriefsBadgeCount] = useState<number>(0);
  const [queueBadgeCount, setQueueBadgeCount]   = useState<number>(0);
  const mainRef = useRef<HTMLElement | null>(null);

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    if (href === "/upload")    return pathname === "/upload";
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  // Load nav badge: escalation indicator on Governance Briefs
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const loadNavBadges = async () => {
      const exposure = await getLatestExposure(controller.signal);
      if (!active) return;
      setBriefsBadgeCount(
        exposure.success && exposure.exposure?.partner_escalation_required ? 1 : 0,
      );
    };
    void loadNavBadges();
    return () => { active = false; controller.abort(); };
  }, []);

  // Approval queue badge — polls every 60s
  useEffect(() => {
    let active = true;
    const poll = async () => {
      try {
        const res = await fetch("/api/approval-queue/stats", {
          headers: { Authorization: "Bearer Themepark12" },
        });
        if (!active || !res.ok) return;
        const s = await res.json();
        setQueueBadgeCount(s.total_pending ?? 0);
      } catch { /* silent */ }
    };
    void poll();
    const t = setInterval(poll, 60_000);
    return () => { active = false; clearInterval(t); };
  }, []);

  const handleLogOut = async () => {
    if (loggingOut) return;
    setLoggingOut(true);
    try {
      await logOut();
      navigate("/login");
    } finally {
      setLoggingOut(false);
    }
  };

  const currentPageLabel = resolvePageLabel(pathname);

  useEffect(() => {
    document.title = `${currentPageLabel} — Clarion`;
  }, [currentPageLabel]);

  useEffect(() => {
    const mainElement = mainRef.current;
    if (!mainElement) return;
    mainElement.scrollTo({ top: 0, left: 0, behavior: "auto" });
  }, [pathname]);

  const planLabel = currentPlan?.firmPlan
    ? currentPlan.firmPlan.toUpperCase()
    : currentPlan?.planLabel
      ? currentPlan.planLabel.toUpperCase()
      : "FREE";
  const userName = (user?.name || user?.email || "").trim();
  const initials = userName
    ? userName.split(/\s+/).slice(0, 2).map((p) => p.charAt(0).toUpperCase()).join("")
    : "U";

  return (
    <div className="gov-canvas flex h-screen w-full overflow-hidden">
      {/* ── Sidebar ─────────────────────────────────────────────────── */}
      <aside
        aria-label="Primary navigation"
        className="workspace-sidebar sticky top-0 flex h-screen w-[17rem] shrink-0 flex-col overflow-y-auto border-r border-white/10 !bg-[#0F172A]"
      >
        {/* Wordmark */}
        <div className="flex shrink-0 flex-col justify-center border-b border-white/10 px-5 py-2">
          <span className="text-[15px] font-bold tracking-[0.01em] text-white">Clarion</span>
          <span className="text-[10px] font-normal uppercase tracking-[0.05em] text-white/45">
            Client Experience Governance
          </span>
        </div>

        {/* Primary nav — governance narrative order */}
        <nav className="flex-1 px-3 py-4" aria-label="Governance workspace">
          <div className="space-y-1">
            {PRIMARY_NAV.map((item) => (
              <NavItem
                key={item.to}
                to={item.to}
                label={item.label}
                Icon={item.Icon}
                isActive={isActive(item.to)}
                badgeCount={
                  "badgeKey" in item && item.badgeKey === "briefs" && briefsBadgeCount > 0
                    ? briefsBadgeCount
                    : "badgeKey" in item && item.badgeKey === "queue" && queueBadgeCount > 0
                      ? queueBadgeCount
                      : undefined
                }
                urgent={"badgeKey" in item && item.badgeKey === "briefs" && briefsBadgeCount > 0}
                iconClass={item.iconClass}
                iconActiveClass={item.iconActiveClass}
                badgeLabel={"badgeLabel" in item ? item.badgeLabel : undefined}
              />
            ))}

            {/* Divider */}
            <div className="my-3 h-px bg-white/10" role="separator" />

            {/* Settings group */}
            {SETTINGS_NAV.map((item) => (
              <NavItem
                key={item.to}
                to={item.to}
                label={item.label}
                Icon={item.Icon}
                isActive={isActive(item.to)}
                iconClass={item.iconClass}
                iconActiveClass={item.iconActiveClass}
              />
            ))}
          </div>
        </nav>

        {/* Log out */}
        <div className="shrink-0 px-4 py-3">
          <div className="mb-3 h-px bg-white/10" />
          <button
            type="button"
            onClick={() => void handleLogOut()}
            disabled={loggingOut}
            className="text-[13px] font-medium text-white/50 transition-colors hover:text-white/70 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loggingOut ? "Logging Out..." : "Log Out"}
          </button>
        </div>
      </aside>

      {/* ── Main content area ────────────────────────────────────────── */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex h-[52px] shrink-0 items-center justify-between border-b border-[#E5E7EB] bg-white px-6">
          <div className="text-sm font-medium text-slate-700">{currentPageLabel}</div>
          <div className="flex items-center gap-2.5">
            <span className="inline-flex items-center rounded-md border border-slate-300 bg-slate-50 px-2 py-1 text-[11px] font-semibold uppercase tracking-[0.05em] text-slate-700">
              {planLabel}
            </span>
            <div
              aria-label="User profile"
              className="inline-flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-slate-100 text-xs font-semibold text-slate-700"
            >
              {initials}
            </div>
          </div>
        </header>
        <main
          ref={mainRef}
          className="workspace-main min-h-0 flex-1 overflow-y-auto bg-[var(--background)]"
        >
          <div className="workspace-route-content min-h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
