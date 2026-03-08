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
  "/demo": "Read-Only Demo",
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
    pathname.startsWith("/verified");

  useEffect(() => {
    const page = PAGE_TITLES[pathname] || "Clarion";
    document.title = `${page} — Clarion`;
  }, [pathname]);

  return (
    <div className={["marketing-shell min-h-screen", isAuthRoute ? "bg-[#0F172A]" : "bg-background"].join(" ")}>
      <SkipToMainContent />
      <SiteNav />
      <main
        id="main-content"
        className={[
          "pt-16 pb-10 transition-colors duration-300",
          isAuthRoute ? "bg-gradient-to-b from-[#0F172A] via-[#132C53] to-[#0F172A]" : "",
        ].join(" ")}
      >
        {children}
      </main>
      <SiteFooter />
    </div>
  );
};

export default PageLayout;

