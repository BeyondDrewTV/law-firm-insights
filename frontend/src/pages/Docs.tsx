import { Link } from "react-router-dom";
import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";

const Docs = () => (
  <PageLayout>
    <section className="marketing-hero">
      <div className="section-container space-y-4">
        <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
          Documentation
        </p>
        <h1 className="marketing-hero-title">What Clarion does today</h1>
        <p className="max-w-3xl marketing-hero-body">
          Clarion is a client-feedback governance workflow for law firms: upload feedback, review recurring client
          issues, assign owners, and generate a governance brief. This page is the truth layer for the current product,
          not another marketing summary.
        </p>
        <p className="max-w-3xl text-sm leading-6 text-white/75">
          Use it to separate what is shipped today from what remains manual, deployment-dependent, or intentionally
          read-only in the public demo.
        </p>
        <MarketingProofBar
          items={[
            "Current shipped workflow only",
            "Manual and deployment-dependent items named plainly",
            "Read-only demo boundaries kept explicit",
          ]}
        />
        <div className="flex flex-wrap gap-3 pt-1">
          <Link to="/demo" className="gov-btn-primary">
            Open read-only demo
          </Link>
          <Link to="/pricing" className="gov-btn-secondary">
            See plans
          </Link>
        </div>
      </div>
    </section>

    <section className="supporting-section border-y border-slate-200 bg-slate-50">
      <div className="section-container space-y-5">
        <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
          <article className="supporting-lead">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Current state</p>
            <h2 className="mt-2 text-2xl font-semibold text-slate-900">The product boundary is simple: what ships, what stays manual, and what remains demo-only.</h2>
            <div className="supporting-divider-list mt-5">
              <div className="py-4 first:pt-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Shipped workflow</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Upload one CSV export, review recurring client issues, assign follow-through, and generate a
                  governance brief.
                </p>
              </div>
              <div className="py-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Still manual or deployment-dependent
                </p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  CSV preparation, support inbox replies, and outbound delivery features still depend on the deployment
                  and current email configuration.
                </p>
              </div>
              <div className="py-4 last:pb-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Read-only demo</p>
                <p className="mt-2 text-sm leading-6 text-slate-700">
                  Public demo pages use sample law-firm data, stay read-only, and never write to a live workspace.
                </p>
              </div>
            </div>
          </article>

          <aside className="supporting-subtle">
            <h2 className="text-lg font-semibold text-slate-900">Current live references</h2>
            <p className="mt-2 text-sm text-slate-600">
              Use these pages when you want a specific answer instead of another high-level summary.
            </p>
            <div className="mt-4 space-y-2 text-sm">
              <Link to="/how-it-works" className="block font-medium text-slate-900 underline underline-offset-4">
                See how the workflow runs
              </Link>
              <Link to="/security" className="block font-medium text-slate-900 underline underline-offset-4">
                Review security notes
              </Link>
            </div>
            <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Next action</p>
              <p className="mt-2 text-sm text-slate-700">
                If the current shipped boundary fits your workflow, inspect the demo once and then choose the plan that
                matches your review cadence.
              </p>
              <div className="mt-3 flex flex-wrap gap-3">
                <Link to="/demo" className="gov-btn-primary">
                  Open read-only demo
                </Link>
                <Link to="/pricing" className="gov-btn-secondary">
                  See plans
                </Link>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>
  </PageLayout>
);

export default Docs;
