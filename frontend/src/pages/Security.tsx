import { Lock, ShieldCheck, UserCheck } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";
import ShowDetails from "@/components/ShowDetails";
import { coreNarrative } from "@/content/marketingCopy";
import { PRODUCT_FLAGS } from "@/lib/productFlags";

const pillars = [
  {
    icon: Lock,
    title: "Data Protection",
    sentence: "Client feedback data is handled with practical safeguards for storage and transport.",
    bullets: [
      "Encrypted transport in production (HTTPS).",
      "Backups and infrastructure protections handled by the hosting layer.",
    ],
    iconTone: "bg-blue-500/20 border-blue-500/30 text-blue-400",
  },
  {
    icon: UserCheck,
    title: "Access Controls",
    sentence: "Workspace data access is scoped to authenticated accounts.",
    bullets: [
      "Protected routes and authenticated API checks.",
      "Session cookies use HttpOnly and SameSite protections.",
    ],
    iconTone: "bg-emerald-500/20 border-emerald-500/30 text-emerald-400",
  },
  {
    icon: ShieldCheck,
    title: "Responsible Use",
    sentence: "Firm data is used only to deliver your reporting workflow.",
    bullets: [
      "No sale of customer data for advertising.",
      "Report deletion is available in-product; account closure and privacy requests are handled through support.",
    ],
    iconTone: "bg-amber-500/20 border-amber-500/30 text-amber-400",
  },
];

const darkCardClass =
  "rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur-sm transition-colors duration-300";

const Security = () => {
  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container max-w-4xl space-y-5">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Security
          </p>
          <h1 className="marketing-hero-title">Security protections for client feedback workflows</h1>
          <p className="max-w-3xl marketing-hero-body">
            {coreNarrative} This page outlines implemented protections and access boundaries.
          </p>
          <MarketingProofBar
            items={[
              "Authentication required for workspace access",
              "Session-cookie protections in place",
              "Data used only for your reporting workflow",
            ]}
          />
          <div className="max-w-3xl rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-200">What this page covers</p>
            <p className="mt-2 text-sm leading-6 text-slate-200">
              Implemented safeguards, authentication boundaries, and current product security notes. It is a reference
              page for the live product, not a certification or compliance summary.
            </p>
          </div>
        </div>
      </section>

      <section className="supporting-section bg-gradient-to-br from-[#0F172A] via-[#1E3A5F] to-[#0F172A]">
        <div className="section-container">
          <div className="mb-6 max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-300">Core controls</p>
            <h2 className="mt-2 text-2xl font-semibold text-white md:text-3xl">Three practical security pillars</h2>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
          {pillars.map((pillar) => (
            <article key={pillar.title} className={darkCardClass}>
              <div
                className={`mb-4 flex h-10 w-10 items-center justify-center rounded-xl border ${pillar.iconTone}`}
              >
                <pillar.icon size={18} />
              </div>
              <h2 className="text-xl font-semibold text-white">{pillar.title}</h2>
              <p className="mt-2 text-sm text-slate-300">{pillar.sentence}</p>
              <ul className="mt-4 space-y-2">
                {pillar.bullets.map((bullet) => (
                  <li key={bullet} className="flex items-start gap-2 text-sm text-slate-300">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-400" />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-slate-200 bg-slate-50">
        <div className="section-container trust-stack">
          <article className="trust-intro">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Reference notes</p>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">
              These notes provide implementation detail behind the high-level security model above. They describe the
              current product state rather than future commitments.
            </p>
          </article>
          <div className="space-y-4">
            <ShowDetails
              title="Infrastructure and transport notes"
              summary="Traffic is expected to run behind HTTPS-enabled infrastructure, and production security headers are applied."
            >
              Session handling uses secure cookie defaults outside local development, with HttpOnly and SameSite protections
              in place. Uploaded CSV content is validated before processing and used to generate report outputs for the
              authenticated workspace.
            </ShowDetails>
            <ShowDetails
              title="Access model and account boundaries"
              summary="Sensitive routes require authentication and data access is scoped to account context."
            >
              The application enforces route protection in the frontend and API authentication checks in the backend
              integration layer. Account-level billing and usage state is mapped to each authenticated workspace.
            </ShowDetails>
            <ShowDetails
              title="Two-factor authentication"
              summary={
                PRODUCT_FLAGS.enableTwoFactorInV1
                  ? "Email-based two-factor authentication is available in Account Security settings."
                  : "Two-factor authentication is not included in V1."
              }
            >
              {PRODUCT_FLAGS.enableTwoFactorInV1
                ? "Users can activate email-based 2FA from dashboard security settings."
                : "For V1, security relies on password authentication, protected sessions, and scoped account access controls."}
            </ShowDetails>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Security;
