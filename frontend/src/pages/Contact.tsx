import { useMemo, useState, type FormEvent } from "react";
import PageLayout from "@/components/PageLayout";
import MarketingProofBar from "@/components/MarketingProofBar";
import { createSupportTicket } from "@/api/authService";
import { useAuth } from "@/contexts/AuthContext";

const SUPPORT_EMAIL = "support@clarionhq.co";
const SECURITY_EMAIL = "security@clarionhq.co";

const CATEGORY_OPTIONS = [
  { value: "product_bug", label: "Product issue" },
  { value: "data_upload", label: "CSV upload help" },
  { value: "partner_brief", label: "Partner brief delivery" },
  { value: "billing", label: "Billing" },
  { value: "account_access", label: "Account access" },
  { value: "privacy", label: "Privacy request" },
  { value: "security", label: "Security issue" },
  { value: "other", label: "Other" },
] as const;

const URGENCY_OPTIONS = [
  { value: "low", label: "Low" },
  { value: "normal", label: "Normal" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
] as const;

const Contact = () => {
  const { user, isLoggedIn } = useAuth();
  const [category, setCategory] = useState("product_bug");
  const [urgency, setUrgency] = useState("normal");
  const [name, setName] = useState("");
  const [email, setEmail] = useState(user?.email || "");
  const [firmName, setFirmName] = useState(user?.firm_name || "");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [ticketState, setTicketState] = useState<{
    ticketRef: string;
    status: string;
    priority: string;
    escalation: string;
    autoResponse?: string | null;
    autoResponseEmailSent: boolean;
    supportNotificationSent: boolean;
  } | null>(null);

  const displayedEmail = useMemo(() => (isLoggedIn ? user?.email || email : email), [email, isLoggedIn, user?.email]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitError("");
    setTicketState(null);
    setIsSubmitting(true);

    const result = await createSupportTicket({
      source: "contact",
      category,
      urgency,
      subject,
      message,
      name: isLoggedIn ? undefined : name,
      email: isLoggedIn ? undefined : email,
      firm_name: isLoggedIn ? undefined : firmName,
    });

    setIsSubmitting(false);

    if (!result.success || !result.ticket) {
      setSubmitError(result.error || "Unable to submit support request.");
      return;
    }

    setTicketState({
      ticketRef: result.ticket.ticket_ref,
      status: result.ticket.status,
      priority: result.ticket.priority,
      escalation: result.ticket.escalation_level,
      autoResponse: result.ticket.auto_response_template,
      autoResponseEmailSent: Boolean(result.auto_response_email_sent),
      supportNotificationSent: Boolean(result.support_notification_sent),
    });
    setSubject("");
    setMessage("");
    if (!isLoggedIn) {
      setName("");
    }
  };

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container max-w-4xl space-y-5">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Support
          </p>
          <h1 className="marketing-hero-title">Support that stays structured when something needs attention.</h1>
          <p className="max-w-3xl marketing-hero-body">
            The primary support path in Clarion is a tracked ticket: submit the issue once, keep the details attached to
            the request, and route sensitive categories into the right review path.
          </p>
          <MarketingProofBar
            items={[
              "Real ticket intake",
              "Server-side triage and escalation",
              "Support inbox stays consistent",
            ]}
          />
          <div className="max-w-3xl rounded-2xl border border-white/10 bg-white/5 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-200">Preferred support path</p>
            <div className="mt-3 grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-start">
              <div>
                <p className="text-sm font-medium text-white">Use the form for operational support</p>
                <p className="mt-1 text-sm leading-6 text-slate-200">
                  Product issues, uploads, billing, account access, privacy requests, and partner-brief delivery all
                  create a tracked ticket here.
                </p>
              </div>
              <div className="hidden self-center text-blue-300 md:block">/</div>
              <div>
                <p className="text-sm font-medium text-white">Use direct email only when needed</p>
                <p className="mt-1 text-sm leading-6 text-slate-200">
                  Security reports and urgent follow-up can still go by email, but the form remains the primary intake
                  path for support work.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="supporting-section border-y border-slate-200 bg-slate-50">
        <div className="section-container max-w-5xl grid gap-5 lg:grid-cols-[1.3fr_0.9fr]">
          <article className="supporting-lead">
            <div className="grid gap-5 border-b border-slate-200 pb-5 lg:grid-cols-[1fr_auto] lg:items-end">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Primary intake</p>
                <h2 className="mt-2 text-2xl font-semibold text-slate-900">Open a support ticket</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                  Submit the issue once and Clarion creates the tracked ticket reference shown on this page. Sensitive
                  categories keep their escalation handling; routine issues can still receive immediate guidance.
                </p>
              </div>
              <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 lg:max-w-[220px]">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Before you submit</p>
                <p className="mt-2 text-sm text-slate-700">
                  Include the workflow, the validation message, and how to reproduce the issue if applicable.
                </p>
              </div>
            </div>

            {submitError ? (
              <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {submitError}
              </div>
            ) : null}

            {ticketState ? (
              <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-4 text-sm text-emerald-900">
                <p className="font-semibold">Support request created: {ticketState.ticketRef}</p>
                <p className="mt-1">
                  Status: {ticketState.status} | Priority: {ticketState.priority} | Escalation: {ticketState.escalation}
                </p>
                {ticketState.autoResponse ? <p className="mt-2">{ticketState.autoResponse}</p> : null}
                <p className="mt-2 text-emerald-800">
                  {ticketState.autoResponseEmailSent
                    ? `An acknowledgement email was sent to ${displayedEmail || "your email"}.`
                    : "No acknowledgement email was sent from this deployment, but the ticket was still stored in Clarion."}
                </p>
                <p className="mt-2 text-emerald-800">
                  {ticketState.supportNotificationSent
                    ? "The support inbox was notified automatically."
                    : `Automatic inbox delivery is unavailable on this deployment. If the issue is urgent, email ${SUPPORT_EMAIL} and include ${ticketState.ticketRef}.`}
                </p>
              </div>
            ) : null}

            <form className="mt-6 space-y-5" onSubmit={(event) => void handleSubmit(event)}>
              {!isLoggedIn ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <label className="block text-sm text-slate-700">
                    Name
                    <input
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                    />
                  </label>
                  <label className="block text-sm text-slate-700">
                    Firm name
                    <input
                      value={firmName}
                      onChange={(event) => setFirmName(event.target.value)}
                      className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                    />
                  </label>
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm text-slate-700">
                  Contact email
                  <input
                    type="email"
                    value={isLoggedIn ? user?.email || "" : email}
                    onChange={(event) => setEmail(event.target.value)}
                    disabled={isLoggedIn}
                    className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900 disabled:bg-slate-50"
                  />
                </label>
                <label className="block text-sm text-slate-700">
                  Category
                  <select
                    value={category}
                    onChange={(event) => setCategory(event.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                  >
                    {CATEGORY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <div className="grid gap-4 md:grid-cols-[1fr_180px]">
                <label className="block text-sm text-slate-700">
                  Subject
                  <input
                    value={subject}
                    onChange={(event) => setSubject(event.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                    placeholder="Brief summary of the issue"
                  />
                </label>
                <label className="block text-sm text-slate-700">
                  Urgency
                  <select
                    value={urgency}
                    onChange={(event) => setUrgency(event.target.value)}
                    className="mt-1 h-10 w-full rounded-md border border-slate-300 bg-white px-3 text-sm text-slate-900"
                  >
                    {URGENCY_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <label className="block text-sm text-slate-700">
                Message
                <textarea
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  className="mt-1 min-h-[180px] w-full rounded-md border border-slate-300 bg-white px-3 py-3 text-sm text-slate-900"
                  placeholder="Include the page, workflow, validation message, or reproduction steps."
                />
              </label>

              <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-4">
                <p className="text-xs text-slate-500">
                  Form submission creates the structured ticket record for this request.
                </p>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="gov-btn-primary disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {isSubmitting ? "Submitting..." : "Submit support request"}
                </button>
              </div>
            </form>
          </article>

          <div className="space-y-5">
            <article className="supporting-subtle">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Direct contact</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">Support addresses</h2>
              <div className="mt-4 space-y-3 text-sm text-slate-700">
                <p>
                  General support:{" "}
                  <a href={`mailto:${SUPPORT_EMAIL}`} className="font-semibold text-slate-900 hover:underline">
                    {SUPPORT_EMAIL}
                  </a>
                </p>
                <p>
                  Security reports:{" "}
                  <a href={`mailto:${SECURITY_EMAIL}`} className="font-semibold text-slate-900 hover:underline">
                    {SECURITY_EMAIL}
                  </a>
                </p>
                <p className="text-xs text-slate-500">
                  Direct email reaches the support inbox, but the form on this page remains the preferred structured
                  intake path.
                </p>
              </div>
            </article>

            <article className="supporting-subtle">
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Triage model</p>
              <h2 className="mt-2 text-lg font-semibold text-slate-900">How requests are handled</h2>
              <div className="supporting-divider-list mt-4">
                <div className="py-3 first:pt-0">
                  <p className="text-sm text-slate-700">
                    Security, privacy, billing, and account-sensitive requests are escalated for manual review.
                  </p>
                </div>
                <div className="py-3">
                  <p className="text-sm text-slate-700">
                    Common product, upload, and partner-brief issues can receive automated guidance immediately.
                  </p>
                </div>
                <div className="py-3">
                  <p className="text-sm text-slate-700">
                    Every request is stored as a ticket with status, priority, escalation level, and timestamps.
                  </p>
                </div>
                <div className="py-3 last:pb-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    What helps support move faster
                  </p>
                  <ul className="mt-2 space-y-2 text-sm text-slate-700">
                    <li>Firm name and account email</li>
                    <li>The page or workflow where the problem occurred</li>
                    <li>Validation messages, screenshots, or steps to reproduce</li>
                  </ul>
                </div>
              </div>
            </article>
          </div>
        </div>
      </section>
    </PageLayout>
  );
};

export default Contact;
