import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";

const FinalCTA = () => (
  <section id="final-cta" className="section-padding border-t border-border bg-background">
    <div className="section-container">
      <div className="gov-level-2 reveal rounded-3xl p-8 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Next step</p>
        <h2 className="section-heading mb-3">Start a more disciplined review cycle.</h2>
        <p className="mx-auto max-w-2xl text-base text-neutral-700">
          Bring in one CSV, review what is repeating, and give leadership a clearer record of what needs follow-through.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <Link to="/signup" className="gov-btn-primary">
            Start Your Workspace <ArrowRight size={15} className="ml-2" />
          </Link>
          <Link to="/demo" className="gov-btn-secondary">
            Explore read-only demo
          </Link>
        </div>
        <p className="mt-4 text-xs text-neutral-600">
          Start when you are ready, or inspect the sample workflow once more before opening a live workspace.
        </p>
        <div className="mt-6 border-t border-slate-200 pt-4">
          <Link to="/pricing" className="text-sm font-medium text-slate-700 underline underline-offset-4 transition-colors hover:text-slate-900">
            Review plans and limits
          </Link>
        </div>
      </div>
    </div>
  </section>
);

export default FinalCTA;
