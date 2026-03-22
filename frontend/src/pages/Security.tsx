import { Lock, ShieldCheck, UserCheck } from "lucide-react";
import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";
import ShowDetails from "@/components/ShowDetails";
import { coreNarrative } from "@/content/marketingCopy";
import { PRODUCT_FLAGS } from "@/lib/productFlags";

const pillars = [
  {
    icon: Lock,
    title: "Data protection",
    sentence: "Client feedback data is handled with practical safeguards for storage and transport.",
    bullets: [
      "Encrypted transport in production.",
      "Backups and infrastructure protections handled by the hosting layer.",
    ],
  },
  {
    icon: UserCheck,
    title: "Access controls",
    sentence: "Workspace data access is scoped to authenticated accounts.",
    bullets: [
      "Protected routes and authenticated API checks.",
      "Session cookies use HttpOnly and SameSite protections.",
    ],
  },
  {
    icon: ShieldCheck,
    title: "Responsible use",
    sentence: "Firm data is used only to deliver your reporting workflow.",
    bullets: [
      "No sale of customer data for advertising.",
      "Report deletion is available in-product and privacy requests are handled through support.",
    ],
  },
];

const Security = () => {
  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container max-w-4xl space-y-5">
          <p className="landing-kicker">Security</p>
          <h1 className="marketing-hero-title">Security notes for the current Clarion workflow.</h1>
          <p className="max-w-3xl marketing-hero-body">
            {coreNarrative} This page is a practical reference for current safeguards, access boundaries, and product
            constraints. It is not a certification claim.
          </p>
          <MarketingProofBar
            items={[
              "Authentication required for workspace access",
              "Session protections in place",
              "Customer data is used only for the reporting workflow",
            ]}
          />
          <div className="public-route-card max-w-3xl">
            <p className="landing-kicker !text-[#5F6470]">What this page covers</p>
            <p className="mt-3 text-sm leading-7 text-slate-700">
              Implemented safeguards, authentication boundaries, and current product notes. This is a live-product
              reference page for firms evaluating Clarion's operating model.
            </p>
          </div>
        </div>
      </section>

      <section className="supporting-section">
        <div className="section-container">
          <div className="mb-6 max-w-2xl">
            <p className="landing-kicker">Core controls</p>
            <h2 className="mt-4 landing-section-title text-[#111827]">Three practical security pillars.</h2>
          </div>
          <div className="grid gap-5 lg:grid-cols-3">
            {pillars.map((pillar) => (
              <article key={pillar.title} className="public-route-card">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-2xl border border-[#D7D0C3] bg-[#FFF9EE] text-slate-800">
                  <pillar.icon size={18} />
                </div>
                <h2 className="text-xl font-semibold text-slate-900">{pillar.title}</h2>
                <p className="mt-3 text-sm leading-7 text-slate-700">{pillar.sentence}</p>
                <ul className="mt-4 space-y-2">
                  {pillar.bullets.map((bullet) => (
                    <li key={bullet} className="flex items-start gap-2 text-sm leading-7 text-slate-700">
                      <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[#8B6F3D]" />
                      <span>{bullet}</span>
                    </li>
                  ))}
                </ul>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-[#D7D0C3] bg-[rgba(255,250,244,0.72)]">
        <div className="section-container trust-stack">
          <article className="trust-intro">
            <p className="landing-kicker !text-[#5F6470]">Reference notes</p>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-700">
              These notes provide implementation detail behind the high-level model above. They describe the current
              product state rather than future commitments.
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
