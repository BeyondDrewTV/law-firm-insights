import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { landingHeroAside, landingProofNotes } from "@/content/landingV3";
import LandingOperatingPreview from "@/components/landing/LandingOperatingPreview";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

const LandingHeroSection = () => {
  const { isLoggedIn, isLoading } = useAuth();
  const workspaceLink = !isLoading && isLoggedIn ? "/upload" : "/signup";

  return (
    <section className="border-b border-[#D7D0C3] bg-[#F6F0E4]">
      <div className="section-container py-20 lg:py-24 xl:py-28">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] lg:items-start lg:gap-14 xl:grid-cols-[minmax(0,0.94fr)_minmax(0,1.06fr)] xl:gap-16">
          <div className="max-w-[39rem]">
            <p className="landing-kicker">Partner-ready client feedback governance</p>
            <h1 className="landing-display mt-6 max-w-[12ch] text-[3.1rem] leading-[1.03] tracking-[-0.035em] text-[#111827] sm:text-[3.55rem] md:text-[4.15rem] xl:text-[4.45rem]">
              See what clients are telling the firm, what needs attention, and what is actually assigned.
            </h1>
            <p className="mt-7 max-w-[33rem] text-[1.05rem] leading-[1.9] text-[#374151]">
              Clarion turns uploaded law-firm feedback into a governance brief, a clear action record, and a meeting-ready
              view of what partners need to review now.
            </p>

            <div className="mt-9 flex flex-wrap gap-3">
              <Link
                to={defaultSampleBriefPath}
                className="gov-btn-primary bg-[#111827] px-6 py-3 text-sm font-semibold text-white hover:bg-[#1F2937]"
              >
                Review sample brief <ArrowRight size={15} className="ml-2" />
              </Link>
              <a
                href="#workflow"
                className="gov-btn-secondary border-[#B9AE99] bg-transparent px-6 py-3 text-sm font-semibold text-[#111827] hover:bg-white"
              >
                See the workflow
              </a>
            </div>

            <div className="landing-hero-aside mt-11">
              <p className="landing-preview-label">What Clarion helps partners do</p>
              <ul className="mt-4 space-y-3">
                {landingHeroAside.map((item) => (
                  <li key={item} className="landing-hero-aside-item">
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="mt-9 flex flex-wrap gap-2">
              {landingProofNotes.map((note) => (
                <span key={note} className="inline-flex items-center gap-1.5 rounded-lg border border-[#C4B99A] bg-white px-3.5 py-2 text-sm font-medium text-[#374151]">
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true"><circle cx="6" cy="6" r="6" fill="#8B6F3D" fillOpacity="0.12"/><path d="M3.5 6.2L5.1 7.8L8.5 4.5" stroke="#8B6F3D" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg>
                  {note}
                </span>
              ))}
            </div>

            <div className="mt-9 border-t border-[#D9D1C3] pt-5 text-sm text-[#4B5563]">
              <p>
                {isLoggedIn ? "Already inside Clarion?" : "Want to run your own first cycle?"}{" "}
                <Link to={workspaceLink} className="font-semibold text-[#111827] underline underline-offset-4">
                  {isLoggedIn ? "Upload recent feedback." : "Start a workspace or pilot."}
                </Link>
              </p>
            </div>
          </div>

          <div className="lg:pt-3">
            <LandingOperatingPreview compact mode="hero" />
          </div>
        </div>
      </div>
    </section>
  );
};

export default LandingHeroSection;
