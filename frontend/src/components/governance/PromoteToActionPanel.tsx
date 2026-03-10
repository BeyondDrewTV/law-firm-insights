/**
 * PromoteToActionPanel
 * ─────────────────────────────────────────────────────────────────────────────
 * Right-rail side panel that guides the user through promoting one or more
 * evidence signals into a single Governance Action.
 *
 * Triggered from the selection bar on SignalsPage when ≥1 signal is selected.
 *
 * Layout zones:
 *   1. Panel header   — eyebrow + title + close
 *   2. Evidence recap — selected signal cards (read-only preview)
 *   3. Action form    — heuristic-prefilled editable fields
 *   4. Panel footer   — submit + cancel
 *
 * Design constraints (GOVERNANCE_DESIGN_SYSTEM_V1):
 *   - Right-rail Sheet at w-[480px], no scale-background effect
 *   - Neutral base; semantic risk chip on each evidence row only
 *   - No gradients, glow, or heavy shadow in the form surface
 *   - 8px rhythm throughout
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { useEffect, useMemo, useState } from "react";
import { AlertCircle, ArrowRight, CheckCircle2, Loader2, X } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import GovStatusChip, {
  type GovStatusChipVariant,
} from "@/components/governance/GovStatusChip";
import type { ActionFormValues } from "@/components/actions/ActionForm";

// ── Types ─────────────────────────────────────────────────────────────────────

export type PromoteSignalItem = {
  id: string;
  title: string;
  severity: "High" | "Medium" | "Low";
  description: string;
  frequencyCount: number;
};

type RiskLevel = "High" | "Medium" | "Low";
type AffectedSegment =
  | "All clients"
  | "Post-hearing clients"
  | "Recent matter closings"
  | "Long-term clients"
  | "New clients"
  | "Other";

type PromoteFormState = {
  actionTitle: string;
  description: string;
  riskLevel: RiskLevel;
  affectedSegment: AffectedSegment;
  owner: string;
  kpi: string;
  notes: string;
};

export type PromoteToActionPanelProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedSignals: PromoteSignalItem[];
  /** Called with the resolved ActionFormValues when user submits */
  onSubmit: (values: ActionFormValues) => Promise<void>;
  submitting?: boolean;
  submitError?: string;
};

// ── Heuristics ────────────────────────────────────────────────────────────────

const SEGMENT_KEYWORDS: Array<{ segment: AffectedSegment; keywords: string[] }> = [
  {
    segment: "Post-hearing clients",
    keywords: ["hearing", "court", "trial", "judge", "proceeding", "litigation"],
  },
  {
    segment: "Recent matter closings",
    keywords: ["closing", "settlement", "resolution", "final", "outcome", "close"],
  },
  {
    segment: "Long-term clients",
    keywords: ["long-term", "ongoing", "retainer", "repeated", "returning", "history"],
  },
  {
    segment: "New clients",
    keywords: ["new", "intake", "initial", "onboarding", "first", "consultation"],
  },
];

function deriveAffectedSegment(signals: PromoteSignalItem[]): AffectedSegment {
  const corpus = signals
    .map((s) => `${s.title} ${s.description}`)
    .join(" ")
    .toLowerCase();

  for (const { segment, keywords } of SEGMENT_KEYWORDS) {
    if (keywords.some((kw) => corpus.includes(kw))) return segment;
  }
  return "All clients";
}

function deriveDominantSeverity(signals: PromoteSignalItem[]): RiskLevel {
  const counts = { High: 0, Medium: 0, Low: 0 };
  for (const s of signals) counts[s.severity]++;
  if (counts.High > 0) return "High";
  if (counts.Medium > 0) return "Medium";
  return "Low";
}

function deriveActionTitle(signals: PromoteSignalItem[]): string {
  if (signals.length === 0) return "";
  if (signals.length === 1) return `Review: ${signals[0].title}`;
  // Lead with the highest-frequency or highest-severity signal
  const sorted = [...signals].sort((a, b) => {
    const sevOrder = { High: 0, Medium: 1, Low: 2 };
    const sevDiff = sevOrder[a.severity] - sevOrder[b.severity];
    if (sevDiff !== 0) return sevDiff;
    return b.frequencyCount - a.frequencyCount;
  });
  return `Governance review — ${sorted[0].title} and ${signals.length - 1} other${signals.length > 2 ? "s" : ""}`;
}

function deriveDescription(signals: PromoteSignalItem[]): string {
  if (signals.length === 0) return "";
  if (signals.length === 1) return signals[0].description;
  const lines = signals
    .slice(0, 4)
    .map((s) => `${s.title}: ${s.description.slice(0, 80)}${s.description.length > 80 ? "…" : ""}`)
    .join("\n");
  return lines;
}

function deriveKpi(signals: PromoteSignalItem[]): string {
  if (signals.length === 0) return "";
  const dominant = deriveDominantSeverity(signals);
  if (dominant === "High")
    return "Owner assigned; escalation brief updated within 14 days.";
  if (dominant === "Medium")
    return "Remediation plan drafted and approved within 30 days.";
  return "Issue reviewed; resolution note added within 45 days.";
}

function buildInitialForm(signals: PromoteSignalItem[]): PromoteFormState {
  return {
    actionTitle: deriveActionTitle(signals),
    description: deriveDescription(signals),
    riskLevel: deriveDominantSeverity(signals),
    affectedSegment: deriveAffectedSegment(signals),
    owner: "",
    kpi: deriveKpi(signals),
    notes: "",
  };
}

// ── Chip helpers ──────────────────────────────────────────────────────────────

const severityToChip: Record<RiskLevel, GovStatusChipVariant> = {
  High: "risk",
  Medium: "warn",
  Low: "success",
};

// ── Field component ───────────────────────────────────────────────────────────

function FieldLabel({
  label,
  required,
  hint,
}: {
  label: string;
  required?: boolean;
  hint?: string;
}) {
  return (
    <span className="flex flex-col gap-0.5">
      <span className="text-[12px] font-semibold text-slate-700">
        {label}
        {required ? <span className="ml-0.5 text-[#DC2626]"> *</span> : null}
      </span>
      {hint ? <span className="text-[11px] text-slate-400">{hint}</span> : null}
    </span>
  );
}

// ── Panel ─────────────────────────────────────────────────────────────────────

export default function PromoteToActionPanel({
  open,
  onOpenChange,
  selectedSignals,
  onSubmit,
  submitting = false,
  submitError = "",
}: PromoteToActionPanelProps) {
  const initialForm = useMemo(
    () => buildInitialForm(selectedSignals),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [open], // re-derive only when the panel opens, not on every render
  );

  const [form, setForm] = useState<PromoteFormState>(initialForm);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<keyof PromoteFormState, string>>>({});

  // Re-seed form when panel opens with a fresh selection
  useEffect(() => {
    if (open) {
      setForm(buildInitialForm(selectedSignals));
      setFieldErrors({});
    }
    // selectedSignals identity may change; only re-seed on open transition
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const set = <K extends keyof PromoteFormState>(key: K, value: PromoteFormState[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFieldErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const validate = (): boolean => {
    const errors: Partial<Record<keyof PromoteFormState, string>> = {};
    if (!form.actionTitle.trim()) errors.actionTitle = "A title is required.";
    if (!form.kpi.trim()) errors.kpi = "A success measure is required.";
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validate()) return;
    const notesLines: string[] = [];
    if (form.description.trim()) notesLines.push(form.description.trim());
    if (form.notes.trim()) notesLines.push(`Additional notes: ${form.notes.trim()}`);
    notesLines.push(`Affected segment: ${form.affectedSegment}`);

    await onSubmit({
      title: form.actionTitle.trim(),
      owner: form.owner.trim(),
      owner_user_id: null,
      due_date: "",
      status: "open",
      timeframe: form.riskLevel === "High" ? "Days 1-30" : form.riskLevel === "Medium" ? "Days 31-60" : "Days 61-90",
      kpi: form.kpi.trim(),
      notes: notesLines.join("\n\n"),
    });
  };

  const canSubmit = form.actionTitle.trim().length > 0 && form.kpi.trim().length > 0;

  // Sort preview: highest severity first, then by frequency
  const sortedPreview = useMemo(
    () =>
      [...selectedSignals].sort((a, b) => {
        const ord = { High: 0, Medium: 1, Low: 2 };
        return ord[a.severity] - ord[b.severity] || b.frequencyCount - a.frequencyCount;
      }),
    [selectedSignals],
  );

  const dominantSeverity = deriveDominantSeverity(selectedSignals);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full max-w-[480px] flex-col gap-0 overflow-hidden border-l border-[#E5E7EB] bg-white p-0 shadow-[-4px_0_24px_rgba(0,0,0,0.06)] focus:outline-none [&>button:last-of-type]:hidden"
      >
        {/* ── Panel header ─────────────────────────────────────────────── */}
        <SheetHeader className="shrink-0 border-b border-[#E5E7EB] px-6 py-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-400">
                Evidence → Action
              </p>
              <SheetTitle className="mt-1 text-[16px] font-semibold text-[#0D1B2A]">
                Promote to Governance Action
              </SheetTitle>
              <SheetDescription className="mt-1 text-[13px] text-slate-500">
                Review the selected signals, refine the prefilled fields, and confirm to create a
                trackable governance action.
              </SheetDescription>
            </div>
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              aria-label="Close panel"
              className="mt-0.5 shrink-0 rounded-[6px] p-1.5 text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-600"
            >
              <X size={16} />
            </button>
          </div>
        </SheetHeader>

        {/* ── Scrollable body ───────────────────────────────────────────── */}
        <div className="min-h-0 flex-1 overflow-y-auto">
          {/* ── Zone 1: Evidence recap ────────────────────────────────── */}
          <section className="border-b border-[#F1F3F5] bg-[#FAFBFC] px-6 py-4">
            <div className="flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
                Selected evidence ({selectedSignals.length})
              </p>
              <GovStatusChip
                label={`${dominantSeverity} risk`}
                variant={severityToChip[dominantSeverity]}
                size="sm"
              />
            </div>

            <ul className="mt-3 space-y-2">
              {sortedPreview.map((signal) => (
                <li
                  key={signal.id}
                  className="flex items-start gap-3 rounded-[8px] border border-[#E5E7EB] bg-white px-3 py-2.5"
                  style={{ borderLeftWidth: 3, borderLeftColor: signal.severity === "High" ? "#EF4444" : signal.severity === "Medium" ? "#F59E0B" : "#10B981" }}
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-semibold leading-snug text-[#0D1B2A]">
                      {signal.title}
                    </p>
                    <p className="mt-0.5 text-[12px] leading-relaxed text-slate-500 line-clamp-2">
                      {signal.description}
                    </p>
                  </div>
                  <div className="shrink-0 pt-0.5">
                    <GovStatusChip
                      label={signal.severity}
                      variant={severityToChip[signal.severity]}
                      size="sm"
                    />
                  </div>
                </li>
              ))}
            </ul>

            {/* Flow indicator */}
            <div className="mt-3 flex items-center gap-2 text-[11px] text-slate-400">
              <span className="font-medium text-slate-500">
                {selectedSignals.length} signal{selectedSignals.length > 1 ? "s" : ""}
              </span>
              <ArrowRight size={11} className="shrink-0" />
              <span>1 consolidated governance action</span>
            </div>
          </section>

          {/* ── Zone 2: Editable action fields ───────────────────────── */}
          <section className="px-6 py-5">
            <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">
              Action details
            </p>
            <p className="mt-1 text-[12px] text-slate-400">
              Fields are pre-populated from signal content. Review and adjust before creating.
            </p>

            <div className="mt-4 space-y-4">
              {/* Title */}
              <label className="flex flex-col gap-1.5">
                <FieldLabel label="Action title" required />
                <input
                  value={form.actionTitle}
                  onChange={(e) => set("actionTitle", e.target.value)}
                  className="gov-field"
                  placeholder="e.g. Review Communication Delays"
                />
                {fieldErrors.actionTitle ? (
                  <p className="text-[11px] text-[#DC2626]">{fieldErrors.actionTitle}</p>
                ) : null}
              </label>

              {/* Risk level + Affected segment — 2-col */}
              <div className="grid grid-cols-2 gap-3">
                <label className="flex flex-col gap-1.5">
                  <FieldLabel label="Risk level" hint="Derived from signal severity" />
                  <select
                    value={form.riskLevel}
                    onChange={(e) => set("riskLevel", e.target.value as RiskLevel)}
                    className="gov-field"
                  >
                    <option value="High">High</option>
                    <option value="Medium">Medium</option>
                    <option value="Low">Low</option>
                  </select>
                </label>

                <label className="flex flex-col gap-1.5">
                  <FieldLabel label="Affected segment" hint="Auto-detected from content" />
                  <select
                    value={form.affectedSegment}
                    onChange={(e) => set("affectedSegment", e.target.value as AffectedSegment)}
                    className="gov-field"
                  >
                    <option value="All clients">All clients</option>
                    <option value="Post-hearing clients">Post-hearing clients</option>
                    <option value="Recent matter closings">Recent matter closings</option>
                    <option value="Long-term clients">Long-term clients</option>
                    <option value="New clients">New clients</option>
                    <option value="Other">Other</option>
                  </select>
                </label>
              </div>

              {/* Owner */}
              <label className="flex flex-col gap-1.5">
                <FieldLabel label="Owner" hint="Optional — assign now or later" />
                <input
                  value={form.owner}
                  onChange={(e) => set("owner", e.target.value)}
                  className="gov-field"
                  placeholder="Partner or team lead name"
                />
              </label>

              {/* Success measure */}
              <label className="flex flex-col gap-1.5">
                <FieldLabel label="Success measure" required hint="What does 'resolved' look like?" />
                <input
                  value={form.kpi}
                  onChange={(e) => set("kpi", e.target.value)}
                  className="gov-field"
                  placeholder="e.g. Owner assigned; plan approved within 14 days"
                />
                {fieldErrors.kpi ? (
                  <p className="text-[11px] text-[#DC2626]">{fieldErrors.kpi}</p>
                ) : null}
              </label>

              {/* Description (pre-filled, editable) */}
              <label className="flex flex-col gap-1.5">
                <FieldLabel label="Description" hint="Condensed from signal descriptions" />
                <textarea
                  value={form.description}
                  onChange={(e) => set("description", e.target.value)}
                  rows={4}
                  className="gov-textarea"
                  placeholder="Describe the pattern or issue being addressed"
                />
              </label>

              {/* Additional notes */}
              <label className="flex flex-col gap-1.5">
                <FieldLabel label="Additional notes" hint="Optional — governance context, decisions, dependencies" />
                <textarea
                  value={form.notes}
                  onChange={(e) => set("notes", e.target.value)}
                  rows={2}
                  className="gov-textarea"
                />
              </label>
            </div>

            {/* Server error */}
            {submitError ? (
              <div className="mt-4 flex items-start gap-2 rounded-[8px] border border-[#FECACA] bg-[#FEF2F2] px-3 py-2.5">
                <AlertCircle size={14} className="mt-0.5 shrink-0 text-[#DC2626]" />
                <p className="text-[12px] text-[#DC2626]">{submitError}</p>
              </div>
            ) : null}
          </section>
        </div>

        {/* ── Sticky panel footer ───────────────────────────────────────── */}
        <footer className="shrink-0 border-t border-[#E5E7EB] bg-white px-6 py-4">
          <div className="flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              disabled={submitting}
              className="inline-flex items-center rounded-[7px] border border-[#D1D5DB] bg-white px-4 py-2 text-[13px] font-medium text-slate-600 transition-colors hover:bg-slate-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={submitting || !canSubmit}
              className="inline-flex items-center gap-2 rounded-[7px] bg-[#0D1B2A] px-5 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-[#16263b] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <Loader2 size={13} className="animate-spin" />
                  Creating…
                </>
              ) : (
                <>
                  <CheckCircle2 size={13} />
                  Create Governance Action
                </>
              )}
            </button>
          </div>
          <p className="mt-2.5 text-[11px] text-slate-400">
            The action will appear in the Actions workspace and can be tracked through resolution.
          </p>
        </footer>
      </SheetContent>
    </Sheet>
  );
}
