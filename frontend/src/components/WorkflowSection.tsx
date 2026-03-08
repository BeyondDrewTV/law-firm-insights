import { Link } from "react-router-dom";
import { Cpu, FileBarChart, Upload } from "lucide-react";

const steps = [
  {
    num: "01",
    icon: Upload,
    title: "Upload Client Feedback",
    desc: "Bring in one CSV export and confirm the required columns before analysis starts.",
  },
  {
    num: "02",
    icon: Cpu,
    title: "See What Keeps Repeating",
    desc: "Clarion groups recurring feedback into client issues your team can review in one operating view.",
  },
  {
    num: "03",
    icon: FileBarChart,
    title: "Assign Owners And Bring The Brief",
    desc: `Assign follow-through and prepare the governance brief for leadership review.`,
  },
];

const WorkflowSection = () => (
  <section id="workflow" className="section-padding">
    <div className="section-container">
      <div className="mb-10 text-center reveal">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-300">Workflow</p>
        <h2 className="text-3xl font-bold text-white lg:text-4xl">The operating loop, in one pass</h2>
        <p className="mx-auto mt-2 max-w-2xl text-base text-slate-300">
          Clarion takes one feedback cycle from uploaded export to partner-ready follow-through.
        </p>
      </div>

      <div className="grid gap-8 md:grid-cols-3">
        {steps.map((step, index) => (
          <div key={step.num} className="relative reveal" style={{ transitionDelay: `${index * 120}ms` }}>
            {index < steps.length - 1 && (
              <div className="absolute left-[60%] top-12 hidden w-[80%] border-t border-dashed border-blue-300/30 md:block" />
            )}
              <div className="relative rounded-xl border border-slate-200 bg-white p-6 text-center shadow-sm">
                <span className="mb-4 block text-xs font-bold tracking-widest text-amber-500">STEP {step.num}</span>
                <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-blue-600">
                  <step.icon size={24} className="text-white" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-slate-900">{step.title}</h3>
                <p className="text-sm leading-relaxed text-slate-700">{step.desc}</p>
              </div>
            </div>
        ))}
      </div>

      <div className="mt-8 flex justify-center reveal">
        <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-center">
          <p className="text-sm text-slate-200">See the full workflow once, then inspect the same sequence in the read-only example cycle.</p>
          <div className="mt-3 flex flex-wrap justify-center gap-3">
            <Link to="/how-it-works" className="gov-btn-secondary">
              See full workflow
            </Link>
            <Link to="/demo" className="text-sm font-medium text-blue-300 underline underline-offset-4 transition-colors hover:text-blue-200">
              Open read-only example
            </Link>
          </div>
        </div>
      </div>
    </div>
  </section>
);

export default WorkflowSection;
