import { PropsWithChildren, useEffect } from "react";
import { useLocation } from "react-router-dom";
import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import { SkipToMainContent } from "@/components/SkipToMainContent";

const PAGE_TITLES: Record<string, string> = {
  "/": "Home",
  "/features": "Features",
  "/how-it-works": "How It Works",
  "/pricing": "Pricing",
  "/security": "Security",
  "/contact": "Contact",
  "/terms": "Terms",
  "/privacy": "Privacy",
  "/login": "Log In",
  "/signup": "Sign Up",
  "/check-email": "Check Email",
  "/verify-success": "Verify Success",
  "/demo": "Sample Workspace",
  "/docs": "Documentation",
  "/forgot-password": "Forgot Password",
};

const PageLayout = ({ children }: PropsWithChildren) => {
  const { pathname } = useLocation();
  const isAuthRoute =
    pathname === "/login" ||
    pathname === "/signup" ||
    pathname === "/check-email" ||
    pathname === "/verify-success" ||
    pathname.startsWith("/verify-email") ||
    pathname === "/verified" ||
    pathname.startsWith("/verified") ||
    pathname === "/forgot-password" ||
    pathname.startsWith("/reset-password");
  const isWorkspaceRoute =
    pathname.startsWith("/dashboard") ||
    pathname.startsWith("/upload") ||
    pathname.startsWith("/signals/");
  const isPublicRoute = !isWorkspaceRoute;

  useEffect(() => {
    const page =
      pathname.startsWith("/demo/reports/") && pathname.endsWith("/pdf")
        ? "Sample Brief"
        : pathname.startsWith("/demo/reports/")
          ? "Sample Report"
          : PAGE_TITLES[pathname] || "Clarion";
    document.title = page === "Clarion" ? "Clarion" : `${page} - Clarion`;
  }, [pathname]);

  return (
    <div
      className={[
        "min-h-screen",
        isPublicRoute ? "marketing-shell landing-v3-shell bg-[#F6F0E4] text-[#111827]" : "bg-background",
      ].join(" ")}
    >
      <SkipToMainContent />
      <SiteNav />
      <main
        id="main-content"
        className={[
          "pt-16",
          isWorkspaceRoute ? "pb-10" : "pb-12",
          isAuthRoute ? "route-shell-auth" : "",
        ].join(" ")}
      >
        {children}
      </main>
      <SiteFooter />
    </div>
  );
};

export default PageLayout;
