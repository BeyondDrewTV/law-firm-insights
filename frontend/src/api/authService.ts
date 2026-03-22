/**

 * Authentication API Service

 * Communicates with Flask backend for authentication and account usage flows.

 */



import { confidenceDefinition, trendStabilityDefinition } from "@/content/marketingCopy";



const API_BASE = "/api";
const DEV_MODE = typeof import.meta !== "undefined" && Boolean(import.meta.env?.DEV);
const warnedNetworkKeys = new Set<string>();
const inflightReportActionsRequests = new Map<number, Promise<ReportActionsResponse>>();
let csrfTokenCache: string | null = null;
export const PLAN_LIMIT_EVENT = "plan-limit-error";

const trimmedStack = () => {
  const raw = new Error().stack || "";
  return raw
    .split("\n")
    .slice(2, 6)
    .map((line) => line.trim())
    .join(" | ");
};


function apiUrl(path: string): string {

  if (path.startsWith("/api")) return path;

  if (path.startsWith("/")) return `${API_BASE}${path}`;

  return `${API_BASE}/${path}`;

}



function apiRequestInit(init: RequestInit = {}): RequestInit {
  return {
    ...init,
    credentials: init.credentials ?? "include",
  };
}

function isMutatingMethod(method?: string): boolean {
  const normalized = String(method || "GET").toUpperCase();
  return normalized !== "GET" && normalized !== "HEAD" && normalized !== "OPTIONS";
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const raw = document.cookie || "";
  const pieces = raw.split(";").map((part) => part.trim());
  for (const part of pieces) {
    if (!part.startsWith(`${name}=`)) continue;
    const value = part.slice(name.length + 1);
    return value ? decodeURIComponent(value) : null;
  }
  return null;
}

function resolveCsrfToken(): string | null {
  return csrfTokenCache || readCookie("csrf_token");
}

export function clearCachedCsrfToken(): void {
  csrfTokenCache = null;
}

async function ensureCsrfToken(forceRefresh = false): Promise<string | null> {
  const existing = forceRefresh ? null : csrfTokenCache;
  if (existing) return existing;
  try {
    const response = await globalThis.fetch(apiUrl("/csrf-token"), {
      method: "GET",
      credentials: "include",
    });
    if (!response.ok) return null;
    const payload = (await response.json()) as { csrf_token?: unknown };
    if (typeof payload.csrf_token === "string" && payload.csrf_token.trim()) {
      csrfTokenCache = payload.csrf_token.trim();
      return csrfTokenCache;
    }
  } catch {
    // non-blocking; request may still proceed if backend route is exempt
  }
  return resolveCsrfToken();
}

async function refreshCsrfToken(): Promise<string | null> {
  clearCachedCsrfToken();
  return ensureCsrfToken(true);
}

function normalizeCheckoutError(response: Response, payload: Record<string, unknown>, fallback: string): string {
  if (response.status === 401) {
    return "Please sign in again before starting secure checkout.";
  }
  const code = typeof payload.code === "string" ? payload.code : "";
  const error = typeof payload.error === "string" ? payload.error : "";
  if (code === "csrf_failed") {
    return "Your session needs a quick refresh before secure checkout can continue. Please try again.";
  }
  if (code === "auth_required") {
    return "Please sign in again before starting secure checkout.";
  }
  return error || fallback;
}

async function postCheckoutJson(
  path: string,
  body: Record<string, unknown>,
): Promise<{ response: Response; payload: Record<string, unknown> }> {
  let response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  let payload = await safeParseJson(response);

  if (payload.code === "csrf_failed") {
    await refreshCsrfToken();
    response = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(body),
    });
    payload = await safeParseJson(response);
  }

  return { response, payload };
}

const fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
  const nextInit = apiRequestInit(init || {});
  if (isMutatingMethod(nextInit.method)) {
    const token = (await ensureCsrfToken()) || resolveCsrfToken();
    if (token) {
      const headers = new Headers(nextInit.headers || {});
      if (!headers.has("X-CSRFToken")) headers.set("X-CSRFToken", token);
      nextInit.headers = headers;
    }
  }
  return globalThis.fetch(input, nextInit);
};


function warnNetworkOnce(key: string, label: string, error: unknown): void {
  if (!DEV_MODE || warnedNetworkKeys.has(key)) return;

  warnedNetworkKeys.add(key);

  console.warn(

    `[authService] ${label} request failed (dev warning). Check Vite /api proxy and backend availability.`,

    error,

  );

}



export type PlanType = "free" | "team" | "firm";

export type BillingPlan = "team" | "firm";

const normalizePlanType = (rawPlanType: string | null | undefined): PlanType => {
  const value = String(rawPlanType || "free").trim().toLowerCase();
  if (
    value === "firm" || value === "firm_monthly" || value === "firm_annual" ||
    value === "pro_annual" || value === "annual" || value === "leadership"
  ) {
    return "firm";
  }
  if (
    value === "team" || value === "team_monthly" || value === "team_annual" ||
    value === "pro_monthly" || value === "monthly" || value === "professional"
  ) {
    return "team";
  }
  return "free";
};

const normalizePlanLabel = (rawLabel: string | null | undefined, planType?: string | null): string => {
  const normalizedType = normalizePlanType(planType || undefined);
  if (normalizedType === "firm") return "Firm";
  if (normalizedType === "team") return "Team";
  if (normalizedType === "free") return "Free";

  const label = String(rawLabel || "").trim().toLowerCase();
  if (!label) return "Free";
  if (label.includes("firm") || label.includes("annual") || label.includes("leadership")) return "Firm";
  if (label.includes("team") || label.includes("monthly") || label.includes("professional")) return "Team";
  if (label.includes("one-time") || label.includes("onetime") || label.includes("free") || label.includes("trial")) {
    return "Free";
  }
  return "Free";
};



export interface LoginCredentials {

  email: string;

  password: string;

}



export interface RegisterData {
  email: string;
  password: string;
  firm_name?: string;
  full_name: string;
}

export function emitPlanLimitError(message?: string): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(PLAN_LIMIT_EVENT, {
      detail: { message: message || "Trial limit reached" },
    }),
  );
}

export interface CreateFirmPayload {
  name: string;
  practice_area?: string;
  firm_size?: string;
}

export interface CreateFirmResponse {
  success: boolean;
  firm_id?: number;
  error?: string;
}

export interface CompleteOnboardingResponse {
  success: boolean;
  user?: User;
  error?: string;
}


export interface User {
  id: number;
  email: string;
  firm_name: string;
  email_verified?: boolean;
  onboarding_complete?: boolean;
  firm_id?: number | null;
  firm_role?: "owner" | "partner" | "member" | null;
  has_firm_context?: boolean;
  firm_membership_disabled?: boolean;
  username?: string;
  subscription_type: "trial" | "team_monthly" | "team_annual" | "firm_monthly" | "firm_annual";

  is_admin?: boolean;

  trial_reviews_used?: number;

  trial_limit?: number;

  two_factor_enabled?: boolean;

  two_factor_available?: boolean;

}



export interface AuthResponse {
  success: boolean;
  user?: User;
  verified?: boolean;
  dev_mode?: boolean;
  requires_verification?: boolean;
  verification_sent?: boolean;
  verification_delivery_available?: boolean;
  verification_delivery_method?: string | null;
  verification_delivery_error?: string | null;
  support_email?: string;
  email?: string;
  requires_2fa?: boolean;
  challenge_id?: string;

  message?: string;

  error?: string;

  errors?: Record<string, string>;

}



export interface TwoFactorToggleResponse {
  success: boolean;

  two_factor_enabled?: boolean;

  error?: string;

}



export interface ReportHistoryItem {

  id: number;

  created_at: string;

  total_reviews: number;

  subscription_type_at_creation: string;

  plan_label: string;

  avg_rating?: number;

  review_date_start?: string | null;

  review_date_end?: string | null;

  review_date_label?: string | null;

}



export interface DashboardStats {

  processed_files: number;

  total_reviews_processed: number;

  last_report_at: string | null;

  recent_reports: ReportHistoryItem[];

  account_status: {

    type: string;

    display: string;

    remaining: number | null;

  };

  trial_reviews_used: number;

  trial_limit: number;

  email_verified: boolean;

  trend_stability: "Stable" | "Moderately stable" | "Volatile" | "Insufficient data";

  trend_stability_explanation: string;

  confidence_level: "Low" | "Medium" | "High";

  confidence_explanation: string;

  avg_sentiment_score?: number | null;

  latest_review_date?: string | null;

  review_volume?: {

    all_time: number;

    last_30_days: number;

    last_90_days: number;

    last_7_days: number;

    month_to_date: number;

  };

}



export interface DashboardStatsResponse {

  success: boolean;

  stats?: DashboardStats;

  error?: string;

}



export interface ExposureSnapshot {

  has_data: boolean;

  report_id: number | null;

  snapshot_id?: number | null;

  latest_timestamp?: string | null;

  exposure_score: number | null;

  exposure_tier: "Controlled" | "Watch" | "Elevated" | "Critical" | null;

  exposure_label: "Baseline" | "Watchlist" | "Elevated" | "High" | null;

  partner_escalation_required: boolean | null;

  primary_risk_driver: string | null;

  responsible_owner: string | null;

}



export interface ExposureSnapshotResponse {

  success: boolean;

  exposure?: ExposureSnapshot;

  error?: string;

}



export type FeatureInterestChoice = "yes" | "no";



export interface FeatureInterestSubmitResponse {

  success: boolean;

  feature_key?: string;

  choice?: FeatureInterestChoice;

  error?: string;

}



export interface FeatureInterestSummary {

  feature_key: string;

  yes_count: number;

  no_count: number;

  total_firms: number;

  current_firm_choice: FeatureInterestChoice | null;

}



export interface FeatureInterestSummaryResponse {

  success: boolean;

  summary?: FeatureInterestSummary;

  error?: string;

}



export interface CurrentPlan {
  planType: PlanType;
  planLabel: string;
  isTrial: boolean;
  firmPlan?: "free" | "team" | "firm" | "trial" | "professional" | "leadership";
  planLimits?: {
    maxReviewsPerUpload: number | null;
    maxReportsPerMonth: number | null;
    maxUsers: number | null;
    historyDays: number | null;
    pdfWatermark: boolean;
  };
}


export interface AccountPlanResponse {

  success: boolean;

  plan?: CurrentPlan;

  error?: string;

}



export interface AccountProfileResponse {

  success: boolean;

  user?: User;

  error?: string;

}



export type SessionTransientKind = "rate_limited" | "connection";



/** Branding (THEIRS) */

export interface BrandingThemeOption {

  id: string;

  label: string;

  accent_hex: string;

  primary_hex: string;

  surface_hex: string;

}



export interface AccountBranding {

  accentTheme: string;

  themeOptions: BrandingThemeOption[];

  logoUrl: string | null;

  hasLogo: boolean;

  logoUpdatedAt: string | null;

  /** True only when the API confirms the firm is on the Firm plan. */
  brandingEditorEnabled: boolean;

}



export interface AccountBrandingResponse {

  success: boolean;

  branding?: AccountBranding;

  error?: string;

}



export interface ReportListItem {

  id: number;

  name: string;

  status: "processing" | "ready" | "failed";

  created_at: string;

  total_reviews: number;

  access_level?: "trial" | "paid";

  plan_label: string;

  plan_type: "free" | "one_time" | "pro_monthly" | "pro_annual" | string;

  review_date_start?: string | null;

  review_date_end?: string | null;

  review_date_label?: string | null;

  custom_name?: string | null;

  view_url: string;

  download_pdf_url: string;

  download_csv_url?: string;

}



export interface ReportListResponse {
  success: boolean;
  reports?: ReportListItem[];
  history_window_days?: number | null;
  history_truncated?: boolean;
  history_notice?: string | null;
  error?: string;
}

export interface PlanLimitsResponse {
  success: boolean;
  plan?: "free" | "team" | "firm";
  limits?: {
    max_users?: number | null;
    max_reviews_per_upload?: number | null;
    max_reports_per_month?: number | null;
    history_days?: number | null;
    pdf_watermark?: boolean;
  };
  error?: string;
}

export interface GovernanceSignal {
  id: number;
  title: string;
  description: string;
  severity: "high" | "medium" | "low" | string;
  created_at?: string | null;
}

export interface GovernanceRecommendation {
  id: number;
  title: string;
  priority: "high" | "medium" | "low" | string;
  suggested_owner: string;
  created_at?: string | null;
}

export interface GovernanceSignalsResponse {
  success: boolean;
  signals?: GovernanceSignal[];
  recommendations?: GovernanceRecommendation[];
  error?: string;
}

export interface GovernanceAlert {
  id: number;
  signal_type: string;
  message: string;
  occurrences: number;
  created_at: string | null;
  status: string;
}

export interface GovernanceAlertsResponse {
  success: boolean;
  alerts?: GovernanceAlert[];
  error?: string;
}

export interface RecentGovernanceAction {
  id: number;
  issue: string;
  action: string;
  owner: string;
  status: string;
  due_date?: string | null;
  updated_at?: string | null;
  report_id: number;
}

export interface RecentGovernanceActionsResponse {
  success: boolean;
  actions?: RecentGovernanceAction[];
  error?: string;
}


export interface DeletedReportItem {

  id: number;

  name: string;

  created_at: string;

  total_reviews: number;

  plan_label: string;

  plan_type: "free" | "one_time" | "pro_monthly" | "pro_annual" | string;

  deleted_at: string;

  purge_at: string;

  can_restore: boolean;

}



export interface DeletedReportsResponse {

  success: boolean;

  reports?: DeletedReportItem[];

  can_restore?: boolean;

  history_window_days?: number | null;

  history_truncated?: boolean;

  history_notice?: string | null;

  retention_days?: number;

  upgrade_required?: boolean;

  error?: string;

}



export interface DeleteReportResponse {

  success: boolean;

  error?: string;

}



export interface RestoreDeletedReportResponse {

  success: boolean;

  report?: {

    id: number;

    name: string;

  };

  upgrade_required?: boolean;

  error?: string;

}



export interface ReportDetail {

  id: number;

  title: string;

  name: string;

  status: "processing" | "ready" | "failed";

  created_at: string;

  access_level: "trial" | "paid";

  plan_type: "free" | "one_time" | "pro_monthly" | "pro_annual";

  total_reviews: number;

  avg_rating: number;

  review_date_start?: string | null;

  review_date_end?: string | null;

  review_date_label?: string | null;

  custom_name?: string | null;

  plan_label: string;



  themes: Array<{ name: string; mentions: number }>;
  theme_trends?: Record<
    string,
    {
      current: number;
      previous: number;
      change: number;
      percent: number;
    }
  >;

  top_praise: string[];

  top_complaints: string[];

  opportunities_for_enhancement: string[];

  executive_summary: string[];

  root_cause_themes: Array<{ theme: string; mentions: number; root_cause: string; impact: string }>;

  recommended_changes: Array<{ theme: string; recommendation: string }>;



  // HEAD: implementation_roadmap supports optional action?: string

  implementation_roadmap: Array<{ theme: string; action?: string; timeline: string; owner: string; kpi: string }>;



  strategic_plans: Array<{

    theme: string;

    objective: string;

    ninety_day_steps: string[];

    owner: string;

    kpi: string;

  }>;



  strategy_limits?: {

    implementation_themes: number | null;

    strategic_plan_themes: number;

  };



  key_numbers: {

    recommended_tier: string;

    expected_margin_impact: string;

    confidence_score: number;

  };



  // HEAD: comparison block

  comparison?: {

    has_previous: boolean;

    current_label: string;

    previous_label: string | null;

    current_generated_at?: string | null;

    previous_generated_at?: string | null;

    current_review_date_start?: string | null;

    current_review_date_end?: string | null;

    current_review_date_label?: string | null;

    previous_review_date_start?: string | null;

    previous_review_date_end?: string | null;

    previous_review_date_label?: string | null;

    comparison_basis?: string | null;

    overall_satisfaction: {

      current: number;

      previous: number | null;

      delta: number | null;

    };

    positive_share: {

      current: number;

      previous: number | null;

      delta: number | null;

    };

    at_risk_signals: {

      current: number;

      previous: number | null;

      delta: number | null;

    };

    theme_changes?: Array<{

      theme: string;

      current: number;

      previous: number;

      delta: number;

    }>;

    note?: string | null;

  };



  download_pdf_url: string;

}



export interface ReportDetailResponse {

  success: boolean;

  report?: ReportDetail;

  history_window_days?: number | null;

  history_truncated?: boolean;

  history_notice?: string | null;

  error?: string;

}

export interface SupportTicket {
  id: number;
  ticket_ref: string;
  user_id?: number | null;
  requester_name?: string | null;
  requester_email: string;
  firm_name?: string | null;
  source: "contact" | "dashboard" | string;
  category: string;
  urgency: string;
  subject: string;
  message: string;
  status: string;
  priority: string;
  escalation_level: string;
  escalation_reason?: string | null;
  auto_response_template?: string | null;
  auto_response_sent?: boolean;
  handled_by_user_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SupportTicketSummary {
  open_count: number;
  escalated_count: number;
}

export interface PartnerBriefDeliveryStatus {
  delivery_available: boolean;
  recipient_count: number;
  recipients: string[];
  from_email: string;
  missing_requirements: string[];
  firm_name?: string;
}



export interface UpdateReportResponse {

  success: boolean;

  report?: {

    id: number;

    name: string;

    title?: string;

    custom_name?: string | null;

  };

  error?: string;

}



export interface ReportActionItem {
  activity_log?: Array<{ date: string; description: string }>;
  id: number;
  report_id?: number;
  report_name?: string;
  report_created_at?: string | null;
  report_status?: string;
  title: string;
  owner: string;
  owner_user_id?: number | null;
  status: "open" | "in_progress" | "done" | "blocked";
  due_date: string | null;
  timeframe?: "Days 1-30" | "Days 31-60" | "Days 61-90" | null;
  kpi: string;
  notes: string;

  created_at: string;

  updated_at: string;

}



export interface ReportActionsResponse {
  success: boolean;

  actions?: ReportActionItem[];

  upsell?: {

    limit: number | null;

    can_add_unlimited: boolean;

    upgrade_message?: string | null;

  };

  error?: string;

  upgrade_required?: boolean;

}



export interface ReportPackSchedule {

  enabled: boolean;

  cadence: "weekly" | "monthly";

  recipients: string[];

  last_sent_at: string | null;

  next_send_at: string | null;

}



export interface ReportPackScheduleResponse {

  success: boolean;

  schedule?: ReportPackSchedule;

  can_manage?: boolean;

  upgrade_required?: boolean;

  upgrade_message?: string | null;

  error?: string;

}



export interface SendReportPackNowResponse {

  success: boolean;

  delivery_count?: number;

  recipient_count?: number;

  message?: string;

  upgrade_required?: boolean;

  error?: string;

}



export interface CreditsState {

  free_reports_remaining: number;

  free_reports_used: number;

  free_reports_limit: number;

  paid_reports_remaining: number;

  paid_reports_used: number;

  paid_reports_purchased: number;

  has_active_subscription: boolean;

  subscription_type: string;

  next_reset: string | null;

}



export interface CreditsResponse {

  success: boolean;

  credits?: CreditsState;

  error?: string;

}



export interface UploadResult {

  summary: {

    imported_count: number;

    report_id: number | null;

    message: string;

    truncated_for_plan?: boolean;

    skipped_due_to_plan_limit?: number;

  };

  usage: {

    trial_reviews_used: number;

    trial_limit: number;

    one_time_reports_used: number;

    one_time_reports_remaining: number;

    subscription_type: string;

  };

}



export interface UploadResponse {

  success: boolean;

  data?: UploadResult;

  error?: string;

}



export interface CheckoutSessionResponse {

  success: boolean;

  checkout_url?: string;

  error?: string;

}



export interface CheckoutFinalizeResponse {

  success: boolean;

  plan?: string;

  error?: string;

}



interface BackendVersionResponse {

  success: boolean;

  service?: string;

  api_version?: string;

}



async function safeParseJson(response: Response): Promise<Record<string, unknown>> {

  const contentType = response.headers.get("content-type");



  if (!contentType || !contentType.includes("application/json")) {

    const bodyText = await response.text();

    console.error("[authService] Non-JSON response received:", {

      status: response.status,

      statusText: response.statusText,

      contentType,

      url: response.url,

      body: bodyText.substring(0, 500),

    });

    throw new Error(`Server responded with ${response.status}: ${bodyText.substring(0, 100)}`);

  }



  return (await response.json()) as Record<string, unknown>;

}



/** HEAD: rate-limit retry helpers */



const MAX_RETRY_ATTEMPTS = 3;
const BASE_BACKOFF_MS = 500;
const MAX_RETRY_WAIT_MS = 30_000;

const parseRetryAfterMs = (headerValue: string | null): number | null => {
  if (!headerValue) return null;
  const asSeconds = Number(headerValue);
  if (Number.isFinite(asSeconds) && asSeconds >= 0) {
    return Math.max(0, asSeconds * 1000);
  }
  const asDate = Date.parse(headerValue);
  if (Number.isFinite(asDate)) {
    return Math.max(0, asDate - Date.now());
  }
  return null;
};

const parseRateLimitResetMs = (headerValue: string | null): number | null => {
  if (!headerValue) return null;
  const numeric = Number(headerValue);
  if (!Number.isFinite(numeric) || numeric <= 0) return null;

  if (numeric > 1_000_000_000_000) {
    return Math.max(0, numeric - Date.now());
  }
  if (numeric > 1_000_000_000) {
    return Math.max(0, numeric * 1000 - Date.now());
  }
  return Math.max(0, numeric * 1000);
};

const withJitter = (ms: number) => ms + Math.floor(Math.random() * 250);


/**

 * Waits `ms` milliseconds. If `signal` fires during the wait, resolves

 * immediately (without throwing) and clears the timer â€” no dangling timeouts.

 * The caller is responsible for checking `signal.aborted` after awaiting.

 */

const waitForRetry = (ms: number, signal?: AbortSignal | null): Promise<void> =>

  new Promise<void>((resolve) => {

    const timer = setTimeout(resolve, ms);

    signal?.addEventListener("abort", () => { clearTimeout(timer); resolve(); }, { once: true });

  });



/**

 * Fetches `url` with automatic, bounded retry on HTTP 429.

 *

 * Abort contract

 *   â€“ Checks `signal.aborted` before every attempt; throws AbortError immediately.

 *   â€“ If signal fires during a backoff wait, the wait resolves early and the

 *     next iteration throws AbortError â€” no fetch is issued.

 *   â€“ fetch() itself throws AbortError when signal fires mid-request; that

 *     propagates unchanged so callers can distinguish abort from server errors.

 *

 * Retry contract

 *   â€“ MAX_RETRY_ATTEMPTS = 2 â†’ at most 3 total HTTP requests per call.

 *   â€“ On 429: honours Retry-After header (seconds) if present; otherwise

 *     exponential backoff: 500 ms, 1 000 ms. Capped at 10 000 ms.

 *   â€“ All other response codes (including 5xx) are returned immediately.

 *   â€“ After exhausting retries the final 429 response is returned so callers

 *     can surface it cleanly rather than receiving a thrown exception.

 */

const fetchWithRateLimitRetry = async (
  url: string,
  init: RequestInit,
  options?: {
    onRetry?: (meta: { attempt: number; maxRetries: number; waitMs: number; reason: "429" | "network" }) => void;
  },
): Promise<Response> => {
  const normalizedUrl = apiUrl(url);

  const normalizedInit = apiRequestInit(init);

  const signal = normalizedInit.signal as AbortSignal | undefined;



  for (let attempt = 0; attempt <= MAX_RETRY_ATTEMPTS; attempt++) {

    if (signal?.aborted) {

      throw new DOMException("Aborted", "AbortError");

    }



    let response: Response;

    try {

      response = await fetch(normalizedUrl, normalizedInit);

    } catch (error) {

      if (signal?.aborted) {

        throw new DOMException("Aborted", "AbortError");

      }

      if (attempt === MAX_RETRY_ATTEMPTS) {

        throw error;

      }

      const retryMs = Math.min(withJitter(BASE_BACKOFF_MS * Math.pow(2, attempt)), MAX_RETRY_WAIT_MS);
      options?.onRetry?.({
        attempt: attempt + 1,
        maxRetries: MAX_RETRY_ATTEMPTS,
        waitMs: retryMs,
        reason: "network",
      });
      await waitForRetry(retryMs, signal);
      continue;
    }



    if (response.status !== 429) {

      return response;

    }



    if (attempt === MAX_RETRY_ATTEMPTS) {

      // Retries exhausted - return the 429 for the caller to handle.
      return response;
    }
    const retryAfterRaw = response.headers.get("Retry-After");
    const rateLimitResetRaw = response.headers.get("X-RateLimit-Reset");
    const retryAfterMs = parseRetryAfterMs(retryAfterRaw);
    const resetMs = parseRateLimitResetMs(rateLimitResetRaw);
    const fallbackMs = BASE_BACKOFF_MS * Math.pow(2, attempt);
    const retryMs = Math.min(withJitter(retryAfterMs ?? resetMs ?? fallbackMs), MAX_RETRY_WAIT_MS);

    options?.onRetry?.({
      attempt: attempt + 1,
      maxRetries: MAX_RETRY_ATTEMPTS,
      waitMs: retryMs,
      reason: "429",
    });

    await waitForRetry(retryMs, signal);


    // Re-check after the wait â€” signal may have fired while sleeping.

    if (signal?.aborted) {

      throw new DOMException("Aborted", "AbortError");

    }

  }



  // Unreachable; satisfies TypeScript exhaustiveness check.

  throw new Error("fetchWithRateLimitRetry: unexpected loop exit");

};



export async function login(credentials: LoginCredentials): Promise<AuthResponse> {

  const url = `${API_BASE}/auth/login`;

  console.log("[authService] Login attempt:", { url, email: credentials.email });



  try {

    const response = await fetch(url, {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify(credentials),

    });



    if (!response.ok) {

      const data = await safeParseJson(response);

      return {

        success: false,

        error:

          (typeof data.error === "string" ? data.error : undefined) ||

          "Login failed. Please check your credentials.",

      };

    }



    const data = await safeParseJson(response);
    await refreshCsrfToken();
    return { ...data, success: true } as AuthResponse;

  } catch (error) {

    console.error("[authService] Login network error:", error);

    const message = error instanceof Error ? error.message : "Unable to connect to server. Please try again.";

    if (

      message.includes("Server responded with 404") ||

      message.includes("<!DOCTYPE html>") ||

      message.includes("NOT FOUND")

    ) {

      return {

        success: false,

          error:

            "Login API returned a non-JSON/404 response. Ensure Vite is proxying /api to the Clarion Flask app in backend/app.py and that /api/version resolves to the law-firm-feedback-saas service.",

      };

    }

    return {

      success: false,

      error: message || "Unable to connect to server. Please try again.",

    };

  }

}



export async function verifyTwoFactor(challengeId: string, code: string): Promise<AuthResponse> {

  try {

    const response = await fetch(`${API_BASE}/auth/2fa/verify`, {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify({ challenge_id: challengeId, code }),

    });



    const data = await safeParseJson(response);

    if (!response.ok || data.success === false) {

      return {

        success: false,

        error: (typeof data.error === "string" ? data.error : undefined) || "Verification failed.",

      };

    }



    return { ...data, success: true } as AuthResponse;

  } catch (error) {

    console.error("[authService] 2FA verification failed:", error);

    return { success: false, error: "Unable to verify code right now." };

  }

}



async function toggleTwoFactor(

  path: "/auth/2fa/enable" | "/auth/2fa/disable",

  password: string,

): Promise<TwoFactorToggleResponse> {

  try {

    const response = await fetch(`${API_BASE}${path}`, {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify({ password }),

    });

    const data = await safeParseJson(response);

    if (!response.ok || data.success === false) {

      return {

        success: false,

        error: (typeof data.error === "string" ? data.error : undefined) || "Unable to update two-factor settings.",

      };

    }

    return {

      success: true,

      two_factor_enabled: Boolean(data.two_factor_enabled),

    };

  } catch (error) {

    console.error("[authService] 2FA toggle failed:", error);

    return { success: false, error: "Unable to update two-factor settings." };

  }

}



export function enableTwoFactor(password: string): Promise<TwoFactorToggleResponse> {

  return toggleTwoFactor("/auth/2fa/enable", password);

}



export function disableTwoFactor(password: string): Promise<TwoFactorToggleResponse> {

  return toggleTwoFactor("/auth/2fa/disable", password);

}



export async function register(data: RegisterData): Promise<AuthResponse> {
  const url = `${API_BASE}/auth/register`;

  console.log("[authService] Register attempt:", { url, email: data.email, firm_name: data.firm_name });



  try {

    const response = await fetch(url, {

      method: "POST",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify(data),

    });



    if (!response.ok) {

      const result = await safeParseJson(response);

      return {

        success: false,

        error: (typeof result.error === "string" ? result.error : undefined) || "Registration failed.",

        errors:

          typeof result.errors === "object" && result.errors

            ? (result.errors as Record<string, string>)

            : undefined,

      };

    }



    const result = await safeParseJson(response);

    return { ...result, success: true } as AuthResponse;

  } catch (error) {

    console.error("[authService] Register network error:", error);

    return {

      success: false,

      error: "Unable to connect to server. Please check your connection and try again.",

    };

  }
}

export interface VerifyEmailResponse {
  verified: boolean;
  error?: string;
}

export interface ResendVerificationResponse {
  success: boolean;
  already_verified?: boolean;
  message?: string;
  verification_delivery_available?: boolean;
  verification_delivery_method?: string | null;
  verification_delivery_error?: string | null;
  support_email?: string;
  error?: string;
}

export async function verifyEmailToken(token: string): Promise<VerifyEmailResponse> {
  try {
    const response = await fetch(`${API_BASE}/auth/verify-email/${encodeURIComponent(token)}`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    return {
      verified: Boolean(payload.verified),
      error:
        response.ok && payload.verified === true
          ? undefined
          : ((typeof payload.error === "string" ? payload.error : undefined) || "Unable to verify email."),
    };
  } catch (error) {
    console.error("[authService] Verify email failed:", error);
    return { verified: false, error: "Unable to verify email right now." };
  }
}

export async function resendVerificationEmail(email: string): Promise<ResendVerificationResponse> {
  try {
    const response = await fetch(`${API_BASE}/auth/resend-verification`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to resend verification email.",
      };
    }
    return {
      success: true,
      already_verified: Boolean(payload.already_verified),
      message: typeof payload.message === "string" ? payload.message : undefined,
      verification_delivery_available:
        typeof payload.verification_delivery_available === "boolean"
          ? payload.verification_delivery_available
          : undefined,
      verification_delivery_method:
        typeof payload.verification_delivery_method === "string" || payload.verification_delivery_method === null
          ? payload.verification_delivery_method
          : undefined,
      verification_delivery_error:
        typeof payload.verification_delivery_error === "string" || payload.verification_delivery_error === null
          ? payload.verification_delivery_error
          : undefined,
      support_email: typeof payload.support_email === "string" ? payload.support_email : undefined,
    };
  } catch (error) {
    console.error("[authService] Resend verification failed:", error);
    return { success: false, error: "Unable to resend verification email right now." };
  }
}

export async function createFirm(payload: CreateFirmPayload): Promise<CreateFirmResponse> {
  try {
    const response = await fetch(apiUrl("/firms/create"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(payload),
    });

    const data = await safeParseJson(response);
    if (!response.ok || data.success === false) {
      return {
        success: false,
        error: (typeof data.error === "string" ? data.error : undefined) || "Unable to create firm.",
      };
    }

    return {
      success: true,
      firm_id: typeof data.firm_id === "number" ? data.firm_id : undefined,
    };
  } catch (error) {
    console.error("[authService] Create firm failed:", error);
    return {
      success: false,
      error: "Unable to create firm right now.",
    };
  }
}

export async function getCurrentUser(): Promise<User | null> {
  return getCurrentUserWithRetry();
}


export async function getCurrentUserWithRetry(options?: {

  onTransientIssue?: (kind: SessionTransientKind) => void;

  maxRetries?: number;

}): Promise<User | null> {

  const notify = options?.onTransientIssue;

  const retries = Math.max(0, options?.maxRetries ?? 2);

  const url = `${API_BASE}/auth/me`;



  for (let attempt = 0; attempt <= retries; attempt++) {

    try {

      const response = await fetchWithRateLimitRetry(url, { method: "GET" });

      if (response.status === 401 || response.status === 403) {

        return null;

      }

      if (response.status === 429) {

        notify?.("rate_limited");

        if (attempt < retries) {

          await waitForRetry(Math.min(BASE_BACKOFF_MS * Math.pow(2, attempt), 10_000));

          continue;

        }

        throw new Error("SESSION_RATE_LIMITED");

      }

      if (response.status >= 500) {

        notify?.("connection");

        if (attempt < retries) {

          await waitForRetry(Math.min(BASE_BACKOFF_MS * Math.pow(2, attempt), 10_000));

          continue;

        }

        throw new Error(`SESSION_SERVER_${response.status}`);

      }

      if (!response.ok) {

        throw new Error(`SESSION_UNEXPECTED_${response.status}`);

      }



      const data = await safeParseJson(response);

      return (data.user as User) || null;

    } catch (err) {

      if (err instanceof DOMException && err.name === "AbortError") {

        throw err;

      }

      notify?.("connection");

      if (attempt < retries) {

        await waitForRetry(Math.min(BASE_BACKOFF_MS * Math.pow(2, attempt), 10_000));

        continue;

      }

      const message = err instanceof Error ? err.message : String(err);

      console.error("[authService] Session check failed:", message);

      throw err;

    }

  }



  throw new Error("SESSION_CHECK_RETRY_EXHAUSTED");

}



export async function getAccountPlan(): Promise<AccountPlanResponse> {
  try {
    const [response, limitsResponse] = await Promise.all([
      fetch(`${API_BASE}/account/plan`, {
        method: "GET",
        credentials: "include",
      }),
      fetch(`${API_BASE}/plan/limits`, {
        method: "GET",
        credentials: "include",
      }),
    ]);
    const payload = await safeParseJson(response);
    const limitsPayload = (await limitsResponse.json().catch(() => ({}))) as PlanLimitsResponse;

    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load plan details.",
      };
    }

    const rawPlanType = typeof payload.plan_type === "string" ? payload.plan_type : "free";
    const planType: PlanType = normalizePlanType(rawPlanType);

    const rawFirmPlan = typeof payload.firm_plan === "string" ? payload.firm_plan : undefined;
    const parseOptionalLimit = (value: unknown): number | null => {
      if (value === null || value === undefined) return null;
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };
    const limits = limitsPayload.success && limitsPayload.limits ? limitsPayload.limits : undefined;

    return {
      success: true,
      plan: {
        planType,
        planLabel: normalizePlanLabel(typeof payload.plan_label === "string" ? payload.plan_label : "Free", rawPlanType),
        isTrial: Boolean(payload.is_trial),
        firmPlan:
          rawFirmPlan === "free" ||
          rawFirmPlan === "team" ||
          rawFirmPlan === "firm" ||
          rawFirmPlan === "trial" ||
          rawFirmPlan === "professional" ||
          rawFirmPlan === "leadership"
            ? rawFirmPlan
            : undefined,
        planLimits: {
          maxReviewsPerUpload: parseOptionalLimit(limits?.max_reviews_per_upload),
          maxReportsPerMonth: parseOptionalLimit(limits?.max_reports_per_month),
          maxUsers: parseOptionalLimit(limits?.max_users),
          historyDays: parseOptionalLimit(limits?.history_days),
          pdfWatermark: Boolean(limits?.pdf_watermark),
        },
      },
    };
  } catch (error) {

    console.error("[authService] Account plan fetch failed:", error);

    return { success: false, error: "Unable to load plan details." };

  }

}

export async function completeOnboarding(): Promise<CompleteOnboardingResponse> {
  try {
    const response = await fetch(apiUrl("/onboarding/complete"), {
      method: "POST",
      credentials: "include",
    });

    const data = await safeParseJson(response);
    if (!response.ok || data.success === false) {
      return {
        success: false,
        error: (typeof data.error === "string" ? data.error : undefined) || "Unable to complete onboarding.",
      };
    }

    return {
      success: true,
      user: (data.user as User | undefined) || undefined,
    };
  } catch (error) {
    console.error("[authService] Complete onboarding failed:", error);
    return { success: false, error: "Unable to complete onboarding right now." };
  }
}

export async function getPlanLimits(): Promise<PlanLimitsResponse> {
  try {
    const response = await fetch(`${API_BASE}/plan/limits`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load plan limits.",
      };
    }
    return {
      success: true,
      plan: payload.plan as PlanLimitsResponse["plan"],
      limits: payload.limits as PlanLimitsResponse["limits"],
    };
  } catch (error) {
    console.error("[authService] Plan limits fetch failed:", error);
    return { success: false, error: "Unable to load plan limits." };
  }
}




export async function updateAccountProfile(input: { firm_name: string }): Promise<AccountProfileResponse> {

  try {

    const response = await fetch(`${API_BASE}/account/profile`, {

      method: "PUT",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify(input),

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update account profile.",

      };

    }

    return {

      success: true,

      user: (payload.user as User) || undefined,

    };

  } catch (error) {

    console.error("[authService] Account profile update failed:", error);

    return { success: false, error: "Unable to update account profile." };

  }

}

export async function createSupportTicket(input: {
  source: "contact" | "dashboard";
  category: string;
  urgency: string;
  subject: string;
  message: string;
  email?: string;
  name?: string;
  firm_name?: string;
}): Promise<{
  success: boolean;
  ticket?: SupportTicket;
  support_email?: string;
  security_email?: string;
  auto_response_email_sent?: boolean;
  support_notification_sent?: boolean;
  error?: string;
}> {
  try {
    const response = await fetch(`${API_BASE}/support/tickets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(input),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to create support request.",
      };
    }
    return {
      success: true,
      ticket: payload.ticket as SupportTicket,
      support_email: typeof payload.support_email === "string" ? payload.support_email : undefined,
      security_email: typeof payload.security_email === "string" ? payload.security_email : undefined,
      auto_response_email_sent: Boolean(payload.auto_response_email_sent),
      support_notification_sent: Boolean(payload.support_notification_sent),
    };
  } catch (error) {
    console.error("[authService] Support ticket create failed:", error);
    return { success: false, error: "Unable to create support request." };
  }
}

export async function getSupportTickets(options?: {
  scope?: "self" | "queue";
}): Promise<{
  success: boolean;
  tickets?: SupportTicket[];
  summary?: SupportTicketSummary;
  support_email?: string;
  security_email?: string;
  scope?: string;
  error?: string;
}> {
  try {
    const params = new URLSearchParams();
    if (options?.scope === "queue") {
      params.set("scope", "queue");
    }
    const url = params.toString() ? `${API_BASE}/support/tickets?${params.toString()}` : `${API_BASE}/support/tickets`;
    const response = await fetch(url, { method: "GET", credentials: "include" });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load support tickets.",
      };
    }
    return {
      success: true,
      tickets: Array.isArray(payload.tickets) ? (payload.tickets as SupportTicket[]) : [],
      summary: payload.summary as SupportTicketSummary,
      support_email: typeof payload.support_email === "string" ? payload.support_email : undefined,
      security_email: typeof payload.security_email === "string" ? payload.security_email : undefined,
      scope: typeof payload.scope === "string" ? payload.scope : undefined,
    };
  } catch (error) {
    console.error("[authService] Support ticket fetch failed:", error);
    return { success: false, error: "Unable to load support tickets." };
  }
}

export async function updateSupportTicket(
  ticketId: number,
  input: { status?: string; priority?: string },
): Promise<{ success: boolean; ticket?: SupportTicket; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/support/tickets/${ticketId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify(input),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update support ticket.",
      };
    }
    return { success: true, ticket: payload.ticket as SupportTicket };
  } catch (error) {
    console.error("[authService] Support ticket update failed:", error);
    return { success: false, error: "Unable to update support ticket." };
  }
}



/** THEIRS: Branding normalizer + API */

function normalizeAccountBranding(payload: Record<string, unknown>): AccountBranding {

  const rawBranding = (payload.branding || payload) as Record<string, unknown>;

  const rawThemeOptions = Array.isArray(rawBranding.theme_options) ? rawBranding.theme_options : [];



  return {

    accentTheme: typeof rawBranding.accent_theme === "string" ? rawBranding.accent_theme : "default",

    themeOptions: rawThemeOptions

      .map((option) => {

        if (!option || typeof option !== "object") {

          return null;

        }

        const raw = option as Record<string, unknown>;

        return {

          id: typeof raw.id === "string" ? raw.id : "",

          label: typeof raw.label === "string" ? raw.label : "",

          accent_hex: typeof raw.accent_hex === "string" ? raw.accent_hex : "#d97706",

          primary_hex: typeof raw.primary_hex === "string" ? raw.primary_hex : "#1e3a8a",

          surface_hex: typeof raw.surface_hex === "string" ? raw.surface_hex : "#f8fafc",

        } as BrandingThemeOption;

      })

      .filter((option): option is BrandingThemeOption => Boolean(option?.id && option?.label)),

    logoUrl: typeof rawBranding.logo_url === "string" ? rawBranding.logo_url : null,

    hasLogo: Boolean(rawBranding.has_logo),

    logoUpdatedAt: typeof rawBranding.logo_updated_at === "string" ? rawBranding.logo_updated_at : null,

    brandingEditorEnabled: Boolean(rawBranding.branding_editor_enabled),

  };

}



export async function getAccountBranding(): Promise<AccountBrandingResponse> {

  try {

    const response = await fetch(`${API_BASE}/account/branding`, {

      method: "GET",

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load branding settings.",

      };

    }

    return { success: true, branding: normalizeAccountBranding(payload) };

  } catch (error) {

    console.error("[authService] Account branding fetch failed:", error);

    return { success: false, error: "Unable to load branding settings." };

  }

}



export async function updateAccountBrandingTheme(accentTheme: string): Promise<AccountBrandingResponse> {

  try {

    const response = await fetch(`${API_BASE}/account/branding/theme`, {

      method: "PUT",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify({ accent_theme: accentTheme }),

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update branding theme.",

      };

    }

    return { success: true, branding: normalizeAccountBranding(payload) };

  } catch (error) {

    console.error("[authService] Branding theme update failed:", error);

    return { success: false, error: "Unable to update branding theme." };

  }

}



export async function uploadAccountBrandingLogo(file: File): Promise<AccountBrandingResponse> {

  try {

    const form = new FormData();

    form.append("logo", file);

    const response = await fetch(`${API_BASE}/account/branding/logo`, {

      method: "POST",

      body: form,

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to upload logo.",

      };

    }

    return { success: true, branding: normalizeAccountBranding(payload) };

  } catch (error) {

    console.error("[authService] Branding logo upload failed:", error);

    return { success: false, error: "Unable to upload logo." };

  }

}



export async function deleteAccountBrandingLogo(): Promise<AccountBrandingResponse> {

  try {

    const response = await fetch(`${API_BASE}/account/branding/logo`, {

      method: "DELETE",

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to remove logo.",

      };

    }

    return { success: true, branding: normalizeAccountBranding(payload) };

  } catch (error) {

    console.error("[authService] Branding logo delete failed:", error);

    return { success: false, error: "Unable to remove logo." };

  }

}



export async function logout(): Promise<boolean> {

  const url = `${API_BASE}/auth/logout`;



  try {

    const response = await fetch(url, {

      method: "POST",

      credentials: "include",

    });

    clearCachedCsrfToken();
    return response.ok;

  } catch (err) {

    clearCachedCsrfToken();
    console.error("[authService] Logout failed:", err instanceof Error ? err.message : String(err));

    return false;

  }

}



export async function getDashboardStats(): Promise<DashboardStatsResponse> {

  const primaryUrl = `${API_BASE}/dashboard/stats`;

  const fallbackUrl = `${API_BASE}/dashboard/metrics`;



  try {

    let response = await fetch(primaryUrl, {

      method: "GET",

      credentials: "include",

    });



    // Backward-compatible fallback if backend still exposes /metrics.

    if (response.status === 404) {

      response = await fetch(fallbackUrl, {

        method: "GET",

        credentials: "include",

      });

    }



    if (response.status === 404) {

      const currentUser = await getCurrentUser();

      if (!currentUser) {

        return { success: false, error: "Not authenticated." };

      }

      return {

        success: true,

        stats: {

          processed_files: 0,

          total_reviews_processed: 0,

          last_report_at: null,

          recent_reports: [],

          account_status: {

            type: currentUser.subscription_type || "trial",

            display: currentUser.subscription_type || "trial",

            remaining:

              typeof currentUser.trial_limit === "number" && typeof currentUser.trial_reviews_used === "number"

                ? Math.max(0, currentUser.trial_limit - currentUser.trial_reviews_used)

                : null,

          },

          trial_reviews_used: currentUser.trial_reviews_used || 0,

          trial_limit: currentUser.trial_limit || 3,

          email_verified: currentUser.email_verified === true,

          trend_stability: "Insufficient data",

          trend_stability_explanation: trendStabilityDefinition,

          confidence_level: "Low",

          confidence_explanation: confidenceDefinition,

          avg_sentiment_score: null,

          latest_review_date: null,

          review_volume: {

            all_time: 0,

            last_30_days: 0,

            last_90_days: 0,

            last_7_days: 0,

            month_to_date: 0,

          },

        },

      };

    }



    const data = await safeParseJson(response);



    if (!response.ok) {

      return {

        success: false,

        error: (typeof data.error === "string" ? data.error : undefined) || "Failed to load dashboard stats.",

      };

    }



    const rawStats = (data.stats || {}) as Partial<DashboardStats>;

    const rawReviewVolume =

      rawStats.review_volume && typeof rawStats.review_volume === "object"

        ? (rawStats.review_volume as Record<string, unknown>)

        : {};



    return {

      success: true,

      stats: {

        processed_files: Number(rawStats.processed_files || 0),

        total_reviews_processed: Number(rawStats.total_reviews_processed || 0),

        last_report_at: rawStats.last_report_at || null,

        recent_reports: Array.isArray(rawStats.recent_reports) ? rawStats.recent_reports : [],

        account_status: rawStats.account_status || { type: "trial", display: "trial", remaining: null },

        trial_reviews_used: Number(rawStats.trial_reviews_used || 0),

        trial_limit: Number(rawStats.trial_limit || 3),

        email_verified: rawStats.email_verified === true,

        trend_stability: rawStats.trend_stability || "Insufficient data",

        trend_stability_explanation: rawStats.trend_stability_explanation || trendStabilityDefinition,

        confidence_level: rawStats.confidence_level || "Low",

        confidence_explanation: rawStats.confidence_explanation || confidenceDefinition,

        avg_sentiment_score: typeof rawStats.avg_sentiment_score === "number" ? rawStats.avg_sentiment_score : null,

        latest_review_date: typeof rawStats.latest_review_date === "string" ? rawStats.latest_review_date : null,

        review_volume: {

          all_time: Number(rawReviewVolume.all_time || 0),

          last_30_days: Number(rawReviewVolume.last_30_days || 0),

          last_90_days: Number(rawReviewVolume.last_90_days || 0),

          last_7_days: Number(rawReviewVolume.last_7_days || 0),

          month_to_date: Number(rawReviewVolume.month_to_date || 0),

        },

      },

    };

  } catch (error) {

    warnNetworkOnce("dashboard-stats", "Dashboard stats", error);

    return {

      success: false,

      error: "Dashboard stats endpoint is unavailable. Verify backend route GET /api/dashboard/stats.",

    };

  }

}



export async function uploadCsv(
  file: File,
  onProgress?: (progress: number) => void,
  signal?: AbortSignal,
): Promise<UploadResponse> {
  const url = `${API_BASE}/upload`;

  onProgress?.(10);



  try {

    const form = new FormData();

    form.append("file", file);

    const sendUpload = async (forceFreshToken = false) => {
      const token = forceFreshToken ? await refreshCsrfToken() : await ensureCsrfToken(true);
      const headers = new Headers();
      if (token) {
        headers.set("X-CSRFToken", token);
      }
      return globalThis.fetch(url, {
        method: "POST",
        body: form,
        headers,
        credentials: "include",
        signal,
      });
    };

    const parseUploadResponse = async (
      response: Response,
      logLabel: string,
    ): Promise<{ payload?: Record<string, unknown>; error?: string }> => {
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("application/json")) {
        const bodyText = await response.text();
        console.error(`[authService] ${logLabel} received non-JSON response:`, {
          status: response.status,
          contentType,
          body: bodyText.substring(0, 500),
        });
        return { error: "Upload failed: unexpected server response." };
      }
      const payload = (await response.json()) as Record<string, unknown>;
      return { payload };
    };

    const normalizeUploadError = (payload: Record<string, unknown>): string => {
      if (payload.error === "plan_limit") {
        emitPlanLimitError(typeof payload.message === "string" ? payload.message : "Trial limit reached");
      }
      return (
        (typeof payload.message === "string" ? payload.message : undefined) ||
        (payload.code === "csrf_failed"
          ? "Your session needs a quick refresh before upload can continue. Please try again."
          : undefined) ||
        (typeof payload.error === "string" ? payload.error : undefined) ||
        "Upload failed. Please try again."
      );
    };

    let response = await sendUpload();

    onProgress?.(85);

    let parsed = await parseUploadResponse(response, "Upload");
    if (parsed.error) {
      return { success: false, error: parsed.error };
    }

    let payload = parsed.payload as Record<string, unknown>;
    if (payload.code === "csrf_failed") {
      response = await sendUpload(true);
      parsed = await parseUploadResponse(response, "Upload retry");
      if (parsed.error) {
        return { success: false, error: parsed.error };
      }
      payload = parsed.payload as Record<string, unknown>;
    }

    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: normalizeUploadError(payload),
      };
    }

    const summary = (payload.summary || {}) as Record<string, unknown>;

    const usage = (payload.usage || {}) as Record<string, unknown>;



    onProgress?.(100);

    return {

      success: true,

      data: {

        summary: {

          imported_count: Number(summary.imported_count || 0),

          report_id: summary.report_id ? Number(summary.report_id) : null,

          message: typeof summary.message === "string" ? summary.message : "Upload completed successfully.",

          truncated_for_plan: Boolean(summary.truncated_for_plan),

          skipped_due_to_plan_limit: Number(summary.skipped_due_to_plan_limit || 0),

        },

        usage: {

          trial_reviews_used: Number(usage.trial_reviews_used || 0),

          trial_limit: Number(usage.trial_limit || 0),

          one_time_reports_used: Number(usage.one_time_reports_used || 0),

          one_time_reports_remaining: Number(usage.one_time_reports_remaining || 0),

          subscription_type: typeof usage.subscription_type === "string" ? usage.subscription_type : "trial",

        },

      },

    };

  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return { success: false, error: "Aborted" };
    }
    console.error("[authService] Upload request failed:", error);
    return { success: false, error: "Upload failed: unexpected server response." };
  }
}

export async function loadOnboardingDemoDataset(): Promise<UploadResponse> {
  try {
    const response = await fetch(`${API_BASE}/onboarding/load-demo`, {
      method: "POST",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      if (payload.error === "plan_limit") {
        emitPlanLimitError(typeof payload.message === "string" ? payload.message : "Trial limit reached");
      }
      return {
        success: false,
        error:
          (typeof payload.message === "string" ? payload.message : undefined) ||
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to load demo dataset.",
      };
    }

    const summary = (payload.summary || {}) as Record<string, unknown>;
    const usage = (payload.usage || {}) as Record<string, unknown>;
    return {
      success: true,
      data: {
        summary: {
          imported_count: Number(summary.imported_count || 0),
          report_id: summary.report_id ? Number(summary.report_id) : null,
          message: typeof summary.message === "string" ? summary.message : "Demo dataset loaded.",
          truncated_for_plan: Boolean(summary.truncated_for_plan),
          skipped_due_to_plan_limit: Number(summary.skipped_due_to_plan_limit || 0),
        },
        usage: {
          trial_reviews_used: Number(usage.trial_reviews_used || 0),
          trial_limit: Number(usage.trial_limit || 0),
          one_time_reports_used: Number(usage.one_time_reports_used || 0),
          one_time_reports_remaining: Number(usage.one_time_reports_remaining || 0),
          subscription_type: typeof usage.subscription_type === "string" ? usage.subscription_type : "trial",
        },
      },
    };
  } catch (error) {
    console.error("[authService] Onboarding demo load failed:", error);
    return { success: false, error: "Unable to load demo dataset." };
  }
}

export interface FirmActionsResponse {
  success: boolean;
  actions?: ReportActionItem[];
  error?: string;
}


export async function startCheckoutSession(plan: BillingPlan, returnTo = "/pricing"): Promise<CheckoutSessionResponse> {

  try {
    const apiPlan = plan === "team" ? "monthly" : "annual";

    const { response, payload } = await postCheckoutJson("/billing/checkout", {
      plan: apiPlan,
      return_to: returnTo,
    });

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: normalizeCheckoutError(response, payload, "Unable to start checkout right now."),

      };

    }



    return {

      success: true,

      checkout_url: typeof payload.checkout_url === "string" ? payload.checkout_url : undefined,

    };

  } catch (error) {

    console.error("[authService] Checkout session failed:", error);

    return { success: false, error: "Unable to start checkout right now." };

  }

}



export async function finalizeCheckoutSession(

  sessionId: string,

  plan: BillingPlan | LegacyBillingPlan,

): Promise<CheckoutFinalizeResponse> {

  try {
    const apiPlan = plan === "team" ? "monthly" : plan === "firm" ? "annual" : plan;

    const { response, payload } = await postCheckoutJson("/billing/checkout/finalize", {
      session_id: sessionId,
      plan: apiPlan,
    });

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: normalizeCheckoutError(response, payload, "Unable to confirm checkout."),

      };

    }



    return { success: true, plan: typeof payload.plan === "string" ? payload.plan : undefined };

  } catch (error) {

    console.error("[authService] Checkout finalize failed:", error);

    return { success: false, error: "Unable to confirm checkout." };

  }

}



export async function getReports(limit = 50): Promise<ReportListResponse> {

  try {

    const response = await fetchWithRateLimitRetry(`${API_BASE}/reports?limit=${limit}`, {

      method: "GET",

      credentials: "include",

    });



    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load reports.",

      };

    }



    return {

      success: true,

      reports: ((payload.reports as ReportListItem[]) || []).map((report) => ({

        ...report,

        status: report.status || "ready",
        plan_label: normalizePlanLabel(report.plan_label, report.plan_type),

      })),
      history_window_days:
        payload.history_window_days === null || payload.history_window_days === undefined
          ? null
          : Number(payload.history_window_days),
      history_truncated: Boolean(payload.history_truncated),
      history_notice: typeof payload.history_notice === "string" ? payload.history_notice : null,

    };

  } catch (error) {

    console.error("[authService] Reports fetch failed:", error);

    return { success: false, error: "Unable to load reports." };

  }

}



export async function getReportDetail(
  reportId: number,
  signal?: AbortSignal,
  options?: { onRetry?: () => void },
): Promise<ReportDetailResponse> {
  try {
    const response = await fetchWithRateLimitRetry(
      `${API_BASE}/reports/${reportId}`,
      {
        method: "GET",
        credentials: "include",
        signal,
      },
      options,
    );
    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,
        history_window_days:
          payload.history_window_days === null || payload.history_window_days === undefined
            ? null
            : Number(payload.history_window_days),
        history_truncated: Boolean(payload.history_truncated),
        history_notice: typeof payload.history_notice === "string" ? payload.history_notice : null,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load report detail.",

      };

    }



    const rawReport = (payload.report || {}) as Record<string, unknown>;

    const rawTopPraise = Array.isArray(rawReport.top_praise) ? rawReport.top_praise : [];

    const rawTopComplaints = Array.isArray(rawReport.top_complaints) ? rawReport.top_complaints : [];



    const normalizeSignal = (item: unknown) => {

      if (typeof item === "string") return item;

      if (item && typeof item === "object") {

        const dict = item as Record<string, unknown>;

        if (typeof dict.review_text === "string" && dict.review_text.trim()) return dict.review_text;

      }

      return "";

    };



    const statusRaw = typeof rawReport.status === "string" ? rawReport.status : "ready";

const status: ReportDetail["status"] =

  statusRaw === "processing" || statusRaw === "failed" ? statusRaw : "ready";



const accessRaw = typeof rawReport.access_level === "string" ? rawReport.access_level : "trial";

const access_level: ReportDetail["access_level"] = accessRaw === "paid" ? "paid" : "trial";



const planRaw = typeof rawReport.plan_type === "string" ? rawReport.plan_type : "free";
const plan_type: ReportDetail["plan_type"] = normalizePlanType(planRaw);



const normalizedReport: ReportDetail = {

  id: Number(rawReport.id || reportId),

  title: typeof rawReport.title === "string" ? rawReport.title : "",

  name: typeof rawReport.name === "string" ? rawReport.name : "",

  status,

  created_at: typeof rawReport.created_at === "string" ? rawReport.created_at : "",

  access_level,

  plan_type,

  total_reviews: Number(rawReport.total_reviews || 0),

  avg_rating: Number(rawReport.avg_rating || 0),

  review_date_start: typeof rawReport.review_date_start === "string" ? rawReport.review_date_start : null,

  review_date_end: typeof rawReport.review_date_end === "string" ? rawReport.review_date_end : null,

  review_date_label: typeof rawReport.review_date_label === "string" ? rawReport.review_date_label : null,

  custom_name: typeof rawReport.custom_name === "string" ? rawReport.custom_name : null,

  plan_label: normalizePlanLabel(typeof rawReport.plan_label === "string" ? rawReport.plan_label : "Free", planRaw),



  themes: Array.isArray(rawReport.themes) ? (rawReport.themes as ReportDetail["themes"]) : [],
  theme_trends:
    rawReport.theme_trends && typeof rawReport.theme_trends === "object"
      ? (rawReport.theme_trends as ReportDetail["theme_trends"])
      : {},

  top_praise: rawTopPraise.map(normalizeSignal).filter(Boolean),

  top_complaints: rawTopComplaints.map(normalizeSignal).filter(Boolean),

  opportunities_for_enhancement: Array.isArray(rawReport.opportunities_for_enhancement)

    ? (rawReport.opportunities_for_enhancement as string[])

    : [],

  executive_summary: Array.isArray(rawReport.executive_summary) ? (rawReport.executive_summary as string[]) : [],

  root_cause_themes: Array.isArray(rawReport.root_cause_themes)

    ? (rawReport.root_cause_themes as ReportDetail["root_cause_themes"])

    : [],

  recommended_changes: Array.isArray(rawReport.recommended_changes)

    ? (rawReport.recommended_changes as ReportDetail["recommended_changes"])

    : [],

  implementation_roadmap: Array.isArray(rawReport.implementation_roadmap)

    ? (rawReport.implementation_roadmap as ReportDetail["implementation_roadmap"])

    : [],

  strategic_plans: Array.isArray(rawReport.strategic_plans)

    ? (rawReport.strategic_plans as ReportDetail["strategic_plans"])

    : [],

  strategy_limits:

    rawReport.strategy_limits && typeof rawReport.strategy_limits === "object"

      ? (rawReport.strategy_limits as ReportDetail["strategy_limits"])

      : undefined,

  key_numbers:

    rawReport.key_numbers && typeof rawReport.key_numbers === "object"

      ? (rawReport.key_numbers as ReportDetail["key_numbers"])

      : { recommended_tier: "", expected_margin_impact: "", confidence_score: 0 },



  comparison:

    rawReport.comparison && typeof rawReport.comparison === "object"

      ? (rawReport.comparison as ReportDetail["comparison"])

      : undefined,



  download_pdf_url: typeof rawReport.download_pdf_url === "string" ? rawReport.download_pdf_url : "",

};



return {
  success: true,
  report: normalizedReport,
  history_window_days:
    payload.history_window_days === null || payload.history_window_days === undefined
      ? rawReport.history_window_days === null || rawReport.history_window_days === undefined
        ? null
        : Number(rawReport.history_window_days)
      : Number(payload.history_window_days),
  history_truncated:
    payload.history_truncated === undefined
      ? Boolean(rawReport.history_truncated)
      : Boolean(payload.history_truncated),
  history_notice:
    typeof payload.history_notice === "string"
      ? payload.history_notice
      : typeof rawReport.history_notice === "string"
        ? rawReport.history_notice
        : null,
};

  } catch (error) {

    if (error instanceof DOMException && error.name === "AbortError") {

      return { success: false, error: "Aborted" };

    }

    console.error("[authService] Report detail fetch failed:", error);

    return { success: false, error: "Unable to load report detail." };

  }

}



export async function sendPartnerBriefEmail(
  html: string,
): Promise<{
  success: boolean;
  emails_sent?: number;
  recipient_count?: number;
  recipients?: string[];
  from_email?: string;
  timestamp?: string;
  error?: string;
}> {
  try {
    const response = await fetchWithRateLimitRetry(`${API_BASE}/email-brief`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ html }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to send partner brief.",
      };
    }
    return {
      success: true,
      emails_sent: typeof payload.emails_sent === "number" ? payload.emails_sent : 0,
      recipient_count: typeof payload.recipient_count === "number" ? payload.recipient_count : 0,
      recipients: Array.isArray(payload.recipients) ? (payload.recipients as string[]) : [],
      from_email: typeof payload.from_email === "string" ? payload.from_email : undefined,
      timestamp: typeof payload.timestamp === "string" ? payload.timestamp : new Date().toISOString(),
    };
  } catch (error) {
    console.error("[authService] Partner brief email send failed:", error);
    return { success: false, error: "Unable to send partner brief." };
  }
}

export async function getPartnerBriefDeliveryStatus(): Promise<{
  success: boolean;
  status?: PartnerBriefDeliveryStatus;
  error?: string;
}> {
  try {
    const response = await fetchWithRateLimitRetry(`${API_BASE}/email-brief/status`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to load partner brief delivery status.",
      };
    }
    return {
      success: true,
      status: {
        delivery_available: Boolean(payload.delivery_available),
        recipient_count: typeof payload.recipient_count === "number" ? payload.recipient_count : 0,
        recipients: Array.isArray(payload.recipients) ? (payload.recipients as string[]) : [],
        from_email: typeof payload.from_email === "string" ? payload.from_email : "",
        missing_requirements: Array.isArray(payload.missing_requirements)
          ? payload.missing_requirements.filter((item): item is string => typeof item === "string")
          : [],
        firm_name: typeof payload.firm_name === "string" ? payload.firm_name : undefined,
      },
    };
  } catch (error) {
    console.error("[authService] Partner brief delivery status fetch failed:", error);
    return { success: false, error: "Unable to load partner brief delivery status." };
  }
}


export async function updateReportName(reportId: number, name: string): Promise<UpdateReportResponse> {

  try {

    const response = await fetch(`${API_BASE}/reports/${reportId}`, {

      method: "PATCH",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify({ name }),

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update report name.",

      };

    }

    return { success: true, report: payload.report as UpdateReportResponse["report"] };

  } catch (error) {

    console.error("[authService] Report update failed:", error);

    return { success: false, error: "Unable to update report name." };

  }

}



export async function getReportActions(
  reportId: number,
  signal?: AbortSignal,
  options?: { onRetry?: () => void },
): Promise<ReportActionsResponse> {
  const existing = inflightReportActionsRequests.get(reportId);
  if (existing) {
    if (DEV_MODE) {
      console.info(`[authService] getReportActions invoked reportId=${reportId} deduped=true stack=${trimmedStack()}`);
    }
    return existing;
  }

  if (DEV_MODE) {
    console.info(`[authService] getReportActions invoked reportId=${reportId} deduped=false stack=${trimmedStack()}`);
  }

  const request = (async (): Promise<ReportActionsResponse> => {
    let outcome = "other_error";
    try {
      const response = await fetchWithRateLimitRetry(
        `${API_BASE}/reports/${reportId}/actions`,
        {
          method: "GET",
          credentials: "include",
          signal,
        },
        options,
      );
      const payload = await safeParseJson(response);
      if (!response.ok || payload.success === false) {
        outcome = response.status === 429 ? "429" : `http_${response.status}`;
        if (DEV_MODE) {
          console.info(`[authService] getReportActions outcome reportId=${reportId} status=${outcome}`);
        }
        return {
          success: false,
          upgrade_required: Boolean(payload.upgrade_required),
          error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load action items.",
        };
      }
      outcome = "success";
      if (DEV_MODE) {
        console.info(`[authService] getReportActions outcome reportId=${reportId} status=${outcome}`);
      }
      return {
        success: true,
        actions: ((payload.actions as ReportActionItem[]) || []).map((item) => ({ ...item })),
        upsell: payload.upsell as ReportActionsResponse["upsell"],
      };
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        outcome = "aborted";
        if (DEV_MODE) {
          console.info(`[authService] getReportActions outcome reportId=${reportId} status=${outcome}`);
        }
        return { success: false, error: "Aborted" };
      }
      outcome = "other_error";
      if (DEV_MODE) {
        console.info(`[authService] getReportActions outcome reportId=${reportId} status=${outcome}`);
      }
      console.error("[authService] Report actions fetch failed:", error);
      return { success: false, error: "Unable to load action items." };
    }
  })().finally(() => {
    inflightReportActionsRequests.delete(reportId);
  });

  inflightReportActionsRequests.set(reportId, request);
  return request;
}

export async function getReportGovernanceSignals(reportId: number): Promise<GovernanceSignalsResponse> {
  try {
    const response = await fetchWithRateLimitRetry(`${API_BASE}/reports/${reportId}/governance-signals`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load governance signals.",
      };
    }
    return {
      success: true,
      signals: Array.isArray(payload.signals) ? (payload.signals as GovernanceSignal[]) : [],
      recommendations: Array.isArray(payload.recommendations)
        ? (payload.recommendations as GovernanceRecommendation[])
        : [],
    };
  } catch (error) {
    console.error("[authService] Governance signals fetch failed:", error);
    return { success: false, error: "Unable to load governance signals." };
  }
}

export async function getFirmActions(
  signal?: AbortSignal,
  options?: { onRetry?: () => void },
): Promise<FirmActionsResponse> {
  try {
    const response = await fetchWithRateLimitRetry(
      `${API_BASE}/actions`,
      {
        method: "GET",
        credentials: "include",
        signal,
      },
      options,
    );
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load actions.",
      };
    }
    return {
      success: true,
      actions: ((payload.actions as ReportActionItem[]) || []).map((item) => ({ ...item })),
    };
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      return { success: false, error: "Aborted" };
    }
    console.error("[authService] Firm actions fetch failed:", error);
    return { success: false, error: "Unable to load actions." };
  }
}

export async function getGovernanceAlerts(): Promise<GovernanceAlertsResponse> {
  try {
    const response = await fetchWithRateLimitRetry(`${API_BASE}/alerts`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load governance alerts.",
      };
    }
    return {
      success: true,
      alerts: Array.isArray(payload.alerts) ? (payload.alerts as GovernanceAlert[]) : [],
    };
  } catch (error) {
    console.error("[authService] Governance alerts fetch failed:", error);
    return { success: false, error: "Unable to load governance alerts." };
  }
}

export async function getRecentGovernanceActions(): Promise<RecentGovernanceActionsResponse> {
  try {
    const response = await fetchWithRateLimitRetry(`${API_BASE}/actions/recent`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to load recent governance actions.",
      };
    }
    return {
      success: true,
      actions: Array.isArray(payload.actions) ? (payload.actions as RecentGovernanceAction[]) : [],
    };
  } catch (error) {
    console.error("[authService] Recent governance actions fetch failed:", error);
    return { success: false, error: "Unable to load recent governance actions." };
  }
}


export async function createReportAction(
  reportId: number,
  input: {
    title: string;
    owner?: string;
    owner_user_id?: number | null;
    status?: "open" | "in_progress" | "done" | "blocked";
    due_date?: string | null;
    timeframe?: "Days 1-30" | "Days 31-60" | "Days 61-90" | null;
    kpi?: string;
    notes?: string;

  },

  options?: { onRetry?: () => void },

): Promise<{ success: boolean; action?: ReportActionItem; upgrade_required?: boolean; error?: string }> {

  try {

    const response = await fetchWithRateLimitRetry(

      `${API_BASE}/reports/${reportId}/actions`,

      {

        method: "POST",

        headers: { "Content-Type": "application/json" },

        credentials: "include",

        body: JSON.stringify(input),

      },

      options,

    );

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        upgrade_required: Boolean(payload.upgrade_required),

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to create action item.",

      };

    }

    return { success: true, action: payload.action as ReportActionItem };

  } catch (error) {

    console.error("[authService] Report action create failed:", error);

    return { success: false, error: "Unable to create action item." };

  }

}



export async function updateReportAction(

  reportId: number,

  actionId: number,

  input: Partial<

    Pick<ReportActionItem, "title" | "owner" | "owner_user_id" | "status" | "due_date" | "timeframe" | "kpi" | "notes">

  >,

  options?: { onRetry?: () => void },

): Promise<{ success: boolean; action?: ReportActionItem; error?: string }> {

  try {

    const response = await fetchWithRateLimitRetry(

      `${API_BASE}/reports/${reportId}/actions/${actionId}`,

      {

        method: "PATCH",

        headers: { "Content-Type": "application/json" },

        credentials: "include",

        body: JSON.stringify(input),

      },

      options,

    );

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update action item.",

      };

    }

    return { success: true, action: payload.action as ReportActionItem | undefined };

  } catch (error) {

    console.error("[authService] Report action update failed:", error);

    return { success: false, error: "Unable to update action item." };

  }

}



export async function deleteReportAction(

  reportId: number,

  actionId: number,

): Promise<{ success: boolean; error?: string }> {

  try {

    const response = await fetch(`${API_BASE}/reports/${reportId}/actions/${actionId}`, {

      method: "DELETE",

      credentials: "include",

    });

    if (response.status === 204) return { success: true };



    let payload: Record<string, unknown> = {};

    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {

      payload = (await response.json()) as Record<string, unknown>;

    }

    return { success: false, error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to delete action item." };

  } catch (error) {

    console.error("[authService] Report action delete failed:", error);

    return { success: false, error: "Unable to delete action item." };

  }

}



export async function deleteReport(reportId: number): Promise<DeleteReportResponse> {

  try {

    const response = await fetch(`${API_BASE}/reports/${reportId}`, {

      method: "DELETE",

      credentials: "include",

    });



    if (response.status === 204) return { success: true };



    let payload: Record<string, unknown> = {};

    const contentType = response.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {

      payload = (await response.json()) as Record<string, unknown>;

    }



    return {

      success: false,

      error:

        (typeof payload.error === "string" ? payload.error : undefined) ||

        (response.status === 404 ? "Report not found." : "We couldn't delete this report. Please try again."),

    };

  } catch (error) {

    console.error("[authService] Report delete failed:", error);

    return { success: false, error: "We couldn't delete this report. Please try again." };

  }

}



export async function getReportPackSchedule(): Promise<ReportPackScheduleResponse> {

  try {

    const response = await fetch(`${API_BASE}/report-packs/schedule`, {

      method: "GET",

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        upgrade_required: Boolean(payload.upgrade_required),

        upgrade_message: typeof payload.upgrade_message === "string" ? payload.upgrade_message : null,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load schedule settings.",

      };

    }

    return {

      success: true,

      schedule: payload.schedule as ReportPackSchedule,

      can_manage: Boolean(payload.can_manage),

      upgrade_required: Boolean(payload.upgrade_required),

      upgrade_message: typeof payload.upgrade_message === "string" ? payload.upgrade_message : null,

    };

  } catch (error) {

    console.error("[authService] Report pack schedule fetch failed:", error);

    return { success: false, error: "Unable to load schedule settings." };

  }

}



export async function updateReportPackSchedule(input: {

  enabled: boolean;

  cadence: "weekly" | "monthly";

  recipients: string[];

}): Promise<ReportPackScheduleResponse> {

  try {

    const response = await fetch(`${API_BASE}/report-packs/schedule`, {

      method: "PUT",

      headers: { "Content-Type": "application/json" },

      credentials: "include",

      body: JSON.stringify(input),

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        upgrade_required: Boolean(payload.upgrade_required),

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to update schedule settings.",

      };

    }

    return { success: true, schedule: payload.schedule as ReportPackSchedule };

  } catch (error) {

    console.error("[authService] Report pack schedule update failed:", error);

    return { success: false, error: "Unable to update schedule settings." };

  }

}



export async function sendReportPackNow(): Promise<SendReportPackNowResponse> {

  try {

    const response = await fetch(`${API_BASE}/report-packs/send-now`, {

      method: "POST",

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        upgrade_required: Boolean(payload.upgrade_required),

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to send executive pack.",

      };

    }

    return {

      success: true,

      delivery_count: Number(payload.delivery_count || 0),

      recipient_count: Number(payload.recipient_count || 0),

      message: typeof payload.message === "string" ? payload.message : "Executive pack sent.",

    };

  } catch (error) {

    console.error("[authService] Report pack send-now failed:", error);

    return { success: false, error: "Unable to send executive pack." };

  }

}



export async function getDeletedReports(limit = 50): Promise<DeletedReportsResponse> {

  try {

    const response = await fetch(`${API_BASE}/reports/deleted?limit=${limit}`, {

      method: "GET",

      credentials: "include",

    });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load recently deleted reports.",

      };

    }



    return {

      success: true,

      reports: ((payload.reports as DeletedReportItem[]) || []).map((report) => ({
        ...report,
        plan_label: normalizePlanLabel(report.plan_label, report.plan_type),
      })),

      can_restore: Boolean(payload.can_restore),
      history_window_days:
        payload.history_window_days === null || payload.history_window_days === undefined
          ? null
          : Number(payload.history_window_days),
      history_truncated: Boolean(payload.history_truncated),
      history_notice: typeof payload.history_notice === "string" ? payload.history_notice : null,

      retention_days: Number(payload.retention_days || 30),

      upgrade_required: Boolean(payload.upgrade_required),

    };

  } catch (error) {

    console.error("[authService] Deleted reports fetch failed:", error);

    return { success: false, error: "Unable to load recently deleted reports." };

  }

}



export async function restoreDeletedReport(reportId: number): Promise<RestoreDeletedReportResponse> {

  try {

    const response = await fetch(`${API_BASE}/reports/${reportId}/restore`, {

      method: "POST",

      credentials: "include",

    });



    const contentType = response.headers.get("content-type") || "";

    let payload: Record<string, unknown> = {};

    if (contentType.includes("application/json")) {

      payload = (await response.json()) as Record<string, unknown>;

    }



    if (!response.ok || payload.success === false) {

      return {

        success: false,

        upgrade_required: Boolean(payload.upgrade_required),

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to restore this report right now.",

      };

    }



    const report = payload.report as { id?: number; name?: string } | undefined;

    return {

      success: true,

      report: report ? { id: Number(report.id || 0), name: String(report.name || "") } : undefined,

    };

  } catch (error) {

    console.error("[authService] Restore report failed:", error);

    return { success: false, error: "Unable to restore this report right now." };

  }

}



export async function getCredits(): Promise<CreditsResponse> {

  try {

    const response = await fetchWithRateLimitRetry("/credits", { method: "GET" });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load credits.",

      };

    }

    return { success: true, credits: payload.credits as CreditsState };

  } catch (error) {

    warnNetworkOnce("credits", "Credits", error);

    return { success: false, error: "Unable to load credits." };

  }

}



export async function checkBackendWiring(): Promise<{ ok: boolean; message?: string }> {

  try {

    const response = await fetch(`${API_BASE}/version`, {

      method: "GET",

      credentials: "include",

    });



    if (response.ok) {

      const payload = (await response.json()) as BackendVersionResponse;

      if (payload.success && payload.service === "law-firm-feedback-saas") {

        return { ok: true };

      }

    }



    if (response.status === 404) {

      return {

        ok: false,

        message:

          "Backend wiring mismatch: /api/version is missing. Ensure Vite is proxying to the Clarion Flask app in backend/app.py and that the backend is reachable on the configured local proxy target.",

      };

    }



    return {

      ok: false,

      message: "Backend API is reachable but does not match expected Clarion service.",

    };

  } catch {

    return {

      ok: false,

      message: "Cannot reach backend at /api. Check Vite proxy and Flask server on port 5000.",

    };

  }

}



export async function getLatestExposure(): Promise<ExposureSnapshotResponse> {

  try {

    const response = await fetchWithRateLimitRetry("/exposure/latest", { method: "GET" });

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load exposure status.",

      };

    }

    const exposure: ExposureSnapshot = {

      has_data: Boolean(payload.has_data),

      report_id: typeof payload.report_id === "number" ? payload.report_id : null,

      snapshot_id: typeof payload.snapshot_id === "number" ? payload.snapshot_id : null,

      latest_timestamp: typeof payload.latest_timestamp === "string" ? payload.latest_timestamp : null,

      exposure_score: typeof payload.exposure_score === "number" ? payload.exposure_score : null,

      exposure_tier:

        payload.exposure_tier === "Controlled" ||

        payload.exposure_tier === "Watch" ||

        payload.exposure_tier === "Elevated" ||

        payload.exposure_tier === "Critical"

          ? payload.exposure_tier

          : null,

      exposure_label:

        payload.exposure_label === "Baseline" ||

        payload.exposure_label === "Watchlist" ||

        payload.exposure_label === "Elevated" ||

        payload.exposure_label === "High"

          ? payload.exposure_label

          : null,

      partner_escalation_required:

        typeof payload.partner_escalation_required === "boolean" ? payload.partner_escalation_required : null,

      primary_risk_driver: typeof payload.primary_risk_driver === "string" ? payload.primary_risk_driver : null,

      responsible_owner: typeof payload.responsible_owner === "string" ? payload.responsible_owner : null,

    };

    return { success: true, exposure };

  } catch (error) {

    warnNetworkOnce("exposure", "Exposure", error);

    return { success: false, error: "Unable to load exposure status." };

  }

}



export async function submitFeatureInterest(input: {

  feature_key: string;

  choice: FeatureInterestChoice;

}): Promise<FeatureInterestSubmitResponse> {

  try {

    const response = await fetch(

      apiUrl("/interest"),

      apiRequestInit({

        method: "POST",

        headers: { "Content-Type": "application/json" },

        body: JSON.stringify({ feature: input.feature_key, choice: input.choice }),

      }),

    );

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error: (typeof payload.error === "string" ? payload.error : undefined) || "Unable to save preference.",

      };

    }

    return {

      success: true,

      feature_key: typeof payload.feature_key === "string" ? payload.feature_key : undefined,

      choice: payload.choice === "yes" || payload.choice === "no" ? payload.choice : undefined,

    };

  } catch (error) {

    warnNetworkOnce("feature-interest-submit", "Feature interest submit", error);

    return { success: false, error: "Unable to save preference." };

  }

}



export async function getFeatureInterestSummary(featureKey: string): Promise<FeatureInterestSummaryResponse> {

  try {

    const query = new URLSearchParams({ feature: featureKey }).toString();

    const response = await fetch(apiUrl(`/interest/summary?${query}`), apiRequestInit());

    const payload = await safeParseJson(response);

    if (!response.ok || payload.success === false) {

      return {

        success: false,

        error:

          (typeof payload.error === "string" ? payload.error : undefined) || "Unable to load preference summary.",

      };

    }

    return {

      success: true,

      summary: {

        feature_key: typeof payload.feature_key === "string" ? payload.feature_key : featureKey,

        yes_count: typeof payload.yes_count === "number" ? payload.yes_count : 0,

        no_count: typeof payload.no_count === "number" ? payload.no_count : 0,

        total_firms: typeof payload.total_firms === "number" ? payload.total_firms : 0,

        current_firm_choice:

          payload.current_firm_choice === "yes" || payload.current_firm_choice === "no"

            ? payload.current_firm_choice

            : null,

      },

    };

  } catch (error) {

    warnNetworkOnce("feature-interest-summary", "Feature interest summary", error);

    return { success: false, error: "Unable to load preference summary." };

  }

}

// ---------------------------------------------------------------------------
// Password reset helpers (used by ForgotPassword / ResetPassword SPA pages)
// ---------------------------------------------------------------------------

export interface PasswordResetRequestResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export interface PasswordResetValidateResponse {
  valid: boolean;
  reason?: string;
}

export interface PasswordResetSubmitResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export async function requestPasswordReset(email: string): Promise<PasswordResetRequestResponse> {
  try {
    const response = await fetch(apiUrl("/auth/forgot-password"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    const payload = (await safeParseJson(response)) as { success?: boolean; message?: string; error?: string };
    return {
      success: Boolean(payload.success),
      message: typeof payload.message === "string" ? payload.message : undefined,
      error: typeof payload.error === "string" ? payload.error : undefined,
    };
  } catch (error) {
    warnNetworkOnce("forgot-password", "Forgot password", error);
    return { success: false, error: "Unable to send reset request. Please try again." };
  }
}

export async function validatePasswordResetToken(token: string): Promise<PasswordResetValidateResponse> {
  try {
    const response = await globalThis.fetch(apiUrl(`/auth/reset-password/${token}`), {
      method: "GET",
      credentials: "include",
    });
    const payload = (await safeParseJson(response)) as { valid?: boolean; reason?: string };
    return {
      valid: Boolean(payload.valid),
      reason: typeof payload.reason === "string" ? payload.reason : undefined,
    };
  } catch (error) {
    warnNetworkOnce("validate-reset-token", "Reset token validation", error);
    return { valid: false, reason: "error" };
  }
}

export async function resetPassword(
  token: string,
  password: string,
  confirmPassword: string,
): Promise<PasswordResetSubmitResponse> {
  try {
    const response = await fetch(apiUrl(`/auth/reset-password/${token}`), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password, confirm_password: confirmPassword }),
    });
    const payload = (await safeParseJson(response)) as { success?: boolean; message?: string; error?: string };
    return {
      success: Boolean(payload.success),
      message: typeof payload.message === "string" ? payload.message : undefined,
      error: typeof payload.error === "string" ? payload.error : undefined,
    };
  } catch (error) {
    warnNetworkOnce("reset-password", "Reset password", error);
    return { success: false, error: "Unable to reset password. Please try again." };
  }
}

// ─── Team Invite API ──────────────────────────────────────────────────────────

export type TeamMemberRole = "owner" | "partner" | "member";
export type TeamMemberStatus = "active" | "invited" | "suspended";

export interface TeamMember {
  user_id: number;
  email: string;
  role: TeamMemberRole;
  status: TeamMemberStatus;
  joined_at: string | null;
  invited_at: string | null;
}

export interface TeamMembersResponse {
  success: boolean;
  firm_id?: number;
  members?: TeamMember[];
  error?: string;
}

export interface TeamInviteResponse {
  success: boolean;
  message?: string;
  /** Only present in dev/test mode — shows token in UI for manual testing */
  invite_token?: string;
  invite_url?: string;
  error?: string;
  code?: string;
}

export interface TeamAcceptResponse {
  success: boolean;
  message?: string;
  error?: string;
}

export async function getTeamMembers(): Promise<TeamMembersResponse> {
  try {
    const response = await fetch(`${API_BASE}/team/members`, {
      method: "GET",
      credentials: "include",
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to load team members.",
      };
    }
    return {
      success: true,
      firm_id: typeof payload.firm_id === "number" ? payload.firm_id : undefined,
      members: Array.isArray(payload.members) ? (payload.members as TeamMember[]) : [],
    };
  } catch (error) {
    console.error("[authService] Team members fetch failed:", error);
    return { success: false, error: "Unable to load team members." };
  }
}

export async function inviteTeamMember(
  email: string,
  role: "partner" | "member",
): Promise<TeamInviteResponse> {
  try {
    const response = await fetch(`${API_BASE}/team/invite`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ email, role }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to send invitation.",
        code: typeof payload.code === "string" ? payload.code : undefined,
      };
    }
    return {
      success: true,
      message: typeof payload.message === "string" ? payload.message : "Invitation sent.",
      invite_token:
        typeof payload.invite_token === "string" ? payload.invite_token : undefined,
      invite_url:
        typeof payload.invite_url === "string" ? payload.invite_url : undefined,
    };
  } catch (error) {
    console.error("[authService] Team invite failed:", error);
    return { success: false, error: "Unable to send invitation." };
  }
}

export async function acceptTeamInvite(
  token: string,
  password: string,
): Promise<TeamAcceptResponse> {
  try {
    // NOTE: Accept endpoint is public (no session cookie required)
    const response = await globalThis.fetch(`${API_BASE}/team/accept`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to accept invitation.",
      };
    }
    return {
      success: true,
      message: typeof payload.message === "string" ? payload.message : "Invitation accepted.",
    };
  } catch (error) {
    console.error("[authService] Team accept failed:", error);
    return { success: false, error: "Unable to accept invitation." };
  }
}

export async function updateTeamMemberRole(
  userId: number,
  role: TeamMemberRole,
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/team/member/${userId}/role`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ role }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to update role.",
      };
    }
    return { success: true };
  } catch (error) {
    console.error("[authService] Team role update failed:", error);
    return { success: false, error: "Unable to update role." };
  }
}

export async function updateTeamMemberStatus(
  userId: number,
  status: "active" | "suspended",
): Promise<{ success: boolean; error?: string }> {
  try {
    const response = await fetch(`${API_BASE}/team/member/${userId}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ status }),
    });
    const payload = await safeParseJson(response);
    if (!response.ok || payload.success === false) {
      return {
        success: false,
        error:
          (typeof payload.error === "string" ? payload.error : undefined) ||
          "Unable to update member status.",
      };
    }
    return { success: true };
  } catch (error) {
    console.error("[authService] Team status update failed:", error);
    return { success: false, error: "Unable to update member status." };
  }
}
