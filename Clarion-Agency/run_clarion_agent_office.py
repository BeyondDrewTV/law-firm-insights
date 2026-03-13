"""
run_clarion_agent_office.py
Clarion — Weekly Agent Office Runner

Runs all active divisions and produces the executive brief.
For daily cadence agents (competitive_intelligence, content_seo),
use run_daily.bat instead — those fire every day, not here.

Double-click run_clarion_agent_office.bat on Fridays, or run directly:

    cd C:\\Users\\beyon\\OneDrive\\Desktop\\CLARION\\law-firm-insights-main\\Clarion-Agency
    python run_clarion_agent_office.py

Output:
    reports\\executive_brief_latest.md   (always overwritten with latest)
    reports\\ceo_brief\\chief_of_staff_YYYY-MM-DD.md  (timestamped archive)

Active divisions (real inputs present):
    Market Intelligence  — competitive_intelligence
    Product Insight      — usage_analyst
    Comms & Content      — content_seo  (Foundation Mode — no external posting)
    Executive            — chief_of_staff  (synthesizes active divisions only)

Gated (skip until real inputs exist):
    Market Intelligence  — customer_discovery  (needs discovery_interviews.md, voc_signals.csv, icp_snapshot.md)
    Revenue              — head_of_growth      (disabled for pre-launch; enable when real pipeline reporting begins)
    Customer, Operations, People, Product Integrity — not wired

Real-input gate rule:
    _has_real_input(files) returns True only when at least one listed file
    exists AND contains more than a header/placeholder line.
    Gated divisions write a structured skip-report so the Chief of Staff
    still sees a DIVISION SIGNAL without an LLM call.
"""

import sys
import shutil
import datetime
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.conversation_discovery import run as run_conversation_discovery
from workflows.chief_of_staff_runner import build_data_context as cos_data_context
from shared.approved_actions_reader import (
    load_approved_actions, route_action, is_safe_execution,
    update_action_status, append_execution_log, log_no_actions,
)
from shared.queue_writer import _load as _load_queue, queue_item as _queue_item

# ── Autonomous Execution Layer ─────────────────────────────────────────────────
try:
    from execution.action_executor import execute_artifact, classify_authority
    _EXEC_LAYER_AVAILABLE = True
except ImportError as _exec_import_err:
    _EXEC_LAYER_AVAILABLE = False
    print(f"  [WARN] execution.action_executor not available: {_exec_import_err}")
    def execute_artifact(artifact, agent_name="unknown"):  # noqa: F811
        return None
    def classify_authority(artifact):  # noqa: F811
        return 3

REPORTS = BASE_DIR / "reports"
DATA    = BASE_DIR / "data"
MEMORY  = BASE_DIR / "memory"

DATE = datetime.date.today().isoformat()

DIVIDER = "=" * 60

def banner(msg: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {msg}")
    print(DIVIDER)


# ── Real-input gate ────────────────────────────────────────────────────────────

# Lines that indicate a file is a placeholder with no real data.
_PLACEHOLDER_MARKERS = (
    "# AUTO-CREATED PLACEHOLDER",
    "# SEED PLACEHOLDER",
    "no competitors tracked yet",
    "[no ",
)

def _has_real_input(paths: list[Path]) -> tuple[bool, list[str]]:
    """
    Returns (True, []) if at least one path contains real non-placeholder data.
    Returns (False, [missing_descriptions]) otherwise.
    A file is considered real if it exists and has at least 2 non-empty,
    non-comment, non-placeholder lines beyond the header.
    """
    missing = []
    for p in paths:
        if not p.exists():
            missing.append(f"{p.relative_to(BASE_DIR)} (file not found)")
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        real_lines = [
            l for l in lines
            if l.strip()
            and not l.strip().startswith("#")
            and not any(m in l.lower() for m in _PLACEHOLDER_MARKERS)
        ]
        # Header counts as 1; need at least 1 data row beyond it
        if len(real_lines) >= 2:
            return True, []
        missing.append(f"{p.relative_to(BASE_DIR)} (empty or placeholder only)")
    return False, missing


def _write_skip_report(subdir: str, agent_key: str, division_label: str,
                        missing: list[str], suggested: list[str]) -> Path:
    """
    Write a structured skip-report so the Chief of Staff sees a DIVISION SIGNAL
    without an LLM call being made.
    """
    report_dir = REPORTS / subdir
    report_dir.mkdir(parents=True, exist_ok=True)
    path = report_dir / f"{agent_key}_{DATE}.md"
    lines = [
        f"AGENT:    {division_label}",
        f"DATE:     {DATE}",
        f"STATUS:   NORMAL",
        f"",
        f"NO REAL INPUT AVAILABLE",
        f"",
        f"Missing inputs:",
    ]
    for m in missing:
        lines.append(f"  - {m}")
    lines += [
        f"",
        f"Suggested next data to add:",
    ]
    for s in suggested:
        lines.append(f"  - {s}")
    lines += [
        f"",
        f"DIVISION SIGNAL",
        f"Status: neutral",
        f"Key Points:",
        f"  - No real input available for this cycle.",
        f"Recommended Direction: Add real source data before next run.",
        f"",
        f"TOKENS USED",
        f"0  (LLM call skipped — no real input)",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Data resilience ────────────────────────────────────────────────────────────

def _ensure_data_files() -> None:
    """Auto-create required data files if missing. Never overwrites existing content."""
    required = [
        (
            DATA / "market" / "competitors.md",
            "# competitors.md\n# Clarion — Competitor Tracking Reference\n"
            "# AUTO-CREATED PLACEHOLDER — populate with competitor data\n\n"
            "## Tracked Competitors\n\n[No competitors tracked yet.]\n",
        ),
        (
            DATA / "comms" / "seo_keywords.csv",
            "keyword,search_volume_monthly,difficulty_score,current_rank,target_url,opportunity_score\n"
            "# AUTO-CREATED PLACEHOLDER — populate with keyword data\n",
        ),
        (
            DATA / "revenue" / "pipeline_snapshot.csv",
            "deal_id,firm_name_anonymized,firm_size_attorneys,practice_area,geography,"
            "plan_tier,deal_value_mrr,stage,days_in_stage,last_activity_date,assigned_rep\n"
            "# AUTO-CREATED PLACEHOLDER — populate with pipeline data\n",
        ),
        (
            DATA / "reviews" / "google_reviews_seed.csv",
            "review_text,rating,owner_response\n"
            "# SEED PLACEHOLDER — see data/reviews/google_reviews_seed.csv for full dataset\n",
        ),
    ]
    for path, placeholder in required:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(placeholder, encoding="utf-8")
            print(f"  [DATA] Created placeholder: {path.relative_to(BASE_DIR)}")


# ── Execution helper ──────────────────────────────────────────────────────────

_AGENT_SUBDIR = {
    "content_seo":             "comms",
    "competitive_intelligence":"market",
    "usage_analyst":           "product_insight",
    "chief_of_staff":          "ceo_brief",
    "customer_discovery":      "market",
    "sales_development":       "revenue",
    "head_of_growth":          "revenue",
    "funnel_conversion":       "revenue",
    "narrative_strategy":      "growth",
    "market_intelligence":     "strategy",
    "launch_readiness":        "strategy",
    "evidence_agent":                "strategy",
    "content_seo_agent":             "comms",
    "product_experience_agent":      "product",
    "outbound_sales":                "sales",
    "outbound_sales_agent":          "sales",
    "prelaunch_content":             "growth",
    "prelaunch_conversion":          "product",
    "prospect_intelligence_agent":   "sales",
}

def _subdir_for_agent(agent_key: str) -> str:
    return _AGENT_SUBDIR.get(agent_key, agent_key)


# ── Delegated Execution Router ─────────────────────────────────────────────────
# Tracks execution stats across the full run for the end-of-run report.
_EXEC_STATS = {
    "autonomous":  [],   # level 1 executed
    "delegated":   [],   # level 2 executed
    "queued":      [],   # sent to founder approval queue
}

def _route_new_artifacts(new_items: list[dict], agent_name: str) -> None:
    """
    Route each new queue item through the authority model.
    Level 1 → execute immediately (no queue write).
    Level 2 + DLA approved → execute (no queue write).
    Level 2 + no DLA / Level 3 → write to approval queue.

    new_items: list of artifact dicts (already written to queue.json by the agent).
    This function may REMOVE level-1/approved-level-2 items from the queue after
    executing them so the founder doesn't see items that were auto-handled.
    """
    if not _EXEC_LAYER_AVAILABLE:
        _EXEC_STATS["queued"].extend([i.get("id", "?") for i in new_items])
        return

    from shared.queue_writer import _load as _qload, _save as _qsave

    for item in new_items:
        result = execute_artifact(item, agent_name=agent_name)
        if result is None:
            _EXEC_STATS["queued"].append(item.get("id", "?"))
            continue

        if result.disposition == "executed" and result.success:
            level = result.authority_level
            if level == 1:
                _EXEC_STATS["autonomous"].append(
                    f"{result.artifact_id} ({result.action_type})"
                )
            else:
                _EXEC_STATS["delegated"].append(
                    f"{result.artifact_id} ({result.action_type})"
                )
            # Remove from queue — was auto-executed, no founder review needed
            try:
                all_items = _qload()
                all_items = [q for q in all_items if q.get("id") != result.artifact_id]
                _qsave(all_items)
            except Exception:
                pass
            print(f"    [EXEC-L{level}] {result.artifact_id} ({result.action_type}): {result.notes}")

        elif result.disposition in ("queued", "fallback_queued"):
            _EXEC_STATS["queued"].append(
                f"{result.artifact_id} ({result.action_type})"
            )
            level_label = f"L{result.authority_level}"
            print(f"    [QUEUE-{level_label}] {result.artifact_id} ({result.action_type}): {result.notes}")

        else:
            # Executed but failed — keep in queue for founder visibility
            _EXEC_STATS["queued"].append(
                f"{result.artifact_id} ({result.action_type}) [exec-failed]"
            )
            print(f"    [EXEC-FAIL] {result.artifact_id} ({result.action_type}): {result.notes}")


def _snapshot_queue() -> set[str]:
    """Return set of current queue item IDs."""
    try:
        return {i.get("id") for i in _load_queue()}
    except Exception:
        return set()


def _new_since_snapshot(before: set[str]) -> list[dict]:
    """Return queue items added since the snapshot."""
    try:
        all_items = _load_queue()
        return [i for i in all_items if i.get("id") not in before]
    except Exception:
        return []


# ── Run wrapper ────────────────────────────────────────────────────────────────

def run_division(label: str, agent_key: str, prompt_rel: str, report_subdir: str,
                 data_fn, agent_title: str) -> Path | None:
    banner(f"Running: {label}")
    try:
        path = run_agent(
            agent_key       = agent_key,
            prompt_rel_path = prompt_rel,
            report_subdir   = report_subdir,
            data_context    = data_fn(),
            agent_title     = agent_title,
        )
        print(f"  ✓ {label} complete → {path.name}")
        return path
    except Exception as e:
        print(f"  ✗ {label} FAILED: {e}")
        traceback.print_exc()
        return None


# ── Data builders (active divisions only) ─────────────────────────────────────

def data_competitive_intelligence():
    return "\n".join([
        f"### {label}\n{_load_file(DATA / path, label)}\n"
        for label, path in [
            ("Competitor Tracking Reference", "market/competitors.md"),
            ("Competitor Pricing Snapshot",   "market/competitor_pricing.md"),
        ]
    ]) + "\n### Live Sources\nAlso check G2, Capterra, and public job boards per your prompt.\n"


def data_usage_analyst():
    return "\n".join([
        f"### {label}\n{_load_file(DATA / path, label)}\n"
        for label, path in [
            ("Feature Usage Log (weekly)",      "product/feature_usage.csv"),
            ("Session Frequency & Depth",        "product/session_log.csv"),
            ("Account Roster (plan + tier)",     "customer/account_roster.csv"),
            ("Feature Adoption Baseline (4wk)",  "product/adoption_baseline.csv"),
        ]
    ])


def data_content_seo():
    def _latest(subdir, prefix):
        d = REPORTS / subdir
        matches = sorted(d.glob(f"{prefix}_*.md"), reverse=True) if d.exists() else []
        return matches[0] if matches else d / f"{prefix}_not_found.md"

    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("Competitive Intelligence Report (latest)", _latest("market", "competitive_intelligence")),
            ("SEO Keyword Data",                         DATA   / "comms/seo_keywords.csv"),
            ("Published Content Log",                    DATA   / "comms/content_log.csv"),
            ("Discovered Conversations (latest)",        DATA   / "comms/discovered_conversations.md"),
            ("Brand Canon",                              MEMORY / "brand_canon.md"),
        ]
    ])


def data_prospect_intelligence():
    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("ICP Definition",            MEMORY / "icp_definition.md"),
            ("Lead Sources",              MEMORY / "lead_sources.md"),
            ("Product Truth",             MEMORY / "product_truth.md"),
            ("Do Not Chase",              MEMORY / "do_not_chase.md"),
            ("Positioning Guardrails",    MEMORY / "positioning_guardrails.md"),
            ("Prelaunch Activation Mode", MEMORY / "prelaunch_activation_mode.md"),
            ("Existing Pipeline",         DATA   / "revenue/leads_pipeline.csv"),
            ("Lead Research Queue",       DATA   / "revenue/lead_research_queue.csv"),
        ]
    ])


def data_outbound_sales():    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("Leads Pipeline",           DATA   / "revenue/leads_pipeline.csv"),
            ("Lead Research Queue",      DATA   / "revenue/lead_research_queue.csv"),
            ("Lead Sources",             MEMORY / "lead_sources.md"),
            ("ICP Definition",           MEMORY / "icp_definition.md"),
            ("Product Truth",            MEMORY / "product_truth.md"),
            ("Sales Outreach Templates", MEMORY / "sales_outreach_templates.md"),
            ("Pilot Offer",              MEMORY / "pilot_offer.md"),
            ("Conversion Friction",      MEMORY / "conversion_friction.md"),
            ("Prelaunch Activation Mode",MEMORY / "prelaunch_activation_mode.md"),
            ("Do Not Chase",             MEMORY / "do_not_chase.md"),
        ]
    ])


def data_prelaunch_content():
    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("Product Narrative",        MEMORY / "product_narrative.md"),
            ("Product Truth",            MEMORY / "product_truth.md"),
            ("Proof Assets",             MEMORY / "proof_assets.md"),
            ("Conversion Friction",      MEMORY / "conversion_friction.md"),
            ("Positioning Guardrails",   MEMORY / "positioning_guardrails.md"),
            ("Brand Voice",              MEMORY / "brand_voice.md"),
            ("Competitor Tracking",      MEMORY / "competitor_tracking.md"),
            ("Content Queue (current)",  DATA   / "growth/content_queue.md"),
            ("Prelaunch Activation Mode",MEMORY / "prelaunch_activation_mode.md"),
        ]
    ])


def data_prelaunch_conversion():
    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("Product Truth",              MEMORY / "product_truth.md"),
            ("Brand QA",                   MEMORY / "brand_qa.md"),
            ("Proof Assets",               MEMORY / "proof_assets.md"),
            ("Conversion Friction",        MEMORY / "conversion_friction.md"),
            ("Positioning Guardrails",     MEMORY / "positioning_guardrails.md"),
            ("Product Experience Log",     MEMORY / "product_experience_log.md"),
            ("Pilot Offer",                MEMORY / "pilot_offer.md"),
            ("Prelaunch Activation Mode",  MEMORY / "prelaunch_activation_mode.md"),
            ("UX Review Access",           MEMORY / "ux_review_access.md"),
            ("Claude Handoff Format",      MEMORY / "claude_handoff_format.md"),
        ]
    ])


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\nStarting Clarion Agent Office...")
    print(f"Date   : {DATE}")
    print(f"Root   : {BASE_DIR}")

    _ensure_data_files()

    # Capture queue depth before any agents run (for ACTIVATION STALLED check)
    try:
        _queue_depth_at_start = len(_load_queue())
    except Exception:
        _queue_depth_at_start = 0

    print(f"\nRunning pre-launch divisions...")

    results = {}

    # ── STAGE 1: Market Intelligence ──────────────────────────────────────────
    banner("STAGE 1 — Market Intelligence")

    # customer_discovery — gate on real inputs
    cd_inputs = [
        DATA / "market/discovery_interviews.md",
        DATA / "market/voc_signals.csv",
        DATA / "market/icp_snapshot.md",
    ]
    cd_real, cd_missing = _has_real_input(cd_inputs)
    if cd_real:
        results["customer_discovery"] = run_division(
            "Customer Discovery", "customer_discovery",
            "agents/market/customer_discovery.md",
            "market", lambda: "\n".join([
                f"### {label}\n{_load_file(DATA / path, label)}\n"
                for label, path in [
                    ("Discovery Interview Notes", "market/discovery_interviews.md"),
                    ("VoC Raw Signals",           "market/voc_signals.csv"),
                    ("ICP Snapshot",              "market/icp_snapshot.md"),
                ]
            ]),
            "Clarion Customer Discovery Agent",
        )
    else:
        print(f"  [GATE] Customer Discovery — skipping (no real input)")
        results["customer_discovery"] = _write_skip_report(
            "market", "customer_discovery", "Customer Discovery Agent",
            cd_missing,
            [
                "data/market/discovery_interviews.md — notes from real prospect calls",
                "data/market/voc_signals.csv — voice-of-customer signals from real users",
                "data/market/icp_snapshot.md — ICP profile from real customer data",
            ],
        )

    # competitive_intelligence — real files confirmed present
    ci_inputs = [DATA / "market/competitors.md", DATA / "market/competitor_pricing.md"]
    ci_real, ci_missing = _has_real_input(ci_inputs)
    if ci_real:
        results["competitive_intelligence"] = run_division(
            "Competitive Intelligence", "competitive_intelligence",
            "agents/market/competitive_intelligence.md",
            "market", data_competitive_intelligence,
            "Clarion Competitive Intelligence Agent",
        )
    else:
        print(f"  [GATE] Competitive Intelligence — skipping (no real input)")
        results["competitive_intelligence"] = _write_skip_report(
            "market", "competitive_intelligence", "Competitive Intelligence Agent",
            ci_missing,
            ["data/market/competitors.md — populate with real competitor entries"],
        )

    # ── STAGE 2: Product Insight ──────────────────────────────────────────────
    banner("STAGE 2 — Product Insight")

    pi_inputs = [
        DATA / "product/feature_usage.csv",
        DATA / "product/session_log.csv",
        DATA / "customer/account_roster.csv",
    ]
    pi_real, pi_missing = _has_real_input(pi_inputs)
    if pi_real:
        results["usage_analyst"] = run_division(
            "Usage Analyst", "usage_analyst",
            "agents/product_insight/usage_analyst.md",
            "product_insight", data_usage_analyst,
            "Clarion Product Usage Analyst Agent",
        )
    else:
        print(f"  [GATE] Usage Analyst — skipping (no real input)")
        results["usage_analyst"] = _write_skip_report(
            "product_insight", "usage_analyst", "Product Usage Analyst",
            pi_missing,
            [
                "data/product/feature_usage.csv — real usage events from production",
                "data/product/session_log.csv — real session data from production",
                "data/customer/account_roster.csv — real account list",
            ],
        )

    # ── STAGE 3: Conversation Discovery ───────────────────────────────────────
    banner("STAGE 3 — Conversation Discovery")
    try:
        discovery_path = run_conversation_discovery()
        print(f"  ✓ Conversation discovery complete → {discovery_path.name}")
    except Exception as e:
        print(f"  ✗ Conversation discovery FAILED: {e}")
        traceback.print_exc()
        print("  [INFO] Comms agent will note data as unavailable — run continues.")

    # ── STAGE 3.5: Evidence & Insight (always runs) ───────────────────────────
    banner("STAGE 3.5 — Evidence & Insight")
    (REPORTS / "strategy").mkdir(parents=True, exist_ok=True)
    _q_before_evidence = _snapshot_queue()
    try:
        from agents.strategy.evidence_agent import run as run_evidence
        ev_result = run_evidence()
        results["evidence_agent"] = ev_result.get("report_path")
        if not ev_result.get("enforcement_passed"):
            print(f"  [WARN] Evidence enforcement FAILED: "
                  f"{ev_result.get('enforcement_reason')}")
        else:
            print(f"  ✓ Evidence — {ev_result.get('artifacts_queued')} artifact(s) queued "
                  f"({', '.join(ev_result.get('artifact_types', []))}) "
                  f"IDs: {', '.join(ev_result.get('artifact_ids', []))}")
    except Exception as e:
        print(f"  ✗ Evidence Agent FAILED: {e}")
        traceback.print_exc()
        results["evidence_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_evidence), "evidence_agent")

    # ── STAGE 4: Comms & Content — Content Engine ────────────────────────────
    banner("STAGE 4 — Comms & Content (Content Engine)")
    (REPORTS / "comms").mkdir(parents=True, exist_ok=True)
    _q_before_content = _snapshot_queue()
    try:
        from agents.comms.content_seo_agent import run as run_content_seo
        cs_result = run_content_seo()
        results["content_seo"] = cs_result.get("report_path")
        if not cs_result.get("enforcement_passed"):
            print(f"  [WARN] Content SEO enforcement FAILED: "
                  f"{cs_result.get('enforcement_reason')}")
        else:
            types_str = ", ".join(cs_result.get("artifact_types", []))
            print(f"  ✓ Content SEO — {cs_result.get('total_artifacts_queued')} artifact(s) "
                  f"queued ({types_str})")
    except Exception as e:
        print(f"  ✗ Content SEO FAILED: {e}")
        traceback.print_exc()
        results["content_seo"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_content), "content_seo_agent")

    # ── STAGE 5: Revenue — DISABLED (pre-launch) ──────────────────────────────
    banner("STAGE 5 — Revenue (disabled — pre-launch)")
    print("  [SKIP] Head of Growth — disabled until real pipeline reporting begins.")
    results["head_of_growth"] = _write_skip_report(
        "revenue", "head_of_growth", "Head of Growth",
        ["Revenue division disabled for pre-launch cycle"],
        ["Enable when real MRR/ARR reporting from paying customers begins"],
    )

    # ── STAGE 4a: Prospect Intelligence (runs before Outbound Sales) ──────────
    banner("STAGE 4a — Prospect Intelligence")
    (REPORTS / "sales").mkdir(parents=True, exist_ok=True)
    pi_result = None
    _q_before_pi = _snapshot_queue()
    try:
        from agents.sales.prospect_intelligence_agent import run as run_prospect_intel
        pi_result = run_prospect_intel()
        results["prospect_intelligence_agent"] = pi_result.get("report_path")
        if not pi_result.get("enforcement_passed"):
            print(f"  [WARN] Prospect Intelligence enforcement FAILED: "
                  f"{pi_result.get('enforcement_reason')}")
        else:
            print(f"  ✓ Prospect Intelligence — {pi_result.get('prospect_count')} prospects queued "
                  f"({pi_result.get('item_id')})")
    except Exception as e:
        print(f"  ✗ Prospect Intelligence FAILED: {e}")
        traceback.print_exc()
        results["prospect_intelligence_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_pi), "prospect_intelligence_agent")

    # ── STAGE 4b: Outbound Sales — email drafting against prospect intel ────────
    banner("STAGE 4b — Outbound Sales (Email Drafting)")
    (REPORTS / "sales").mkdir(parents=True, exist_ok=True)
    os_result = None
    _q_before_sales = _snapshot_queue()
    try:
        from agents.sales.outbound_sales_agent import run as run_outbound_sales
        os_result = run_outbound_sales(pi_result=pi_result)
        results["outbound_sales"] = os_result.get("report_path")
        if not os_result.get("enforcement_passed"):
            print(f"  [WARN] Outbound Sales enforcement FAILED: "
                  f"{os_result.get('enforcement_reason')}")
        else:
            print(f"  ✓ Outbound Sales — {os_result.get('artifacts_queued')} outreach "
                  f"email(s) queued ({', '.join(os_result.get('artifact_ids', []))})")
    except Exception as e:
        print(f"  ✗ Outbound Sales FAILED: {e}")
        traceback.print_exc()
        results["outbound_sales"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_sales), "outbound_sales_agent")

    # ── STAGE 4c: Pre-Launch Content (Pre-Launch Activation — always runs) ────
    banner("STAGE 4c — Pre-Launch Content")
    (REPORTS / "growth").mkdir(parents=True, exist_ok=True)
    (DATA / "growth").mkdir(parents=True, exist_ok=True)
    _q_before_growth = _snapshot_queue()
    results["prelaunch_content"] = run_division(
        "Pre-Launch Content", "prelaunch_content",
        "agents/growth/prelaunch_content.md",
        "growth", data_prelaunch_content,
        "Clarion Pre-Launch Content Agent",
    )
    _route_new_artifacts(_new_since_snapshot(_q_before_growth), "prelaunch_content")

    # ── STAGE 4d: Product Experience / UX ────────────────────────────────────
    banner("STAGE 4d — Product Experience (Conversion Optimization)")
    (REPORTS / "product").mkdir(parents=True, exist_ok=True)
    _q_before_product = _snapshot_queue()
    try:
        from agents.product.product_experience_agent import run as run_product_experience
        pe_result = run_product_experience()
        results["prelaunch_conversion"] = pe_result.get("report_path")
        if not pe_result.get("enforcement_passed"):
            print(f"  [WARN] Product Experience enforcement FAILED: "
                  f"{pe_result.get('enforcement_reason')}")
        else:
            types_str = ", ".join(pe_result.get("artifact_types", []))
            print(f"  ✓ Product Experience — {pe_result.get('artifacts_queued')} artifact(s) "
                  f"queued ({types_str})")
    except Exception as e:
        print(f"  ✗ Product Experience FAILED: {e}")
        traceback.print_exc()
        results["prelaunch_conversion"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_product), "product_experience_agent")

    # ── STAGE 4e: Runner Enforcement — ACTIVATION STALLED check ──────────────
    # Runs after all production agents so the queue count reflects their output.
    banner("STAGE 4e — Runner Enforcement: Queue Output Check")
    _queue_items_at_stage5 = len(_load_queue())
    new_items_this_run = _queue_items_at_stage5 - _queue_depth_at_start
    if new_items_this_run == 0:
        print("  [ACTIVATION STALLED] Zero new approval queue items produced this run.")
        print("  Chief of Staff will flag this run as ACTIVATION STALLED.")
        _stall_note_for_brief = (
            "\n\n## RUNNER ENFORCEMENT — ACTIVATION STALLED\n\n"
            f"**Zero new approval queue items were produced during this run ({DATE}).**\n\n"
            "All active agents (Prospect Intelligence, Outbound Sales, Pre-Launch Content, "
            "Content SEO, Product Experience, Evidence & Insight) are required to queue "
            "at least one item per run. "
            "This run failed the minimum-output requirement.\n\n"
            "**Action required:** Review agent reports above. Identify which agent "
            "produced no queue output and investigate the blocking condition.\n"
        )
    else:
        print(f"  [OK] {new_items_this_run} new approval queue item(s) produced this run.")
        _stall_note_for_brief = ""

    # ── STAGE 5.5: Execute Approved Actions ───────────────────────────────────
    banner("STAGE 5.5 — Execute Approved Actions")
    approved = load_approved_actions()

    if not approved:
        print("  No approved actions found — nothing to execute this cycle.")
        log_no_actions()
    else:
        print(f"  Found {len(approved)} approved action(s).")
        exec_reports = BASE_DIR / "reports" / "execution"
        exec_reports.mkdir(parents=True, exist_ok=True)

        for action in approved:
            act_id   = action.get("action_id", "UNKNOWN")
            act_text = action.get("action", "")
            owner    = action.get("owner", "")
            notes    = action.get("notes", "")

            print(f"\n  → {act_id}: {act_text[:70]}...")

            # Safety gate
            if not is_safe_execution(action):
                reason = "Action contains a blocked execution type (post/publish/send/etc). Must be executed manually."
                print(f"    [BLOCKED] {reason}")
                update_action_status(act_id, "blocked", reason)
                append_execution_log(
                    action_id        = act_id,
                    action_text      = act_text,
                    owner            = owner,
                    status_result    = "blocked",
                    what_was_done    = "Not executed — blocked execution type detected.",
                    next_step        = "CEO must execute manually or revise action to a bounded internal deliverable.",
                    ceo_review_needed= True,
                )
                continue

            # Route to owning division
            route = route_action(action)
            if not route:
                reason = f"Owner '{owner}' is not mapped to a division agent."
                print(f"    [BLOCKED] {reason}")
                update_action_status(act_id, "blocked", reason)
                append_execution_log(
                    action_id        = act_id,
                    action_text      = act_text,
                    owner            = owner,
                    status_result    = "blocked",
                    what_was_done    = "Not executed — owner not routable.",
                    next_step        = "Update Owner field to a known division (see approved_actions_reader.py OWNER_ROUTE).",
                    ceo_review_needed= False,
                )
                continue

            agent_key, prompt_rel, report_subdir = route

            # Build execution prompt — wraps the original agent with the specific action
            exec_context = (
                f"## EXECUTION TASK\n\n"
                f"Action ID: {act_id}\n"
                f"Approved Action: {act_text}\n"
                f"Notes: {notes}\n\n"
                f"You are executing this specific approved action as a bounded internal deliverable.\n"
                f"Produce the requested output now. Be concrete and complete.\n"
                f"Do not propose — execute. Output the actual deliverable.\n\n"
                f"## CONTEXT FROM LATEST DIVISION DATA\n\n"
            )

            # Attach latest relevant report as context
            latest_dir = BASE_DIR / "reports" / report_subdir.replace("execution", _subdir_for_agent(agent_key))
            latest_reports = sorted(latest_dir.glob("*.md"), reverse=True)[:1] if latest_dir.exists() else []
            for lr in latest_reports:
                exec_context += f"### Latest {agent_key} Report\n"
                exec_context += lr.read_text(encoding="utf-8", errors="replace")[:2000]
                exec_context += "\n\n"

            update_action_status(act_id, "in_progress")

            try:
                out_path = run_agent(
                    agent_key       = agent_key,
                    prompt_rel_path = prompt_rel,
                    report_subdir   = "execution",
                    data_context    = exec_context,
                    agent_title     = f"Clarion Execution — {act_id}",
                )
                print(f"    ✓ Executed → {out_path.name}")
                update_action_status(act_id, "completed",
                    f"Execution output: reports/execution/{out_path.name}")
                append_execution_log(
                    action_id        = act_id,
                    action_text      = act_text,
                    owner            = owner,
                    status_result    = "completed",
                    what_was_done    = f"Agent produced deliverable: reports/execution/{out_path.name}",
                    next_step        = "CEO reviews output and decides whether to stage, publish, or archive.",
                    ceo_review_needed= True,
                )
            except Exception as e:
                err_str = str(e)[:120]
                print(f"    ✗ Execution FAILED: {err_str}")
                traceback.print_exc()
                update_action_status(act_id, "blocked", f"Execution error: {err_str}")
                append_execution_log(
                    action_id        = act_id,
                    action_text      = act_text,
                    owner            = owner,
                    status_result    = "blocked",
                    what_was_done    = f"LLM execution failed: {err_str}",
                    next_step        = "Check console output. Retry next run or revise action.",
                    ceo_review_needed= False,
                )

    # ── STAGE 6: Executive Synthesis ──────────────────────────────────────────
    banner("STAGE 6 — Executive Synthesis (Chief of Staff)")
    print("  Building executive brief...")
    cos_path = None
    try:
        cos_path = run_agent(
            agent_key       = "chief_of_staff",
            prompt_rel_path = "agents/executive/chief_of_staff.md",
            report_subdir   = "ceo_brief",
            data_context    = cos_data_context(),
            agent_title     = "Clarion Chief of Staff",
        )
        print(f"  ✓ Executive brief → {cos_path.name}")
    except Exception as e:
        print(f"  ✗ Chief of Staff FAILED: {e}")
        traceback.print_exc()

    # ── STAGE 7: Write executive_brief_latest.md ──────────────────────────────
    banner("STAGE 7 — Writing executive_brief_latest.md")
    latest_path = REPORTS / "executive_brief_latest.md"
    if cos_path and cos_path.exists():
        shutil.copy2(cos_path, latest_path)
        # Append ACTIVATION STALLED notice if triggered
        if _stall_note_for_brief:
            with open(latest_path, "a", encoding="utf-8") as f:
                f.write(_stall_note_for_brief)
            with open(cos_path, "a", encoding="utf-8") as f:
                f.write(_stall_note_for_brief)
        print(f"  ✓ Copied to: {latest_path}")
    else:
        fallback = (
            f"# Clarion Executive Brief — {DATE}\n\n"
            "**No major signals this run.**\n\n"
            "The Chief of Staff agent did not produce a report this cycle.\n"
            "Check the console output above for errors.\n\n"
            "## Division Reports Filed This Run\n"
        )
        for name, path in results.items():
            status = f"✓ {path.name}" if path else "✗ Not produced"
            fallback += f"- {name}: {status}\n"
        latest_path.write_text(fallback, encoding="utf-8")
        print(f"  Fallback brief written to: {latest_path}")

    # ── Summary ───────────────────────────────────────────────────────────────
    banner("RUN COMPLETE")
    llm_ran   = [k for k, v in results.items() if v and "0  (LLM call skipped" not in v.read_text(encoding="utf-8", errors="replace")]
    llm_skip  = [k for k, v in results.items() if v and "0  (LLM call skipped" in v.read_text(encoding="utf-8", errors="replace")]
    llm_fail  = [k for k, v in results.items() if not v]

    print(f"\n  Done.")
    print(f"  New approval queue items this run: {new_items_this_run}")
    if new_items_this_run == 0:
        print(f"  [ACTIVATION STALLED] — See executive_brief_latest.md for details.")
    print(f"\n  LLM calls made  : {len(llm_ran) + 1} (divisions: {', '.join(llm_ran) or 'none'} + chief_of_staff)")
    print(f"  Skipped (no data): {len(llm_skip)} ({', '.join(llm_skip) or 'none'})")
    if llm_fail:
        print(f"  Failed          : {', '.join(llm_fail)}")

    # ── Autonomous Execution Report ───────────────────────────────────────────
    print(f"\n{'─' * 60}")
    print(f"  AUTONOMOUS ACTIONS EXECUTED  ({len(_EXEC_STATS['autonomous'])})")
    for item in _EXEC_STATS["autonomous"]:
        print(f"    ✅ {item}")
    if not _EXEC_STATS["autonomous"]:
        print("    (none this run)")

    print(f"\n  DELEGATED ACTIONS EXECUTED  ({len(_EXEC_STATS['delegated'])})")
    for item in _EXEC_STATS["delegated"]:
        print(f"    🔑 {item}")
    if not _EXEC_STATS["delegated"]:
        print("    (none this run)")

    print(f"\n  QUEUED FOR FOUNDER  ({len(_EXEC_STATS['queued'])})")
    for item in _EXEC_STATS["queued"]:
        print(f"    📋 {item}")
    if not _EXEC_STATS["queued"]:
        print("    (none this run)")
    print(f"{'─' * 60}")

    print(f"\n  Report written to:")
    print(f"  {latest_path}\n")

    if not cos_path:
        print("\n  [WARN] Chief of Staff did not complete.")
        print( "  The executive_brief_latest.md contains a fallback summary.")

    # ── STAGE 8: Update office_health_log.md orchestration state ─────────────
    banner("STAGE 8 — Updating office_health_log.md")
    try:
        health_log = MEMORY / "office_health_log.md"
        now_iso = datetime.datetime.now().isoformat(timespec="seconds")
        llm_count = len(llm_ran) + 1  # +1 for chief_of_staff
        log_text = health_log.read_text(encoding="utf-8")
        log_text = log_text.replace(
            "last_trigger_check:  null",
            f"last_trigger_check:  {now_iso}",
        )
        log_text = log_text.replace(
            f"last_trigger_check:  {now_iso}",
            f"last_trigger_check:  {now_iso}",
        )
        # Update daily_llm_count (simple overwrite of field line)
        import re as _re
        log_text = _re.sub(
            r"daily_llm_count:\s+\d+",
            f"daily_llm_count:     {llm_count}",
            log_text,
        )
        health_log.write_text(log_text, encoding="utf-8")
        print(f"  ✓ office_health_log.md updated — last_trigger_check: {now_iso}")
    except Exception as e:
        print(f"  [WARN] Could not update office_health_log.md: {e}")


if __name__ == "__main__":
    main()
