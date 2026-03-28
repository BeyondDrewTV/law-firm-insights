import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import {
  getCredits,
  getReportPackSchedule,
  updateReportPackSchedule,
  type CreditsState,
  type ReportPackSchedule,
} from "@/api/authService";
import GovPageHeader from "@/components/governance/GovPageHeader";
import GovSectionCard from "@/components/governance/GovSectionCard";
import PlanCurrentBanner from "@/components/billing/PlanCurrentBanner";
import { useAuth } from "@/contexts/AuthContext";
import { resolvePlanLimits } from "@/config/planLimits";


const DashboardBilling = () => {
  const { currentPlan } = useAuth();
  const [credits, setCredits] = useState<CreditsState | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [schedule, setSchedule] = useState<ReportPackSchedule | null>(null);
  const [canManageSchedule, setCanManageSchedule] = useState(false);
  const [scheduleError, setScheduleError] = useState("");
  const [scheduleLoading, setScheduleLoading] = useState(true);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);
  const [recipientsDraft, setRecipientsDraft] = useState("");

  useEffect(() => {
    const load = async () => {
      setIsLoading(true);
      setError("");
      setScheduleLoading(true);
      setScheduleError("");
      const [creditsResult, scheduleResult] = await Promise.all([getCredits(), getReportPackSchedule()]);
      if (creditsResult.success && creditsResult.credits) {
        setCredits(creditsResult.credits);
      } else {
        setCredits(null);
        setError(creditsResult.error || "Unable to load billing usage.");
      }

      if (scheduleResult.success && scheduleResult.schedule) {
        setSchedule(scheduleResult.schedule);
        setCanManageSchedule(Boolean(scheduleResult.can_manage));
        setRecipientsDraft((scheduleResult.schedule.recipients || []).join(", "));
      } else {
        setSchedule(null);
        setCanManageSchedule(false);
        setScheduleError(
          scheduleResult.error || scheduleResult.upgrade_message || "Unable to load executive report pack schedule.",
        );
      }

      setIsLoading(false);
      setScheduleLoading(false);
    };
    void load();
  }, []);

  const recipientsList = useMemo(
    () =>
      recipientsDraft
        .split(",")
        .map((item) => item.trim().toLowerCase())
        .filter(Boolean),
    [recipientsDraft],
  );

  const handleSaveSchedule = async () => {
    if (!schedule) {
      return;
    }
    setIsSavingSchedule(true);
    const result = await updateReportPackSchedule({
      enabled: schedule.enabled,
      cadence: schedule.cadence,
      recipients: recipientsList,
    });
    if (result.success && result.schedule) {
      setSchedule(result.schedule);
      setRecipientsDraft((result.schedule.recipients || []).join(", "));
      toast.success("Executive report pack schedule saved. Delivery still depends on email configuration.");
      setScheduleError("");
    } else {
      setScheduleError(result.error || "Unable to save schedule settings.");
      toast.error(result.error || "Unable to save schedule settings.");
    }
    setIsSavingSchedule(false);
  };

  const isPaidSubscription =
    Boolean(credits?.has_active_subscription) ||
    currentPlan?.planType === "pro_monthly" ||
    currentPlan?.planType === "pro_annual";
  const planLabel = currentPlan?.firmPlan
    ? currentPlan.firmPlan === "leadership"
      ? "Firm"
      : currentPlan.firmPlan === "professional"
        ? "Team"
        : "Free"
    : currentPlan?.planLabel || (isPaidSubscription ? "Team" : "Free");
  const nextUpgradePlan = currentPlan?.planType === "pro_annual" ? null : currentPlan?.planType === "pro_monthly" ? "firm" : "team";
  const nextUpgradeLabel = nextUpgradePlan === "firm" ? "Firm" : "Team";
  const focusedUpgradePath = nextUpgradePlan ? `/pricing?intent=${nextUpgradePlan}` : "/pricing";
  const planLimits = resolvePlanLimits(currentPlan);

  return (
      <section className="gov-page space-y-6">
        <GovPageHeader
          title="Billing & Usage"
          subtitle="Current plan allowances and automation settings."
          actions={
            <Link to={focusedUpgradePath} className="gov-btn-secondary">
              {nextUpgradePlan ? `View ${nextUpgradeLabel} overview` : "View plan details"}
            </Link>
          }
        />

        {error && <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{error}</div>}

        <PlanCurrentBanner
          firmPlan={currentPlan?.firmPlan}
          planLabel={planLabel}
          isPaidSubscription={isPaidSubscription}
          planLimits={planLimits}
          nextReset={credits?.next_reset}
          nextUpgradePath={focusedUpgradePath}
          isLoading={isLoading}
        />

        <GovSectionCard accent="attention" padding="lg" className="space-y-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="gov-h2">Automation & Delivery (Included in Team/Firm)</h2>
              <p className="text-sm text-neutral-700">
                Save recipient and cadence settings here. Clarion stores these scheduled recipients and cadence for this
                workspace, but delivery only runs when outbound email is configured for this deployment.
              </p>
              {!canManageSchedule ? (
                <p className="mt-2 text-xs text-neutral-600">
                  Team and Firm unlock saved recipient lists and recurring report-pack cadence for leadership review cycles.
                </p>
              ) : null}
            </div>
            {canManageSchedule ? (
              <span className="gov-badge gov-badge-watch">Included in Team/Firm</span>
            ) : (
              <Link to="/pricing?intent=team" className="gov-btn-secondary">
                Upgrade to Team
              </Link>
            )}
          </div>

          {!canManageSchedule && !scheduleLoading ? (
            <div className="rounded border border-neutral-200 bg-white p-4">
              <p className="text-sm font-semibold text-neutral-900">What this unlocks</p>
              <ul className="mt-2 space-y-1 text-sm text-neutral-700">
                <li>Save the partner or ops distribution list once instead of re-entering recipients each cycle.</li>
                <li>Set a recurring weekly or monthly cadence for report-pack delivery.</li>
                <li>Keep leadership delivery settings attached to the workspace instead of running a manual handoff each time.</li>
              </ul>
            </div>
          ) : null}

          {scheduleError && !scheduleLoading && (
            <div className="rounded border border-amber-300/60 bg-amber-50/30 px-3 py-2 text-sm text-amber-900">
              {scheduleError}
            </div>
          )}

          {scheduleLoading ? (
            <p className="text-sm text-neutral-700">Loading schedule settings...</p>
          ) : schedule ? (
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <label className="flex items-center gap-2 text-sm text-neutral-900">
                  <input
                    type="checkbox"
                    checked={schedule.enabled}
                    disabled={!canManageSchedule}
                    onChange={(event) => setSchedule((prev) => (prev ? { ...prev, enabled: event.target.checked } : prev))}
                  />
                  Enable scheduled report packs
                </label>
                <label className="flex items-center gap-2 text-sm text-neutral-900">
                  Cadence
                  <select
                    className="gov-field max-w-[180px]"
                    value={schedule.cadence}
                    disabled={!canManageSchedule}
                    onChange={(event) =>
                      setSchedule((prev) => (prev ? { ...prev, cadence: event.target.value === "monthly" ? "monthly" : "weekly" } : prev))
                    }
                  >
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </label>
              </div>

              <label className="block text-sm text-neutral-900">
                Recipients (comma-separated)
                <input
                  type="text"
                  className="gov-field mt-1"
                  value={recipientsDraft}
                  disabled={!canManageSchedule}
                  onChange={(event) => setRecipientsDraft(event.target.value)}
                  placeholder="partner@firm.com, ops@firm.com"
                />
              </label>

              <p className="text-xs text-neutral-700">
                Last sent: {schedule.last_sent_at || "Never"} | Next run: {schedule.next_send_at || "Not scheduled"}
              </p>
              {!canManageSchedule ? (
                <p className="text-xs text-neutral-600">
                  Settings are visible here for reference, but editing and scheduled delivery are available on Team and Firm.
                </p>
              ) : null}

              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="gov-btn-primary"
                  disabled={!canManageSchedule || isSavingSchedule}
                  onClick={() => void handleSaveSchedule()}
                >
                  {isSavingSchedule ? "Saving..." : "Save schedule"}
                </button>
              </div>
            </div>
          ) : null}
        </GovSectionCard>
      </section>
  );
};

export default DashboardBilling;
