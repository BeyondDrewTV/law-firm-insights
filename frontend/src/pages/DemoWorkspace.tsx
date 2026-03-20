import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  BarChart2,
  BookOpen,
  CheckSquare,
  ChevronDown,
  FileText,
  RefreshCw,
  Star,
} from "lucide-react";
import PageLayout from "@/components/PageLayout";
import { defaultSampleBriefPath } from "@/data/sampleFirmData";

interface GovernanceSignal {
  title: string;
  description: string;
  severity: "high" | "medium" | "low";
  source_metric: string;
}

interface RecommendedAction {
  title: string;
  suggested_owner: string;
  priority: "high" | "medium" | "low";
}

interface RoadmapItem {
  theme: string;
  action: string;
  timeline: string;
  owner: string;
  kpi: string;
}

interface DemoResult {
  total_reviews: number;
  avg_rating: number;
  positive_share: number;
  negative_share: number;
  themes: Record<string, number>;
  top_praise: string[];
  top_complaints: string[];
  all_reviews: Array<{ rating: number; review_text: string; date: string }>;
  governance_signals: GovernanceSignal[];
  recommended_actions: RecommendedAction[];
  implementation_roadmap: RoadmapItem[];
  partner_brief: string;
}

type Step = 1 | 2 | 3 | 4 | 5;

const STEP_LABELS: Record<Step, string> = {
  1: "Reviews",
  2: "Detected Themes",
  3: "Governance Signals",
  4: "Partner Actions",
  5: "Governance Brief",
};

const STEP_ICONS: Record<Step, ReactNode> = {
  1: <FileText size={16} />,
  2: <BarChart2 size={16} />,
  3: <AlertTriangle size={16} />,
  4: <CheckSquare size={16} />,
  5: <BookOpen size={16} />,
};

function SeverityBadge({ severity }: { severity: "high" | "medium" | "low" }) {
  const cls = {
    high: "bg-red-100 text-red-700 border-red-200",
    medium: "bg-amber-100 text-amber-700 border-amber-200",
    low: "bg-emerald-100 text-emerald-700 border-emerald-200",
  }[severity];

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold capitalize ${cls}`}>
      {severity}
    </span>
  );
}

function StarRating({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <Star
          key={n}
          size={11}
          className={n <= Math.round(rating) ? "fill-amber-400 text-amber-400" : "fill-slate-200 text-slate-200"}
        />
      ))}
    </span>
  );
}

function StepReviews({ data }: { data: DemoResult }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? data.all_reviews : data.all_reviews.slice(0, 8);

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Reviews Processed</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{data.total_reviews}</p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Avg Rating</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">
            {data.avg_rating.toFixed(2)}
            <span className="text-sm font-normal text-slate-500"> / 5</span>
          </p>
        </article>
        <article className="rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Positive Share</p>
          <p className="mt-1 text-3xl font-bold text-slate-900">{data.positive_share}%</p>
        </article>
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[520px] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50">
              <th className="px-3 py-2 font-semibold text-slate-700">Rating</th>
              <th className="px-3 py-2 font-semibold text-slate-700">Review</th>
              <th className="px-3 py-2 font-semibold text-slate-700">Date</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((review, index) => (
              <tr key={index} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2">
                  <StarRating rating={review.rating} />
                </td>
                <td className="px-3 py-2 text-slate-700">{review.review_text}</td>
                <td className="px-3 py-2 text-xs whitespace-nowrap text-slate-500">{review.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {data.all_reviews.length > 8 && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 text-sm text-slate-600 hover:text-slate-900"
        >
          <ChevronDown size={14} className={expanded ? "rotate-180" : ""} />
          {expanded ? "Show fewer" : `Show all ${data.all_reviews.length} reviews`}
        </button>
      )}
    </div>
  );
}

function StepThemes({ data }: { data: DemoResult }) {
  const entries = Object.entries(data.themes).sort(([, a], [, b]) => b - a);
  const max = entries[0]?.[1] ?? 1;

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Clarion groups recurring issues across the uploaded review set and shows how often
        each issue family appears. Each bar reflects how many reviews mention that theme.
      </p>
      <div className="space-y-2">
        {entries.map(([theme, count]) => (
          <div key={theme} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-4">
              <span className="min-w-[160px] text-sm font-semibold text-slate-800">{theme}</span>
              <div className="flex flex-1 items-center gap-2">
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${Math.round((count / max) * 100)}%` }}
                  />
                </div>
                <span className="min-w-[80px] text-right text-sm tabular-nums text-slate-600">
                  {count} mention{count !== 1 ? "s" : ""}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StepSignals({ data }: { data: DemoResult }) {
  if (!data.governance_signals.length) {
    return <p className="text-sm text-slate-500">No governance signals were generated for this dataset.</p>;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Clarion turns repeated complaints and service-risk patterns into governance
        signals, each rated by severity.
      </p>
      {data.governance_signals.map((signal, index) => (
        <article key={index} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">{signal.title}</h3>
            <SeverityBadge severity={signal.severity} />
          </div>
          <p className="mt-2 text-sm text-slate-600">{signal.description}</p>
          <p className="mt-1 text-xs text-slate-400">Source metric: {signal.source_metric}</p>
        </article>
      ))}
    </div>
  );
}

function StepActions({ data }: { data: DemoResult }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Recommended actions are produced from the governance signals. Each carries an
        owner suggestion and priority level, matching the format used in the live workspace.
      </p>
      {data.recommended_actions.map((action, index) => (
        <article key={index} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">{action.title}</h3>
            <SeverityBadge severity={action.priority} />
          </div>
          <p className="mt-1 text-sm text-slate-500">
            Suggested owner: <span className="font-medium text-slate-700">{action.suggested_owner}</span>
          </p>
        </article>
      ))}
      {data.implementation_roadmap.length > 0 && (
        <>
          <p className="mt-4 text-sm font-semibold text-slate-800">90-Day Implementation Plan</p>
          {data.implementation_roadmap.map((item, index) => (
            <article key={index} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">{item.action}</p>
              <p className="mt-1 text-xs text-slate-500">
                Theme: {item.theme} &middot; {item.timeline}
              </p>
              <p className="mt-1 text-xs text-slate-500">Owner: {item.owner}</p>
              <p className="mt-1 text-xs text-slate-600">KPI: {item.kpi}</p>
            </article>
          ))}
        </>
      )}
    </div>
  );
}

function StepBrief({ data }: { data: DemoResult }) {
  // Split the raw brief text into readable paragraphs for document-forward rendering
  const paragraphs = data.partner_brief
    .split(/\n{2,}/)
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        This is the governance brief format Clarion produces for partner meetings, using the same sample review set
        and issue priorities shown above.
      </p>

      <article
        className="overflow-hidden rounded-[20px] border border-[#D7D0C3]"
        style={{ background: "linear-gradient(180deg, #fffdfa 0%, #f8f3ea 100%)" }}
      >
        <header className="border-b border-[#D7D0C3] px-6 py-5">
          <p className="landing-preview-label">Partner governance brief</p>
          <p
            className="mt-2 font-semibold text-[#111827]"
            style={{ fontFamily: "'Newsreader', Georgia, serif", fontSize: "1.25rem", lineHeight: "1.3" }}
          >
            Sample Governance Brief
          </p>
          <p className="mt-1 text-sm text-[#5F6470]">
            {data.total_reviews} reviews analyzed · Sample law-firm data
          </p>
        </header>
        <div className="px-6 py-5 space-y-4">
          {paragraphs.map((para, index) => (
            <p
              key={`brief-para-${index}`}
              className="text-sm leading-7 text-[#374151]"
              style={{ borderLeft: index === 0 ? "3px solid #D7D0C3" : undefined, paddingLeft: index === 0 ? "1rem" : undefined }}
            >
              {para}
            </p>
          ))}
        </div>
      </article>

      <div className="rounded-lg border border-[#D7D0C3] bg-[#F6F0E4] p-4 text-sm text-[#374151]">
        <p className="font-semibold text-[#111827]">The sample brief route shows the full governance artifact.</p>
        <p className="mt-1">
          In a live workspace, this brief is generated from your uploaded reviews and delivered as a structured PDF
          covering the cycles you choose to review.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 pt-2">
        <Link to={defaultSampleBriefPath} className="gov-btn-primary">
          Open sample brief
        </Link>
        <Link to="/signup" className="gov-btn-secondary">
          Start workspace
        </Link>
      </div>
    </div>
  );
}

const STEPS: Step[] = [1, 2, 3, 4, 5];
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

const DemoWorkspace = () => {
  const [step, setStep] = useState<Step>(1);
  const [data, setData] = useState<DemoResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  const runAnalysis = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    setStep(1);

    try {
      const response = await fetch(`${API_BASE}/api/demo/analyze`);
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error ?? `Server error ${response.status}`);
      }

      const json = await response.json();
      if (!json.success) {
        throw new Error(json.error ?? "Analysis failed");
      }

      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    runAnalysis();
  }, []);

  const advanceStep = () => {
    if (step < 5) {
      setStep((current) => (current + 1) as Step);
      setTimeout(() => contentRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  };

  return (
    <PageLayout>
      <section className="marketing-hero">
        <div className="section-container space-y-4">
          <p className="landing-kicker">Sample Workspace</p>
          <h1 className="marketing-hero-title">Inspect the sample workspace after you review the brief.</h1>
          <p className="max-w-3xl marketing-hero-body">
            The sample brief is the clearest public proof of Clarion. This workspace stays available as a secondary
            mechanics view so you can inspect how one review set turns into signals, assigned follow-through, and the
            same meeting-ready brief.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Link to={defaultSampleBriefPath} className="gov-btn-primary">
              Review sample brief
            </Link>
            <button
              type="button"
              onClick={runAnalysis}
              disabled={loading}
              className="gov-btn-secondary inline-flex items-center gap-2"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              {loading ? "Refreshing sample workspace..." : "Restart sample workspace"}
            </button>
            <Link to="/signup" className="gov-btn-secondary">
              Start workspace
            </Link>
          </div>
        </div>
      </section>

      <section className="section-container section-padding space-y-6">
        <nav className="flex flex-wrap gap-2">
          {STEPS.map((currentStep) => (
            <button
              key={currentStep}
              type="button"
              onClick={() => data && setStep(currentStep)}
              disabled={!data}
              className={[
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                step === currentStep
                  ? "border-slate-900 bg-slate-900 text-white"
                  : data
                    ? "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
                    : "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-400",
              ].join(" ")}
            >
              {STEP_ICONS[currentStep]}
              <span className="hidden sm:inline">Step {currentStep} - </span>
              {STEP_LABELS[currentStep]}
            </button>
          ))}
        </nav>

        {loading && (
          <article className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
            <RefreshCw size={28} className="mx-auto animate-spin text-slate-400" />
            <p className="mt-3 text-base font-semibold text-slate-700">Refreshing sample workspace...</p>
            <p className="mt-1 text-sm text-slate-500">
              Loading reviews, grouping recurring issues, and preparing the brief
            </p>
          </article>
        )}

        {error && !loading && (
          <article className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
            <p className="font-semibold text-red-800">Sample workspace error</p>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button type="button" onClick={runAnalysis} className="mt-3 gov-btn-secondary text-sm">
              Retry
            </button>
          </article>
        )}

        {data && !loading && (
          <div ref={contentRef}>
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="gov-type-eyebrow">Step {step} of 5</p>
                  <h2 className="mt-1 flex items-center gap-2 text-xl font-semibold text-slate-900">
                    {STEP_ICONS[step]}
                    {STEP_LABELS[step]}
                  </h2>
                </div>
                {step < 5 && (
                  <button
                    type="button"
                    onClick={advanceStep}
                    className="gov-btn-primary inline-flex items-center gap-1.5 text-sm"
                  >
                    Next: {STEP_LABELS[(step + 1) as Step]}
                    <ArrowRight size={14} />
                  </button>
                )}
              </div>

              {step === 1 && <StepReviews data={data} />}
              {step === 2 && <StepThemes data={data} />}
              {step === 3 && <StepSignals data={data} />}
              {step === 4 && <StepActions data={data} />}
              {step === 5 && <StepBrief data={data} />}
            </article>
          </div>
        )}

        {data && !loading && (
          <div className="supporting-cta-strip">
            <p className="text-sm text-slate-600">
              The brief remains the clearest proof artifact. Use this workspace when you want to inspect the mechanics
              behind that same sample cycle.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to={defaultSampleBriefPath} className="gov-btn-primary">
                Review sample brief
              </Link>
              <Link to="/signup" className="gov-btn-secondary">
                Start workspace
              </Link>
            </div>
          </div>
        )}
      </section>
    </PageLayout>
  );
};

export default DemoWorkspace;
