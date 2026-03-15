import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import { toast } from "sonner";
import GovPageHeader from "@/components/governance/GovPageHeader";
import GovSectionCard from "@/components/governance/GovSectionCard";
import { useAuth } from "@/contexts/AuthContext";
import {
  createSupportTicket,
  emitPlanLimitError,
  getSupportTickets,
  loadOnboardingDemoDataset,
  updateSupportTicket,
  type SupportTicket,
} from "@/api/authService";

type AccountTab = "profile" | "billing" | "security";

const SUPPORT_CATEGORY_OPTIONS = [
  { value: "product_bug", label: "Product issue" },
  { value: "data_upload", label: "CSV upload help" },
  { value: "partner_brief", label: "Partner brief delivery" },
  { value: "billing", label: "Billing" },
  { value: "account_access", label: "Account access" },
  { value: "privacy", label: "Privacy request" },
  { value: "security", label: "Security issue" },
  { value: "other", label: "Other" },
] as const;

const TABS: Array<{ key: AccountTab; label: string }> = [
  { key: "profile", label: "Account" },
  { key: "billing", label: "Billing" },
  { key: "security", label: "Security" },
];

const tabButtonClass = (active: boolean) =>
  [
    "rounded border px-3 py-1.5 text-xs font-medium transition-colors",
    active
      ? "border-neutral-300 bg-neutral-100 text-neutral-900"
      : "border-neutral-200 bg-white text-neutral-700 hover:bg-neutral-50",
  ].join(" ");

const supportCategoryLabel = (value: string) =>
  SUPPORT_CATEGORY_OPTIONS.find((option) => option.value === value)?.label || value;

const supportStatusClass = (status: string) => {
  if (status === "resolved") return "border-emerald-200 bg-emerald-50 text-emerald-800";
  if (status === "in_review") return "border-blue-200 bg-blue-50 text-blue-800";
  return "border-amber-200 bg-amber-50 text-amber-900";
};

const supportEscalationClass = (level: string) => {
  if (level === "high" || level === "critical") return "border-rose-200 bg-rose-50 text-rose-800";
  if (level === "medium") return "border-amber-200 bg-amber-50 text-amber-900";
  return "border-slate-200 bg-slate-50 text-slate-700";
};

const SecurityChecklist = () => {
  return (
    <section className="gov-level-2 p-6" aria-label="Security capabilities">
      <h2 className="gov-h2 mb-1">Security</h2>
      <p className="mb-4 text-sm text-neutral-700">
        Current safeguards and operational boundaries for this deployment.
      </p>

      <div className="space-y-4">
        <article className="rounded border border-neutral-200 bg-white p-4">
          <p className="gov-micro-label">Implemented In Clarion</p>
          <div className="mt-3 space-y-3 text-sm text-neutral-800">
            <div>
              <p className="font-semibold text-neutral-900">Authentication And Session Controls</p>
              <ul className="mt-1 space-y-1">
                <li>Session cookies are HttpOnly.</li>
                <li>Session cookies use SameSite=Lax by default.</li>
                <li>Secure cookie mode is enabled outside debug by configuration.</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-neutral-900">Access Control And Firm Scoping</p>
              <ul className="mt-1 space-y-1">
                <li>Firm context is required on governance API routes.</li>
                <li>Reports, actions, and governance briefs are queried with firm scope.</li>
                <li>Cross-firm access attempts are rejected.</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-neutral-900">Request Traceability</p>
              <ul className="mt-1 space-y-1">
                <li>API responses include a request ID header for support and incident tracing.</li>
                <li>Error responses include request IDs so events can be correlated in server logs.</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-neutral-900">Upload Validation</p>
              <ul className="mt-1 space-y-1">
                <li>CSV upload checks file type and required structure before processing.</li>
                <li>Server-side row limits and validation are applied during ingestion.</li>
              </ul>
            </div>
            <div>
              <p className="font-semibold text-neutral-900">Export And Abuse Controls</p>
              <ul className="mt-1 space-y-1">
                <li>Plan gates and history windows are enforced server-side for report and PDF access.</li>
                <li>Rate limits are applied on authentication and high-cost API endpoints.</li>
              </ul>
            </div>
          </div>
        </article>

        <article className="rounded border border-neutral-200 bg-white p-4">
          <p className="gov-micro-label">Deployment Responsibilities</p>
          <ul className="mt-3 space-y-2 text-sm text-neutral-800">
            <li>
              <span className="font-semibold text-neutral-900">Transport Security (TLS/HTTPS): </span>
              Enforced by hosting or reverse-proxy configuration.
            </li>
            <li>
              <span className="font-semibold text-neutral-900">Encryption At Rest: </span>
              Provided by your infrastructure provider and database/storage configuration.
            </li>
            <li>
              <span className="font-semibold text-neutral-900">Backup And Retention Operations: </span>
              Managed at the deployment layer unless separately configured.
            </li>
          </ul>
        </article>

        <article className="rounded border border-neutral-200 bg-white p-4">
          <p className="gov-micro-label">What Matters For Law Firm Review</p>
          <ul className="mt-3 space-y-2 text-sm text-neutral-800">
            <li>Firm-scoped access controls for reports, actions, and client issues.</li>
            <li>Server-side plan enforcement on export and report-history endpoints.</li>
            <li>Rate limiting and request correlation for incident and abuse response.</li>
            <li>Clear separation between application controls and infrastructure controls.</li>
          </ul>
        </article>
      </div>
    </section>
  );
};


const DashboardAccount = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [supportTickets, setSupportTickets] = useState<SupportTicket[]>([]);
  const [supportQueue, setSupportQueue] = useState<SupportTicket[]>([]);
  const [supportLoading, setSupportLoading] = useState(false);
  const [supportError, setSupportError] = useState("");
  const [supportSubmitting, setSupportSubmitting] = useState(false);
  const [supportSummary, setSupportSummary] = useState<{ open_count: number; escalated_count: number } | null>(null);
  const [supportSubmissionState, setSupportSubmissionState] = useState<{
    ticketRef: string;
    autoResponseEmailSent: boolean;
    supportNotificationSent: boolean;
  } | null>(null);
  const [queueUpdatingTicketId, setQueueUpdatingTicketId] = useState<number | null>(null);
  const [supportCategory, setSupportCategory] = useState("product_bug");
  const [supportUrgency, setSupportUrgency] = useState("normal");
  const [supportSubject, setSupportSubject] = useState("");
  const [supportMessage, setSupportMessage] = useState("");
  const [internalTestingAvailable, setInternalTestingAvailable] = useState(false);
  const [internalTestingLoading, setInternalTestingLoading] = useState(false);
  const [internalTestingBusy, setInternalTestingBusy] = useState(false);

  const activeTab = useMemo<AccountTab>(() => {
    const raw = (searchParams.get("tab") || "profile").toLowerCase();
    return raw === "billing" || raw === "security" || raw === "profile" ? (raw as AccountTab) : "profile";
  }, [searchParams]);

  const setTab = (tab: AccountTab) => {
    const next = new URLSearchParams(searchParams);
    next.set("tab", tab);
    setSearchParams(next, { replace: true });
  };

  useEffect(() => {
    if (activeTab !== "profile" || !user?.is_admin) {
      setInternalTestingAvailable(false);
      return;
    }
    let active = true;
    const loadSystemStatus = async () => {
      setInternalTestingLoading(true);
      try {
        const response = await fetch("/api/system/status", {
          method: "GET",
          credentials: "include",
        });
        const payload = (await response.json()) as { internal_testing_available?: boolean };
        if (active) {
          setInternalTestingAvailable(payload.internal_testing_available === true);
        }
      } catch {
        if (active) {
          setInternalTestingAvailable(false);
        }
      } finally {
        if (active) {
          setInternalTestingLoading(false);
        }
      }
    };
    void loadSystemStatus();
    return () => {
      active = false;
    };
  }, [activeTab, user?.is_admin]);


  useEffect(() => {
    if (activeTab !== "profile") return;
    let active = true;
    const loadSupport = async () => {
      setSupportLoading(true);
      const [selfResult, queueResult] = await Promise.all([
        getSupportTickets(),
        user?.is_admin ? getSupportTickets({ scope: "queue" }) : Promise.resolve({ success: true as const, tickets: [] as SupportTicket[] }),
      ]);
      if (!active) return;
      if (!selfResult.success || !selfResult.tickets) {
        setSupportTickets([]);
        setSupportError(selfResult.error || "Unable to load support tickets.");
        setSupportSummary(null);
      } else {
        setSupportTickets(selfResult.tickets);
        setSupportError("");
        setSupportSummary(selfResult.summary || null);
      }
      if (user?.is_admin && queueResult.success && queueResult.tickets) {
        setSupportQueue(queueResult.tickets);
      } else if (user?.is_admin) {
        setSupportQueue([]);
      }
      setSupportLoading(false);
    };
    void loadSupport();
    return () => {
      active = false;
    };
  }, [activeTab, user?.is_admin]);


  const refreshSupportTickets = async () => {
    const [selfResult, queueResult] = await Promise.all([
      getSupportTickets(),
      user?.is_admin ? getSupportTickets({ scope: "queue" }) : Promise.resolve({ success: true as const, tickets: [] as SupportTicket[] }),
    ]);
    if (selfResult.success && selfResult.tickets) {
      setSupportTickets(selfResult.tickets);
      setSupportError("");
      setSupportSummary(selfResult.summary || null);
    } else {
      setSupportError(selfResult.error || "Unable to load support tickets.");
      setSupportSummary(null);
    }
    if (user?.is_admin && queueResult.success && queueResult.tickets) {
      setSupportQueue(queueResult.tickets);
    }
  };

  const handleSupportSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSupportSubmitting(true);
    const result = await createSupportTicket({
      source: "dashboard",
      category: supportCategory,
      urgency: supportUrgency,
      subject: supportSubject,
      message: supportMessage,
    });
    setSupportSubmitting(false);
    if (!result.success || !result.ticket) {
      toast.error(result.error || "Unable to submit support request.");
      return;
    }
    setSupportSubmissionState({
      ticketRef: result.ticket.ticket_ref,
      autoResponseEmailSent: Boolean(result.auto_response_email_sent),
      supportNotificationSent: Boolean(result.support_notification_sent),
    });
    toast.success(`Support request logged under ${result.ticket.ticket_ref}.`);
    setSupportSubject("");
    setSupportMessage("");
    await refreshSupportTickets();
  };

  const handleSupportQueueUpdate = async (ticketId: number, status: "in_review" | "resolved") => {
    setQueueUpdatingTicketId(ticketId);
    const result = await updateSupportTicket(ticketId, { status });
    setQueueUpdatingTicketId(null);
    if (!result.success) {
      toast.error(result.error || "Unable to update support ticket.");
      return;
    }
    toast.success(status === "resolved" ? "Ticket marked resolved." : "Ticket moved to in review.");
    await refreshSupportTickets();
  };

  const handleLoadExampleCycle = async () => {
    setInternalTestingBusy(true);
    const result = await loadOnboardingDemoDataset();
    setInternalTestingBusy(false);
    if (!result.success) {
      toast.error(result.error || "Unable to load example cycle.");
      return;
    }
    toast.success("Example cycle loaded into the current test workspace.");
    window.dispatchEvent(new Event("reports:uploaded"));
  };

  return (
      <section className="gov-page px-8 py-8">
        <div className="mx-auto w-full max-w-[1200px] space-y-6">
          <GovPageHeader
            title="Account"
            subtitle="Profile, billing, and security controls for your workspace."
          />

          <div className="flex flex-wrap items-center gap-2" role="tablist" aria-label="Account sections">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                onClick={() => setTab(tab.key)}
                className={tabButtonClass(activeTab === tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {activeTab === "profile" && (
            <section className="grid gap-4 md:grid-cols-2" aria-label="Profile section">
              <GovSectionCard accent="neutral" padding="lg" className="md:col-span-2">
                <p className="gov-micro-label">WORKSPACE ADMINISTRATION</p>
                <h2 className="gov-h2 mt-2">Workspace Administration</h2>
                <p className="mt-1 max-w-3xl text-sm text-neutral-700">
                  Manage the workspace basics that support each governance cycle: identity, team access, support intake,
                  and internal operations when applicable.
                </p>
                <div className="mt-4 flex flex-wrap gap-2">
                  <Link to="/dashboard/billing" className="gov-btn-secondary">
                    Open Billing & Credits
                  </Link>
                  <Link to="/dashboard/security" className="gov-btn-secondary">
                    Open Security
                  </Link>
                </div>
              </GovSectionCard>
              <GovSectionCard accent="watch" padding="md">
                <p className="gov-micro-label">FIRM</p>
                <p className="mt-1 text-lg font-semibold text-neutral-900">{user?.firm_name || "Not set"}</p>
                <p className="mt-2 text-sm text-neutral-700">
                  Primary workspace identity used for report ownership, access control, and leadership-facing outputs.
                </p>
              </GovSectionCard>
              <GovSectionCard accent="watch" padding="md">
                <p className="gov-micro-label">PRIMARY ACCOUNT EMAIL</p>
                <p className="mt-1 text-lg font-semibold text-neutral-900">{user?.email || "Not available"}</p>
                <p className="mt-2 text-sm text-neutral-700">Sign-in and account notices are sent to this address.</p>
              </GovSectionCard>
              <GovSectionCard accent="watch" padding="lg" className="md:col-span-2">
                <h2 className="gov-h2">Team & Seats</h2>
                <p className="mt-1 text-sm text-neutral-700">
                  Multi-user team access is not available in this release. Single-seat workspace access is fully operational.
                </p>
              </GovSectionCard>
              <GovSectionCard accent="watch" padding="lg" className="md:col-span-2">
                <p className="gov-micro-label">SUPPORT SPACE</p>
                <h2 className="gov-h2 mt-2">Support</h2>
                <p className="mt-1 max-w-3xl text-sm text-neutral-700">
                  Use the tracked support path for product, billing, account, privacy, and security issues. Clarion stores
                  the request, assigns status and priority, and keeps the latest ticket history visible here.
                </p>
                <div className="mt-4 grid gap-3 md:grid-cols-3">
                  <div className="rounded border border-neutral-200 bg-white px-4 py-3">
                    <p className="gov-micro-label">PRIMARY PATH</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900">Submit a tracked request</p>
                    <p className="mt-1 text-xs text-neutral-600">Use the form when you need a ticket reference and in-product status updates.</p>
                  </div>
                  <div className="rounded border border-neutral-200 bg-white px-4 py-3">
                    <p className="gov-micro-label">OPEN</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900">
                      {supportSummary ? `${supportSummary.open_count} ticket${supportSummary.open_count === 1 ? "" : "s"}` : "Loading..."}
                    </p>
                    <p className="mt-1 text-xs text-neutral-600">Requests still in queue or under review.</p>
                  </div>
                  <div className="rounded border border-neutral-200 bg-white px-4 py-3">
                    <p className="gov-micro-label">ESCALATED</p>
                    <p className="mt-1 text-sm font-semibold text-neutral-900">
                      {supportSummary ? `${supportSummary.escalated_count}` : "Loading..."}
                    </p>
                    <p className="mt-1 text-xs text-neutral-600">Tickets currently marked for higher-priority handling.</p>
                  </div>
                </div>
                <div className="mt-4 grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
                  <div className="rounded border border-neutral-200 bg-white p-5">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="gov-micro-label">NEW REQUEST</p>
                        <h3 className="mt-1 text-base font-semibold text-neutral-900">Open a support ticket</h3>
                        <p className="mt-1 text-sm text-neutral-700">
                          Describe the issue, expected outcome, and any reproduction steps. The request stays visible here after submission.
                        </p>
                      </div>
                      <div className="rounded border border-neutral-200 bg-neutral-50 px-3 py-2 text-xs text-neutral-600">
                        Tracked tickets are the preferred support path.
                      </div>
                    </div>
                    <form className="mt-4 space-y-3" onSubmit={handleSupportSubmit}>
                      <div className="grid gap-3 md:grid-cols-2">
                        <select
                          value={supportCategory}
                          onChange={(event) => setSupportCategory(event.target.value)}
                          className="rounded border border-neutral-300 px-3 py-2 text-sm"
                        >
                          {SUPPORT_CATEGORY_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                        <select
                          value={supportUrgency}
                          onChange={(event) => setSupportUrgency(event.target.value)}
                          className="rounded border border-neutral-300 px-3 py-2 text-sm"
                        >
                          <option value="low">Low</option>
                          <option value="normal">Normal</option>
                          <option value="high">High</option>
                          <option value="critical">Critical</option>
                        </select>
                      </div>
                      <input
                        value={supportSubject}
                        onChange={(event) => setSupportSubject(event.target.value)}
                        placeholder="Short subject"
                        className="w-full rounded border border-neutral-300 px-3 py-2 text-sm"
                      />
                      <textarea
                        value={supportMessage}
                        onChange={(event) => setSupportMessage(event.target.value)}
                        placeholder="Describe the issue, page, validation message, or steps to reproduce."
                        className="min-h-[140px] w-full rounded border border-neutral-300 px-3 py-2 text-sm"
                      />
                      <div className="flex flex-wrap items-center gap-2">
                        <button type="submit" className="gov-btn-primary" disabled={supportSubmitting}>
                          {supportSubmitting ? "Submitting..." : "Submit support request"}
                        </button>
                      </div>
                      {supportSubmissionState ? (
                        <div className="rounded border border-emerald-200 bg-emerald-50 px-3 py-3 text-sm text-emerald-900">
                          <p className="font-medium">Ticket created: {supportSubmissionState.ticketRef}</p>
                          <p className="mt-1">
                            {supportSubmissionState.autoResponseEmailSent
                              ? "An acknowledgement email was sent."
                              : "No acknowledgement email was sent from this deployment, but the ticket is stored."}
                          </p>
                          <p className="mt-1">
                            {supportSubmissionState.supportNotificationSent
                              ? "The support inbox was notified automatically."
                              : "Automatic inbox notification is unavailable on this deployment. Email support@clarionhq.co with the ticket reference if the issue is urgent."}
                          </p>
                        </div>
                      ) : null}
                    </form>
                  </div>
                  <div className="space-y-4">
                    <div className="rounded border border-neutral-200 bg-white p-5">
                      <p className="gov-micro-label">STATUS AND CONTACT</p>
                      <h3 className="mt-1 text-base font-semibold text-neutral-900">Support routing</h3>
                      <div className="mt-3 space-y-3 text-sm text-neutral-700">
                        <div className="rounded border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="font-medium text-neutral-900">Tracked ticket path</p>
                          <p className="mt-1">
                            Clarion keeps request status, priority, and escalation handling tied to the ticket history below.
                          </p>
                        </div>
                        <div className="rounded border border-neutral-200 bg-neutral-50 px-3 py-3">
                          <p className="font-medium text-neutral-900">Direct contact</p>
                          <p className="mt-1">
                            Use direct email when inbox delivery or escalation follow-up needs an external thread.
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            <a href="mailto:support@clarionhq.co" className="gov-btn-secondary">
                              Email support@clarionhq.co
                            </a>
                            <a href="mailto:security@clarionhq.co" className="gov-btn-secondary">
                              Email security@clarionhq.co
                            </a>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="rounded border border-neutral-200 bg-white p-5">
                      <p className="gov-micro-label">{user?.is_admin ? "RECENT TICKETS" : "YOUR RECENT TICKETS"}</p>
                      <h3 className="mt-1 text-base font-semibold text-neutral-900">Recent request history</h3>
                      <p className="mt-1 text-sm text-neutral-700">
                        Review the latest ticket references, status, and escalation state for this workspace.
                      </p>
                      {supportError ? <p className="mt-3 text-xs text-red-700">{supportError}</p> : null}
                      {supportLoading ? (
                        <p className="mt-4 text-sm text-neutral-600">Loading support tickets...</p>
                      ) : supportTickets.length === 0 ? (
                        <p className="mt-4 text-sm text-neutral-600">No support requests yet.</p>
                      ) : (
                        <ul className="mt-4 space-y-3">
                          {supportTickets.slice(0, 5).map((ticket) => (
                            <li key={ticket.id} className="rounded border border-neutral-200 bg-neutral-50 px-3 py-3 text-sm text-neutral-800">
                              <div className="flex flex-wrap items-start justify-between gap-2">
                                <div>
                                  <p className="font-semibold text-neutral-900">{ticket.ticket_ref}</p>
                                  <p className="mt-1 text-sm text-neutral-900">{ticket.subject}</p>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                  <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${supportStatusClass(ticket.status)}`}>
                                    {ticket.status.replaceAll("_", " ")}
                                  </span>
                                  {ticket.escalation_level !== "none" ? (
                                    <span className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-medium ${supportEscalationClass(ticket.escalation_level)}`}>
                                      Escalated: {ticket.escalation_level}
                                    </span>
                                  ) : null}
                                </div>
                              </div>
                              <p className="mt-2 text-xs text-neutral-600">
                                {supportCategoryLabel(ticket.category)} | {ticket.priority} priority
                              </p>
                              <p className="mt-1 text-xs text-neutral-500">Updated {new Date(ticket.updated_at).toLocaleString()}</p>
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              </GovSectionCard>
              {user?.is_admin ? (
                <GovSectionCard accent="neutral" padding="lg" className="md:col-span-2 border-slate-300 bg-slate-50/70">
                  <p className="gov-micro-label">ADMIN ONLY</p>
                  <h2 className="gov-h2 mt-2">Admin Operations</h2>
                  <p className="mt-1 text-sm text-neutral-700">
                    Internal queue handling and testing tools for owner/admin use. These controls are operational and do
                    not affect the standard workspace administration experience for normal users.
                  </p>
                  <div className="mt-4 grid gap-4">
                    <div className="rounded border border-neutral-200 bg-white p-4">
                      <h3 className="text-sm font-semibold text-neutral-900">Support Queue</h3>
                      <p className="mt-1 text-sm text-neutral-700">
                        Admin-visible queue of the latest support requests, including escalated billing, account, privacy,
                        and security tickets.
                      </p>
                      <div className="mt-3 space-y-3">
                        {supportLoading ? (
                          <p className="text-sm text-neutral-600">Loading queue...</p>
                        ) : supportQueue.length === 0 ? (
                          <p className="text-sm text-neutral-600">No support tickets in the queue.</p>
                        ) : (
                          supportQueue.slice(0, 10).map((ticket) => (
                            <div key={`queue-${ticket.id}`} className="rounded border border-neutral-200 bg-white p-4">
                              <div className="flex flex-wrap items-start justify-between gap-3">
                                <div>
                                  <p className="font-semibold text-neutral-900">
                                    {ticket.ticket_ref} - {ticket.subject}
                                  </p>
                                  <p className="mt-1 text-sm text-neutral-700">
                                    {ticket.requester_email} {ticket.firm_name ? `| ${ticket.firm_name}` : ""}
                                  </p>
                                  <p className="mt-1 text-xs text-neutral-600">
                                    {ticket.category} | {ticket.urgency} urgency | {ticket.priority} priority | {ticket.status}
                                    {ticket.escalation_level !== "none" ? ` | escalated: ${ticket.escalation_level}` : ""}
                                  </p>
                                  {ticket.escalation_reason ? (
                                    <p className="mt-1 text-xs text-neutral-700">{ticket.escalation_reason}</p>
                                  ) : null}
                                </div>
                                <div className="flex flex-wrap gap-2">
                                  <button
                                    type="button"
                                    className="gov-btn-secondary"
                                    onClick={() => void handleSupportQueueUpdate(ticket.id, "in_review")}
                                    disabled={queueUpdatingTicketId === ticket.id}
                                  >
                                    {queueUpdatingTicketId === ticket.id ? "Updating..." : "Mark in review"}
                                  </button>
                                  <button
                                    type="button"
                                    className="gov-btn-secondary"
                                    onClick={() => void handleSupportQueueUpdate(ticket.id, "resolved")}
                                    disabled={queueUpdatingTicketId === ticket.id}
                                  >
                                    {queueUpdatingTicketId === ticket.id ? "Updating..." : "Resolve"}
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                    {(internalTestingAvailable || internalTestingLoading) ? (
                      <div className="rounded border border-neutral-200 bg-white p-4">
                        <h3 className="text-sm font-semibold text-neutral-900">Internal Testing</h3>
                        <p className="mt-1 text-sm text-neutral-700">
                          Owner-only tools for running onboarding and first-cycle checks without creating additional accounts.
                        </p>
                        {internalTestingLoading ? (
                          <p className="mt-3 text-sm text-neutral-600">Checking internal testing availability...</p>
                        ) : internalTestingAvailable ? (
                          <div className="mt-4 grid gap-3 md:grid-cols-2">
                            <div className="rounded border border-neutral-200 bg-white p-4">
                              <p className="gov-micro-label">ONBOARDING PREVIEW</p>
                              <p className="mt-2 text-sm text-neutral-700">
                                Re-enter the onboarding flow from the beginning in a read-only owner preview. This does not change workspace data.
                              </p>
                              <a
                                href="/onboarding?preview=true&step=1"
                                className="gov-btn-secondary mt-3 inline-flex items-center gap-2"
                              >
                                <ExternalLink size={14} />
                                Preview onboarding from start
                              </a>
                            </div>
                            <div className="rounded border border-neutral-200 bg-white p-4">
                              <p className="gov-micro-label">START STEP PREVIEW</p>
                              <p className="mt-2 text-sm text-neutral-700">
                                Jump directly into the upload/start portion of onboarding when you only need to test the first-run handoff.
                              </p>
                              <a
                                href="/onboarding?preview=true&step=3"
                                className="gov-btn-secondary mt-3 inline-flex items-center gap-2"
                              >
                                <ExternalLink size={14} />
                                Preview start step
                              </a>
                            </div>
                            <div className="rounded border border-neutral-200 bg-white p-4 md:col-span-2">
                              <p className="gov-micro-label">EXAMPLE CYCLE LOAD</p>
                              <p className="mt-2 text-sm text-neutral-700">
                                Seed the current test workspace with the internal example dataset using the normal ingestion path.
                              </p>
                              <button
                                type="button"
                                className="gov-btn-secondary mt-3"
                                onClick={() => void handleLoadExampleCycle()}
                                disabled={internalTestingBusy}
                              >
                                {internalTestingBusy ? "Loading example cycle..." : "Load example cycle into workspace"}
                              </button>
                            </div>
                            <div className="rounded border border-neutral-200 bg-white p-4 md:col-span-2">
                              <p className="gov-micro-label">ENGINE HARDENING TOOLS</p>
                              <p className="mt-2 text-sm text-neutral-700">
                                Open internal calibration and benchmark utilities in one click. This avoids re-entering internal
                                localhost URLs during calibration/hardening sessions.
                              </p>
                              <div className="mt-3 flex flex-wrap gap-2">
                                <a href="/internal/calibration/" className="gov-btn-secondary inline-flex items-center gap-2">
                                  <ExternalLink size={14} />
                                  Open Calibration Console
                                </a>
                                <a href="/internal/benchmark/themes" className="gov-btn-secondary inline-flex items-center gap-2">
                                  <ExternalLink size={14} />
                                  Open Benchmark Console
                                </a>
                              </div>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                </GovSectionCard>
              ) : null}
            </section>
          )}

          {activeTab === "billing" && (
            <GovSectionCard accent="watch" padding="lg" aria-label="Billing section">
              <h2 className="gov-h2 mb-2">Billing & Credits</h2>
              <p className="mb-4 text-sm text-neutral-700">Plan, usage, and automation scheduling are managed in Billing.</p>
              <Link to="/dashboard/billing" className="gov-btn-secondary">
                Open Billing & Credits
              </Link>
            </GovSectionCard>
          )}

          {activeTab === "security" && <SecurityChecklist />}
        </div>
      </section>
  );
};

export default DashboardAccount;
