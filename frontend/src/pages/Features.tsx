import { Link } from "react-router-dom";
import { BriefcaseBusiness, CheckCircle2, ShieldAlert } from "lucide-react";
import InfoTooltip from "@/components/InfoTooltip";
import MarketingReportPreview from "@/components/MarketingReportPreview";
import PageLayout from "@/components/PageLayout";
import { useAuth } from "@/contexts/AuthContext";
import { implementationPlanDefinition } from "@/content/marketingCopy";

const personaBands = [
  {
    id: "partners",
    title: "For Managing Partners",
    description: "Use the cycle to see where client experience needs leadership attention before the next meeting.",
    icon: ShieldAlert,
    iconTone: "bg-amber-500/20 border-amber-500/30 text-amber-400",
    outcomes: [
      {
        label: "Spot recurring service risk before it becomes client loss.",
        detail: "Client issues are surfaced from repeated negative patterns across the uploaded review set.",
      },
      {
        label: "Review one operating record instead of reading every comment.",
        detail: "Reports summarize movement and repeated complaints in one place.",
      },
      {
        label: "Walk into the meeting with a brief and a next-step agenda.",
        detail: "The governance brief keeps issues, actions, and discussion points aligned.",
      },
    ],
  },
  {
    id: "operations",
    title: "For Operations Leaders",
    description: "Run the cycle consistently and keep follow-through visible after the meeting ends.",
    icon: BriefcaseBusiness,
    iconTone: "bg-blue-500/20 border-blue-500/30 text-blue-400",
    outcomes: [
      {
        label: "Keep report status, review volume, and action ownership in one workspace.",
        detail: "The product keeps current-cycle output tied to the next round of execution.",
      },
      {
        label: "Assign owners, timelines, and measurable success criteria.",
        detail: implementationPlanDefinition,
      },
      {
        label: "Preserve a report record the team can return to next cycle.",
        detail: "Reports and briefs stay connected to the same operating history.",
      },
    ],
  },
  {
    id: "intake",
    title: "For Intake And Marketing",
    description: "Turn repeated complaints into specific service-improvement priorities instead of anecdotal fixes.",
    icon: CheckCircle2,
    iconTone: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
    outcomes: [
      {
        label: "See where communication and intake friction repeat.",
        detail: "Theme grouping highlights where clients report the same problem over and over.",
      },
      {
        label: "Tie service fixes to owners rather than informal notes.",
        detail: "Clarion keeps action ownership visible after the cycle is reviewed.",
      },
      {
        label: "Compare one cycle to the next when process changes are made.",
        detail: "Recurring use helps teams see whether the service experience is moving in the right direction.",
      },
    ],
  },
];

const darkCardClass =
  "rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition-colors duration-300";

const Features = () => {
  const { isLoggedIn, isLoading } = useAuth();

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-4">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Features
          </p>
          <h1 className="marketing-hero-title">Built for the people who have to run the cycle.</h1>
          <p className="max-w-3xl marketing-hero-body">
            Clarion is most useful when leadership, operations, and client-facing teams can work from the same client
            feedback record without turning it into another loose analytics exercise.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            {!isLoading && isLoggedIn ? (
              <Link to="/dashboard" className="gov-btn-primary">
                Go to Dashboard
              </Link>
            ) : (
              <Link to="/pricing" className="gov-btn-primary">
                See plans
              </Link>
            )}
            <Link to="/demo" className="gov-btn-secondary">
              Open read-only example cycle
            </Link>
          </div>
        </div>
      </section>

      <section className="supporting-section bg-gradient-to-br from-[#0F172A] via-[#1E3A5F] to-[#0F172A]">
        <div className="section-container grid gap-6 lg:grid-cols-[0.95fr_1.05fr] lg:items-start">
          <article className={`${darkCardClass} lg:sticky lg:top-24`}>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-300">Shared operating record</p>
            <h2 className="mt-3 text-3xl font-bold text-white md:text-4xl">
              One product view should settle the meeting, not create more interpretation work.
            </h2>
            <p className="mt-3 max-w-xl text-sm leading-6 text-slate-200">
              Clarion is strongest when leadership, operations, and client-facing teams can work from the same client
              feedback record, see what moved, and leave with owned follow-through.
            </p>
          </article>

          <div className="space-y-4">
            {personaBands.map((band) => (
              <article key={band.id} className={darkCardClass}>
                <div className="grid gap-5 lg:grid-cols-[220px_1fr] lg:items-start">
                  <div>
                    <div className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl border ${band.iconTone}`}>
                      <band.icon size={20} />
                    </div>
                    <h2 className="text-xl font-bold text-white">{band.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-200">{band.description}</p>
                  </div>
                  <ul className="supporting-divider-list">
                    {band.outcomes.map((outcome) => (
                      <li key={outcome.label} className="py-3 text-sm text-slate-200 first:pt-0 last:pb-0">
                        <span className="inline-flex items-start">
                          {outcome.label}
                          <InfoTooltip title={outcome.label} body={outcome.detail} />
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-slate-200 bg-slate-50">
        <div className="section-container space-y-5">
          <article className="supporting-lead">
            <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
              <div>
                <h2 className="text-3xl font-bold text-slate-900 md:text-4xl">One operating record the whole firm can use</h2>
                <p className="mt-2 text-lg text-slate-500">
                  Clarion is strongest when the same cycle supports leadership review, operational follow-through, and
                  the next round of service improvement.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                <MarketingReportPreview compact />
                <p className="mt-2 text-xs text-slate-500">
                  One shared report view keeps recurring client issues, action owners, and the leadership brief aligned.
                </p>
              </div>
            </div>
          </article>

          <div className="supporting-cta-strip">
            <p className="text-sm text-slate-600">See the example cycle if you want proof first, or move straight to the plan that fits your review rhythm.</p>
            <div className="flex flex-wrap gap-3">
              {!isLoading && isLoggedIn ? (
                <Link to="/dashboard" className="gov-btn-primary">
                  Go to Dashboard
                </Link>
              ) : (
                <Link to="/pricing" className="gov-btn-primary">
                  See plans
                </Link>
              )}
              <Link to="/demo" className="gov-btn-secondary">
                Open read-only example cycle
              </Link>
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Features;
