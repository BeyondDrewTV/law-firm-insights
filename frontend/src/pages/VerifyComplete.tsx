import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import PageLayout from "@/components/PageLayout";
import { getRequiredAuthenticatedDestination, isUserOnboardingComplete } from "@/lib/authRedirect";

type SessionUser = {
  onboarding_complete?: boolean;
  has_firm_context?: boolean;
};

type SessionPayload = {
  success?: boolean;
  user?: SessionUser;
};

const REDIRECT_DELAY_MS = 700;
const STORAGE_EMAIL_KEY = "pending_verification_email";
const VERIFICATION_COMPLETED_KEY = "clarion_verification_completed_at";

const VerifyComplete = () => {
  const navigate = useNavigate();
  const redirectTimerRef = useRef<number | null>(null);
  const [nextStepLabel, setNextStepLabel] = useState("Preparing your next step...");

  useEffect(() => {
    let cancelled = false;

    const resolveSession = async (): Promise<SessionPayload | null> => {
      try {
        const response = await fetch("/api/auth/me", {
          method: "GET",
          credentials: "include",
        });
        if (!response.ok) return null;
        const payload = (await response.json()) as SessionPayload;
        return payload;
      } catch {
        return null;
      }
    };

    const run = async () => {
      const payload = await resolveSession();
      const user = payload?.user;

      let destination = "/login";
      let state: Record<string, unknown> | undefined;

      if (user) {
        const requiredDestination = getRequiredAuthenticatedDestination(user);
        destination = requiredDestination;
        setNextStepLabel(
          isUserOnboardingComplete(user)
            ? "Returning to your workspace..."
            : "Taking you into workspace setup...",
        );
      } else {
        const email = window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || "";
        state = { justVerified: true, email };
        setNextStepLabel("Email verified. Taking you to sign in...");
      }

      redirectTimerRef.current = window.setTimeout(() => {
        if (cancelled) return;
        window.localStorage.removeItem(VERIFICATION_COMPLETED_KEY);
        navigate(destination, { replace: true, state });
      }, REDIRECT_DELAY_MS);
    };

    void run();

    return () => {
      cancelled = true;
      if (redirectTimerRef.current !== null) {
        window.clearTimeout(redirectTimerRef.current);
      }
    };
  }, [navigate]);

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl">
        <div className="rounded-xl border border-border bg-card p-8 shadow-sm">
          <div className="flex min-h-[220px] flex-col items-center justify-center text-center animate-fade-in">
            <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-400 border-t-transparent" />
            <p className="mt-4 text-lg font-medium text-foreground">{nextStepLabel}</p>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default VerifyComplete;
