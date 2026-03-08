import { Clock, DollarSign, ShieldCheck } from "lucide-react";

const values = [
  { icon: Clock, text: "Respects your time — analysis in minutes, not weeks" },
  { icon: DollarSign, text: "Right-sized pricing for smaller practices" },
  { icon: ShieldCheck, text: "No long-term contracts — cancel anytime" },
];

const ValueStrip = () => (
  <section className="border-y border-slate-200 bg-slate-50">
    <div className="section-container py-12 lg:py-14">
      <div className="reveal flex flex-col items-center justify-center gap-8 md:flex-row md:gap-14">
        {values.map((v) => (
          <div key={v.text} className="flex items-center gap-3 text-sm font-medium text-slate-700">
            <v.icon size={18} className="shrink-0 text-amber-500" />
            <span>{v.text}</span>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default ValueStrip;

