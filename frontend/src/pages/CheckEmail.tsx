import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle, CheckCircle2, MailWarning, Mail } from "lucide-react";

import PageLayout from "@/components/PageLayout";
import { resendVerificationEmail } from "@/api/authService";

const STORAGE_EMAIL_KEY = "pending_verification_email";
const STORAGE_VERIFICATION_STATUS_KEY = "pending_verification_status";
const VERIFICATION_COMPLETED_KEY = "clarion_verification_completed_at";

interface VerificationStatusSnapshot {
  verification_sent?: boolean;
  verification_delivery_available?: boolean;
  verification_delivery_method?: string | null;
  verification_delivery_error?: string | null;
  support_email?: string;
}

const readVerificationStatus = (): VerificationStatusSnapshot => {
  if (typeof window === "undefined") return {};
  const raw = window.sessionStorage.getItem(STORAGE_VERIFICATION_STATUS_KEY);
  if (!raw) return {};
  try {
    const parsed = JSON.parse(raw) as VerificationStatusSnapshot;
    return typeof parsed === "object" && parsed ? parsed : {};
  } catch {
    return {};
  }
};

const CheckEmail = () => {
  const navigate = useNavigate();
  const pendingEmail =
    typeof window !== "undefined" ? window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || "" : "";
  const [verificationStatus, setVerificationStatus] = useState<VerificationStatusSnapshot>(() => readVerificationStatus());
  const [isVerified, setIsVerified] = useState(false);
  const [isResending, setIsResending] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);
  const cooldownTimerRef = useRef<number | null>(null);
  const redirectTimerRef = useRef<number | null>(null);

  const deliveryUnavailable = verificationStatus.verification_delivery_available === false;
  const supportEmail = verificationStatus.support_email || "support@clarionhq.co";
  useEffect(() => {
    let cancelled = false;
    const markVerified = () => {
      setIsVerified(true);
      window.sessionStorage.removeItem(STORAGE_VERIFICATION_STATUS_KEY);

      redirectTimerRef.current = window.setTimeout(() => {
        if (cancelled) return;
        navigate("/verify-complete", { replace: true });
      }, 800);
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key === VERIFICATION_COMPLETED_KEY && event.newValue) {
        markVerified();
      }
      if (event.key === STORAGE_VERIFICATION_STATUS_KEY) {
        setVerificationStatus(readVerificationStatus());
      }
    };

    if (window.localStorage.getItem(VERIFICATION_COMPLETED_KEY)) {
      markVerified();
    }
    window.addEventListener("storage", handleStorage);

    return () => {
      cancelled = true;
      window.removeEventListener("storage", handleStorage);
      if (redirectTimerRef.current !== null) {
        window.clearTimeout(redirectTimerRef.current);
        redirectTimerRef.current = null;
      }
      if (cooldownTimerRef.current !== null) {
        window.clearInterval(cooldownTimerRef.current);
        cooldownTimerRef.current = null;
      }
    };
  }, [navigate]);

  const handleResend = async () => {
    if (!pendingEmail || isResending || deliveryUnavailable || resendCooldown > 0) return;
    setIsResending(true);
    setResendMessage("");
    const result = await resendVerificationEmail(pendingEmail);
    setIsResending(false);

    const nextStatus: VerificationStatusSnapshot = {
      ...verificationStatus,
      verification_delivery_available: result.verification_delivery_available ?? verificationStatus.verification_delivery_available,
      verification_delivery_method: result.verification_delivery_method ?? verificationStatus.verification_delivery_method,
      verification_delivery_error: result.verification_delivery_error ?? verificationStatus.verification_delivery_error,
      support_email: result.support_email ?? verificationStatus.support_email,
      verification_sent: result.success && (result.verification_delivery_available ?? true),
    };
    setVerificationStatus(nextStatus);
    window.sessionStorage.setItem(STORAGE_VERIFICATION_STATUS_KEY, JSON.stringify(nextStatus));

    setResendMessage(
      result.success
        ? result.verification_delivery_available === false
          ? result.verification_delivery_error || `Email delivery is unavailable right now. Contact ${result.support_email || supportEmail}.`
          : `Verification email resent to ${pendingEmail}. Check your spam folder if it doesn't arrive within a minute.`
        : result.error || "Unable to resend verification email right now.",
    );

    if (result.success) {
      // Start 60-second cooldown to prevent rapid re-sends
      setResendCooldown(60);
      let remaining = 60;
      cooldownTimerRef.current = window.setInterval(() => {
        remaining -= 1;
        setResendCooldown(remaining);
        if (remaining <= 0 && cooldownTimerRef.current !== null) {
          window.clearInterval(cooldownTimerRef.current);
          cooldownTimerRef.current = null;
        }
      }, 1000);
    }
  };

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card rounded-xl border border-white/25 bg-card p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)] transition-all motion-slow ease-out">
          <div className="animate-fade-in space-y-6">
            <div className="space-y-3 text-center">
              <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-blue-700">
                Clarion Verification
              </span>
              <div className="flex justify-center">
                <Mail className="h-10 w-10 text-slate-400" />
              </div>
              <h1 className="text-3xl font-semibold text-slate-900">Check your inbox.</h1>
              <p className="text-sm text-slate-700">
                {deliveryUnavailable ? (
                  "Email verification is required, but delivery is currently unavailable in this deployment."
                ) : verificationStatus.verification_sent && pendingEmail ? (
                  <>
                    We sent a verification link to{" "}
                    <span className="font-semibold text-slate-900">{pendingEmail}</span>.
                  </>
                ) : pendingEmail ? (
                  <>
                    Open the inbox for <span className="font-semibold text-slate-900">{pendingEmail}</span> and click
                    the verification link to activate your workspace.
                  </>
                ) : (
                  "Open your inbox and click the verification link to activate your workspace."
                )}
              </p>
              {!deliveryUnavailable && (
                <p className="text-xs text-slate-500">
                  The link expires in 24 hours. If you don't see it, check your spam or junk folder.
                </p>
              )}
            </div>

            {deliveryUnavailable ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50/90 px-4 py-4 text-sm text-amber-900">
                <div className="flex items-start gap-3">
                  <MailWarning className="mt-0.5 h-5 w-5 shrink-0" />
                  <div className="space-y-2">
                    <p className="font-medium">Verification email delivery is currently unavailable.</p>
                    <p>
                      {verificationStatus.verification_delivery_error ||
                        "This deployment is not configured to send verification emails yet."}
                    </p>
                    <p>
                      Contact <a href={`mailto:${supportEmail}`} className="font-medium underline underline-offset-4">{supportEmail}</a> to finish account setup or ask for a new verification link after email delivery is restored.
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                Open the inbox for <span className="font-semibold text-slate-900">{pendingEmail || "your address"}</span>,
                click the verification link, then return here.
              </div>
            )}

            {isVerified ? (
              <div className="animate-slide-up rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-center text-sm font-medium text-emerald-800">
                <div className="inline-flex items-center gap-2">
                  <CheckCircle2 size={16} />
                  <span>Email verified successfully. Returning you to Clarion.</span>
                </div>
              </div>
            ) : (
              <div className="animate-slide-up rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-center text-sm text-slate-700">
                {deliveryUnavailable ? (
                  <div className="inline-flex items-center gap-2 text-amber-800">
                    <AlertCircle size={16} />
                    <span>You can sign in after support helps complete verification.</span>
                  </div>
                ) : (
                  <>
                    After verifying your email, return here to continue. If the verification link opens in this browser, Clarion will continue automatically.
                  </>
                )}
              </div>
            )}

            {!isVerified ? (
              <div className="rounded-lg border border-slate-200 bg-white px-4 py-4 text-sm text-slate-700">
                <p>
                  {deliveryUnavailable
                    ? "If your team restores email delivery later, you can return here and request another verification email."
                    : "If the verification link opens in another tab or browser, finish verification there. Then either return here, or go straight to sign in if this page does not update."}
                </p>
                <div className="mt-4 flex flex-wrap justify-center gap-2">
                  <button
                    type="button"
                    className="gov-btn-secondary"
                    onClick={() => void handleResend()}
                    disabled={!pendingEmail || isResending || deliveryUnavailable || resendCooldown > 0}
                  >
                    {isResending
                      ? "Resending…"
                      : resendCooldown > 0
                      ? `Resend again in ${resendCooldown}s`
                      : "Resend verification email"}
                  </button>
                  <Link to="/login" className="gov-btn-secondary">
                    Return to sign in
                  </Link>
                </div>
                <p className="mt-3 text-center text-xs text-slate-500">
                  Used a different email?{" "}
                  <Link to="/signup" className="underline underline-offset-2 hover:text-slate-700">
                    Go back to sign up
                  </Link>
                </p>
                {resendMessage ? <p className="mt-3 text-xs text-slate-600">{resendMessage}</p> : null}
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default CheckEmail;
