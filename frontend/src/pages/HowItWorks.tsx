import { Link } from "react-router-dom";
import { ArrowDown, ArrowLeft, BarChart3, BriefcaseBusiness, Upload } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import MarketingReportPreview from "@/components/MarketingReportPreview";
import { useAuth } from "@/contexts/AuthContext";
import {
  confidenceDefinition,
  implementationPlanDefinition,
  trendStabilityDefinition,
} from "@/content/marketingCopy";

const loopSteps = [
  {
    icon: Upload,
    title: "Upload",
    description: "Import one CSV export and confirm the required structure before analysis starts.",
    bullets: ["Checks required columns", "Flags malformed or empty rows"],
  },
  {
    icon: BarChart3,
    title: "Review",
    description: "Surface recurring client issues, report movement, and what needs partner visibility now.",
    bullets: [trendStabilityDefinition, confidenceDefinition],
  },
  {
    icon: BriefcaseBusiness,
    title: "Act",
    description: "Assign owners, timelines, and next steps so the cycle produces accountable follow-through.",
    bullets: [implementationPlanDefinition, "Governance brief prepared for leadership review"],
  },
];

const darkCardClass =
  "rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition-colors duration-300";

const HowItWorks = () => {
  const { isLoggedIn, isLoading } = useAuth();

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-4">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            How It Works
          </p>
          <h1 className="marketing-hero-title">See the workflow once, clearly.</h1>
          <p className="max-w-2xl marketing-hero-body">
            Clarion takes one review-period export through a simple operating loop: validate the CSV, surface recurring
            client issues, assign follow-through, and prepare the governance brief for leadership review.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link to="/demo" className="gov-btn-primary">
              Open read-only example cycle
            </Link>
            <Link to={!isLoading && isLoggedIn ? "/upload" : "/pricing"} className="gov-btn-secondary">
              {!isLoading && isLoggedIn ? "Begin with a CSV upload" : "See plans"}
            </Link>
          </div>
        </div>
      </section>

      <section id="reporting-loop" className="supporting-section bg-gradient-to-br from-[#0F172A] via-[#1E3A5F] to-[#0F172A]">
        <div className="section-container">
          <h2 className="text-3xl font-bold text-white md:text-4xl">The operating loop</h2>
          <p className="mt-2 text-lg text-slate-200">
            One cycle turns feedback into issues, ownership, and the next leadership discussion.
          </p>

          <div className="mt-8 hidden items-stretch gap-3 lg:grid lg:grid-cols-[1fr_auto_1fr_auto_1fr]">
            {loopSteps.map((step, index) => (
              <div key={step.title} className="contents">
                <article className={`${darkCardClass} relative overflow-hidden`}>
                  <p className="absolute -top-3 left-2 text-6xl font-black text-blue-500/20">{index + 1}</p>
                  <div className="relative">
                    <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-500/20">
                      <step.icon className="text-blue-400" size={20} />
                    </div>
                    <p className="text-xs uppercase tracking-widest text-blue-400">Step {index + 1}</p>
                    <h3 className="mt-1 text-xl font-bold text-white">{step.title}</h3>
                    <p className="mt-2 text-sm text-slate-200">{step.description}</p>
                    <ul className="mt-3 space-y-1.5">
                      {step.bullets.map((bullet) => (
                        <li key={bullet} className="text-xs text-slate-200">
                          - {bullet}
                        </li>
                      ))}
                    </ul>
                  </div>
                </article>
                {index < loopSteps.length - 1 && (
                  <div className="flex items-center justify-center text-2xl text-blue-500">&rarr;</div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-6 space-y-3 lg:hidden">
            {loopSteps.map((step, index) => (
              <div key={step.title}>
                <article className={`${darkCardClass} relative overflow-hidden`}>
                  <p className="absolute -top-3 left-2 text-6xl font-black text-blue-500/20">{index + 1}</p>
                  <div className="relative">
                    <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-xl border border-blue-500/30 bg-blue-500/20">
                      <step.icon className="text-blue-400" size={20} />
                    </div>
                    <p className="text-xs uppercase tracking-widest text-blue-400">Step {index + 1}</p>
                    <h3 className="mt-1 text-xl font-bold text-white">{step.title}</h3>
                    <p className="mt-2 text-sm text-slate-200">{step.description}</p>
                  </div>
                </article>
                {index < loopSteps.length - 1 && (
                  <div className="flex justify-center py-2 text-blue-500">
                    <ArrowDown size={18} />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-slate-300">
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs font-semibold uppercase tracking-widest text-slate-300">Return lane</p>
              <div className="inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-2.5 py-1 text-xs text-slate-200">
                Repeat
                <ArrowLeft size={13} className="text-blue-400" />
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-200">
              After action items are assigned, run the next upload cycle to measure movement.
            </p>
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-slate-200 bg-slate-50">
        <div className="section-container space-y-5">
          <div className="grid gap-5 lg:grid-cols-[1.08fr_0.92fr]">
            <article className="supporting-lead">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">After upload</p>
              <h2 className="mt-2 text-2xl font-bold text-slate-900">The product does three things, in order.</h2>
              <div className="supporting-divider-list mt-5">
                <div className="py-4 first:pt-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">1. Validation</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    Clarion checks required CSV columns and flags obvious formatting problems before analysis.
                  </p>
                </div>
                <div className="py-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">2. Report creation</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    The app creates a governance report, surfaces recurring client issues, and updates the current cycle.
                  </p>
                </div>
                <div className="py-4 last:pb-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">3. Follow-through</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">
                    Your team reviews owners, due dates, and the governance brief. Clarion does not auto-contact clients
                    or partners on its own.
                  </p>
                </div>
              </div>
            </article>

            <article className="supporting-subtle">
              <h2 className="text-xl font-bold text-slate-900">See the output before you upload</h2>
              <p className="mt-2 text-sm text-slate-600">
                One read-only example is enough to show what the finished cycle looks like in product.
              </p>
              <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <MarketingReportPreview compact />
              </div>
              <p className="mt-3 text-xs text-slate-500">
                Read-only example report: recurring client issues, action ownership, and the same brief structure used
                in product.
              </p>
            </article>
          </div>

          <div className="supporting-cta-strip">
            <p className="text-sm text-slate-600">Inspect the finished output first, then move to a live upload when you are ready to run your own cycle.</p>
            <div className="flex flex-wrap gap-3">
              <Link to="/demo" className="gov-btn-primary">
                Open read-only example cycle
              </Link>
              <Link to={!isLoading && isLoggedIn ? "/upload" : "/pricing"} className="gov-btn-secondary">
                {!isLoading && isLoggedIn ? "Begin with a CSV upload" : "See plans"}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default HowItWorks;
