import { Link } from "react-router-dom";
import { BriefcaseBusiness, Building2, UserRoundSearch } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import LandingOperatingPreview from "@/components/landing/LandingOperatingPreview";
import { useAuth } from "@/contexts/AuthContext";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

const roleBands = [
  {
    id: "partners",
    title: "Managing partners",
    body: "See what clients are telling the firm, where partner attention is required, and which actions are still stalled before the next review meeting.",
    icon: Building2,
  },
  {
    id: "operations",
    title: "Operations leaders",
    body: "Run the review cycle consistently, keep ownership visible, and carry the same operating record from upload through follow-through.",
    icon: BriefcaseBusiness,
  },
  {
    id: "client-service",
    title: "Client service and intake owners",
    body: "Turn repeated complaints into named issues, assigned fixes, and a cleaner handoff back into the next cycle.",
    icon: UserRoundSearch,
  },
];

const featureGroups = [
  {
    title: "Clarify what needs partner attention",
    body: "Clarion structures recurring service issues so leaders can review the pattern quickly instead of reading every comment one by one.",
    bullets: [
      "Recurring communication, billing, and responsiveness issues are surfaced together.",
      "The same cycle keeps issue summaries connected to the source report.",
    ],
  },
  {
    title: "Keep action ownership in the same record",
    body: "The product is designed to stop decisions from disappearing into meeting notes.",
    bullets: [
      "Owners, due dates, and current status stay attached to the same review cycle.",
      "The brief and workspace point to the same follow-through record.",
    ],
  },
  {
    title: "Carry the output into the room",
    body: "Clarion gives the firm a meeting-ready operating artifact, not a dashboard wall that still needs interpretation.",
    bullets: [
      "Use the workspace, PDF brief, and email summary from the same cycle.",
      "Review what changed, what is unresolved, and what should be escalated now.",
    ],
  },
];

const Features = () => {
  const { isLoggedIn, isLoading } = useAuth();

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-5">
          <p className="landing-kicker">Features</p>
          <h1 className="marketing-hero-title">Built for the people who have to run the review cycle, not admire it.</h1>
          <p className="max-w-3xl marketing-hero-body">
            Clarion gives law firms one operating record for client feedback: what clients are saying, what needs
            partner attention, who owns the response, and what still needs to move before the next meeting.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={defaultSampleBriefPath} className="gov-btn-primary">
              Review sample brief
            </Link>
            {!isLoading && isLoggedIn ? (
              <Link to="/upload" className="gov-btn-secondary">
                Begin with a CSV upload
              </Link>
            ) : (
              <Link to="/demo" className="gov-btn-secondary">
                See sample workspace
              </Link>
            )}
          </div>
        </div>
      </section>

      <section className="supporting-section">
        <div className="section-container grid gap-5 lg:grid-cols-3">
          {roleBands.map((band) => (
            <article key={band.id} className="public-route-card">
              <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#D7D0C3] bg-[#FFF9EE] text-slate-800">
                <band.icon size={20} />
              </div>
              <p className="landing-kicker !text-[#5F6470]">{band.title}</p>
              <p className="mt-3 text-base leading-7 text-slate-700">{band.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="supporting-section border-y border-[#D7D0C3] bg-[rgba(255,250,244,0.72)]">
        <div className="section-container grid gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start">
          <article className="supporting-lead">
            <p className="landing-kicker">What stays consistent</p>
            <h2 className="landing-section-title mt-4 text-[#111827]">
              Every role works from the same governance record.
            </h2>
            <p className="mt-4 max-w-xl text-base leading-8 text-slate-700">
              Clarion does not ask leadership, operations, and client-service owners to work from separate stories.
              The same cycle produces the brief, the action rows, and the workspace record used to check whether the
              firm is improving.
            </p>
            <div className="mt-8 space-y-4">
              {featureGroups.map((group) => (
                <article key={group.title} className="rounded-2xl border border-[#DED7CA] bg-white/80 p-5">
                  <h3 className="text-lg font-semibold text-slate-900">{group.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-600">{group.body}</p>
                  <ul className="mt-4 space-y-2 text-sm leading-7 text-slate-700">
                    {group.bullets.map((bullet) => (
                      <li key={bullet} className="flex items-start gap-2">
                        <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#8B6F3D]" />
                        <span>{bullet}</span>
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
            </div>
          </article>

          <div className="lg:sticky lg:top-24">
            <LandingOperatingPreview mode="outputs" />
            <p className="mt-3 text-sm leading-7 text-slate-600">
              The live product is strongest when the brief, action ownership, and meeting agenda are all visible in one
              place instead of scattered across separate tools.
            </p>
          </div>
        </div>
      </section>

      <section className="supporting-section">
        <div className="section-container">
          <div className="supporting-cta-strip">
            <div className="max-w-2xl">
              <p className="landing-kicker !text-[#5F6470]">Next step</p>
              <p className="mt-2 text-sm leading-7 text-slate-700">
                Review the sample brief first if you want the finished artifact. Move to the sample workspace only if
                you want to inspect the mechanics behind that same story.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <Link to={defaultSampleBriefPath} className="gov-btn-primary">
                Review sample brief
              </Link>
              {!isLoading && isLoggedIn ? (
                <Link to="/upload" className="gov-btn-secondary">
                  Begin with a CSV upload
                </Link>
              ) : (
                <Link to="/demo" className="gov-btn-secondary">
                  See sample workspace
                </Link>
              )}
            </div>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Features;
