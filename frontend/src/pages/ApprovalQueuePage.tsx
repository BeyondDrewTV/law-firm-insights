/**
 * ApprovalQueuePage.tsx
 * Clarion — Founder Approval Command Center
 * Polls every 30s for new queue items; no WebSocket dependency.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  CheckCircle2, Circle, Clock, AlertTriangle, Send, FileText,
  UserPlus, Inbox, RefreshCw, ChevronDown, ChevronUp, XCircle,
  PauseCircle, Rocket, Filter, LayoutGrid,
} from "lucide-react";
import { toast } from "sonner";
import {
  batchAction, getQueueStats, listQueueItems,
  updateQueueItem, type QueueItem, type QueueStats,
} from "@/api/approvalQueueService";
import PageWrapper from "@/components/governance/PageWrapper";
import { useAuth } from "@/contexts/AuthContext";

// ── Constants ─────────────────────────────────────────────────────────────────
const POLL_MS = 30_000;

const TYPE_META: Record<string, { label: string; Icon: typeof Send; color: string }> = {
  outreach:     { label: "Outreach",     Icon: Send,     color: "text-blue-400"   },
  content:      { label: "Content",      Icon: FileText, color: "text-violet-400" },
  account_setup:{ label: "Account Setup",Icon: UserPlus, color: "text-emerald-400"},
  pilot_invite: { label: "Pilot Invite", Icon: Rocket,   color: "text-amber-400"  },
  other:        { label: "Other",        Icon: Inbox,    color: "text-slate-400"  },
};

const STATUS_META: Record<string, { label: string; badge: string }> = {
  pending:  { label: "Pending",  badge: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  approved: { label: "Approved", badge: "bg-blue-500/15 text-blue-300 border-blue-500/30"   },
  released: { label: "Released", badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  held:     { label: "Held",     badge: "bg-slate-500/15 text-slate-300 border-slate-500/30"  },
  rejected: { label: "Rejected", badge: "bg-red-500/15 text-red-300 border-red-500/30"       },
};

const RISK_META: Record<string, string> = {
  low:    "text-emerald-400",
  medium: "text-amber-400",
  high:   "text-red-400",
};

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: string }) {
  const m = STATUS_META[status] ?? STATUS_META.pending;
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${m.badge}`}>
      {m.label}
    </span>
  );
}

function TypeChip({ type }: { type: string }) {
  const m = TYPE_META[type] ?? TYPE_META.other;
  return (
    <span className={`flex items-center gap-1.5 text-[12px] font-medium ${m.color}`}>
      <m.Icon size={12} />
      {m.label}
    </span>
  );
}

function StatCard({ label, value, sub, accent }: { label: string; value: number; sub?: string; accent?: string }) {
  return (
    <div className="rounded-xl border border-[#1E293B] bg-[#0F172A] px-5 py-4">
      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500">{label}</p>
      <p className={`mt-1.5 text-3xl font-bold ${accent ?? "text-white"}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-500">{sub}</p>}
    </div>
  );
}

function EmptyState({ filter }: { filter: string }) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-[#1E293B] py-16 text-center">
      <Inbox size={32} className="mb-3 text-slate-600" />
      <p className="text-sm font-medium text-slate-400">No {filter === "all" ? "" : filter} items</p>
      <p className="mt-1 text-xs text-slate-600">Items will appear here after new submissions are staged for review.</p>
    </div>
  );
}

// ── Item Detail Panel ─────────────────────────────────────────────────────────

function ItemPanel({ item, onAction, onClose }: {
  item: QueueItem;
  onAction: (id: string, action: "approve" | "reject" | "hold" | "release") => void;
  onClose: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const canApprove = item.status === "pending" || item.status === "held";
  const canRelease = item.status === "approved";
  const canReject  = item.status !== "released" && item.status !== "rejected";
  const canHold    = item.status === "pending" || item.status === "approved";

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-[#1E293B] bg-[#0B1120]">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 border-b border-[#1E293B] px-5 py-4">
        <div className="min-w-0 flex-1">
          <TypeChip type={item.type} />
          <h3 className="mt-1.5 truncate text-[15px] font-semibold text-white">{item.title}</h3>
          <p className="mt-0.5 text-[11px] text-slate-500">
            Submitted by {item.created_by_agent} · {new Date(item.created_at).toLocaleString()}
          </p>
        </div>
        <div className="flex shrink-0 flex-col items-end gap-2">
          <StatusBadge status={item.status} />
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition-colors">
            <XCircle size={16} />
          </button>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4 text-[13px]">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Summary</p>
          <p className="text-slate-300 leading-relaxed">{item.summary || "—"}</p>
        </div>
        {item.recommended_action && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Recommended Action</p>
            <p className="text-slate-300">{item.recommended_action}</p>
          </div>
        )}
        <div className="flex gap-6">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Risk</p>
            <p className={`font-semibold capitalize ${RISK_META[item.risk_level]}`}>{item.risk_level}</p>
          </div>
          {item.released_at && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Released</p>
              <p className="text-slate-300">{new Date(item.released_at).toLocaleString()}</p>
            </div>
          )}
        </div>
        {item.notes && (
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-500 mb-1">Notes</p>
            <p className="text-slate-400">{item.notes}</p>
          </div>
        )}

        {/* Payload collapsible */}
        <div className="rounded-lg border border-[#1E293B]">
          <button
            onClick={() => setExpanded(e => !e)}
            className="flex w-full items-center justify-between px-4 py-3 text-left text-[12px] font-semibold text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span>Submission details</span>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
          {expanded && (
            <pre className="overflow-x-auto border-t border-[#1E293B] px-4 py-3 text-[11px] text-slate-400 leading-relaxed whitespace-pre-wrap">
              {JSON.stringify(item.payload, null, 2)}
            </pre>
          )}
        </div>
      </div>

      {/* Action bar */}
      <div className="flex flex-wrap gap-2 border-t border-[#1E293B] px-5 py-4">
        {canApprove && (
          <button
            onClick={() => onAction(item.id, "approve")}
            className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-4 py-2 text-[12px] font-semibold text-white hover:bg-blue-500 transition-colors"
          >
            <CheckCircle2 size={13} /> Approve
          </button>
        )}
        {canRelease && (
          <button
            onClick={() => onAction(item.id, "release")}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-[12px] font-semibold text-white hover:bg-emerald-500 transition-colors"
          >
            <Rocket size={13} /> Release
          </button>
        )}
        {canHold && (
          <button
            onClick={() => onAction(item.id, "hold")}
            className="flex items-center gap-1.5 rounded-lg border border-[#1E293B] px-4 py-2 text-[12px] font-semibold text-slate-400 hover:text-slate-200 transition-colors"
          >
            <PauseCircle size={13} /> Hold
          </button>
        )}
        {canReject && (
          <button
            onClick={() => onAction(item.id, "reject")}
            className="flex items-center gap-1.5 rounded-lg border border-red-900/50 px-4 py-2 text-[12px] font-semibold text-red-400 hover:border-red-700 transition-colors"
          >
            <XCircle size={13} /> Reject
          </button>
        )}
      </div>
    </div>
  );
}

// ── Queue Item Row ────────────────────────────────────────────────────────────

function QueueRow({ item, selected, onSelect, onClick }: {
  item: QueueItem;
  selected: boolean;
  onSelect: (id: string, checked: boolean) => void;
  onClick: () => void;
}) {
  return (
    <div
      onClick={onClick}
      className={`group flex cursor-pointer items-center gap-3 rounded-lg border px-4 py-3.5 transition-all duration-150 ${
        selected
          ? "border-[#0EA5C2]/50 bg-[#0EA5C2]/8"
          : "border-[#1E293B] bg-[#0B1120] hover:border-slate-600 hover:bg-[#101928]"
      }`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={e => { e.stopPropagation(); onSelect(item.id, e.target.checked); }}
        onClick={e => e.stopPropagation()}
        className="h-3.5 w-3.5 shrink-0 accent-[#0EA5C2]"
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <TypeChip type={item.type} />
          <span className={`text-[10px] font-semibold uppercase ${RISK_META[item.risk_level]}`}>
            {item.risk_level} risk
          </span>
        </div>
        <p className="mt-1 truncate text-[13px] font-medium text-white">{item.title}</p>
        <p className="mt-0.5 truncate text-[11px] text-slate-500">{item.summary}</p>
      </div>
      <div className="shrink-0 flex flex-col items-end gap-1.5">
        <StatusBadge status={item.status} />
        <span className="text-[10px] text-slate-600">
          {new Date(item.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  );
}

// ── Notification Banner ───────────────────────────────────────────────────────

function NotificationBanner({ count, onDismiss }: { count: number; onDismiss: () => void }) {
  if (count === 0) return null;
  return (
    <div className="flex items-center justify-between rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3">
      <div className="flex items-center gap-2 text-[13px] text-amber-300">
        <AlertTriangle size={14} className="shrink-0" />
        <span><strong>{count}</strong> new item{count !== 1 ? "s" : ""} need your attention</span>
      </div>
      <button onClick={onDismiss} className="text-amber-400 hover:text-amber-200 transition-colors">
        <XCircle size={15} />
      </button>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

type TabType = "all" | "outreach" | "content" | "account_setup" | "pilot_invite";
type StatusFilter = "all" | "pending" | "approved" | "released" | "held" | "rejected";

const TABS: { key: TabType; label: string }[] = [
  { key: "all",          label: "All" },
  { key: "outreach",     label: "Outreach" },
  { key: "content",      label: "Content" },
  { key: "account_setup",label: "Account Setup" },
  { key: "pilot_invite", label: "Pilot Invites" },
];

const STATUS_FILTERS: { key: StatusFilter; label: string }[] = [
  { key: "all",      label: "All" },
  { key: "pending",  label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "released", label: "Released" },
  { key: "held",     label: "Held" },
  { key: "rejected", label: "Rejected" },
];

export default function ApprovalQueuePage() {
  const { user } = useAuth();

  // Defense-in-depth: redirect non-admin users even if they reach this component directly
  if (!user?.is_admin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <ApprovalQueueContent />;
}

function ApprovalQueueContent() {
  const [items, setItems]           = useState<QueueItem[]>([]);
  const [stats, setStats]           = useState<QueueStats | null>(null);
  const [tab, setTab]               = useState<TabType>("all");
  const [statusFilter, setStatus]   = useState<StatusFilter>("all");
  const [selected, setSelected]     = useState<Set<string>>(new Set());
  const [activeItem, setActiveItem] = useState<QueueItem | null>(null);
  const [loading, setLoading]       = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [newCount, setNewCount]     = useState(0);
  const prevPendingRef              = useRef(0);

  const fetchAll = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const [data, s] = await Promise.all([listQueueItems(), getQueueStats()]);
      setItems(data);
      setStats(s);
      // Notify on new pending items
      if (s.total_pending > prevPendingRef.current) {
        setNewCount(s.total_pending - prevPendingRef.current);
      }
      prevPendingRef.current = s.total_pending;
    } catch (e) {
      if (!silent) toast.error("Failed to load approval queue");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial load + polling
  useEffect(() => {
    fetchAll();
    const t = setInterval(() => fetchAll(true), POLL_MS);
    return () => clearInterval(t);
  }, [fetchAll]);

  const handleAction = useCallback(async (id: string, action: "approve" | "reject" | "hold" | "release") => {
    const statusMap = { approve: "approved", reject: "rejected", hold: "held", release: "released" } as const;
    try {
      await updateQueueItem(id, { status: statusMap[action] });
      toast.success(`Item ${statusMap[action]}`);
      fetchAll(true);
      if (activeItem?.id === id) setActiveItem(prev => prev ? { ...prev, status: statusMap[action] } : null);
    } catch { toast.error("Action failed"); }
  }, [activeItem, fetchAll]);

  const handleBatch = useCallback(async (action: "approve" | "reject" | "release" | "hold") => {
    if (selected.size === 0) { toast.info("Select items first"); return; }
    try {
      const res = await batchAction(action, [...selected]);
      toast.success(`${res.updated} item${res.updated !== 1 ? "s" : ""} ${action}d`);
      setSelected(new Set());
      fetchAll(true);
    } catch { toast.error("Batch action failed"); }
  }, [selected, fetchAll]);

  const toggleSelect = (id: string, checked: boolean) =>
    setSelected(s => { const n = new Set(s); checked ? n.add(id) : n.delete(id); return n; });

  const filtered = items.filter(i => {
    if (tab !== "all" && i.type !== tab) return false;
    if (statusFilter !== "all" && i.status !== statusFilter) return false;
    return true;
  });

  const pendingCount = stats?.total_pending ?? 0;

  if (loading) return (
    <div className="flex h-48 items-center justify-center text-slate-500 text-sm">
      Loading approval queue…
    </div>
  );

  return (
    <PageWrapper title="Approval Queue" description="Internal review queue for approving, holding, and releasing staged items.">
      <div className="space-y-5">

        {/* Notification banner */}
        <NotificationBanner count={newCount} onDismiss={() => setNewCount(0)} />

        {/* Stat cards */}
        {stats && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard label="Pending"  value={stats.total_pending}  accent="text-amber-300"   sub="needs review" />
            <StatCard label="Approved" value={stats.total_approved} accent="text-blue-300"    sub="ready to release" />
            <StatCard label="Released" value={stats.total_released} accent="text-emerald-300" sub="sent / published" />
            <StatCard label="Held"     value={stats.total_held}     accent="text-slate-400"   sub="paused" />
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-1 overflow-x-auto border-b border-[#1E293B] pb-0">
          {TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`shrink-0 border-b-2 px-4 pb-2.5 pt-1 text-[13px] font-medium transition-colors ${
                tab === t.key
                  ? "border-[#0EA5C2] text-white"
                  : "border-transparent text-slate-500 hover:text-slate-300"
              }`}
            >
              {t.label}
              {t.key !== "all" && stats?.by_type[t.key]?.pending
                ? <span className="ml-1.5 rounded-full bg-amber-500/20 px-1.5 text-[10px] text-amber-300">
                    {stats.by_type[t.key].pending}
                  </span>
                : null}
            </button>
          ))}
        </div>

        {/* Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-[#1E293B] px-3 py-1.5">
            <Filter size={12} className="text-slate-500" />
            <select
              value={statusFilter}
              onChange={e => setStatus(e.target.value as StatusFilter)}
              className="bg-transparent text-[12px] text-slate-300 outline-none"
            >
              {STATUS_FILTERS.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </div>
          <button
            onClick={() => fetchAll()}
            disabled={refreshing}
            className="flex items-center gap-1.5 rounded-lg border border-[#1E293B] px-3 py-1.5 text-[12px] text-slate-400 hover:text-slate-200 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={12} className={refreshing ? "animate-spin" : ""} /> Refresh
          </button>
          <span className="text-[11px] text-slate-600 ml-auto">
            Polls every 30s · {filtered.length} item{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>

        {/* Batch actions bar */}
        {selected.size > 0 && (
          <div className="flex items-center gap-2 rounded-lg border border-[#1E293B] bg-[#0F172A] px-4 py-3">
            <span className="text-[12px] text-slate-400 mr-2">{selected.size} selected</span>
            <button onClick={() => handleBatch("approve")}  className="rounded bg-blue-600 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-blue-500">Approve all</button>
            <button onClick={() => handleBatch("release")}  className="rounded bg-emerald-700 px-3 py-1.5 text-[11px] font-semibold text-white hover:bg-emerald-600">Release approved</button>
            <button onClick={() => handleBatch("hold")}     className="rounded border border-[#1E293B] px-3 py-1.5 text-[11px] text-slate-400 hover:text-slate-200">Hold</button>
            <button onClick={() => handleBatch("reject")}   className="rounded border border-red-900/40 px-3 py-1.5 text-[11px] text-red-400 hover:border-red-700">Reject</button>
            <button onClick={() => setSelected(new Set())} className="ml-auto text-[11px] text-slate-600 hover:text-slate-400">Clear</button>
          </div>
        )}

        {/* Content area: list + detail panel */}
        <div className={`grid gap-4 ${activeItem ? "lg:grid-cols-[1fr_420px]" : ""}`}>
          {/* Item list */}
          <div className="space-y-2">
            {filtered.length === 0
              ? <EmptyState filter={tab} />
              : filtered.map(item => (
                  <QueueRow
                    key={item.id}
                    item={item}
                    selected={selected.has(item.id)}
                    onSelect={toggleSelect}
                    onClick={() => setActiveItem(prev => prev?.id === item.id ? null : item)}
                  />
                ))}
          </div>

          {/* Detail panel */}
          {activeItem && (
            <div className="lg:sticky lg:top-4 lg:self-start lg:max-h-[calc(100vh-120px)]">
              <ItemPanel
                item={activeItem}
                onAction={handleAction}
                onClose={() => setActiveItem(null)}
              />
            </div>
          )}
        </div>
      </div>
    </PageWrapper>
  );
}
