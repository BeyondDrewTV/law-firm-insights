import { useNavigate } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import PageLayout from "@/components/PageLayout";

const VerifySuccess = () => {
  const navigate = useNavigate();

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card rounded-xl border border-white/25 bg-card p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)] transition-all motion-slow ease-out">
          <div className="flex min-h-[240px] flex-col items-center justify-center text-center animate-fade-in">
            <CheckCircle2 size={36} className="text-emerald-600" />
            <h1 className="mt-4 text-3xl font-semibold text-slate-900">Your email has been verified.</h1>
            <button
              type="button"
              className="gov-btn-primary mt-6"
              onClick={() => navigate("/verify-complete", { replace: true })}
            >
              Continue to Clarion
            </button>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default VerifySuccess;
