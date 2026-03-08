import { Calendar, FileText, ListChecks, PieChart } from "lucide-react";
import MarketingReportPreview from "@/components/MarketingReportPreview";
import MarketingDashboardPreview from "@/components/MarketingDashboardPreview";

const deliverables = [
  { icon: PieChart, text: "Weekly: Review client issues" },
  { icon: ListChecks, text: "Monthly: Assign partner actions" },
  { icon: Calendar, text: "Quarterly: Generate governance brief" },
  { icon: FileText, text: "Use one cycle record across leadership meetings" },
];

const ReportSection = () => (
  <section id="report-preview" className="section-padding">
    <div className="section-container">
      <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
        <div className="reveal">
          <span className="mb-5 inline-block rounded border border-amber-300/40 bg-amber-100/20 px-2 py-1 text-[10px] font-semibold uppercase tracking-wide text-amber-200">
            Governance Workflow
          </span>
          <h2 className="text-4xl font-bold text-white">How firms run Clarion in practice</h2>
          <p className="mb-8 leading-relaxed text-slate-300">
            Clarion supports a repeatable operating cadence, from weekly client issue checks to quarterly governance brief
            generation.
          </p>
          <div className="grid gap-4 sm:grid-cols-2">
            {deliverables.map((d) => (
              <div key={d.text} className="flex items-start gap-3">
                <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-blue-500/35 bg-blue-500/20">
                  <d.icon size={16} className="text-blue-300" />
                </div>
                <span className="text-sm font-medium leading-snug text-slate-100">{d.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="reveal">
          <div className="space-y-4">
            <div className="rounded-xl border border-white/10 bg-slate-950/25 p-3">
              <MarketingDashboardPreview compact variant="overview" />
            </div>
            <div className="rounded-xl border border-white/10 bg-slate-950/25 p-3">
              <MarketingReportPreview compact />
            </div>
            <div className="rounded-lg border border-slate-300 bg-white px-4 py-3 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-slate-500">Product Visual Strip</p>
              <p className="mt-1 text-sm text-slate-700">
                Uses real dashboard and report surfaces from the product interface.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default ReportSection;
