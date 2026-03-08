import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import MarketingDashboardPreview from "@/components/MarketingDashboardPreview";

const HeroSection = () => {
  const { isLoggedIn, isLoading } = useAuth();
  const primaryCtaTo = !isLoading && isLoggedIn ? "/upload" : "/signup";
  const primaryCtaLabel = !isLoading && isLoggedIn ? "Begin With a CSV Upload" : "Start Your Workspace";

  return (
    <section
      className="section-padding relative overflow-hidden border-b border-white/10"
      style={{
        background: "linear-gradient(135deg, #0F172A 0%, #1E3A5F 60%, #0F172A 100%)",
      }}
    >
      <div className="absolute top-1/4 right-1/4 h-96 w-96 rounded-full bg-blue-600 opacity-10 blur-3xl pointer-events-none" />
      <div className="section-container">
        <div className="grid gap-10 lg:grid-cols-[1.35fr_1fr] lg:items-start">
          <div className="reveal relative z-10">
            <span className="animate-fade-up mb-4 inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
              Client Experience Governance
            </span>
            <h1 className="animate-fade-up animate-fade-up-delay-1 max-w-3xl text-5xl font-extrabold leading-tight text-white">
              Client feedback, run with more discipline.
            </h1>
            <p className="animate-fade-up animate-fade-up-delay-2 mt-4 max-w-2xl text-base leading-relaxed text-slate-300">
              Clarion gives law firms a practical governance workflow for client feedback: upload a CSV, surface recurring client issues, assign owners, and walk into leadership meetings with a brief built for review.
            </p>
            <p className="animate-fade-up animate-fade-up-delay-2 mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
              Start with exported reviews from Google, Avvo, surveys, or internal feedback systems. Clarion helps the firm see where service problems are repeating and what warrants partner attention next.
            </p>

            <div className="animate-fade-up animate-fade-up-delay-3 mt-7 flex flex-wrap items-center gap-3">
              <Link
                to={primaryCtaTo}
                className="inline-flex items-center rounded-xl bg-blue-600 px-6 py-3 font-semibold text-white shadow-lg shadow-blue-600/30 transition-all duration-200 hover:-translate-y-0.5 hover:bg-blue-500 hover:shadow-blue-500/40"
              >
                {primaryCtaLabel} <ArrowRight size={15} className="ml-2" />
              </Link>
              <Link
                to="/how-it-works#reporting-loop"
                className="rounded-xl border border-white/20 px-6 py-3 font-medium text-white/80 transition-all duration-200 hover:border-white/40 hover:text-white"
              >
                See the workflow
              </Link>
              <Link
                to="/demo"
                className="text-sm text-blue-400 underline-offset-4 transition-colors hover:text-blue-300 hover:underline"
              >
                Explore read-only demo
              </Link>
            </div>

            {!isLoggedIn && (
              <div className="mt-3">
                <Link to="/login" className="text-sm font-medium text-slate-300 hover:text-white">
                  Already have an account? Log in
                </Link>
              </div>
            )}
          </div>

          <aside className="reveal relative z-10">
            <MarketingDashboardPreview compact variant="overview" />
          </aside>
        </div>
      </div>
    </section>
  );
};

export default HeroSection;
