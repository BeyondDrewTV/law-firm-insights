import { Fragment, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Check, Minus } from "lucide-react";
import { toast } from "sonner";
import { startCheckoutSession, type BillingPlan } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";
import { pricingPlans, comparisonRows, pricingFaqs, type PricingPlan } from "@/data/pricingPlans";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";

interface PricingSectionProps {
  sectionId?: string;
  showIntro?: boolean;
  showEntryCtas?: boolean;
  highlightedPlanId?: PricingPlan["id"] | null;
  showTeaserOnly?: boolean;
  showFaq?: boolean;
  billingCycle?: "monthly" | "annual";
  onBillingCycleChange?: (cycle: "monthly" | "annual") => void;
}

const getPlanToneClass = (id: PricingPlan["id"]) => {
  if (id === "free") return "marketing-tone-blue";
  if (id === "team") return "marketing-tone-emerald";
  return "marketing-tone-violet";
};

const groupedRows = comparisonRows.reduce<Record<string, typeof comparisonRows>>((acc, row) => {
  if (!acc[row.category]) acc[row.category] = [];
  acc[row.category].push(row);
  return acc;
}, {});

const CellValue = ({ value }: { value: string | boolean }) => {
  if (value === true) return <Check size={16} className="mx-auto text-emerald-600" aria-label="Included" />;
  if (value === false) return <Minus size={16} className="mx-auto text-slate-300" aria-label="Not included" />;
  return <span className="text-xs text-slate-700">{value}</span>;
};

const PricingSection = ({
  sectionId = "pricing",
  showIntro = true,
  showEntryCtas = false,
  highlightedPlanId = null,
  showTeaserOnly = false,
  showFaq = true,
  billingCycle: controlledCycle,
  onBillingCycleChange,
}: PricingSectionProps) => {
  const navigate = useNavigate();
  const { isLoggedIn, isLoading, currentPlan } = useAuth();
  const [loadingPlan, setLoadingPlan] = useState<BillingPlan | null>(null);
  const [internalCycle, setInternalCycle] = useState<"monthly" | "annual">("monthly");

  const billingCycle = controlledCycle ?? internalCycle;
  const setBillingCycle = (cycle: "monthly" | "annual") => {
    if (onBillingCycleChange) onBillingCycleChange(cycle);
    else setInternalCycle(cycle);
  };
  const showInternalToggle = controlledCycle === undefined;

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
    if (currentPlan?.planType === tier.planType) return tier.cta.current;
    const checkoutPlan: BillingPlan = tier.id === "firm" ? "firm" : "team";
    if (loadingPlan === checkoutPlan) return "Starting checkout...";
    return tier.cta.default;
  };

  if (showTeaserOnly) {
    return (
      <section id={sectionId} className="section-padding">
        <div className="section-container">
          <div className="mb-8 max-w-3xl reveal">
            <h2 className="text-4xl font-bold tracking-tight text-slate-900">
              Choose the plan that fits your review cadence
            </h2>
            <p className="mt-3 max-w-2xl text-lg leading-relaxed text-slate-700">
              Free for a first cycle. Team for recurring monthly governance. Firm for broader, ongoing partner review.
            </p>
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            {pricingPlans.map((tier, i) => (
              <article
                key={tier.name}
                className={`marketing-panel reveal rounded-xl p-6 shadow-sm ${getPlanToneClass(tier.id)}`}
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                {tier.badge && (
                  <span className="mb-3 inline-block rounded-full bg-slate-100 px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                    {tier.badge}
                  </span>
                )}
                <h3 className="text-base font-semibold text-slate-900">{tier.name}</h3>
                <p className="mt-1 text-xs uppercase tracking-wide text-slate-600">{tier.audience}</p>
                <p className="mt-4 text-3xl font-bold text-slate-900">
                  {tier.price}
                  {tier.period ? <span className="ml-1 text-sm font-normal text-slate-600">{tier.period}</span> : null}
                </p>
                {tier.annualSavings && (
                  <p className="mt-1 text-xs font-medium text-emerald-700">{tier.annualSavings} billed annually</p>
                )}
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
    <section id={sectionId} className="section-padding">
      <div className="section-container">
        {showIntro && (
          <div className="mb-10 text-center reveal">
            <h2 className="section-heading text-slate-900">Plans for every stage of governance maturity</h2>
            <p className="mx-auto mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
              Start with a free workspace to validate your first cycle. Upgrade when governance becomes part of the
              firm's operating rhythm.
            </p>
            {showEntryCtas && (
              <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                <Link to={!isLoading && isLoggedIn ? "/dashboard" : "/signup"} className="gov-btn-primary">
                  {!isLoading && isLoggedIn ? "Go to Dashboard" : "Start free workspace"}
                </Link>
                {!isLoggedIn ? (
                  <Link to="/login?redirectTo=/pricing" className="gov-btn-secondary">
                    Log in
                  </Link>
                ) : null}
                <Link to="/demo/reports/26" className="gov-btn-secondary">
                  Review sample brief
                </Link>
              </div>
            )}
          </div>
        )}

        {showInternalToggle && (
          <div className="mb-8 flex justify-center">
            <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 p-1 text-sm">
              <button
                type="button"
                onClick={() => setBillingCycle("monthly")}
                className={`rounded-full px-4 py-1.5 font-medium transition ${
                  billingCycle === "monthly" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                Monthly
              </button>
              <button
                type="button"
                onClick={() => setBillingCycle("annual")}
                className={`rounded-full px-4 py-1.5 font-medium transition ${
                  billingCycle === "annual" ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"
                }`}
              >
                Annual
                <span className="ml-1.5 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">
                  Save up to 17%
                </span>
              </button>
            </div>
          </div>
        )}

        <div className="grid gap-6 lg:grid-cols-3">
          {pricingPlans.map((tier, i) => {
            const isCurrentPlan = currentPlan?.planType === tier.planType;
            const isHighlighted = highlightedPlanId === tier.id;
            const displayPrice = billingCycle === "annual" ? tier.annualPrice : tier.price;
            const displayPeriod = billingCycle === "annual" ? tier.annualPeriod : tier.period;

            return (
              <div
                key={tier.name}
                className={`marketing-panel reveal relative flex h-full flex-col rounded-xl p-6 shadow-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-md ${getPlanToneClass(
                  tier.id,
                )} ${isCurrentPlan || isHighlighted ? "border-primary/45 ring-1 ring-primary/30" : "border-border"}`}
                style={{ transitionDelay: `${i * 80}ms` }}
              >
                {isCurrentPlan && (
                  <span className="absolute right-3 top-3 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
                    Current plan
                  </span>
                )}
                {!isCurrentPlan && isHighlighted && (
                  <span className="absolute right-3 top-3 rounded-full border border-primary/30 bg-primary/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-primary">
                    Selected
                  </span>
                )}
                {!isCurrentPlan && !isHighlighted && tier.badge && (
                  <span className="absolute right-3 top-3 rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-slate-600">
                    {tier.badge}
                  </span>
                )}

                <h3 className="text-base font-semibold text-slate-900">{tier.name}</h3>
                <p className="mt-1 text-xs leading-snug text-slate-600">{tier.audience}</p>

                <div className="mb-1 mt-4">
                  <span className="text-3xl font-bold text-slate-900">{displayPrice}</span>
                  {displayPeriod && <span className="ml-1 text-sm text-slate-600">{displayPeriod}</span>}
                </div>
                {billingCycle === "annual" && tier.annualSavings ? (
                  <p className="mb-4 text-xs font-medium text-emerald-700">{tier.annualSavings}</p>
                ) : (
                  <div className="mb-4" />
                )}

                <ul className="mb-8 flex-1 space-y-2.5">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-start gap-2 text-sm text-slate-800">
                      <Check size={15} className="mt-0.5 shrink-0 text-gold" />
                      <span>{feature}</span>
                    </li>
                  ))}
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
                      <p className="mt-2 text-center text-xs text-slate-500">Secure checkout via Stripe</p>
                    ) : null}
                  </>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-14 reveal">
          <h3 className="mb-6 text-center text-lg font-semibold text-slate-900">Full feature comparison</h3>
          <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50">
                  <th className="w-2/5 px-5 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Feature
                  </th>
                  {pricingPlans.map((tier) => (
                    <th key={tier.id} className="px-4 py-3 text-center text-xs font-semibold uppercase tracking-wider text-slate-700">
                      {tier.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(groupedRows).map(([category, rows]) => (
                  <Fragment key={category}>
                    <tr className="border-y border-slate-100 bg-slate-50/60">
                      <td colSpan={4} className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest text-slate-400">
                        {category}
                      </td>
                    </tr>
                    {rows.map((row) => (
                      <tr key={row.feature} className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/40">
                        <td className="px-5 py-3 text-slate-700">{row.feature}</td>
                        <td className="px-4 py-3 text-center">
                          <CellValue value={row.free} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <CellValue value={row.team} />
                        </td>
                        <td className="px-4 py-3 text-center">
                          <CellValue value={row.firm} />
                        </td>
                      </tr>
                    ))}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {showFaq && (
          <div className="mx-auto mt-14 max-w-3xl border-t border-slate-200 pt-10 reveal">
            <h3 className="mb-2 text-lg font-semibold text-slate-900">Frequently asked questions</h3>
            <p className="mb-6 text-sm text-slate-600">
              Questions about contracts, billing, or data? These are the ones managing partners and office
              administrators ask most often.
            </p>
            <Accordion type="single" collapsible className="divide-y divide-slate-200">
              {pricingFaqs.map((item) => (
                <AccordionItem key={item.value} value={item.value} className="border-none">
                  <AccordionTrigger className="py-4 text-left text-sm font-medium text-slate-900 hover:no-underline">
                    {item.question}
                  </AccordionTrigger>
                  <AccordionContent className="pb-4 text-sm leading-relaxed text-slate-700">
                    {item.answer}
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </div>
        )}
      </div>
    </section>
  );
};

export default PricingSection;
