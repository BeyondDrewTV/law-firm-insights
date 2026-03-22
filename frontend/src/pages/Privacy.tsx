import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";

const Privacy = () => (
  <PageLayout>
    <section className="marketing-hero">
      <div className="section-container max-w-4xl space-y-5">
        <p className="landing-kicker">Privacy</p>
        <h1 className="marketing-hero-title">Privacy Policy</h1>
        <p className="max-w-3xl marketing-hero-body">
          This page explains what Clarion collects, how that data is used, and how retention, deletion, and privacy
          requests work in the current product.
        </p>
        <MarketingProofBar
          items={[
            "No sale of customer data",
            "Current data flow described plainly",
            "Retention and deletion behavior included",
          ]}
        />
        <div className="public-route-card max-w-3xl">
          <p className="landing-kicker !text-[#5F6470]">What this page is for</p>
          <p className="mt-3 text-sm leading-7 text-slate-700">
            A plainspoken reference for current data handling. It is meant to answer practical questions about product
            data flow without turning privacy language into marketing copy.
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
              <p className="text-sm text-slate-700">What data Clarion collects to run the product.</p>
            </div>
            <div className="py-3">
              <p className="text-sm text-slate-700">How uploaded and generated workspace data is used.</p>
            </div>
            <div className="py-3 last:pb-0">
              <p className="text-sm text-slate-700">How retention, deletion, and privacy requests work today.</p>
            </div>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">What Clarion Collects</h2>
          <div className="trust-section-body">
            <p>
              Effective date: March 6, 2026. Clarion collects account details, authentication and security metadata,
              billing metadata, uploaded CSV contents, generated report records, action items, and related operational
              logs needed to run the service.
            </p>
            <ul className="list-disc space-y-2 pl-6">
              <li>Account data can include email address, firm name, login events, and team membership details.</li>
              <li>Uploaded data can include review dates, ratings, comments, and any other fields present in your CSV.</li>
              <li>Generated data can include themes, complaints, praise, scores, PDFs, action plans, and governance signals tied to your workspace.</li>
            </ul>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">How Clarion Uses Data</h2>
          <div className="trust-section-body">
            <p>
              We use your data to authenticate users, enforce plan limits, process billing, validate CSV uploads,
              generate governance reports and workspace records, support PDF export, send transactional emails, and
              operate support and security workflows.
            </p>
            <p>
              Clarion currently uses deterministic analysis and workflow logic to structure feedback into governance
              outputs. Billing is processed by Stripe. Partner-brief delivery and transactional email depend on
              configured email providers in the deployment environment, and we do not sell customer data.
            </p>
          </div>
        </article>

        <article className="trust-section">
          <h2 className="text-lg font-semibold text-slate-900">Retention, Deletion, and Requests</h2>
          <div className="trust-section-body">
            <p>
              Active reports remain in your workspace until you delete them or we process an account closure request.
              Deleted reports move to Recently Deleted and are scheduled for automatic purge after 30 days. Free
              workspaces do not have restore access unless paid restore access is added during that window; Team and
              Firm workspaces can restore deleted reports within current plan permissions and history limits.
            </p>
            <p>
              Clarion does not currently provide a self-serve full account deletion workflow on the public site. For
              export, deletion, correction, or privacy questions, contact{" "}
              <a href="mailto:support@clarionhq.co" className="font-semibold text-slate-900 hover:underline">
                support@clarionhq.co
              </a>.
            </p>
            <p>
              You are responsible for ensuring you have the right to upload and use the review data you submit to
              Clarion.
            </p>
          </div>
        </article>
      </div>
    </section>
  </PageLayout>
);

export default Privacy;
