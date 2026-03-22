import { useEffect } from "react";
import SiteNav from "@/components/SiteNav";
import SiteFooter from "@/components/SiteFooter";
import LandingHeroSection from "@/components/landing/LandingHeroSection";
import LandingTrustSection from "@/components/landing/LandingTrustSection";
import LandingWorkflowSection from "@/components/landing/LandingWorkflowSection";
import LandingOutputsSection from "@/components/landing/LandingOutputsSection";
import LandingAccountabilitySection from "@/components/landing/LandingAccountabilitySection";
import LandingMeetingSection from "@/components/landing/LandingMeetingSection";
import LandingFinalSection from "@/components/landing/LandingFinalSection";

const Index = () => {
  useEffect(() => {
    document.title = "Clarion - Partner-Ready Client Feedback Governance for Law Firms";
  }, []);

  useEffect(() => {
    const revealNodes = Array.from(document.querySelectorAll<HTMLElement>(".landing-reveal"));
    if (!revealNodes.length) {
      return;
    }

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || typeof IntersectionObserver === "undefined") {
      revealNodes.forEach((node) => node.classList.add("reveal--visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) {
            return;
          }
          entry.target.classList.add("reveal--visible");
          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.16,
        rootMargin: "0px 0px -8% 0px",
      },
    );

    revealNodes.forEach((node) => {
      node.classList.remove("reveal--visible");
      observer.observe(node);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div id="top" className="marketing-shell landing-v3-shell min-h-screen bg-[#F6F0E4] text-[#111827]">
      <SiteNav />
      <main id="main-content" className="landing-main pt-16">
        <LandingHeroSection />
        <LandingTrustSection />
        <LandingWorkflowSection />
        <LandingOutputsSection />
        <LandingAccountabilitySection />
        <LandingMeetingSection />
        <LandingFinalSection />
      </main>
      <SiteFooter />
    </div>
  );
};

export default Index;
