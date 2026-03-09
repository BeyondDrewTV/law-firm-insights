import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { finalizeCheckoutSession, startCheckoutSession, type BillingPlan } from "@/api/authService";
import PricingSection from "@/components/PricingSection";
import PageLayout from "@/components/PageLayout";
import { useAuth } from "@/contexts/AuthContext";
import { pricingPlans, type PricingPlanId } from "@/data/pricingPlans";

const validPlans: BillingPlan[] = ["team", "firm"];
const focusedPlanIds: PricingPlanId[] = ["team", "firm"];

const Pricing = () => {
  const { isLoggedIn, isLoading, refreshPlan, refreshUser, currentPlan } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFinalizing, setIsFinalizing] = useState(false);
  const [focusedCheckoutPlan, setFocusedCheckoutPlan] = useState<BillingPlan | null>(null);

  const checkoutStatus = searchParams.get("checkout");
  const sessionId = searchParams.get("session_id");
  const plan = searchParams.get("plan");
  const selectedPlanParam = searchParams.get("intent");
  const parsedPlan = useMemo(() => {
    if (validPlans.includes(plan as BillingPlan)) return plan as BillingPlan;
    if (legacyPlans.includes(plan as (typeof legacyPlans)[number])) {
      return plan === "annual" ? "firm" : "team";
    }
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
      const result = await finalizeCheckoutSession(sessionId, parsedPlan);
      if (result.success) {
        await Promise.all([refreshUser(), refreshPlan()]);
        toast.success("Checkout confirmed. Your account has been updated.");
        navigate("/dashboard", { replace: true });
      } else {
        toast.error(result.error || "We couldn't verify checkout yet. Please refresh in a few seconds.");
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
    toast.message("Checkout canceled. You can choose a plan any time.");
    setSearchParams({}, { replace: true });
  }, [checkoutStatus, setSearchParams]);

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
    const result = await startCheckoutSession(checkoutPlan, `/pricing?intent=${focusedPlan.id}`);
    if (!result.success || !result.checkout_url) {
      setFocusedCheckoutPlan(null);
      const message = result.error || "Unable to start checkout.";
      if (message.includes("sign in again")) {
        toast.message(message);
        navigate(`/login?redirectTo=${encodeURIComponent(`/pricing?intent=${focusedPlan.id}`)}`);
        return;
      }
      toast.error(message);
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
        <div className="section-container space-y-4">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Pricing
          </p>
          <h1 className="marketing-hero-title">Governance tools built for how law firms actually operate.</h1>
          <p className="max-w-3xl marketing-hero-body">
            Start with a free trial — no credit card required. Move to Team when governance becomes a monthly discipline. Choose Firm for full-platform coverage with scheduled delivery, custom branding, and unlimited capacity.
          </p>
          <div className="flex flex-wrap gap-3 pt-1">
            <a href="#pricing-page-plans" className="gov-btn-primary">
              Compare plans
            </a>
            <Link to="/contact" className="gov-btn-secondary">
              Contact support
            </Link>
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

      {focusedPlan && (
        <section className="section-container pb-2 pt-6">
          <div className="marketing-panel marketing-tone-blue rounded-2xl px-6 py-6">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-2xl">
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-600">Selected upgrade</p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-900">{focusedPlan.name}</h2>
                <p className="mt-2 text-sm text-slate-700">{focusedPlan.audience}</p>
                <p className="mt-3 text-sm text-slate-700">
                  This tier is designed for firms that need more room to run recurring governance cycles without losing
                  workflow continuity.
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
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Choose by cadence</p>
            <p className="mt-2 text-sm text-slate-700">
              Free validates a first cycle. Team supports a recurring monthly operating rhythm. Firm is for broader,
              ongoing coverage across practice groups.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link to={!isLoading && isLoggedIn ? "/dashboard" : "/signup"} className="gov-btn-primary">
              {!isLoading && isLoggedIn ? "Go to Dashboard" : "Start Free workspace"}
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
        />
      </section>
    </PageLayout>
  );
};

export default Pricing;
