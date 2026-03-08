import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import PageLayout from "@/components/PageLayout";
import { validatePasswordResetToken, resetPassword } from "@/api/authService";

const ResetPassword = () => {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();

  const [tokenState, setTokenState] = useState<"loading" | "valid" | "invalid" | "expired" | "used">("loading");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setTokenState("invalid");
      return;
    }
    validatePasswordResetToken(token).then((result) => {
      if (result.valid) {
        setTokenState("valid");
      } else if (result.reason === "expired") {
        setTokenState("expired");
      } else if (result.reason === "used") {
        setTokenState("used");
      } else {
        setTokenState("invalid");
      }
    });
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;
    setError("");
    setIsSubmitting(true);
    try {
      const result = await resetPassword(token, password, confirmPassword);
      if (result.success) {
        toast.success("Password reset. Please sign in with your new password.");
        navigate("/login", { state: { passwordReset: true }, replace: true });
      } else {
        setError(result.error || "Unable to reset password. Please try again.");
        toast.error(result.error || "Unable to reset password.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  if (tokenState === "loading") {
    return (
      <PageLayout>
        <section className="section-container section-padding max-w-xl auth-shell">
          <div className="auth-card bg-card border border-white/25 rounded-xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)]">
            <p className="text-slate-600">Checking reset link…</p>
          </div>
        </section>
      </PageLayout>
    );
  }

  if (tokenState !== "valid") {
    const message =
      tokenState === "expired"
        ? "This reset link has expired."
        : tokenState === "used"
          ? "This reset link has already been used."
          : "This reset link is invalid or no longer works.";
    return (
      <PageLayout>
        <section className="section-container section-padding max-w-xl auth-shell">
          <div className="auth-card bg-card border border-white/25 rounded-xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)]">
            <h1 className="mb-3 text-2xl font-bold text-slate-900">Reset link unavailable</h1>
            <p className="mb-6 text-slate-700">{message}</p>
            <Link to="/forgot-password" className="gov-btn-primary inline-block">
              Request a new link
            </Link>
          </div>
        </section>
      </PageLayout>
    );
  }

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card bg-card border border-white/25 rounded-xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)]">
          <h1 className="mb-3 text-3xl font-bold text-slate-900">Choose a new password</h1>
          <p className="mb-6 text-slate-700">
            Enter a new password for your account. Use at least 8 characters.
          </p>
          {error && (
            <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
              {error}
            </div>
          )}
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-900">
                New password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="New password"
                  disabled={isSubmitting}
                  className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 pr-12 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((p) => !p)}
                  disabled={isSubmitting}
                  className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-slate-500 hover:text-slate-900"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            <div>
              <label htmlFor="confirm-password" className="mb-2 block text-sm font-medium text-slate-900">
                Confirm new password
              </label>
              <input
                id="confirm-password"
                type={showPassword ? "text" : "password"}
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                disabled={isSubmitting}
                className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
              />
            </div>
            <button type="submit" disabled={isSubmitting} className="gov-btn-primary w-full disabled:opacity-50">
              {isSubmitting ? "Saving..." : "Set new password"}
            </button>
          </form>
          <div className="mt-6 text-center text-sm">
            <Link to="/login" className="text-slate-500 underline underline-offset-4 hover:text-slate-900">
              Back to sign in
            </Link>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default ResetPassword;
