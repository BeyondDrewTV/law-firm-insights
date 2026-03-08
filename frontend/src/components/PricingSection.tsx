import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { toast } from "sonner";
import { startCheckoutSession, type BillingPlan } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";
import { pricingPlans, type PricingPlan } from "@/data/pricingPlans";
import InfoTooltip from "@/components/InfoTooltip";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import {
  confidenceDefinition,
  implementationPlanDefinition,
  trendStabilityDefinition,
} from "@/content/marketingCopy";

interface PricingSectionProps {
  sectionId?: string;
  showIntro?: boolean;
  showEntryCtas?: boolean;
  highlightedPlanId?: PricingPlan["id"] | null;
  showTeaserOnly?: boolean;
  showFaq?: boolean;
}

const featureExplanations: Array<{
  match: string;
  title: string;
  body: string;
}> = [
  {
    match: "Preview PDF export",
    title: "Preview PDF export",
    body: "Free plan exports are watermarked and intentionally limited to preview-level detail.",
  },
  {
    match: "implementation plan",
    title: "Implementation plans",
    body: implementationPlanDefinition,
  },
  {
    match: "Strategic plans",
    title: "Strategic plans",
    body: "Structured plans are generated for top themes based on your active plan limits.",
  },
  {
    match: "Dashboard analytics",
    title: "Dashboard analytics",
    body: `${trendStabilityDefinition} ${confidenceDefinition}`,
  },
  {
    match: "High review capacity",
    title: "High review capacity",
    body: "Paid plans process substantially larger uploads than Free, subject to platform row guards.",
  },
];

const faqItems = [
  {
    value: "free-vs-team-firm",
    question: "When should we use Free, Team, or Firm?",
    answer:
      "Free is designed for first-cycle validation. Team is for recurring monthly governance work. Firm is for year-round, cross-practice governance coverage.",
  },
  {
    value: "cancel-subscription",
    question: "What happens if we cancel a paid plan?",
    answer:
      "Paid access remains active through the billing period. After that, existing reports stay visible in your dashboard history and new report generation follows your active plan limits.",
  },
  {
    value: "team-to-firm",
    question: "Can we upgrade from Team to Firm later?",
    answer:
      "Yes. You can move from Team to Firm as governance volume grows and continue using the same workspace.",
  },
];

const getFeatureExplanation = (feature: string) =>
  featureExplanations.find((item) => feature.includes(item.match));

const getPlanToneClass = (id: PricingPlan["id"]) => {
  if (id === "free") return "marketing-tone-blue";
  if (id === "team") return "marketing-tone-emerald";
  return "marketing-tone-violet";
};

const PricingSection = ({
  sectionId = "pricing",
  showIntro = true,
  showEntryCtas = false,
  highlightedPlanId = null,
  showTeaserOnly = false,
  showFaq = true,
}: PricingSectionProps) => {
  const navigate = useNavigate();
  const { isLoggedIn, isLoading, currentPlan } = useAuth();
  const [loadingPlan, setLoadingPlan] = useState<BillingPlan | null>(null);

  const startPaidCheckout = async (tier: PricingPlan) => {
    const checkoutPlan: BillingPlan = tier.id === "firm" ? "firm" : "team";
    setLoadingPlan(checkoutPlan);
    const result = await startCheckoutSession(checkoutPlan, "/pricing");
    if (!result.success || !result.checkout_url) {
      setLoadingPlan(null);
      const message = result.error || "Unable to start checkout.";
      if (message.includes("sign in again")) {
        toast.message(message);
        navigate("/login?redirectTo=/pricing");
        return;
      }
      toast.error(message);
      return;
    }

    window.location.assign(result.checkout_url);
  };

  const handlePlanClick = async (tier: PricingPlan) => {
    const isCurrentPlan = currentPlan?.planType === tier.planType;
    if (isCurrentPlan) {
      navigate("/dashboard");
      return;
    }

    if (tier.id === "free") {
      navigate(isLoggedIn ? "/dashboard" : "/signup");
      return;
    }

    if (!isLoggedIn) {
      navigate("/login?redirectTo=/pricing");
      return;
    }

    await startPaidCheckout(tier);
  };

  const getButtonLabel = (tier: PricingPlan) => {
    const isCurrentPlan = currentPlan?.planType === tier.planType;
    if (isCurrentPlan) {
      return tier.cta.current;
    }

    const checkoutPlan: BillingPlan = tier.id === "firm" ? "firm" : "team";
    if (loadingPlan === checkoutPlan) {
      return "Starting checkout...";
    }

    return tier.cta.default;
  };

  if (showTeaserOnly) {
    return (
      <section id={sectionId} className="section-padding">
        <div className="section-container">
          <div className="mb-8 max-w-3xl reveal">
            <h2 className="text-4xl font-bold tracking-tight text-slate-900">Choose the plan that fits your review cadence</h2>
            <p className="mt-3 max-w-2xl text-lg leading-relaxed text-slate-700">
              Start free for first-cycle validation, then move to Team or Firm when the governance cycle becomes a recurring operating rhythm.
            </p>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {pricingPlans.map((tier, i) => (
              <article
                key={tier.name}
                className={`marketing-panel reveal rounded-xl p-6 shadow-sm ${getPlanToneClass(tier.id)}`}
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                <h3 className="text-base font-semibold text-slate-900">{tier.name}</h3>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-700">{tier.audience}</p>
                <p className="mt-4 text-3xl font-bold text-slate-900">
                  {tier.price}
                  {tier.period ? <span className="ml-1 text-sm font-normal text-slate-700">{tier.period}</span> : null}
                </p>
                <p className="mt-4 text-sm leading-relaxed text-slate-700">
                  {tier.id === "free"
                    ? "Best for validating the first review cycle and seeing how Clarion fits your firm."
                    : tier.id === "team"
                      ? "Best for firms running a recurring monthly governance rhythm with shared ownership."
                      : "Best for firms that need broader capacity and ongoing coverage across repeated cycles."}
                </p>
              </article>
            ))}
          </div>
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link to="/pricing" className="gov-btn-primary">
              Compare plans
            </Link>
            <Link to="/signup" className="gov-btn-secondary">
              Start free
            </Link>
          </div>
        </div>
      </section>
    );
  }

  return (
    <>
      <section id={sectionId} className="section-padding">
        <div className="section-container">
                  {showIntro && (
            <div className="mb-12 text-center reveal">
              <h2 className="section-heading text-slate-900">Choose the plan for your governance cycle</h2>
              <p className="mx-auto mt-1 max-w-2xl text-sm text-slate-700">Start free, upgrade when you are ready.</p>
              <p className="mx-auto mt-1 max-w-2xl text-sm text-slate-600">
                One free governance brief per month to start. Upgrade when your governance cycle demands more depth.
              </p>
              {showEntryCtas && (
                <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                  <Link to={!isLoading && isLoggedIn ? "/dashboard" : "/signup"} className="gov-btn-primary">
                    {!isLoading && isLoggedIn ? "Go to Dashboard" : "Start Free"}
                  </Link>
                  {!isLoggedIn ? (
                    <Link to="/login?redirectTo=/pricing" className="gov-btn-secondary">
                      Log in
                    </Link>
                  ) : null}
                  <Link to="/demo" className="gov-btn-secondary">
                    Explore demo workspace
                  </Link>
                </div>
              )}
            </div>
          )}

          <div className="grid gap-6 lg:grid-cols-3">
            {pricingPlans.map((tier, i) => {
              const isCurrentPlan = currentPlan?.planType === tier.planType;
              const isHighlighted = highlightedPlanId === tier.id;
              return (
                <div
                  key={tier.name}
                  className={`marketing-panel reveal relative flex h-full flex-col rounded-xl p-6 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md ${getPlanToneClass(
                    tier.id,
                  )} ${
                    isCurrentPlan || isHighlighted ? "border-primary/45 ring-1 ring-primary/30" : "border-border"
                  }`}
                  style={{ transitionDelay: `${i * 80}ms` }}
                >
                  {isCurrentPlan && (
                    <span className="absolute top-3 right-3 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
                      Current plan
                    </span>
                  )}
                  {!isCurrentPlan && isHighlighted && (
                    <span className="absolute top-3 right-3 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
                      Selected upgrade
                    </span>
                  )}
                  <h3 className="text-base font-semibold text-slate-900">{tier.name}</h3>
                  <p className="mt-1 text-xs uppercase tracking-wide text-slate-700">{tier.audience}</p>
                  <div className="mb-5">
                    <span className="text-3xl font-bold text-slate-900">{tier.price}</span>
                    {tier.period && <span className="ml-1 text-sm text-slate-700">{tier.period}</span>}
                  </div>
                  <ul className="mb-8 flex-1 space-y-2.5">
                    {tier.features.map((f) => {
                      const explanation = getFeatureExplanation(f);
                      return (
                        <li key={f} className="flex items-start gap-2 text-sm text-slate-800">
                          <Check size={15} className="mt-0.5 shrink-0 text-gold" />
                          <span className="inline-flex items-center">
                            {f}
                            {explanation && <InfoTooltip title={explanation.title} body={explanation.body} />}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  {isCurrentPlan ? (
                    <Link to="/dashboard" className="gov-btn-secondary w-full justify-center">
                      Go to Dashboard
                    </Link>
                  ) : (
                    <>
                      <button
                        type="button"
                        onClick={() => void handlePlanClick(tier)}
                        disabled={loadingPlan !== null}
                        className="gov-btn-primary w-full text-center disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {getButtonLabel(tier)}
                      </button>
                      {tier.id !== "free" ? (
                        <p className="mt-2 text-center text-xs text-slate-600">Secure checkout powered by Stripe</p>
                      ) : null}
                    </>
                  )}
                </div>
              );
            })}
          </div>

          {showFaq ? (
            <div className="mx-auto mt-10 max-w-3xl border-t border-slate-200 pt-5">
              <p className="text-sm font-semibold text-slate-900">Pricing FAQ</p>
              <Accordion type="single" collapsible className="mt-2">
                {faqItems.map((item) => (
                  <AccordionItem key={item.value} value={item.value}>
                    <AccordionTrigger className="text-left text-sm text-slate-900">{item.question}</AccordionTrigger>
                    <AccordionContent className="text-sm text-slate-800">{item.answer}</AccordionContent>
                  </AccordionItem>
                ))}
              </Accordion>
            </div>
          ) : null}
        </div>
      </section>
    </>
  );
};

export default PricingSection;
