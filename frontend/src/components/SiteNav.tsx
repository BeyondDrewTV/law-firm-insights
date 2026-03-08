import { useEffect, useRef, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { Menu, X } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

const sharedMoreLinks = [
  { label: "Docs", to: "/docs" },
  { label: "Read-Only Demo", to: "/demo" },
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
  const isHomeHero = normalizedPathname === "/";
  const isWorkspaceRoute =
    normalizedPathname.startsWith("/dashboard") ||
    normalizedPathname.startsWith("/upload") ||
    normalizedPathname.startsWith("/onboarding");
  const isMarketingOrAuth = !isWorkspaceRoute;

  const getNavLinkClass = ({ isActive }: { isActive: boolean }) => {
    if (isMarketingOrAuth) {
      return `text-sm font-medium transition-colors ${isActive ? "text-white" : "text-white/80 hover:text-white"}`;
    }
    return `text-sm font-medium transition-colors ${isActive ? "text-slate-900" : "text-slate-700 hover:text-slate-900"}`;
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
    if (!isMarketingOrAuth) {
      setScrolled(false);
      return;
    }
    const onScroll = () => setScrolled(window.scrollY > 50);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [isMarketingOrAuth]);

  const handleLogout = async () => {
    await logOut();
    setMobileOpen(false);
    toast.success("You have been logged out.");
    navigate("/");
  };

  const headerClass = isMarketingOrAuth
    ? [
        "fixed top-0 left-0 right-0 z-50 border-b transition-all duration-200",
        scrolled
          ? "border-white/20 bg-[#0F172A]/96 backdrop-blur-md"
          : "border-white/15 bg-gradient-to-r from-[#0F172A] via-[#17345a] to-[#0F172A]",
      ].join(" ")
    : "fixed top-0 left-0 right-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur-md";

  const brandTitleClass = isMarketingOrAuth
    ? "text-lg font-bold tracking-tight leading-tight text-white"
    : "text-lg font-bold tracking-tight leading-tight text-slate-900";
  const menuButtonClass = isMarketingOrAuth
    ? "p-2 text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    : "p-2 text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  const moreButtonClass = isMarketingOrAuth
    ? "text-sm font-medium text-white/90 hover:text-white transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
    : "text-sm font-medium text-slate-700 hover:text-slate-900 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2";

  const dropdownClass = isMarketingOrAuth
    ? "rounded-xl border border-white/25 bg-[#0B1730] shadow-2xl shadow-black/50 ring-1 ring-white/15 p-2"
    : "rounded-lg border border-border bg-card shadow-lg p-2";
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
                Dashboard
              </NavLink>
              <NavLink to="/dashboard/reports" className={getNavLinkClass} data-tour-id="nav-reports-link">
                Reports
              </NavLink>
              <NavLink to="/dashboard/billing" className={getNavLinkClass}>
                Billing
              </NavLink>
              <NavLink to="/upload" className={getNavLinkClass}>
                Upload
              </NavLink>
              <NavLink to="/pricing" className={getNavLinkClass}>
                Pricing
              </NavLink>
              <button
                type="button"
                onClick={handleLogout}
                className={isMarketingOrAuth
                  ? "text-sm font-medium text-white/80 transition-colors hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  : "text-sm font-medium text-slate-700 transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"}
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
              <Link to="/signup" className="inline-flex items-center rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-blue-500">
                Start Free
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
                        "block rounded-md px-3 py-2 text-sm",
                        isMarketingOrAuth
                          ? isActive
                            ? "text-white bg-white/15"
                            : "text-white hover:text-white hover:bg-white/14"
                          : isActive
                            ? "text-slate-900"
                            : "text-slate-700 hover:text-slate-900 hover:bg-slate-100",
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
        <nav className={[
          "md:hidden px-6 py-4 space-y-3 border-t",
          isMarketingOrAuth ? "border-white/10 bg-slate-900/95 text-white" : "border-slate-200 bg-white",
        ].join(" ")}>
          {showWorkspaceNav ? (
            <>
              <NavLink to="/dashboard" end onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Dashboard
              </NavLink>
              <NavLink to="/dashboard/reports" onClick={() => setMobileOpen(false)} className={getNavLinkClass} data-tour-id="nav-reports-link">
                Reports
              </NavLink>
              <NavLink to="/dashboard/billing" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Billing
              </NavLink>
              <NavLink to="/upload" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Upload
              </NavLink>
              <NavLink to="/pricing" onClick={() => setMobileOpen(false)} className={getNavLinkClass}>
                Pricing
              </NavLink>
              <button
                type="button"
                onClick={handleLogout}
                className={isMarketingOrAuth
                  ? "block text-left text-sm font-medium text-white/80 hover:text-white"
                  : "block text-left text-sm font-medium text-slate-700 hover:text-slate-900"}
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
              <Link to="/signup" onClick={() => setMobileOpen(false)} className="inline-flex w-full items-center justify-center rounded-xl bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition-all duration-200 hover:bg-blue-500">
                Start Free
              </Link>
            </>
          )}

          <div className={[
            "pt-3 space-y-2 border-t",
            isMarketingOrAuth ? "border-white/10" : "border-slate-200",
          ].join(" ")}>
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


