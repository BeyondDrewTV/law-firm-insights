import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Activity, FileText, Home, Upload, Users, Zap } from "lucide-react";
import { getLatestExposure } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";
import { DISPLAY_LABELS } from "@/constants/displayLabels";

const NAV_ITEMS = [
  {
    to: "/dashboard",
    label: "Overview",
    Icon: Home,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/upload",
    label: "Uploads",
    Icon: Upload,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/signals",
    label: DISPLAY_LABELS.clientIssuePlural,
    Icon: Activity,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
  {
    to: "/dashboard/actions",
    label: "Actions",
    Icon: Zap,
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
    to: "/dashboard/account",
    label: "Account",
    Icon: Users,
    iconClass: "text-[#E2E8F0]",
    iconActiveClass: "text-white",
  },
] as const;

const PRIMARY_NAV_ITEMS = NAV_ITEMS.filter((item) => item.to !== "/dashboard/account");
const SETTINGS_NAV_ITEMS = NAV_ITEMS.filter((item) => item.to === "/dashboard/account");

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

export default function WorkspaceLayout({ children }: { children: React.ReactNode }) {
  const { logOut, user, currentPlan } = useAuth();
  const location = useLocation();
  const { pathname } = location;
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);
  const [briefsBadgeCount, setBriefsBadgeCount] = useState<number>(0);
  const mainRef = useRef<HTMLElement | null>(null);

  const isActive = (href: string) => {
    if (href === "/dashboard") {
      return pathname === "/dashboard";
    }
    if (href === "/upload") {
      return pathname === "/upload";
    }
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  useEffect(() => {
    let active = true;
    const controller = new AbortController();

    const loadNavBadges = async () => {
      const exposure = await getLatestExposure(controller.signal);
      if (!active) return;
      const escalationRequired = Boolean(exposure.success && exposure.exposure?.partner_escalation_required);
      setBriefsBadgeCount(escalationRequired ? 1 : 0);
    };

    void loadNavBadges();
    return () => {
      active = false;
      controller.abort();
    };
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

  const currentPageLabel =
    pathname.startsWith("/dashboard/brief-customization")
      ? "Brief Customization"
      :
    NAV_ITEMS.find((item) => item.to !== "/upload" && (pathname === item.to || pathname.startsWith(`${item.to}/`)))
      ?.label || (pathname === "/upload" ? "Uploads" : "Overview");

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
    ? userName
        .split(/\s+/)
        .slice(0, 2)
        .map((part) => part.charAt(0).toUpperCase())
        .join("")
    : "U";

  return (
    <div className="gov-canvas flex h-screen w-full overflow-hidden">
      <aside className="workspace-sidebar sticky top-0 flex h-screen w-[17rem] shrink-0 flex-col overflow-y-auto border-r border-white/10 !bg-[#0F172A]">
        <div className="flex shrink-0 flex-col justify-center border-b border-white/10 px-5 py-2">
          <span className="text-[15px] font-bold tracking-[0.01em] text-white">Clarion</span>
          <span className="text-[10px] font-normal uppercase tracking-[0.05em] text-white/45">
            Client Experience Governance
          </span>
        </div>
        <nav className="flex-1 px-3 py-4">
          <div className="space-y-1">
            {PRIMARY_NAV_ITEMS.map((item) => (
              <NavItem
                key={item.to}
                to={item.to}
                label={item.label}
                Icon={item.Icon}
                isActive={isActive(item.to)}
                badgeCount={item.badgeKey === "briefs" ? (briefsBadgeCount > 0 ? briefsBadgeCount : undefined) : undefined}
                urgent={item.badgeKey === "briefs" && briefsBadgeCount > 0}
                iconClass={item.iconClass}
                iconActiveClass={item.iconActiveClass}
                badgeLabel={item.badgeLabel}
              />
            ))}
            <div className="my-3 h-px bg-white/10" />
            {SETTINGS_NAV_ITEMS.map((item) => (
              <NavItem
                key={item.to}
                to={item.to}
                label={item.label}
                Icon={item.Icon}
                isActive={isActive(item.to)}
                badgeCount={item.badgeKey === "briefs" ? (briefsBadgeCount > 0 ? briefsBadgeCount : undefined) : undefined}
                urgent={item.badgeKey === "briefs" && briefsBadgeCount > 0}
                iconClass={item.iconClass}
                iconActiveClass={item.iconActiveClass}
                badgeLabel={item.badgeLabel}
              />
            ))}
          </div>
        </nav>
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
        <main ref={mainRef} className="workspace-main min-h-0 flex-1 overflow-y-auto bg-[var(--background)]">
          <div className="workspace-route-content min-h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
