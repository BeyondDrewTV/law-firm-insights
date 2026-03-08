import SiteNav from "@/components/SiteNav";
import HeroSection from "@/components/HeroSection";
import ProblemSection from "@/components/ProblemSection";
import WorkflowSection from "@/components/WorkflowSection";
import FeaturesSection from "@/components/FeaturesSection";
import CredibilityStrip from "@/components/CredibilityStrip";
import PricingSection from "@/components/PricingSection";
import FinalCTA from "@/components/FinalCTA";
import SiteFooter from "@/components/SiteFooter";

const Index = () => {
  return (
    <div id="top" className="marketing-shell min-h-screen bg-background">
      <SiteNav />
      <main>
        <HeroSection />

        <section className="bg-slate-50">
          <ProblemSection />
        </section>

        <section className="bg-gradient-to-br from-[#0F172A] via-[#153458] to-[#0F172A]">
          <WorkflowSection />
        </section>

        <section className="bg-slate-50">
          <FeaturesSection />
        </section>

        <section className="bg-slate-50">
          <CredibilityStrip />
          <PricingSection showIntro={false} showEntryCtas={false} showTeaserOnly />
        </section>

        <section className="bg-[#0F172A] relative overflow-hidden">
          <div className="absolute -top-24 right-20 h-80 w-80 rounded-full bg-blue-500/20 blur-3xl pointer-events-none" />
          <FinalCTA />
        </section>
      </main>
      <SiteFooter />
    </div>
  );
};

export default Index;
