import { Building, Scale, Users } from "lucide-react";

const items = [
  {
    icon: Scale,
    title: "Built For Lean Firm Teams",
    desc: "Designed for small to mid-sized practices that want tighter oversight without the drag of enterprise software.",
  },
  {
    icon: Users,
    title: "Operational, Not Theoretical",
    desc: "Each cycle ends with concrete next steps, visible owners, and a brief ready for leadership review.",
  },
  {
    icon: Building,
    title: "Low Friction By Design",
    desc: "CSV upload, validated processing, and no required integrations to begin a disciplined review cycle.",
  },
];

const CredibilityStrip = () => (
  <section className="border-y border-slate-200 bg-slate-50">
    <div className="section-container py-12 lg:py-16">
      <div className="mb-8 max-w-2xl">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Why it fits</p>
        <p className="mt-2 text-sm leading-6 text-slate-700">
          Clarion is intentionally narrow: a practical review cycle for firms that want discipline without adding a
          large software program around it.
        </p>
      </div>
      <div className="grid gap-8 md:grid-cols-3 reveal">
        {items.map((item) => (
          <div key={item.title} className="flex gap-4">
            <div className="shrink-0 flex h-10 w-10 items-center justify-center rounded-lg border border-blue-100 bg-blue-50">
              <item.icon size={20} className="text-blue-600" />
            </div>
            <div>
              <h3 className="mb-1 text-base font-semibold text-slate-800">{item.title}</h3>
              <p className="text-sm leading-relaxed text-slate-700">{item.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default CredibilityStrip;
