import { useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import PageLayout from "@/components/PageLayout";
import { requestPasswordReset } from "@/api/authService";

const ForgotPassword = () => {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const result = await requestPasswordReset(email.trim().toLowerCase());
      if (result.success) {
        setSubmitted(true);
      } else {
        setError(result.error || "Unable to send reset request. Please try again.");
        toast.error(result.error || "Unable to send reset request.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card bg-card border border-white/25 rounded-xl p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)]">
          <h1 className="mb-3 text-3xl font-bold text-slate-900">Reset your password</h1>
          {submitted ? (
            <>
              <p className="mb-6 text-slate-700">
                If that email is registered, a reset link has been sent. Check your inbox and follow
                the link to choose a new password.
              </p>
              <p className="text-sm text-slate-500">
                Didn't receive anything?{" "}
                <button
                  type="button"
                  onClick={() => setSubmitted(false)}
                  className="text-gold underline underline-offset-4 hover:text-gold/80"
                >
                  Try again
                </button>{" "}
                or{" "}
                <Link to="/contact" className="text-gold underline underline-offset-4 hover:text-gold/80">
                  contact support
                </Link>
                .
              </p>
            </>
          ) : (
            <>
              <p className="mb-6 text-slate-700">
                Enter the email address for your account and we'll send you a reset link.
              </p>
              {error && (
                <div className="mb-4 p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-sm text-destructive">
                  {error}
                </div>
              )}
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
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="gov-btn-primary w-full disabled:opacity-50"
                >
                  {isSubmitting ? "Sending..." : "Send reset link"}
                </button>
              </form>
              <div className="mt-6 text-center text-sm">
                <Link to="/login" className="text-slate-500 underline underline-offset-4 hover:text-slate-900">
                  Back to sign in
                </Link>
              </div>
            </>
          )}
        </div>
      </section>
    </PageLayout>
  );
};

export default ForgotPassword;
