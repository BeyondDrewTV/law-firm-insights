import { type ChangeEvent, type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { CheckCircle2, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

import PageLayout from "@/components/PageLayout";
import { register } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";
import { getRequiredAuthenticatedDestination } from "@/lib/authRedirect";
import { evaluatePasswordStrength } from "@/lib/passwordStrength";

type ViewState = "form" | "check-email" | "verified";

interface FormErrors {
  firm_name?: string;
  email?: string;
  password?: string;
  general?: string;
}

const CONTENT_TRANSITION_MS = 220;
const STORAGE_EMAIL_KEY = "pending_verification_email";
const STORAGE_VERIFICATION_STATUS_KEY = "pending_verification_status";

interface VerificationStatusSnapshot {
  verification_sent: boolean;
  verification_delivery_available?: boolean;
  verification_delivery_method?: string | null;
  verification_delivery_error?: string | null;
  support_email?: string;
}

const Signup = () => {
  const navigate = useNavigate();
  const { isLoggedIn, isLoading, user } = useAuth();

  const [view] = useState<ViewState>("form");
  const [formData, setFormData] = useState({
    firm_name: "",
    email: "",
    password: "",
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const passwordStrength = evaluatePasswordStrength(formData.password);
  const passwordCriteria = [
    { label: "At least 8 characters", passed: formData.password.length >= 8 },
    { label: "Uppercase letter", passed: /[A-Z]/.test(formData.password) },
    { label: "Lowercase letter", passed: /[a-z]/.test(formData.password) },
    { label: "Number", passed: /\d/.test(formData.password) },
    { label: "Special character", passed: /[^A-Za-z0-9]/.test(formData.password) },
  ];

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
    setErrors((prev) => ({ ...prev, [name]: undefined, general: undefined }));
  };

  const validate = (): FormErrors => {
    const next: FormErrors = {};
    const firmName = formData.firm_name.trim();
    const email = formData.email.trim();

    if (!firmName || firmName.length < 2 || firmName.length > 120) {
      next.firm_name = "Firm name must be 2-120 characters.";
    }
    if (!email) next.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email address.";

    if (!formData.password || formData.password.length < 8) {
      next.password = "Password must be at least 8 characters.";
    }

    return next;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length > 0) {
      setErrors(validationErrors);
      return;
    }

    setErrors({});
    setIsSubmitting(true);

    const normalizedEmail = formData.email.trim();
    const normalizedFirmName = formData.firm_name.trim();

    const result = await register({
      email: normalizedEmail,
      password: formData.password,
      full_name: normalizedFirmName,
      firm_name: normalizedFirmName,
    });

    if (result.success) {
      window.sessionStorage.setItem(STORAGE_EMAIL_KEY, normalizedEmail);
      const verificationStatus: VerificationStatusSnapshot = {
        verification_sent: Boolean(result.verification_sent),
        verification_delivery_available: result.verification_delivery_available,
        verification_delivery_method: result.verification_delivery_method,
        verification_delivery_error: result.verification_delivery_error,
        support_email: result.support_email,
      };
      window.sessionStorage.setItem(STORAGE_VERIFICATION_STATUS_KEY, JSON.stringify(verificationStatus));
      if (result.requires_verification === false || result.verified === true) {
        window.sessionStorage.removeItem(STORAGE_VERIFICATION_STATUS_KEY);
        toast.success("Account created. Sign in to continue.");
        navigate("/login", {
          replace: true,
          state: {
            accountReady: true,
            email: normalizedEmail,
          },
        });
        return;
      }

      if (result.verification_sent) {
        toast.success("Verification email sent.");
      } else if (result.verification_delivery_available === false) {
        toast.error(result.verification_delivery_error || "Verification email is unavailable in this deployment right now.");
      } else {
        toast.error("We could not send the verification email. Use resend or contact support before continuing.");
      }
      navigate("/check-email", { replace: true });
    } else {
      setErrors({ ...result.errors, general: result.error || "Registration failed. Please try again." });
      toast.error(result.error || "Registration failed.");
    }

    setIsSubmitting(false);
  };
  useEffect(() => {
    if (isLoading || !isLoggedIn) return;
    navigate(getRequiredAuthenticatedDestination(user), { replace: true });
  }, [isLoading, isLoggedIn, navigate, user]);

  if (!isLoading && isLoggedIn) {
    return null;
  }

  const pendingEmail = window.sessionStorage.getItem(STORAGE_EMAIL_KEY) || formData.email.trim();

  return (
    <PageLayout>
      <section className="section-container section-padding max-w-xl auth-shell">
        <div className="auth-card rounded-xl border border-white/25 bg-card p-8 shadow-[0_20px_50px_rgba(0,0,0,0.32)] transition-all motion-slow ease-out">
          <div
            className={[
              "min-h-[420px] transition-all ease-out",
              "motion-med animate-soft-scale",
            ].join(" ")}
          >
            {view === "form" ? (
              <div className="animate-fade-in transition-all motion-med ease-in-out">
                <h1 className="mb-3 text-3xl font-semibold text-slate-900">Create your firm account</h1>
                <p className="mb-6 text-slate-600">Set up your workspace to begin your governance cycle.</p>

                {errors.general && (
                  <div className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
                    {errors.general}
                  </div>
                )}

                <form className="space-y-4" onSubmit={handleSubmit}>
                  <div>
                    <label htmlFor="firm_name" className="mb-2 block text-sm font-medium text-slate-900">
                      Firm Name
                    </label>
                    <input
                      id="firm_name"
                      name="firm_name"
                      type="text"
                      required
                      value={formData.firm_name}
                      onChange={handleChange}
                      placeholder="Smith & Associates"
                      disabled={isSubmitting}
                      className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
                    />
                    {errors.firm_name && <p className="mt-1 text-xs text-destructive">{errors.firm_name}</p>}
                  </div>

                  <div>
                    <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-900">
                      Email
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleChange}
                      placeholder="you@firm.com"
                      disabled={isSubmitting}
                      className="w-full rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-slate-900 placeholder:text-slate-500 focus:border-blue-600 focus:ring-2 focus:ring-blue-200 disabled:opacity-60"
                    />
                    {errors.email && <p className="mt-1 text-xs text-destructive">{errors.email}</p>}
                  </div>

                  <div>
                    <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-900">
                      Password
                    </label>
                    {!formData.password && (
                      <p className="mb-2 text-xs text-slate-500">At least 8 characters — uppercase, lowercase, number, and special character recommended.</p>
                    )}
                    <div className="relative">
                      <input
                        id="password"
                        name="password"
                        type={showPassword ? "text" : "password"}
                        required
                        value={formData.password}
                        onChange={handleChange}
                        placeholder="Minimum 8 characters"
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
                    {formData.password ? (
                      <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
                        <div className="mb-2 flex items-center justify-between text-xs">
                          <span className="font-medium text-slate-700">Password Strength</span>
                          <span className="font-semibold text-slate-800">{passwordStrength.label}</span>
                        </div>
                        <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
                          <div
                            className={`h-full transition-all duration-200 ${passwordStrength.progressClass}`}
                            style={{
                              width: `${Math.max(8, (passwordStrength.score / passwordStrength.maxScore) * 100)}%`,
                            }}
                          />
                        </div>
                        <p className="mt-2 text-xs text-slate-600">{passwordStrength.hint}</p>
                        <ul className="mt-2 grid grid-cols-1 gap-1 text-xs text-slate-600 sm:grid-cols-2">
                          {passwordCriteria.map((item) => (
                            <li key={item.label} className={item.passed ? "text-emerald-700" : "text-slate-500"}>
                              {item.label}
                            </li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    {errors.password && <p className="mt-1 text-xs text-destructive">{errors.password}</p>}
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="gov-btn-primary w-full disabled:opacity-60 flex items-center justify-center gap-2"
                  >
                    {isSubmitting ? (
                      <>
                        <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                        Creating your account…
                      </>
                    ) : (
                      "Create Free Account"
                    )}
                  </button>
                </form>

                <p className="mt-3 text-center text-sm text-slate-600">No credit card required.</p>

                <div className="mt-6 text-center text-sm">
                  <p className="mb-2 text-slate-600">Already have an account?</p>
                  <Link to="/login" className="font-medium text-gold hover:text-gold/80">
                    Log in here
                  </Link>
                </div>
              </div>
            ) : view === "check-email" ? (
              <div
                className="flex h-full min-h-[420px] flex-col items-center justify-center text-center transition-all motion-med ease-in-out animate-fade-in"
                style={{ animationDuration: `${CONTENT_TRANSITION_MS}ms` }}
              >
                <h2 className="text-3xl font-semibold text-slate-900">Check your email.</h2>
                <p className="mt-3 text-sm text-slate-700">
                  We sent a verification link to:
                </p>
                <p className="mt-1 text-sm font-semibold text-slate-900">{pendingEmail || "your email"}</p>

                <div className="mt-6 flex flex-col items-center gap-2 sm:flex-row">
                  <button
                    type="button"
                    className="gov-btn-primary"
                    onClick={() => navigate("/login")}
                  >
                    I verified, continue
                  </button>
                  <button
                    type="button"
                    className="gov-btn-secondary"
                    onClick={() => navigate("/check-email")}
                  >
                    Resend Email
                  </button>
                </div>

                <p className="mt-4 text-xs text-slate-600">
                  Open the inbox you actually use for {pendingEmail || "this address"}, click the verification link,
                  then continue to sign in here.
                </p>
              </div>
            ) : (
              <div
                className="flex h-full min-h-[420px] flex-col items-center justify-center text-center transition-all motion-med ease-in-out animate-slide-up"
                style={{ animationDuration: `${CONTENT_TRANSITION_MS}ms` }}
              >
                <CheckCircle2 size={34} className="text-emerald-600" />
                <h2 className="mt-3 text-3xl font-semibold text-slate-900">Email Verified</h2>
                <p className="mt-2 text-sm text-slate-600">Preparing onboarding...</p>
              </div>
            )}
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Signup;
