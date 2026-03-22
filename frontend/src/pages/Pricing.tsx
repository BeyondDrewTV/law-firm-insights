import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { finalizeCheckoutSession, startCheckoutSession, type BillingPlan } from "@/api/authService";
import PricingSection from "@/components/PricingSection";
import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";
import { useAuth } from "@/contexts/AuthContext";
import { pricingPlans, type PricingPlanId } from "@/data/pricingPlans";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

const validPlans: BillingPlan[] = ["team", "firm"];
const focusedPlanIds: PricingPlanId[] = ["team", "firm"];

const Pricing = () => {
  const { isLoggedIn, isLoading, refreshPlan, refreshUser, currentPlan } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [focusedCheckoutPlan, setFocusedCheckoutPlan] = useState<BillingPlan | null>(null);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const [checkoutCanceled, setCheckoutCanceled] = useState(false);
  const [canceledPlan, setCanceledPlan] = useState<BillingPlan | null>(null);
  const [finalizeError, setFinalizeError] = useState<string | null>(null);
  const [startCheckoutError, setStartCheckoutError] = useState<string | null>(null);

  const checkoutStatus = searchParams.get("checkout");
  const sessionId = searchParams.get("session_id");
  const plan = searchParams.get("plan");
  const selectedPlanParam = searchParams.get("intent");

  const parsedPlan = useMemo(() => {
    if (validPlans.includes(plan as BillingPlan)) return plan as BillingPlan;
    return null;
  }, [plan]);

  const focusedPlanId = useMemo(() => {
    if (focusedPlanIds.includes(selectedPlanParam as PricingPlanId)) {
      return selectedPlanParam as PricingPlanId;
    }
    return null;
  }, [selectedPlanParam]);

  const focusedPlan = useMemo(
    () => pricingPlans.find((tier) => tier.id === focusedPlanId) ?? null,
    [focusedPlanId],
  );

  const finalizeAfterLoginPath =
    checkoutStatus === "success" && sessionId && parsedPlan
      ? `/pricing?checkout=success&session_id=${encodeURIComponent(sessionId)}&plan=${encodeURIComponent(parsedPlan)}`
      : "/pricing";
  const needsCheckoutSignIn =
    !isLoading && checkoutStatus === "success" && !!sessionId && !!parsedPlan && !isLoggedIn;

  useEffect(() => {
    if (isLoading || checkoutStatus !== "success" || !sessionId || !parsedPlan || !isLoggedIn || isFinalizing) {
      return;
    }

    const finalize = async () => {
      setIsFinalizing(true);
      setFinalizeError(null);
      const result = await finalizeCheckoutSession(sessionId, parsedPlan);
      if (result.success) {
        await Promise.all([refreshUser(), refreshPlan()]);
        toast.success("Checkout confirmed. Your account has been updated.");
        navigate("/dashboard", { replace: true });
      } else {
        const message = result.error || "We could not verify your payment. Please refresh or contact support.";
        setFinalizeError(message);
        setSearchParams({}, { replace: true });
      }
      setIsFinalizing(false);
    };

    void finalize();
  }, [
    checkoutStatus,
    isFinalizing,
    isLoading,
    isLoggedIn,
    navigate,
    parsedPlan,
    refreshPlan,
    refreshUser,
    sessionId,
    setSearchParams,
  ]);

  useEffect(() => {
    if (checkoutStatus !== "canceled") {
      return;
    }
    if (parsedPlan) setCanceledPlan(parsedPlan);
    setCheckoutCanceled(true);
    setSearchParams({}, { replace: true });
  }, [checkoutStatus, parsedPlan, setSearchParams]);

  const handleFocusedCheckout = async () => {
    if (!focusedPlan || focusedPlan.id === "free") {
      return;
    }

    if (!isLoggedIn) {
      navigate(`/login?redirectTo=${encodeURIComponent(`/pricing?intent=${focusedPlan.id}`)}`);
      return;
    }

    if (currentPlan?.planType === focusedPlan.planType) {
      navigate("/dashboard");
      return;
    }

    const checkoutPlan: BillingPlan = focusedPlan.id === "firm" ? "firm" : "team";
    setFocusedCheckoutPlan(checkoutPlan);
    setStartCheckoutError(null);
    const result = await startCheckoutSession(checkoutPlan, `/pricing?intent=${focusedPlan.id}`);
    if (!result.success || !result.checkout_url) {
      setFocusedCheckoutPlan(null);
      const message = result.error || "Unable to start checkout.";
      if (message.includes("sign in again")) {
        toast.message(message);
        navigate(`/login?redirectTo=${encodeURIComponent(`/pricing?intent=${focusedPlan.id}`)}`);
        return;
      }
      setStartCheckoutError(message);
      return;
    }

    window.location.assign(result.checkout_url);
  };

  const handleRetryCheckout = async (retryPlan: BillingPlan) => {
    setCheckoutCanceled(false);
    setStartCheckoutError(null);
    if (!isLoggedIn) {
      navigate(`/login?redirectTo=${encodeURIComponent(`/pricing?intent=${retryPlan}`)}`);
      return;
    }
    const result = await startCheckoutSession(retryPlan, `/pricing?intent=${retryPlan}`);
    if (!result.success || !result.checkout_url) {
      setStartCheckoutError(result.error || "Unable to restart checkout. Please try again.");
      return;
    }
    window.location.assign(result.checkout_url);
  };

  const focusedPlanButtonLabel = useMemo(() => {
    if (!focusedPlan) return "";
    if (currentPlan?.planType === focusedPlan.planType) {
      return "Current workspace plan";
    }
    if (!isLoggedIn) {
      return `Sign in for ${focusedPlan.name}`;
    }
    if (focusedCheckoutPlan === focusedPlan.id) {
      return "Starting checkout...";
    }
    return `Continue to ${focusedPlan.name} checkout`;
  }, [currentPlan?.planType, focusedCheckoutPlan, focusedPlan, isLoggedIn]);

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-5">
          <p className="landing-kicker">Pricing</p>
          <h1 className="marketing-hero-title">Choose the review cadence that fits the firm.</h1>
          <p className="max-w-3xl marketing-hero-body">
            Start with a free first cycle. Move to Team when governance becomes a recurring monthly discipline. Choose
            Firm for broader coverage, scheduled delivery, and a steadier cross-practice review rhythm.
          </p>

          <MarketingProofBar
            items={[
              "Built for law firms",
              "No credit card required to start Free",
              "Secure checkout via Stripe",
              "Plans sized around governance cadence",
            ]}
          />

          <div className="pt-2">
            <div className="inline-flex items-center rounded-full border border-[#D7D0C3] bg-[#FFFDF9] p-1 text-sm shadow-sm">
              <button
                type="button"
                onClick={() => setBillingCycle("monthly")}
                className={`rounded-full px-4 py-1.5 font-medium transition ${
                  billingCycle === "monthly" ? "bg-[#111827] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setBillingCycle("annual")}
                className={`rounded-full px-4 py-1.5 font-medium transition ${
                  billingCycle === "annual" ? "bg-[#111827] text-white shadow-sm" : "text-slate-600 hover:text-slate-900"
                }`}
              >
                Annual
                <span className="ml-1.5 rounded-full bg-[#EAF6EE] px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                  Save up to 17%
                </span>
              </button>
            </div>
          </div>

          <div className="flex flex-wrap gap-3 pt-1">
            <Link to={defaultSampleBriefPath} className="gov-btn-primary">
              Review sample brief
            </Link>
            <a href="#pricing-page-plans" className="gov-btn-secondary">
              Compare plans
            </a>
          </div>
        </div>
      </section>

      {isFinalizing && (
        <section className="section-container pb-2 pt-4">
          <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">
            Confirming your Stripe checkout...
          </div>
        </section>
      )}

      {needsCheckoutSignIn && (
        <section className="section-container pb-2 pt-4">
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-slate-800">
            <p className="font-medium text-slate-900">Return to finish secure checkout</p>
            <p className="mt-1">
              Your payment is waiting to be confirmed in Clarion. Sign in again to finish applying the plan to your
              workspace.
            </p>
            <div className="mt-3">
              <Link to={`/login?redirectTo=${encodeURIComponent(finalizeAfterLoginPath)}`} className="gov-btn-secondary">
                Sign in to finish checkout
              </Link>
            </div>
          </div>
        </section>
      )}

      {checkoutCanceled && (
        <section className="section-container pb-2 pt-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-5 py-4 text-sm text-slate-800">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-semibold text-slate-900">Checkout was canceled. Your plan has not changed.</p>
                <p className="mt-1 text-slate-600">
                  You can pick up where you left off. Your workspace and data are untouched.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {canceledPlan ? (
                    <button type="button" onClick={() => void handleRetryCheckout(canceledPlan)} className="gov-btn-primary">
                      Try checkout again
                    </button>
                  ) : (
                    <a href="#pricing-page-plans" className="gov-btn-primary">
                      Choose a plan
                    </a>
                  )}
                  <Link to="/contact" className="gov-btn-secondary">
                    Contact support
                  </Link>
                </div>
              </div>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setCheckoutCanceled(false)}
                className="shrink-0 rounded p-1 text-slate-400 transition-colors hover:bg-slate-200 hover:text-slate-700"
              >
                X
              </button>
            </div>
          </div>
        </section>
      )}

      {finalizeError && (
        <section className="section-container pb-2 pt-4">
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-semibold text-red-900">Payment could not be confirmed.</p>
                <p className="mt-1 text-red-800">{finalizeError}</p>
                <p className="mt-2 text-red-700">
                  If your card was declined, double-check the card details or try a different payment method. If you
                  used a test card number in a live checkout session, it will not be accepted.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <a href="#pricing-page-plans" className="gov-btn-primary">
                    Try a different card
                  </a>
                  <Link to="/contact" className="gov-btn-secondary">
                    Contact support
                  </Link>
                </div>
              </div>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setFinalizeError(null)}
                className="shrink-0 rounded p-1 text-red-400 transition-colors hover:bg-red-100 hover:text-red-700"
              >
                X
              </button>
            </div>
          </div>
        </section>
      )}

      {startCheckoutError && (
        <section className="section-container pb-2 pt-4">
          <div className="rounded-lg border border-red-200 bg-red-50 px-5 py-4 text-sm">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-semibold text-red-900">We could not start checkout.</p>
                <p className="mt-1 text-red-800">{startCheckoutError}</p>
                <p className="mt-2 text-red-700">
                  This is sometimes caused by a billing or sign-in problem before reaching Stripe. Try again or contact
                  support if the issue continues.
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <a href="#pricing-page-plans" className="gov-btn-primary">
                    Try again
                  </a>
                  <Link to="/contact" className="gov-btn-secondary">
                    Contact support
                  </Link>
                </div>
              </div>
              <button
                type="button"
                aria-label="Dismiss"
                onClick={() => setStartCheckoutError(null)}
                className="shrink-0 rounded p-1 text-red-400 transition-colors hover:bg-red-100 hover:text-red-700"
              >
                X
              </button>
            </div>
          </div>
        </section>
      )}

      {focusedPlan && (
        <section className="section-container pb-2 pt-6">
          <div className={`marketing-panel rounded-2xl px-6 py-6 ${focusedPlan.id === "firm" ? "marketing-tone-violet" : "marketing-tone-blue"}`}>
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-2xl">
                <p className="landing-kicker !text-[#5F6470]">Selected upgrade</p>
                <h2 className="mt-3 text-2xl font-semibold text-slate-900">{focusedPlan.name}</h2>
                <p className="mt-2 text-sm leading-7 text-slate-700">{focusedPlan.audience}</p>
                <p className="mt-3 text-sm leading-7 text-slate-700">
                  This tier is designed for firms that need more room to run recurring governance cycles without losing
                  workflow continuity between uploads and partner review.
                </p>
                <ul className="mt-4 grid gap-2 text-sm text-slate-800 sm:grid-cols-2">
                  {focusedPlan.features.slice(0, 4).map((feature) => (
                    <li key={feature} className="rounded-lg border border-slate-200 bg-white/80 px-3 py-2">
                      {feature}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="min-w-[240px] rounded-xl border border-slate-200 bg-white px-4 py-4">
                <p className="text-sm font-semibold text-slate-900">
                  {focusedPlan.price}
                  {focusedPlan.period}
                </p>
                <p className="mt-1 text-xs text-slate-600">
                  Quick overview first, then the same secure Stripe checkout already used across Clarion.
                </p>
                <div className="mt-4 flex flex-col gap-2">
                  <button
                    type="button"
                    onClick={() => void handleFocusedCheckout()}
                    disabled={focusedCheckoutPlan !== null || currentPlan?.planType === focusedPlan.planType}
                    className="gov-btn-primary justify-center disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {focusedPlanButtonLabel}
                  </button>
                  <Link to="/contact" className="gov-btn-secondary justify-center text-center">
                    Contact support
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      <section className="section-container pb-2 pt-6">
        <div className="supporting-cta-strip">
          <div className="max-w-2xl">
            <p className="landing-kicker !text-[#5F6470]">Choose by cadence</p>
            <p className="mt-2 text-sm leading-7 text-slate-700">
              Free validates a first cycle. Team supports a recurring monthly operating rhythm. Firm is for broader,
              ongoing coverage across practice groups and partner review.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to={defaultSampleBriefPath} className="gov-btn-primary">
              Review sample brief
            </Link>
            <Link to={!isLoading && isLoggedIn ? "/dashboard" : "/signup"} className="gov-btn-secondary">
              {!isLoading && isLoggedIn ? "Open workspace home" : "Start free workspace"}
            </Link>
            <Link to="/contact" className="gov-btn-secondary">
              Contact support
            </Link>
          </div>
        </div>
      </section>

      <section className="border-y border-slate-200 bg-slate-50">
        <PricingSection
          sectionId="pricing-page-plans"
          showIntro={false}
          showEntryCtas={false}
          highlightedPlanId={focusedPlanId}
          showFaq
          billingCycle={billingCycle}
          onBillingCycleChange={setBillingCycle}
        />
      </section>
    </PageLayout>
  );
};

export default Pricing;
