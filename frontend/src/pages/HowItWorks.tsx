import { Link } from "react-router-dom";
import PageLayout from "@/components/PageLayout";
import LandingOperatingPreview from "@/components/landing/LandingOperatingPreview";
import { useAuth } from "@/contexts/AuthContext";
import { landingWorkflowSteps } from "@/content/landingV3";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

const postUploadRows = [
  {
    title: "A governance brief leadership can use",
    body: "Recurring issues, what changed, and the decisions that need partner attention now.",
  },
  {
    title: "An operating record that stays live",
    body: "The report, issues, actions, and review history stay tied to the same cycle instead of being split across notes and follow-up threads.",
  },
  {
    title: "Meeting-ready outputs",
    body: "Use the workspace, PDF brief, and email summary to carry the same review into the room and back into execution after the meeting.",
  },
];

const HowItWorks = () => {
  const { isLoggedIn, isLoading } = useAuth();

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-5">
          <p className="landing-kicker">How It Works</p>
          <h1 className="marketing-hero-title">From one feedback export to a meeting-ready governance review.</h1>
          <p className="max-w-3xl marketing-hero-body">
            Clarion follows a simple operating loop: upload feedback, structure the recurring service issues, assign
            follow-through, and carry the same brief into partner review.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={defaultSampleBriefPath} className="gov-btn-primary">
              Review sample brief
            </Link>
            <Link to={!isLoading && isLoggedIn ? "/upload" : "/demo"} className="gov-btn-secondary">
              {!isLoading && isLoggedIn ? "Begin with a CSV upload" : "See sample workspace"}
            </Link>
          </div>
        </div>
      </section>

      <section className="supporting-section">
        <div className="section-container grid gap-8 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
          <article className="supporting-lead">
            <p className="landing-kicker">Workflow</p>
            <h2 className="landing-section-title mt-4 text-[#111827]">Five steps, one operating record.</h2>
            <div className="landing-rail mt-8">
              {landingWorkflowSteps.map((step) => (
                <div key={step.step} className="landing-rail-step">
                  <div>
                    <p className="landing-rail-step-number">Step {step.step}</p>
                  </div>
                  <div>
                    <h3 className="text-xl font-semibold text-slate-900">{step.title}</h3>
                    <p className="mt-2 text-sm leading-7 text-slate-700">{step.body}</p>
                  </div>
                </div>
              ))}
            </div>
          </article>

          <div className="lg:sticky lg:top-24">
            <LandingOperatingPreview mode="outputs" />
            <p className="mt-3 text-sm leading-7 text-slate-600">
              Clarion is designed to make the output visible before the meeting starts: what clients are telling the
              firm, what is assigned, and what is still lagging.
            </p>
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-[#D7D0C3] bg-[rgba(255,250,244,0.72)]">
        <div className="section-container grid gap-5 lg:grid-cols-3">
          {postUploadRows.map((row) => (
            <article key={row.title} className="public-route-card">
              <p className="landing-kicker !text-[#5F6470]">After upload</p>
              <h2 className="mt-3 text-xl font-semibold text-slate-900">{row.title}</h2>
              <p className="mt-3 text-sm leading-7 text-slate-700">{row.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="supporting-section">
        <div className="section-container">
          <div className="supporting-cta-strip">
            <div className="max-w-2xl">
              <p className="landing-kicker !text-[#5F6470]">Run the cycle</p>
              <p className="mt-2 text-sm leading-7 text-slate-700">
                Start with the sample brief if you want the finished artifact first. Move to the sample workspace only
                if you want to inspect how the cycle is assembled step by step.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to={defaultSampleBriefPath} className="gov-btn-primary">
                Review sample brief
              </Link>
              <Link to={!isLoading && isLoggedIn ? "/upload" : "/demo"} className="gov-btn-secondary">
                {!isLoading && isLoggedIn ? "Begin with a CSV upload" : "See sample workspace"}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default HowItWorks;
