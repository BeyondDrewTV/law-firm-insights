import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

const sharedMoreLinks = [
  { label: "Sample Brief", to: defaultSampleBriefPath },
  { label: "Sample Workspace", to: "/demo" },
  { label: "Docs", to: "/docs" },
  { label: "Contact", to: "/contact" },
  { label: "Terms", to: "/terms" },
  { label: "Privacy", to: "/privacy" },
];

const dashboardMoreLinks = [
  { label: "Features", to: "/features" },
  { label: "How It Works", to: "/how-it-works" },
  { label: "Pricing", to: "/pricing" },
  { label: "Security", to: "/security" },
  ...sharedMoreLinks,
];

const SiteNav = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { isLoggedIn, isLoading, logOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const normalizedPathname = location.pathname.toLowerCase().replace(/\s+/g, "-");
  const isWorkspaceRoute =
    normalizedPathname.startsWith("/dashboard") ||
    normalizedPathname.startsWith("/upload") ||
    normalizedPathname.startsWith("/onboarding");
  const isPublicRoute = !isWorkspaceRoute;

  const getNavLinkClass = ({ isActive }: { isActive: boolean }) => {
    if (isWorkspaceRoute) {
      return `text-sm font-medium transition-colors ${isActive ? "text-slate-900" : "text-slate-700 hover:text-slate-900"}`;
    }
    return [
      "text-sm font-medium transition-colors md:rounded-full md:px-3 md:py-2 landing-nav-link",
      isActive ? "text-slate-900 md:bg-white/70" : "text-slate-700 hover:text-slate-900",
    ].join(" ");
  };

  const clearCloseTimer = () => {
    if (closeTimerRef.current) {
      clearTimeout(closeTimerRef.current);
      closeTimerRef.current = null;
    }
  };

  const openMoreMenu = () => {
    clearCloseTimer();
    setIsMoreOpen(true);
  };

  const closeMoreMenuWithDelay = () => {
    clearCloseTimer();
    closeTimerRef.current = setTimeout(() => {
      setIsMoreOpen(false);
    }, 380);
  };

  useEffect(() => {
    return () => clearCloseTimer();
  }, []);

  useEffect(() => {
    if (!isPublicRoute) {
      setScrolled(false);
      return;
    }
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isPublicRoute]);

  const handleLogout = async () => {
    await logOut();
    setMobileOpen(false);
    toast.success("You have been logged out.");
    navigate("/");
  };

  const headerClass = isPublicRoute
    ? [
        "landing-nav-shell fixed top-0 left-0 right-0 z-50 border-b border-[#D7D0C3] transition-all duration-200",
        scrolled ? "bg-[#FAF6EE]/96 backdrop-blur-md shadow-sm" : "bg-[#F6F0E4]/94 backdrop-blur-md",
      ].join(" ")
    : "fixed top-0 left-0 right-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur-md";

  const brandTitleClass = "text-lg font-bold tracking-tight leading-tight text-slate-900";
  const menuButtonClass =
    "p-2 text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  const moreButtonClass =
    "landing-nav-link text-sm font-medium text-slate-700 transition-colors md:rounded-full md:px-3 md:py-2 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  const dropdownClass = "landing-nav-dropdown rounded-xl border border-[#D7D0C3] bg-[#FFFDF9] shadow-lg p-2";
  const showWorkspaceNav = !isLoading && isLoggedIn;

  return (
    <header className={headerClass}>
      <div className="section-container flex h-16 items-center justify-between">
        <Link to="/" className="min-w-0">
          <div className={brandTitleClass}>Clarion</div>
        </Link>

        <nav className="hidden md:flex items-center gap-4">
          {showWorkspaceNav ? (
            <>
              <NavLink to="/dashboard" end className={getNavLinkClass}>
                Workspace Home
              </NavLink>
              <NavLink to="/dashboard/reports" className={getNavLinkClass} data-tour-id="nav-reports-link">
                Briefs
              </NavLink>
              <NavLink to="/dashboard/billing" className={getNavLinkClass}>
                Billing
              </NavLink>
              <NavLink to="/upload" className={getNavLinkClass}>
                Upload Cycle
              </NavLink>
              <NavLink to="/pricing" className={getNavLinkClass}>
                Pricing
              </NavLink>
              <button
                type="button"
                onClick={handleLogout}
                className="text-sm font-medium text-slate-700 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/features" className={getNavLinkClass}>
                Features
              </NavLink>
              <NavLink to="/how-it-works" className={getNavLinkClass}>
                How It Works
              </NavLink>
              <NavLink to="/pricing" className={getNavLinkClass}>
                Pricing
              </NavLink>
              <NavLink to="/security" className={getNavLinkClass}>
                Security
              </NavLink>
              <NavLink to="/login" className={getNavLinkClass}>
                Log in
              </NavLink>
              <Link
                to={defaultSampleBriefPath}
                className="landing-nav-cta inline-flex items-center rounded-xl border border-[#111827] bg-[#111827] px-5 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-[#1F2937]"
              >
                Review sample brief
              </Link>
            </>
          )}

          <div className="relative" onMouseEnter={openMoreMenu} onMouseLeave={closeMoreMenuWithDelay}>
            <button
              type="button"
              className={moreButtonClass}
              aria-haspopup="menu"
              aria-expanded={isMoreOpen}
              onFocus={openMoreMenu}
              onBlur={closeMoreMenuWithDelay}
            >
              Resources
            </button>
            <div
              className={`absolute right-0 top-full w-48 pt-2 transition-all duration-150 ${
                isMoreOpen ? "opacity-100 visible translate-y-0 pointer-events-auto" : "opacity-0 invisible translate-y-1 pointer-events-none"
              } z-[120]`}
              onMouseEnter={openMoreMenu}
              onMouseLeave={closeMoreMenuWithDelay}
            >
              <div className={dropdownClass}>
                {(isLoggedIn ? dashboardMoreLinks : sharedMoreLinks).map((link) => (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    onClick={() => setIsMoreOpen(false)}
                    className={({ isActive }) =>
                      [
                        "landing-nav-dropdown-link block rounded-md px-3 py-2 text-sm",
                        isActive ? "text-slate-900 bg-[#F3ECDD]" : "text-slate-700 hover:text-slate-900 hover:bg-slate-100",
                      ].join(" ")
                    }
                  >
                    {link.label}
                  </NavLink>
                ))}
              </div>
            </div>
          </div>
        </nav>

        <div className="md:hidden flex items-center gap-2">
          <button onClick={() => setMobileOpen(!mobileOpen)} className={menuButtonClass} aria-label="Toggle menu">
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <nav
          className={[
            "md:hidden px-6 py-4 space-y-3 border-t",
            isPublicRoute ? "border-[#D7D0C3] bg-[#FAF6EE] text-slate-900" : "border-slate-200 bg-white",
          ].join(" ")}
        >
          {showWorkspaceNav ? (
            <>
              <NavLink to="/dashboard" end onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Workspace Home
              </NavLink>
              <NavLink to="/dashboard/reports" onClick={() => setMobileOpen(false)} className={getNavLinkClass} data-tour-id="nav-reports-link">
                Briefs
              </NavLink>
              <NavLink to="/dashboard/billing" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Billing
              </NavLink>
              <NavLink to="/upload" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Upload Cycle
              </NavLink>
              <NavLink to="/pricing" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Pricing
              </NavLink>
              <button
                type="button"
                onClick={handleLogout}
                className="block text-left text-sm font-medium text-slate-700 hover:text-slate-900"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/features" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Features
              </NavLink>
              <NavLink to="/how-it-works" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                How It Works
              </NavLink>
              <NavLink to="/pricing" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Pricing
              </NavLink>
              <NavLink to="/security" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Security
              </NavLink>
              <NavLink to="/login" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Log in
              </NavLink>
              <Link
                to={defaultSampleBriefPath}
                onClick={() => setMobileOpen(false)}
                className="landing-nav-cta inline-flex w-full items-center justify-center rounded-xl border border-[#111827] bg-[#111827] px-5 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-[#1F2937]"
              >
                Review sample brief
              </Link>
            </>
          )}

          <div
            className={[
              "pt-3 space-y-2 border-t",
              isPublicRoute ? "border-[#D7D0C3]" : "border-slate-200",
            ].join(" ")}
          >
            {(isLoggedIn ? dashboardMoreLinks : sharedMoreLinks).map((link) => (
              <NavLink key={link.to} to={link.to} onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
      )}
    </header>
  );
};

export default SiteNav;
