import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import {
  FileText, BarChart2, AlertTriangle, CheckSquare, BookOpen,
  RefreshCw, ChevronRight, ChevronDown, Star, ArrowRight,
} from "lucide-react";
import PageLayout from "@/components/PageLayout";

// ── Types ──────────────────────────────────────────────────────────────────
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

// ── Helpers ────────────────────────────────────────────────────────────────
const STEP_LABELS: Record<Step, string> = {
  1: "Reviews",
  2: "Detected Themes",
  3: "Governance Signals",
  4: "Partner Actions",
  5: "Governance Brief",
};

const STEP_ICONS: Record<Step, React.ReactNode> = {
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

// ── Step 1 — Reviews ──────────────────────────────────────────────────────
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
          <p className="mt-1 text-3xl font-bold text-slate-900">{data.avg_rating.toFixed(2)}<span className="text-sm font-normal text-slate-500"> / 5</span></p>
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
            {shown.map((r, i) => (
              <tr key={i} className="border-b border-slate-100 last:border-0">
                <td className="px-3 py-2"><StarRating rating={r.rating} /></td>
                <td className="px-3 py-2 text-slate-700">{r.review_text}</td>
                <td className="px-3 py-2 text-xs text-slate-500 whitespace-nowrap">{r.date}</td>
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

// ── Step 2 — Detected Themes ──────────────────────────────────────────────
function StepThemes({ data }: { data: DemoResult }) {
  const entries = Object.entries(data.themes).sort(([, a], [, b]) => b - a);
  const max = entries[0]?.[1] ?? 1;
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Themes are detected by the Clarion classification engine using keyword patterns
        across all {data.total_reviews} reviews. Each bar shows how many reviews mention that theme.
      </p>
      <div className="space-y-2">
        {entries.map(([theme, count]) => (
          <div key={theme} className="rounded-lg border border-slate-200 bg-slate-50 p-3">
            <div className="flex items-center justify-between gap-4">
              <span className="text-sm font-semibold text-slate-800 min-w-[160px]">{theme}</span>
              <div className="flex flex-1 items-center gap-2">
                <div className="flex-1 overflow-hidden rounded-full bg-slate-200 h-2">
                  <div
                    className="h-full rounded-full bg-blue-500"
                    style={{ width: `${Math.round((count / max) * 100)}%` }}
                  />
                </div>
                <span className="text-sm text-slate-600 tabular-nums min-w-[80px] text-right">
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

// ── Step 3 — Governance Signals ───────────────────────────────────────────
function StepSignals({ data }: { data: DemoResult }) {
  if (!data.governance_signals.length) {
    return (
      <p className="text-sm text-slate-500">
        No governance signals were generated for this dataset.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        The governance insight engine converts complaint frequency and sentiment ratios
        into exposure signals — each rated by severity.
      </p>
      {data.governance_signals.map((sig, i) => (
        <article key={i} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h3 className="text-base font-semibold text-slate-900">{sig.title}</h3>
            <SeverityBadge severity={sig.severity} />
          </div>
          <p className="mt-2 text-sm text-slate-600">{sig.description}</p>
          <p className="mt-1 text-xs text-slate-400">Source metric: {sig.source_metric}</p>
        </article>
      ))}
    </div>
  );
}

// ── Step 4 — Partner Actions ──────────────────────────────────────────────
function StepActions({ data }: { data: DemoResult }) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-600">
        Recommended actions are produced from the governance signals. Each carries an
        owner suggestion and priority level, matching the format used in the live dashboard.
      </p>
      {data.recommended_actions.map((action, i) => (
        <article key={i} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
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
          {data.implementation_roadmap.map((item, i) => (
            <article key={i} className="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-900">{item.action}</p>
              <p className="mt-1 text-xs text-slate-500">Theme: {item.theme} &middot; {item.timeline}</p>
              <p className="mt-1 text-xs text-slate-500">Owner: {item.owner}</p>
              <p className="mt-1 text-xs text-slate-600">KPI: {item.kpi}</p>
            </article>
          ))}
        </>
      )}
    </div>
  );
}

// ── Step 5 — Partner Brief ─────────────────────────────────────────────────
function StepBrief({ data }: { data: DemoResult }) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-600">
        This is the governance brief Clarion produces for partner meetings.
        It is generated from the real <code className="text-xs bg-slate-100 px-1 rounded">generate_partner_summary()</code> function
        using the actual review data and top issue detected above.
      </p>
      <article className="rounded-lg border border-slate-200 bg-slate-50 p-5">
        <pre className="whitespace-pre-wrap font-mono text-sm text-slate-800 leading-relaxed">
          {data.partner_brief}
        </pre>
      </article>
      <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-sm text-blue-900">
        <p className="font-semibold">This is the real pipeline output.</p>
        <p className="mt-1">
          In a live workspace, this brief is generated from your uploaded reviews and delivered to
          partners as a PDF — covering all cycles you have uploaded.
        </p>
      </div>
      <div className="flex flex-wrap gap-3 pt-2">
        <Link to="/signup" className="gov-btn-primary">Start real workspace</Link>
        <Link to="/pricing" className="gov-btn-secondary">See plans</Link>
      </div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────
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
      const res = await fetch(`${API_BASE}/api/demo/analyze`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error ?? `Server error ${res.status}`);
      }
      const json = await res.json();
      if (!json.success) throw new Error(json.error ?? "Analysis failed");
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  // Auto-run on mount
  useEffect(() => { runAnalysis(); }, []);

  const advanceStep = () => {
    if (step < 5) {
      setStep((s) => (s + 1) as Step);
      setTimeout(() => contentRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
    }
  };

  return (
    <PageLayout>
      {/* Hero */}
      <section className="marketing-hero">
        <div className="section-container space-y-4">
          <p className="inline-flex items-center rounded-full border border-blue-500/30 bg-blue-500/20 px-3 py-1 text-xs font-semibold uppercase tracking-widest text-blue-300">
            Live Demo — Real Pipeline
          </p>
          <h1 className="marketing-hero-title">See Clarion run in 3 minutes</h1>
          <p className="max-w-3xl marketing-hero-body">
            This demo runs 40 law-firm reviews through the real Clarion pipeline — the same
            theme detection, governance signals, and partner brief engine used in live workspaces.
            Nothing is hardcoded.
          </p>
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              type="button"
              onClick={runAnalysis}
              disabled={loading}
              className="gov-btn-secondary inline-flex items-center gap-2"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              {loading ? "Running pipeline…" : "Reset Demo"}
            </button>
            <Link to="/signup" className="gov-btn-primary">Start real workspace</Link>
          </div>
        </div>
      </section>

      <section className="section-container section-padding space-y-6">
        {/* Step nav */}
        <nav className="flex flex-wrap gap-2">
          {STEPS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => data && setStep(s)}
              disabled={!data}
              className={[
                "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm font-medium transition-colors",
                step === s
                  ? "border-slate-900 bg-slate-900 text-white"
                  : data
                  ? "border-slate-200 bg-white text-slate-700 hover:border-slate-400"
                  : "border-slate-100 bg-slate-50 text-slate-400 cursor-not-allowed",
              ].join(" ")}
            >
              {STEP_ICONS[s]}
              <span className="hidden sm:inline">Step {s} — </span>
              {STEP_LABELS[s]}
            </button>
          ))}
        </nav>

        {/* Loading state */}
        {loading && (
          <article className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
            <RefreshCw size={28} className="mx-auto animate-spin text-slate-400" />
            <p className="mt-3 text-base font-semibold text-slate-700">Running real pipeline…</p>
            <p className="mt-1 text-sm text-slate-500">
              Loading reviews → detecting themes → generating governance signals
            </p>
          </article>
        )}

        {/* Error state */}
        {error && !loading && (
          <article className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
            <p className="font-semibold text-red-800">Pipeline error</p>
            <p className="mt-1 text-sm text-red-700">{error}</p>
            <button type="button" onClick={runAnalysis} className="mt-3 gov-btn-secondary text-sm">
              Retry
            </button>
          </article>
        )}

        {/* Step content */}
        {data && !loading && (
          <div ref={contentRef}>
            <article className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
                <div>
                  <p className="gov-type-eyebrow">Step {step} of 5</p>
                  <h2 className="mt-1 text-xl font-semibold text-slate-900 flex items-center gap-2">
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

        {/* CTA strip */}
        {data && !loading && (
          <div className="supporting-cta-strip">
            <p className="text-sm text-slate-600">
              Upload your own reviews to generate a live governance brief for your firm.
            </p>
            <div className="flex flex-wrap gap-3">
              <Link to="/signup" className="gov-btn-primary">Start real workspace</Link>
              <Link to="/pricing" className="gov-btn-secondary">See plans</Link>
            </div>
          </div>
        )}
      </section>
    </PageLayout>
  );
};

export default DemoWorkspace;
