import { BarChart3, FileText, Zap } from "lucide-react";
import MarketingReportPreview from "@/components/MarketingReportPreview";

const proofBlocks = [
  {
    icon: BarChart3,
    title: "See The Issues That Keep Coming Back",
    desc: "The dashboard shows recurring client issues, trend movement, and what needs partner visibility now.",
    detail:
      "Instead of chasing anecdotes across inboxes and review sites, leadership gets one operating view of repeated client-service risk.",
  },
  {
    icon: Zap,
    title: "Turn Findings Into Owned Work",
    desc: "Assign owners, due dates, and success measures so the response does not disappear after the meeting.",
    detail:
      "Operations and partner teams can see what is owned, what is overdue, and where follow-through is slipping.",
  },
  {
    icon: FileText,
    title: "Bring A Brief, Not Raw Comments",
    desc: "Generate a governance brief that summarizes the cycle, the issues, and the next actions for leadership review.",
    detail: "The report is designed for partner discussion and operating review, not just recordkeeping.",
  },
];

const FeaturesSection = () => (
  <section id="features" className="section-padding border-y border-slate-200 bg-[#F6F8FC] opacity-100">
    <div className="section-container">
      <div className="reveal mb-10 max-w-3xl opacity-100">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Operating changes</p>
        <h2 className="text-4xl font-bold tracking-tight text-slate-900">What changes once the cycle is in place</h2>
        <p className="mt-3 max-w-2xl text-lg leading-relaxed text-slate-700">
          Clarion helps a firm move from uploaded feedback to recurring issues, accountable execution, and a brief
          leadership can use immediately.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_0.95fr]">
        <article className="reveal rounded-2xl border border-slate-300 bg-white px-6 py-4 shadow-sm">
          <div className="supporting-divider-list">
            {proofBlocks.map((block) => (
              <section key={block.title} className="py-5 first:pt-2 last:pb-2">
                <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-300 bg-slate-100 text-slate-800">
                  <block.icon size={18} />
                </div>
                <h3 className="text-2xl font-semibold text-slate-900">{block.title}</h3>
                <p className="mt-2 text-base leading-relaxed text-slate-700">{block.desc}</p>
                <p className="mt-2 text-base leading-relaxed text-slate-700">{block.detail}</p>
              </section>
            ))}
          </div>
        </article>

        <article className="reveal rounded-xl border border-slate-300 bg-white p-6 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Output reference</p>
          <h3 className="mt-2 text-2xl font-semibold text-slate-900">One brief, one operating record</h3>
          <p className="mt-2 text-sm leading-relaxed text-slate-700">
            Clarion's report and brief output give leadership one place to review recurring client issues, action
            ownership, and what should be discussed next.
          </p>
          <div className="mt-4 rounded-xl border border-slate-300 bg-slate-50 p-3">
            <MarketingReportPreview compact />
          </div>
        </article>
      </div>
    </div>
  </section>
);

export default FeaturesSection;
