import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";

const Terms = () => (
  <PageLayout>
    <section className="marketing-hero">
      <div className="section-container max-w-4xl space-y-5">
        <p className="landing-kicker">Terms</p>
        <h1 className="marketing-hero-title">Terms of Service</h1>
        <p className="max-w-3xl marketing-hero-body">
          This page explains the service scope, customer responsibilities, and the current billing, retention, and
          availability boundaries for Clarion.
        </p>
        <MarketingProofBar
          items={[
            "Written for current Clarion workflows",
            "Plan and deletion behavior included",
            "Analysis and report boundaries stated plainly",
          ]}
        />
        <div className="public-route-card max-w-3xl">
          <p className="landing-kicker !text-[#5F6470]">What this page is for</p>
          <p className="mt-3 text-sm leading-7 text-slate-700">
            A current-product terms reference. It is meant to clarify how Clarion is provided and where responsibility
            remains with the customer.
          </p>
        </div>
      </div>
    </section>

    <section className="supporting-section border-y border-slate-200 bg-slate-50">
      <div className="section-container trust-stack">
        <article className="trust-intro">
          <p className="landing-kicker !text-[#5F6470]">Quick map</p>
          <div className="trust-divider-list mt-4">
            <div className="py-3 first:pt-0">
              <p className="text-sm text-slate-700">What Clarion includes in the service today.</p>
            </div>
            <div className="py-3">
              <p className="text-sm text-slate-700">What customers are responsible for when using the product.</p>
            </div>
            <div className="py-3 last:pb-0">
              <p className="text-sm text-slate-700">How billing, deleted-report retention, and availability are framed.</p>
            </div>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">Service Scope</h2>
          <div className="trust-section-body">
            <p>
              Effective date: March 6, 2026. Clarion is a software product for uploading CSV-based client feedback,
              generating governance reports, reviewing the resulting governance record in the workspace, assigning
              follow-up actions, and exporting report PDFs based on the features available on your plan.
            </p>
            <ul className="list-disc space-y-2 pl-6">
              <li>Free, Team, and Firm plans have different limits for reviews per upload, reports per month, seats, PDF output, report history access, and deleted-report restore.</li>
              <li>Partner-brief email delivery is available only when Clarion email delivery is configured in the deployment environment.</li>
              <li>Clarion supports client-feedback governance and follow-through. It does not provide legal advice.</li>
            </ul>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">Customer Responsibilities</h2>
          <div className="trust-section-body">
            <p>
              You are responsible for the lawfulness of the data you upload and for managing access to your workspace.
            </p>
            <p>
              You may not upload data you do not have the right to use, attempt to bypass account or plan controls,
              interfere with the service, or use Clarion to send spam or unlawful content.
            </p>
            <p>
              You remain solely responsible for your legal work, client relationships, regulatory duties, and decisions
              made from any report output, issue summary, or recommended action.
            </p>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">Billing, Retention, and Availability</h2>
          <div className="trust-section-body">
            <p>
              Paid checkout is processed through Stripe. Subscription pricing and plan limits may change over time.
              Unless required by law, fees are non-refundable after the purchased billing period or report entitlement
              has been provisioned.
            </p>
            <p>
              Reports you delete move to Recently Deleted for up to 30 days before automatic purge. Free workspaces do
              not have restore access unless paid restore access is added during that 30-day window. Team and Firm
              workspaces can restore deleted reports within the retention window, subject to current plan permissions,
              owner-level access, and applicable history limits. Clarion does not currently provide a self-serve full
              account deletion flow on the public site; contact support for account closure requests.
            </p>
            <p>
              The service is provided on an &quot;as is&quot; and &quot;as available&quot; basis. We aim for reliability, but we do not
              guarantee uninterrupted availability, error-free analysis, or uninterrupted third-party services such as
              billing and email delivery.
            </p>
          </div>
        </article>
      </div>
    </section>
  </PageLayout>
);

export default Terms;
