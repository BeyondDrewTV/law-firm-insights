import { AlertTriangle, Inbox, MessageSquareWarning } from "lucide-react";

const problems = [
  {
    icon: Inbox,
    title: "Feedback Lives In Too Many Places",
    desc: "Google reviews, Avvo, surveys, and inbox comments rarely end up in one operating view for leadership.",
  },
  {
    icon: MessageSquareWarning,
    title: "Important Patterns Stay Buried",
    desc: "Teams can read comments manually, but recurring communication, billing, and responsiveness issues still slip through.",
  },
  {
    icon: AlertTriangle,
    title: "Action Usually Starts Too Late",
    desc: "By the time a pattern reaches partner attention, the firm may already be feeling it in complaints, churn, or referrals.",
  },
];

const ProblemSection = () => (
  <section className="section-padding">
    <div className="section-container">
      <div className="mb-14 text-center reveal">
        <h2 className="section-heading text-slate-900">Why firms need this now</h2>
        <p className="section-subheading mx-auto text-slate-700">
          Most firms already have feedback. What they usually lack is a steady way to turn that feedback into oversight,
          ownership, and a leadership agenda that stands up in the meeting.
        </p>
      </div>
      <div className="grid gap-8 md:grid-cols-3">
        {problems.map((p, i) => (
          <div key={p.title} className="reveal gov-level-2 p-6 text-center" style={{ transitionDelay: `${i * 100}ms` }}>
            <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-xl border border-blue-100 bg-blue-50">
              <p.icon size={24} className="text-blue-600" />
            </div>
            <h3 className="mb-2 text-lg font-semibold text-slate-900">{p.title}</h3>
            <p className="text-sm leading-relaxed text-slate-700">{p.desc}</p>
          </div>
        ))}
      </div>
    </div>
  </section>
);

export default ProblemSection;
