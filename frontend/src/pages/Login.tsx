import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import PageLayout from "@/components/PageLayout";
import { useAuth } from "@/contexts/AuthContext";
import { getPostLoginDestination } from "@/lib/authRedirect";

const Login = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const { logIn, verifyTwoFactor, isLoading, isLoggedIn, user } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [challengeId, setChallengeId] = useState<string | null>(null);
  const [requiresTwoFactor, setRequiresTwoFactor] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const EMAIL_VERIFICATION_ERROR = "Please verify your email before logging in.";
  const verificationMessage =
    (location.state as { justVerified?: boolean; accountReady?: boolean; email?: string } | null)?.justVerified
      ? "Email verified. Sign in to continue into Clarion."
      : (location.state as { justVerified?: boolean; accountReady?: boolean; email?: string } | null)?.accountReady
        ? "Account created. Sign in to continue."
        : "";

  const redirectTo = searchParams.get("redirectTo");
  const fromState = (location.state as { from?: string } | null)?.from;
  const from = redirectTo && redirectTo.startsWith("/") ? redirectTo : fromState || "/dashboard";

  useEffect(() => {
    const emailFromState = (location.state as { email?: string } | null)?.email;
    const emailFromStorage = window.sessionStorage.getItem("pending_verification_email") || "";
    if (!email && (emailFromState || emailFromStorage)) {
      setEmail(emailFromState || emailFromStorage);
    }
  }, [email, location.state]);

  useEffect(() => {
    if (isLoading || !isLoggedIn) return;
    navigate(getPostLoginDestination(user, from), { replace: true });
  }, [from, isLoading, isLoggedIn, navigate, user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);

    const result = await logIn(email.trim(), password);
    if (result.success && result.requiresTwoFactor && result.challengeId) {
      setRequiresTwoFactor(true);
      setChallengeId(result.challengeId);
      setError("");
      toast.info(result.message || "Enter the code sent to your email.");
    } else if (result.success) {
      window.localStorage.removeItem("clarion_verification_completed_at");
      toast.success("Logged in successfully.");
      navigate(getPostLoginDestination(result.user ?? user ?? null, from), { replace: true });
    } else {
      const message = result.error || "Login failed. Please check your credentials.";
      const isVerificationError = message === EMAIL_VERIFICATION_ERROR;
      if (isVerificationError) {
        window.sessionStorage.setItem("pending_verification_email", email.trim());
      }
      setError(isVerificationError ? "" : message);
      toast.error(message);
    }

    setIsSubmitting(false);
  };

  const handleVerifyCode = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!challengeId) {
      setError("Verification challenge expired. Please log in again.");
      setRequiresTwoFactor(false);
      return;
    }

    setError("");
    setIsSubmitting(true);
    const result = await verifyTwoFactor(challengeId, verificationCode.trim());

    if (result.success) {
      toast.success("Logged in successfully.");
      navigate(getPostLoginDestination(result.user ?? user ?? null, from), { replace: true });
    } else {
      const message = result.error || "Verification failed.";
      setError(message);
      toast.error(message);
    }

    setIsSubmitting(false);
  };

  if (!isLoading && isLoggedIn) {
    return null;
  }

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card bg-card border border-white/25 rounded-xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)] transition-all motion-slow ease-out">
          <h1 className="mb-3 text-3xl font-bold text-slate-900">
            {requiresTwoFactor ? "Enter verification code" : "Log in to Clarion"}
          </h1>
          <p className="mb-6 text-slate-700">
            {requiresTwoFactor
              ? "Complete sign-in with the 6-digit code sent to your email"
              : "Access your dashboard and feedback analysis"}
          </p>

          {verificationMessage ? (
            <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
              {verificationMessage}
            </div>
          ) : null}

          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {error}
            </div>
          )}

          {!requiresTwoFactor && !error && email ? (
            <p className="mb-4 text-sm text-slate-600">
              Use <span className="font-medium text-slate-900">{email}</span> to continue.
            </p>
          ) : null}

          {!requiresTwoFactor ? (
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-900">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@lawfirm.com"
                  disabled={isSubmitting}
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-900">
                  Password
                </label>
                <div className="relative">
                  <input
                    id="password"
                    type={showPassword ? "text" : "password"}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                    disabled={isSubmitting}
                    className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 pr-12 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((previous) => !previous)}
                    disabled={isSubmitting}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-slate-500 hover:text-slate-900"
                    aria-label={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button type="submit" disabled={isSubmitting} className="gov-btn-primary w-full disabled:opacity-50">
                {isSubmitting ? "Logging in..." : "Log in"}
              </button>

              <div className="flex flex-col items-center gap-1">
                <Link to="/forgot-password" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-900">
                  Forgot password?
                </Link>
                <Link to="/check-email" className="text-sm text-slate-500 underline underline-offset-4 transition-colors hover:text-slate-900">
                  Need another verification email?
                </Link>
              </div>
            </form>
          ) : (
            <form className="space-y-4" onSubmit={handleVerifyCode}>
              <div>
                <label htmlFor="otp" className="mb-2 block text-sm font-medium text-slate-900">
                  6-digit code
                </label>
                <input
                  id="otp"
                  type="text"
                  required
                  maxLength={6}
                  inputMode="numeric"
                  pattern="[0-9]{6}"
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="123456"
                  disabled={isSubmitting}
                  className="w-full rounded-lg border border-input bg-background px-4 py-2.5 text-foreground placeholder:text-muted-foreground focus:border-blue-500 focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
              </div>

              <button type="submit" disabled={isSubmitting} className="gov-btn-primary w-full disabled:opacity-50">
                {isSubmitting ? "Verifying..." : "Verify code"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setRequiresTwoFactor(false);
                  setChallengeId(null);
                  setVerificationCode("");
                }}
                className="w-full text-sm text-slate-600 hover:text-slate-900"
              >
                Use different sign-in details
              </button>
            </form>
          )}

          <div className="mt-6 text-center text-sm">
            <p className="mb-2 text-slate-600">Don't have an account?</p>
            <Link to="/signup" className="text-gold hover:text-gold/80 font-medium">
              Sign up here
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Login;

