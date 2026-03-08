import { Download, Lock, ShieldCheck } from "lucide-react";

const trustPoints = [
  {
    icon: Lock,
    title: "Encrypted Review Processing",
    desc: "Traffic is protected in transit and uploads are processed through authenticated workspace routes.",
  },
  {
    icon: ShieldCheck,
    title: "No Client PII Stored",
    desc: "Clarion is designed to process review feedback for governance analysis without storing client PII fields.",
  },
  {
    icon: Download,
    title: "Data Export Available",
    desc: "Firms can export governance artifacts for leadership meetings and internal records.",
  },
];

const SecuritySection = () => (
  <section id="security" className="section-padding border-y border-border bg-background">
    <div className="section-container">
      <div className="mb-12 text-center reveal">
        <h2 className="section-heading text-slate-900">Trust and Security</h2>
        <p className="section-subheading mx-auto text-slate-700">
          Built for legal teams that require a clean governance workflow and clear operational safeguards.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {trustPoints.map((point, index) => (
          <article key={point.title} className="gov-level-2 reveal p-6 text-left" style={{ transitionDelay: `${index * 90}ms` }}>
            <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-slate-700">
              <point.icon size={18} />
            </div>
            <h3 className="text-lg font-semibold text-slate-900">{point.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-700">{point.desc}</p>
          </article>
        ))}
      </div>
    </div>
  </section>
);

export default SecuritySection;
