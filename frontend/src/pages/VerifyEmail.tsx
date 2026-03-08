import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";

import PageLayout from "@/components/PageLayout";
import { verifyEmailToken } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";

type VerifyView = "verifying" | "verified" | "error";

const TRANSITION_MS = 220;
const REDIRECT_DELAY_MS = 700;
const STORAGE_EMAIL_KEY = "pending_verification_email";
const VERIFICATION_COMPLETED_KEY = "clarion_verification_completed_at";

const VerifyEmail = () => {
  const navigate = useNavigate();
  const { token: pathToken } = useParams<{ token?: string }>();
  const [searchParams] = useSearchParams();
  const { isLoggedIn, refreshUser, user } = useAuth();

  const [view, setView] = useState<VerifyView>("verifying");
  const [error, setError] = useState("");
  const transitionTimerRef = useRef<number | null>(null);

  const token = useMemo(() => pathToken || searchParams.get("token") || "", [pathToken, searchParams]);
  const verifiedNextStepLabel = isLoggedIn ? "Returning to your workspace..." : "Taking you back to sign in...";

  useEffect(() => {
    return () => {
      if (transitionTimerRef.current !== null) {
        window.clearTimeout(transitionTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    const run = async () => {
      if (!token) {
        setView("error");
        setError("Invalid verification link.");
        return;
      }

      const result = await verifyEmailToken(token);
      if (!result.verified) {
        setView("error");
        setError(result.error || "This verification link is invalid or expired.");
        return;
      }

      await refreshUser();
      setView("verified");
      window.localStorage.setItem(VERIFICATION_COMPLETED_KEY, String(Date.now()));
      transitionTimerRef.current = window.setTimeout(() => {
        const email = window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || "";
        navigate("/verify-complete", {
          replace: true,
          state: {
            justVerified: true,
            email,
          },
        });
      }, REDIRECT_DELAY_MS);
    };

    void run();
  }, [navigate, token]);

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl">
        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <div
            className="min-h-[240px] transition-all ease-in-out"
            style={{ transitionDuration: `${TRANSITION_MS}ms` }}
          >
            {view === "verifying" ? (
              <div className="flex min-h-[220px] flex-col items-center justify-center text-center animate-fade-in">
                <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
                <p className="mt-4 text-lg font-medium text-foreground">Verifying your email...</p>
              </div>
            ) : view === "verified" ? (
              <div className="flex min-h-[220px] flex-col items-center justify-center text-center animate-slide-up">
                <CheckCircle2 size={34} className="text-emerald-600" />
                <h1 className="mt-3 text-2xl font-semibold text-foreground">Email Verified</h1>
                <p className="mt-2 text-sm text-muted-foreground">{verifiedNextStepLabel}</p>
              </div>
            ) : (
              <div className="space-y-4 text-center animate-fade-in">
                <h1 className="text-2xl font-semibold text-foreground">Verification failed</h1>
                <p className="text-sm text-muted-foreground">{error}</p>
                <div className="flex flex-wrap justify-center gap-2">
                  <Link to="/check-email" className="gov-btn-secondary">
                    Return to check email
                  </Link>
                  <Link to="/signup" className="gov-btn-secondary">
                    Back to signup
                  </Link>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default VerifyEmail;
