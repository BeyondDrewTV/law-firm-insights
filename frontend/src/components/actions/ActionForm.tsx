import { useEffect, useMemo, useState } from "react";
import { Loader2 } from "lucide-react";

export type ActionStatus = "open" | "in_progress" | "done" | "blocked";
export type ActionTimeframe = "Days 1-30" | "Days 31-60" | "Days 61-90";

export interface ActionFormValues {
  title: string;
  owner: string;
  owner_user_id: number | null;
  due_date: string;
  status: ActionStatus;
  timeframe: ActionTimeframe;
  kpi: string;
  notes: string;
}

interface ActionFormFieldErrors {
  title?: string;
  owner?: string;
  status?: string;
  due_date?: string;
  timeframe?: string;
  kpi?: string;
}

interface ActionFormProps {
  open: boolean;
  mode: "create" | "edit";
  initialValues: ActionFormValues;
  ownerOptions: string[];
  submitting: boolean;
  submitLabel?: string;
  submittingLabel?: string;
  serverError?: string;
  onCancel: () => void;
  onSubmit: (values: ActionFormValues) => Promise<void>;
}

const STATUS_OPTIONS: Array<{ value: ActionStatus; label: string }> = [
  { value: "open", label: "Planned" },
  { value: "in_progress", label: "In Progress" },
  { value: "blocked", label: "Blocked" },
  { value: "done", label: "Completed" },
];

const TIMEFRAME_OPTIONS: Array<{ value: ActionTimeframe; label: string }> = [
  { value: "Days 1-30", label: "Days 1-30" },
  { value: "Days 31-60", label: "Days 31-60" },
  { value: "Days 61-90", label: "Days 61-90" },
];

function isValidDateString(value: string): boolean {
  if (!value) return false;
  const parsed = new Date(value);
  return !Number.isNaN(parsed.getTime());
}

function toLocalIsoDate(date: Date): string {
  const local = new Date(date);
  local.setMinutes(local.getMinutes() - local.getTimezoneOffset());
  return local.toISOString().slice(0, 10);
}

function isBeforeToday(value: string): boolean {
  if (!isValidDateString(value)) return false;
  return value < toLocalIsoDate(new Date());
}

function parseBackendFieldErrors(message: string): ActionFormFieldErrors {
  const lower = message.toLowerCase();
  const out: ActionFormFieldErrors = {};
  if (lower.includes("title")) out.title = message;
  if (lower.includes("owner")) out.owner = message;
  if (lower.includes("status")) out.status = message;
  if (lower.includes("due date")) out.due_date = message;
  if (lower.includes("timeframe")) out.timeframe = message;
  if (lower.includes("kpi") || lower.includes("success measure")) out.kpi = message;
  return out;
}

export default function ActionForm({
  open,
  mode,
  initialValues,
  ownerOptions,
  submitting,
  submitLabel,
  submittingLabel,
  serverError,
  onCancel,
  onSubmit,
}: ActionFormProps) {
  const minDueDate = useMemo(() => toLocalIsoDate(new Date()), []);
  const [title, setTitle] = useState(initialValues.title || "");
  const [owner, setOwner] = useState(initialValues.owner || "");
  const [dueDate, setDueDate] = useState(initialValues.due_date || "");
  const [status, setStatus] = useState<ActionStatus>(initialValues.status || "open");
  const [timeframe, setTimeframe] = useState<ActionTimeframe>(initialValues.timeframe || "Days 1-30");
  const [kpi, setKpi] = useState(initialValues.kpi || "");
  const [notes, setNotes] = useState(initialValues.notes || "");
  const [fieldErrors, setFieldErrors] = useState<ActionFormFieldErrors>({});

  useEffect(() => {
    if (!open) return;
    setTitle(initialValues.title || "");
    setOwner(initialValues.owner || "");
    setDueDate(initialValues.due_date || "");
    setStatus(initialValues.status || "open");
    setTimeframe(initialValues.timeframe || "Days 1-30");
    setKpi(initialValues.kpi || "");
    setNotes(initialValues.notes || "");
    setFieldErrors({});
  }, [initialValues, open]);

  useEffect(() => {
    if (!serverError) return;
    const parsed = parseBackendFieldErrors(serverError);
    if (Object.keys(parsed).length > 0) {
      setFieldErrors((prev) => ({ ...prev, ...parsed }));
    }
  }, [serverError]);

  const canSubmit = useMemo(
    () =>
      title.trim().length > 0 &&
      status.trim().length > 0 &&
      timeframe.trim().length > 0 &&
      kpi.trim().length > 0,
    [kpi, status, timeframe, title],
  );

  const validate = (): ActionFormFieldErrors => {
    const errors: ActionFormFieldErrors = {};
    if (!title.trim()) errors.title = "Title is required.";
    if (dueDate.trim() && !isValidDateString(dueDate)) {
      errors.due_date = "A valid due date is required.";
    } else if (dueDate.trim() && isBeforeToday(dueDate)) {
      errors.due_date = "Due date cannot be in the past.";
    }
    if (!status.trim()) errors.status = "Status is required.";
    if (!timeframe.trim()) errors.timeframe = "Timeframe is required.";
    if (!kpi.trim()) errors.kpi = "Success measure is required.";
    return errors;
  };

  const handleSubmit = async () => {
    const errors = validate();
    setFieldErrors(errors);
    if (Object.keys(errors).length > 0) return;
    await onSubmit({
      title: title.trim(),
      owner: owner.trim(),
      owner_user_id: null,
      due_date: dueDate || "",
      status,
      timeframe,
      kpi: kpi.trim(),
      notes: notes.trim(),
    });
  };

  if (!open) return null;

  return (
    <div data-testid="action-modal" className="gov-level-2 mt-4 p-4">
      <p className="gov-micro-label">{mode === "create" ? "Create Action" : "Edit Action"}</p>
      {serverError && (
        <div data-testid="action-error-banner" className="gov-alert mt-3 text-xs">
          {serverError}
        </div>
      )}
      <div className="mt-3 grid gap-3 md:grid-cols-2">
        <label className="text-sm text-neutral-900">
          <span className="mb-1 block">Title</span>
          <input
            data-testid="action-title"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setFieldErrors((prev) => ({ ...prev, title: undefined }));
            }}
            className="gov-field"
          />
          {fieldErrors.title && <p className="mt-1 text-xs text-red-700">{fieldErrors.title}</p>}
        </label>

        <label className="text-sm text-neutral-900">
          <span className="mb-1 block">Due date</span>
          <input
            data-testid="action-due-date"
            type="date"
            value={dueDate}
            min={minDueDate}
            onChange={(e) => {
              setDueDate(e.target.value);
              setFieldErrors((prev) => ({ ...prev, due_date: undefined }));
            }}
            className="gov-field"
          />
          {fieldErrors.due_date && <p className="mt-1 text-xs text-red-700">{fieldErrors.due_date}</p>}
        </label>

        <label className="text-sm text-neutral-900">
          <span className="mb-1 block">Status</span>
          <select
            data-testid="action-status"
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as ActionStatus);
              setFieldErrors((prev) => ({ ...prev, status: undefined }));
            }}
            className="gov-field"
          >
            {STATUS_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {fieldErrors.status && <p className="mt-1 text-xs text-red-700">{fieldErrors.status}</p>}
        </label>

        <label className="text-sm text-neutral-900">
          <span className="mb-1 block">Timeframe</span>
          <select
            data-testid="action-timeframe"
            value={timeframe}
            onChange={(e) => {
              setTimeframe(e.target.value as ActionTimeframe);
              setFieldErrors((prev) => ({ ...prev, timeframe: undefined }));
            }}
            className="gov-field"
          >
            {TIMEFRAME_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {fieldErrors.timeframe && <p className="mt-1 text-xs text-red-700">{fieldErrors.timeframe}</p>}
        </label>

        <label className="md:col-span-2 text-sm text-neutral-900">
          <span className="mb-1 block">Owner (optional)</span>
          <input
            data-testid="action-owner"
            value={owner}
            list="action-owner-suggestions"
            onChange={(e) => {
              setOwner(e.target.value);
              setFieldErrors((prev) => ({ ...prev, owner: undefined }));
            }}
            className="gov-field"
            placeholder="Partner name"
          />
          <datalist id="action-owner-suggestions">
            {ownerOptions.map((ownerOption) => (
              <option key={ownerOption} value={ownerOption} />
            ))}
          </datalist>
          {fieldErrors.owner && <p className="mt-1 text-xs text-red-700">{fieldErrors.owner}</p>}
        </label>

        <label className="md:col-span-2 text-sm text-neutral-900">
          <span className="mb-1 block">Success measure</span>
          <input
            data-testid="action-kpi"
            value={kpi}
            onChange={(e) => {
              setKpi(e.target.value);
              setFieldErrors((prev) => ({ ...prev, kpi: undefined }));
            }}
            className="gov-field"
          />
          {fieldErrors.kpi && <p className="mt-1 text-xs text-red-700">{fieldErrors.kpi}</p>}
        </label>

        <label className="md:col-span-2 text-sm text-neutral-900">
          <span className="mb-1 block">Notes (optional)</span>
          <textarea
            data-testid="action-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            className="gov-textarea"
          />
        </label>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          data-testid="action-submit"
          type="button"
          className="gov-btn-primary"
          disabled={submitting || !canSubmit}
          onClick={() => void handleSubmit()}
        >
          {submitting ? (
            <span className="inline-flex items-center gap-1">
              <Loader2 size={14} className="animate-spin" />
              {submittingLabel || "Saving..."}
            </span>
          ) : (
            submitLabel || (mode === "create" ? "Save action" : "Save")
          )}
        </button>
        <button type="button" className="gov-btn-secondary" disabled={submitting} onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

