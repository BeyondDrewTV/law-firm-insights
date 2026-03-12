/**
 * approvalQueueService.ts
 * Frontend API client for the Clarion Approval Queue.
 */

import { getAuthHeaders } from "./authService";

const BASE = "/api/approval-queue";

export type QueueItemType = "outreach" | "content" | "account_setup" | "pilot_invite" | "other";
export type QueueItemStatus = "pending" | "approved" | "rejected" | "released" | "held";
export type RiskLevel = "low" | "medium" | "high";

export interface QueueItem {
  id: string;
  type: QueueItemType;
  created_at: string;
  updated_at: string;
  created_by_agent: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  risk_level: RiskLevel;
  status: QueueItemStatus;
  recommended_action: string;
  notes: string;
  released_at: string | null;
  released_by: string | null;
}

export interface QueueStats {
  total_pending: number;
  total_approved: number;
  total_released: number;
  total_held: number;
  by_type: Record<string, Record<string, number>>;
}

async function _fetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const listQueueItems = (params?: { status?: string; type?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return _fetch<QueueItem[]>(`${BASE}${qs ? `?${qs}` : ""}`);
};

export const getQueueStats = () => _fetch<QueueStats>(`${BASE}/stats`);

export const updateQueueItem = (id: string, patch: Partial<Pick<QueueItem, "status" | "notes">>) =>
  _fetch<QueueItem>(`${BASE}/${id}`, { method: "PATCH", body: JSON.stringify(patch) });

export const batchAction = (
  action: "approve" | "reject" | "release" | "hold",
  ids: string[],
) =>
  _fetch<{ updated: number; ids: string[] }>(`${BASE}/batch`, {
    method: "POST",
    body: JSON.stringify({ action, ids }),
  });
