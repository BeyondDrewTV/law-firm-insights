import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { AlertTriangle, CheckCircle2 } from "lucide-react";

import PageLayout from "@/components/PageLayout";
import { verifyEmailToken } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";

type VerifyView = "verifying" | "verified" | "error";

const TRANSITION_MS = 220;
const REDIRECT_DELAY_MS = 700;
const STORAGE_EMAIL_KEY = "pending_verification_email";
const VERIFICATION_COMPLETED_KEY = "clarion_verification_completed_at";

/** Map raw API error strings → human-readable copy shown in the UI. */
function humanVerifyError(raw: string): string {
  const lower = raw.toLowerCase();
  if (lower.includes("expired") || lower.includes("expir")) {
    return "This verification link has expired. Links are valid for 24 hours after signup.";
  }
  if (lower.includes("already") || lower.includes("used") || lower.includes("already_verified")) {
    return "This link has already been used. Your email may already be verified — try signing in.";
  }
  if (lower.includes("invalid") || lower.includes("not found") || lower.includes("no token")) {
    return "This verification link is invalid or malformed. Please request a new one.";
  }
  if (lower.includes("network") || lower.includes("unable")) {
    return "We couldn't reach the server to verify your link. Check your connection and try again.";
  }
  // Fallback — still friendlier than a raw API string
  return "We couldn't verify this link. It may have expired or already been used.";
}

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
        setError("This verification link is missing or incomplete. Please request a new one.");
        return;
      }

      const result = await verifyEmailToken(token);
      if (!result.verified) {
        setView("error");
        setError(humanVerifyError(result.error || ""));
        return;
      }

      // Mark verification timestamp so VerifyComplete can skip an extra /me call
      window.localStorage.setItem(VERIFICATION_COMPLETED_KEY, String(Date.now()));

      // Refresh the in-memory user so AuthContext reflects email_verified=true.
      // On HTTPS production the browser will accept the new session cookie only if
      // it carries the Secure flag — which is set correctly after the backend fix.
      // We call refreshUser() first; if it resolves a logged-in user we go to
      // /verify-complete (which re-checks /api/auth/me and routes to /onboarding).
      // If no session was established (e.g. cookie was dropped for any reason),
      // we redirect to /login with justVerified=true so the user gets a clear
      // "Email verified — sign in to continue" banner instead of hitting 401s in
      // the onboarding flow.
      await refreshUser();

      setView("verified");

      transitionTimerRef.current = window.setTimeout(async () => {
        const email = window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || "";

        // Re-read isLoggedIn from a fresh /api/auth/me rather than the stale
        // closure value — refreshUser() may have just updated AuthContext.
        // We do a lightweight check via the user object that refreshUser populated.
        // If still no session, send to login with the verified banner.
        try {
          const meResp = await fetch("/api/auth/me", {
            method: "GET",
            credentials: "include",
          });

          if (meResp.ok) {
            const meData = (await meResp.json()) as { user?: { email_verified?: boolean } };
            if (meData.user) {
              // Session is live — proceed to verify-complete which will route to /onboarding
              navigate("/verify-complete", {
                replace: true,
                state: { justVerified: true, email },
              });
              return;
            }
          }
        } catch {
          // Network error during the check — fall through to login redirect
        }

        // No active session after verification: redirect to login with clear banner.
        navigate("/login", {
          replace: true,
          state: { justVerified: true, email },
        });
      }, REDIRECT_DELAY_MS);
    };

    void run();
  }, [navigate, refreshUser, token]);

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
              <div className="space-y-5 text-center animate-fade-in">
                <div className="flex justify-center">
                  <AlertTriangle className="h-10 w-10 text-amber-500" />
                </div>
                <div>
                  <h1 className="text-2xl font-semibold text-foreground">Verification failed</h1>
                  <p className="mt-2 text-sm text-muted-foreground max-w-sm mx-auto">{error}</p>
                </div>
                <div className="flex flex-wrap justify-center gap-2">
                  <Link to="/check-email" className="gov-btn-primary">
                    Resend verification email
                  </Link>
                  <Link to="/signup" className="gov-btn-secondary">
                    Start over
                  </Link>
                </div>
                <p className="text-xs text-muted-foreground">
                  Still having trouble?{" "}
                  <a href="mailto:support@clarionhq.co" className="underline underline-offset-2 hover:text-foreground">
                    Contact support
                  </a>
                </p>
              </div>
            )}
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default VerifyEmail;
