"""
run_clarion_agent_office.py
Clarion — Agent Office Runner

MODES
-----
  Lean (default) — revenue-first, skips expensive synthesis stages:
      Prospect Intelligence → Outbound Sales → Content Engine →
      Product Experience → Execute Approved Actions → Summary

  Full  (--full-office) — all stages including Market Intelligence,
      Product Insight, Conversation Discovery, Evidence & Insight,
      and Chief of Staff synthesis.

Usage:
    python run_clarion_agent_office.py            # lean mode (default)
    python run_clarion_agent_office.py --full-office  # full mode
"""

import sys
import io
import argparse
import shutil
import datetime
import traceback
import json
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in LLM output don't crash the runner
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
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
DATE    = datetime.date.today().isoformat()
DIVIDER = "=" * 60

# ── Fail-fast: validate config keys before any LLM call ───────────────────────

# Every agent key used anywhere in this runner must appear here.
_REQUIRED_AGENT_KEYS = [
    "prospect_intelligence_agent",
    "outbound_sales_agent",
    "followup_sales_agent",
    "content_seo",
    "product_experience_agent",
    "prelaunch_content",
    # full-office extras
    "evidence_agent",
    "competitive_intelligence",
    "usage_analyst",
    "customer_discovery",
    "chief_of_staff",
]

def _validate_config() -> list[str]:
    """Return list of missing agent keys. Empty list = all good."""
    config_path = BASE_DIR / "config.json"
    try:
        with open(config_path, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        return [f"[FATAL] Could not load config.json: {e}"]
    registered = set(cfg.get("agents", {}).keys())
    return [k for k in _REQUIRED_AGENT_KEYS if k not in registered]


def banner(msg: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {msg}")
    print(DIVIDER)

# ── Real-input gate ────────────────────────────────────────────────────────────

_PLACEHOLDER_MARKERS = (
    "# AUTO-CREATED PLACEHOLDER",
    "# SEED PLACEHOLDER",
    "no competitors tracked yet",
    "[no ",
)

def _has_real_input(paths: list[Path]) -> tuple[bool, list[str]]:
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
        if len(real_lines) >= 2:
            return True, []
        missing.append(f"{p.relative_to(BASE_DIR)} (empty or placeholder only)")
    return False, missing


def _write_skip_report(subdir: str, agent_key: str, division_label: str,
                        missing: list[str], suggested: list[str]) -> Path:
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
    lines += ["", "Suggested next data to add:"]
    for s in suggested:
        lines.append(f"  - {s}")
    lines += [
        "", "DIVISION SIGNAL",
        "Status: neutral",
        "Key Points:",
        "  - No real input available for this cycle.",
        "Recommended Direction: Add real source data before next run.",
        "",
        "TOKENS USED",
        "0  (LLM call skipped — no real input)",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Data resilience ────────────────────────────────────────────────────────────

def _ensure_data_files() -> None:
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


# ── Agent subdir map ──────────────────────────────────────────────────────────

_AGENT_SUBDIR = {
    "content_seo":                   "comms",
    "competitive_intelligence":      "market",
    "usage_analyst":                 "product_insight",
    "chief_of_staff":                "ceo_brief",
    "customer_discovery":            "market",
    "sales_development":             "revenue",
    "head_of_growth":                "revenue",
    "funnel_conversion":             "revenue",
    "narrative_strategy":            "growth",
    "market_intelligence":           "strategy",
    "launch_readiness":              "strategy",
    "evidence_agent":                "strategy",
    "prospect_intelligence_agent":   "sales",
    "outbound_sales_agent":          "sales",
    "followup_sales_agent":          "sales",
    "product_experience_agent":      "product",
    "prelaunch_content":             "growth",
    "prelaunch_conversion":          "product",
}

def _subdir_for_agent(agent_key: str) -> str:
    return _AGENT_SUBDIR.get(agent_key, agent_key)


# ── Execution layer tracking ──────────────────────────────────────────────────

_EXEC_STATS = {
    "autonomous": [],
    "delegated":  [],
    "queued":     [],
}

def _route_new_artifacts(new_items: list[dict], agent_name: str) -> None:
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
            stat_entry = f"{result.artifact_id} ({result.action_type})"
            if level == 1:
                _EXEC_STATS["autonomous"].append(stat_entry)
            else:
                _EXEC_STATS["delegated"].append(stat_entry)
            try:
                all_items = _qload()
                all_items = [q for q in all_items if q.get("id") != result.artifact_id]
                _qsave(all_items)
            except Exception:
                pass
            print(f"    [EXEC-L{level}] {result.artifact_id} ({result.action_type}): {result.notes}")

        elif result.disposition in ("queued", "fallback_queued"):
            _EXEC_STATS["queued"].append(f"{result.artifact_id} ({result.action_type})")
            print(f"    [QUEUE-L{result.authority_level}] {result.artifact_id} "
                  f"({result.action_type}): {result.notes}")
        else:
            _EXEC_STATS["queued"].append(
                f"{result.artifact_id} ({result.action_type}) [exec-failed]"
            )
            print(f"    [EXEC-FAIL] {result.artifact_id} ({result.action_type}): {result.notes}")


def _snapshot_queue() -> set[str]:
    try:
        return {i.get("id") for i in _load_queue()}
    except Exception:
        return set()


def _new_since_snapshot(before: set[str]) -> list[dict]:
    try:
        return [i for i in _load_queue() if i.get("id") not in before]
    except Exception:
        return []


# ── run_division wrapper ──────────────────────────────────────────────────────

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
        print(f"  [OK] {label} complete -> {path.name}")
        return path
    except Exception as e:
        print(f"  [FAIL] {label} FAILED: {e}")
        traceback.print_exc()
        return None


# ── Data builders ─────────────────────────────────────────────────────────────

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
            ("Competitive Intelligence (latest)", _latest("market", "competitive_intelligence")),
            ("SEO Keyword Data",                  DATA   / "comms/seo_keywords.csv"),
            ("Published Content Log",             DATA   / "comms/content_log.csv"),
            ("Discovered Conversations (latest)", DATA   / "comms/discovered_conversations.md"),
            ("Brand Canon",                       MEMORY / "brand_canon.md"),
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


# ── Approved actions executor ─────────────────────────────────────────────────

def _run_approved_actions() -> int:
    """
    Two-phase execution:
    Phase 1 — approval_queue.json: find 'approved'/'released' items and run them
               through action_executor. This is the primary path for outreach_email,
               linkedin_post, thought_leadership_article, etc.
    Phase 2 — memory/approved_actions.md: legacy file-based approved actions.
    Returns total count executed.
    """
    executed = 0

    # ── Phase 1: queue-based execution ───────────────────────────────────────
    if _EXEC_LAYER_AVAILABLE:
        try:
            from shared.queue_writer import _load as _qload, _save as _qsave
            all_items = _qload()
            approved_items = [
                i for i in all_items
                if i.get("status", "").lower() in ("approved", "released")
            ]
            if approved_items:
                print(f"  Found {len(approved_items)} approved queue item(s) — executing via action_executor.")
            remaining = list(all_items)
            for item in approved_items:
                result = execute_artifact(item, agent_name="stage5_queue_runner")
                if result is None:
                    continue
                if result.disposition == "executed" and result.success:
                    level = result.authority_level
                    stat_entry = f"{result.artifact_id} ({result.action_type})"
                    if level == 1:
                        _EXEC_STATS["autonomous"].append(stat_entry)
                    else:
                        _EXEC_STATS["delegated"].append(stat_entry)
                    # Mark as completed in queue instead of removing
                    for q in remaining:
                        if q.get("id") == result.artifact_id:
                            q["status"] = "completed"
                            q["executed_at"] = datetime.datetime.now().isoformat()
                            q["execution_notes"] = result.notes
                    print(f"    [EXEC-L{result.authority_level}] {result.artifact_id} "
                          f"({result.action_type}): {result.notes[:100]}")
                    executed += 1
                elif result.disposition in ("queued", "fallback_queued"):
                    print(f"    [QUEUE-L{result.authority_level}] {result.artifact_id} "
                          f"({result.action_type}): {result.notes[:100]}")
                else:
                    print(f"    [EXEC-FAIL] {result.artifact_id} ({result.action_type}): "
                          f"{result.notes[:100]}")
            if approved_items:
                _qsave(remaining)
        except Exception as e:
            print(f"  [WARN] Phase 1 queue execution error: {e}")
            traceback.print_exc()
    else:
        print("  [WARN] action_executor not available — skipping queue-based execution.")

    # ── Phase 2: legacy approved_actions.md ──────────────────────────────────
    approved = load_approved_actions()
    if not approved:
        if executed == 0:
            print("  No approved actions found — nothing to execute this cycle.")
            log_no_actions()
        return executed

    print(f"  Found {len(approved)} legacy approved action(s) in approved_actions.md.")
    exec_reports = BASE_DIR / "reports" / "execution"
    exec_reports.mkdir(parents=True, exist_ok=True)

    for action in approved:
        act_id   = action.get("action_id", "UNKNOWN")
        act_text = action.get("action", "")
        owner    = action.get("owner", "")
        notes    = action.get("notes", "")

        print(f"\n  -> {act_id}: {act_text[:70]}...")

        if not is_safe_execution(action):
            reason = "Blocked execution type — must be executed manually."
            print(f"    [BLOCKED] {reason}")
            update_action_status(act_id, "blocked", reason)
            append_execution_log(act_id, act_text, owner, "blocked",
                "Not executed — blocked execution type.",
                "CEO must execute manually.", True)
            continue

        route = route_action(action)
        if not route:
            reason = f"Owner '{owner}' not mapped to a division agent."
            print(f"    [BLOCKED] {reason}")
            update_action_status(act_id, "blocked", reason)
            append_execution_log(act_id, act_text, owner, "blocked",
                "Not executed — owner not routable.",
                "Update Owner to a known division.", False)
            continue

        agent_key, prompt_rel, report_subdir = route

        exec_context = (
            f"## EXECUTION TASK\n\nAction ID: {act_id}\n"
            f"Approved Action: {act_text}\nNotes: {notes}\n\n"
            "You are executing this specific approved action as a bounded internal deliverable.\n"
            "Produce the requested output now. Be concrete and complete.\n"
            "Do not propose — execute. Output the actual deliverable.\n\n"
            "## CONTEXT FROM LATEST DIVISION DATA\n\n"
        )

        latest_dir = BASE_DIR / "reports" / _subdir_for_agent(agent_key)
        latest_reports = sorted(latest_dir.glob("*.md"), reverse=True)[:1] if latest_dir.exists() else []
        for lr in latest_reports:
            exec_context += f"### Latest {agent_key} Report\n"
            exec_context += lr.read_text(encoding="utf-8", errors="replace")[:2000]
            exec_context += "\n\n"

        update_action_status(act_id, "in_progress")
        try:
            out_path = run_agent(
                agent_key=agent_key, prompt_rel_path=prompt_rel,
                report_subdir="execution", data_context=exec_context,
                agent_title=f"Clarion Execution — {act_id}",
            )
            print(f"    [OK] Executed -> {out_path.name}")
            update_action_status(act_id, "completed",
                f"Execution output: reports/execution/{out_path.name}")
            append_execution_log(act_id, act_text, owner, "completed",
                f"Agent produced deliverable: reports/execution/{out_path.name}",
                "CEO reviews output and decides whether to stage, publish, or archive.", True)
            executed += 1
        except Exception as e:
            err_str = str(e)[:120]
            print(f"    [FAIL] Execution FAILED: {err_str}")
            traceback.print_exc()
            update_action_status(act_id, "blocked", f"Execution error: {err_str}")
            append_execution_log(act_id, act_text, owner, "blocked",
                f"LLM execution failed: {err_str}",
                "Check console output. Retry next run or revise action.", False)

    return executed


# ── Lean run summary ──────────────────────────────────────────────────────────

def _print_lean_summary(run_stats: dict) -> None:
    # Count outreach emails actually sent this run
    try:
        from execution.action_executor import _SENT_THIS_RUN
        outreach_sent = len(_SENT_THIS_RUN)
    except Exception:
        outreach_sent = 0

    lines = [
        f"\n{'-' * 60}",
        f"  CLARION AGENT OFFICE -- RUN COMPLETE",
        f"  Mode                     : {run_stats.get('mode', 'lean')}",
        f"  Prospects found          : {run_stats.get('prospects_found', 0)}",
        f"  Outreach drafted         : {run_stats.get('outreach_created', 0)}",
        f"  Outreach actually sent   : {outreach_sent}",
        f"  Follow-ups drafted       : {run_stats.get('followups_drafted', 0)}",
        f"  Content created          : {run_stats.get('content_created', 0)}",
        f"  Product artifacts        : {run_stats.get('product_artifacts_created', 0)}",
        f"  Approved actions executed: {run_stats.get('approved_actions_executed', 0)}",
        f"  New queue items          : {run_stats.get('new_queue_items', 0)}",
        f"  Autonomous executed      : {len(_EXEC_STATS['autonomous'])}",
        f"  Delegated executed       : {len(_EXEC_STATS['delegated'])}",
        f"  Queued for founder       : {len(_EXEC_STATS['queued'])}",
    ]
    if _EXEC_STATS["autonomous"]:
        for item in _EXEC_STATS["autonomous"]:
            lines.append(f"    [AUTO] {item}")
    if _EXEC_STATS["delegated"]:
        for item in _EXEC_STATS["delegated"]:
            lines.append(f"    [DELEGATED] {item}")
    if _EXEC_STATS["queued"]:
        for item in _EXEC_STATS["queued"]:
            lines.append(f"    [QUEUED] {item}")
    lines.append(f"{'-' * 60}\n")
    for line in lines:
        print(line)

    # Write a markdown run summary for easy review
    _write_run_summary(run_stats, outreach_sent)


def _write_run_summary(run_stats: dict, outreach_sent: int) -> None:
    """Write a concise per-run markdown summary to reports/run_summary_latest.md."""
    now_iso  = datetime.datetime.now().isoformat(timespec="seconds")
    summary_path = REPORTS / "run_summary_latest.md"
    archive_path = REPORTS / f"run_summary_{DATE}.md"

    # Collect blocked reasons from queued items
    blocked_lines = []
    for item in _EXEC_STATS["queued"]:
        blocked_lines.append(f"- {item}")

    # Collect sent emails from the dedicated outbound log (not the contaminated email_log.md)
    outbound_log = MEMORY / "outbound_email_log.md"
    sent_lines    = []
    staged_lines  = []
    failed_lines  = []
    if outbound_log.exists():
        for line in outbound_log.read_text(encoding="utf-8", errors="replace").splitlines():
            if DATE not in line:
                continue
            if "STATUS: sent" in line:
                sent_lines.append(f"- {line.strip()}")
            elif "STATUS: staged_no_recipient" in line:
                staged_lines.append(f"- {line.strip()}")
            elif "STATUS: failed" in line:
                failed_lines.append(f"- {line.strip()}")

    lines = [
        f"# Clarion Agent Office — Run Summary",
        f"",
        f"**Date:** {DATE}  ",
        f"**Completed:** {now_iso}  ",
        f"**Mode:** {run_stats.get('mode', 'lean')}",
        f"",
        f"## Outbound",
        f"",
        f"- Prospects found: {run_stats.get('prospects_found', 0)}",
        f"- Outreach drafted this run: {run_stats.get('outreach_created', 0)}",
        f"- Outreach actually sent: {outreach_sent}",
        f"",
    ]
    if sent_lines:
        lines.append("**Sent this run:**")
        lines.extend(sent_lines)
        lines.append("")
    else:
        lines.append("_Sent: 0 (no emails sent via Zoho this run)._")
        lines.append("")
    if staged_lines:
        lines.append("**Staged - no recipient found (email discovery returned empty):**")
        lines.extend(staged_lines)
        lines.append("")
    if failed_lines:
        lines.append("**Failed sends (SMTP error - check outbound_email_log.md):**")
        lines.extend(failed_lines)
        lines.append("")

    lines += [
        f"## Content",
        f"",
        f"- Content artifacts created: {run_stats.get('content_created', 0)}",
        f"- Product artifacts: {run_stats.get('product_artifacts_created', 0)}",
        f"- Published to data/publish_ready/: {len(_EXEC_STATS['autonomous'])} item(s)",
        f"",
        f"## Execution",
        f"",
        f"- Autonomous (Level 1): {len(_EXEC_STATS['autonomous'])}",
        f"- Delegated (Level 2): {len(_EXEC_STATS['delegated'])}",
        f"- Queued for founder (Level 3): {len(_EXEC_STATS['queued'])}",
        f"- Approved actions run (Stage 5): {run_stats.get('approved_actions_executed', 0)}",
        f"",
    ]
    if blocked_lines:
        lines.append("## Blocked / Queued (requires founder approval or credentials)")
        lines.append("")
        lines.extend(blocked_lines)
        lines.append("")

    lines += [
        f"## Log Locations",
        f"",
        f"- Execution log: `data/autonomous_execution_log.md`",
        f"- Outbound email log: `memory/outbound_email_log.md`",
        f"- Publish-ready content: `data/publish_ready/`",
        f"- Staged outreach (no recipient): `data/executed_outputs/`",
    ]

    content = "\n".join(lines) + "\n"
    summary_path.write_text(content, encoding="utf-8")
    archive_path.write_text(content, encoding="utf-8")
    print(f"  [SUMMARY] Run summary written -> reports/run_summary_latest.md")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Clarion Agent Office Runner")
    parser.add_argument("--full-office", action="store_true",
                        help="Run all stages including synthesis (slower, more expensive)")
    args = parser.parse_args()
    full_mode = args.full_office
    mode_label = "full" if full_mode else "lean"

    print(f"\nStarting Clarion Agent Office [{mode_label} mode]...")
    print(f"Date   : {DATE}")
    print(f"Root   : {BASE_DIR}")

    # ── FAIL-FAST: Validate config before any LLM call ────────────────────────
    banner("CONFIG VALIDATION")
    missing_keys = _validate_config()
    if missing_keys:
        print(f"\n  BLOCKED -- missing agent keys in config.json:")
        for k in missing_keys:
            print(f"     - {k}")
        print(f"\n  Add these keys to Clarion-Agency/config.json to proceed.")
        print(f"  No LLM calls were made. Exiting.\n")
        sys.exit(1)
    print(f"  [OK] All required agent keys present in config.json")

    _ensure_data_files()

    try:
        _queue_depth_at_start = len(_load_queue())
    except Exception:
        _queue_depth_at_start = 0

    # ── Run stats collector ───────────────────────────────────────────────────
    run_stats = {
        "mode": mode_label,
        "prospects_found": 0,
        "outreach_created": 0,
        "content_created": 0,
        "product_artifacts_created": 0,
        "approved_actions_executed": 0,
        "new_queue_items": 0,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # FULL-OFFICE STAGES (skipped in lean mode)
    # ─────────────────────────────────────────────────────────────────────────
    results = {}
    _stall_note_for_brief = ""

    if full_mode:
        # Stage 1: Market Intelligence
        banner("STAGE 1 — Market Intelligence")
        cd_inputs = [DATA / "market/discovery_interviews.md",
                     DATA / "market/voc_signals.csv",
                     DATA / "market/icp_snapshot.md"]
        cd_real, cd_missing = _has_real_input(cd_inputs)
        if cd_real:
            results["customer_discovery"] = run_division(
                "Customer Discovery", "customer_discovery",
                "agents/market/customer_discovery.md", "market",
                lambda: "\n".join([
                    f"### {label}\n{_load_file(DATA / path, label)}\n"
                    for label, path in [
                        ("Discovery Interview Notes", "market/discovery_interviews.md"),
                        ("VoC Raw Signals",           "market/voc_signals.csv"),
                        ("ICP Snapshot",              "market/icp_snapshot.md"),
                    ]]),
                "Clarion Customer Discovery Agent",
            )
        else:
            print(f"  [GATE] Customer Discovery — skipping (no real input)")
            results["customer_discovery"] = _write_skip_report(
                "market", "customer_discovery", "Customer Discovery Agent", cd_missing,
                ["data/market/discovery_interviews.md", "data/market/voc_signals.csv",
                 "data/market/icp_snapshot.md"],
            )

        ci_inputs = [DATA / "market/competitors.md", DATA / "market/competitor_pricing.md"]
        ci_real, ci_missing = _has_real_input(ci_inputs)
        if ci_real:
            results["competitive_intelligence"] = run_division(
                "Competitive Intelligence", "competitive_intelligence",
                "agents/market/competitive_intelligence.md", "market",
                data_competitive_intelligence, "Clarion Competitive Intelligence Agent",
            )
        else:
            print(f"  [GATE] Competitive Intelligence — skipping (no real input)")
            results["competitive_intelligence"] = _write_skip_report(
                "market", "competitive_intelligence", "Competitive Intelligence Agent",
                ci_missing, ["data/market/competitors.md — populate with real competitor entries"],
            )

        # Stage 2: Product Insight
        banner("STAGE 2 — Product Insight")
        pi_inputs = [DATA / "product/feature_usage.csv", DATA / "product/session_log.csv",
                     DATA / "customer/account_roster.csv"]
        pi_real, pi_missing = _has_real_input(pi_inputs)
        if pi_real:
            results["usage_analyst"] = run_division(
                "Usage Analyst", "usage_analyst",
                "agents/product_insight/usage_analyst.md", "product_insight",
                data_usage_analyst, "Clarion Product Usage Analyst Agent",
            )
        else:
            print(f"  [GATE] Usage Analyst — skipping (no real input)")
            results["usage_analyst"] = _write_skip_report(
                "product_insight", "usage_analyst", "Product Usage Analyst", pi_missing,
                ["data/product/feature_usage.csv", "data/product/session_log.csv",
                 "data/customer/account_roster.csv"],
            )

        # Stage 3: Conversation Discovery
        banner("STAGE 3 — Conversation Discovery")
        try:
            from shared.conversation_discovery import run as run_conversation_discovery
            discovery_path = run_conversation_discovery()
            print(f"  [OK] Conversation discovery complete -> {discovery_path.name}")
        except Exception as e:
            print(f"  [FAIL] Conversation discovery FAILED: {e}")
            traceback.print_exc()

        # Stage 3.5: Evidence & Insight
        banner("STAGE 3.5 — Evidence & Insight")
        (REPORTS / "strategy").mkdir(parents=True, exist_ok=True)
        _q_before_evidence = _snapshot_queue()
        try:
            from agents.strategy.evidence_agent import run as run_evidence
            ev_result = run_evidence()
            results["evidence_agent"] = ev_result.get("report_path")
            if not ev_result.get("enforcement_passed"):
                print(f"  [WARN] Evidence enforcement FAILED: {ev_result.get('enforcement_reason')}")
            else:
                print(f"  [OK] Evidence - {ev_result.get('artifacts_queued')} artifact(s) queued")
        except Exception as e:
            print(f"  [FAIL] Evidence Agent FAILED: {e}")
            traceback.print_exc()
            results["evidence_agent"] = None
        _route_new_artifacts(_new_since_snapshot(_q_before_evidence), "evidence_agent")


    # ─────────────────────────────────────────────────────────────────────────
    # LEAN STAGES (always run — in both lean and full mode)
    # ─────────────────────────────────────────────────────────────────────────

    # Stage 4a: Prospect Intelligence
    banner("STAGE 4a — Prospect Intelligence")
    (REPORTS / "sales").mkdir(parents=True, exist_ok=True)
    pi_result = None
    _q_before_pi = _snapshot_queue()
    try:
        from agents.sales.prospect_intelligence_agent import run as run_prospect_intel
        pi_result = run_prospect_intel()
        results["prospect_intelligence_agent"] = pi_result.get("report_path")
        run_stats["prospects_found"] = pi_result.get("prospect_count", 0)
        if not pi_result.get("enforcement_passed"):
            print(f"  [WARN] Prospect Intelligence enforcement FAILED: "
                  f"{pi_result.get('enforcement_reason')}")
        else:
            print(f"  [OK] Prospect Intelligence -- {pi_result.get('prospect_count')} prospects queued "
                  f"({pi_result.get('item_id')})")
    except Exception as e:
        print(f"  [FAIL] Prospect Intelligence FAILED: {e}")
        traceback.print_exc()
        results["prospect_intelligence_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_pi), "prospect_intelligence_agent")

    # Stage 4b: Outbound Sales
    banner("STAGE 4b — Outbound Sales (Email Drafting)")
    os_result = None
    _q_before_sales = _snapshot_queue()
    try:
        from agents.sales.outbound_sales_agent import run as run_outbound_sales
        os_result = run_outbound_sales(pi_result=pi_result)
        results["outbound_sales_agent"] = os_result.get("report_path")
        run_stats["outreach_created"] = os_result.get("artifacts_queued", 0)
        if not os_result.get("enforcement_passed"):
            print(f"  [WARN] Outbound Sales enforcement FAILED: "
                  f"{os_result.get('enforcement_reason')}")
        else:
            print(f"  [OK] Outbound Sales -- {os_result.get('artifacts_queued')} outreach email(s) queued")
    except Exception as e:
        print(f"  [FAIL] Outbound Sales FAILED: {e}")
        traceback.print_exc()
        results["outbound_sales_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_sales), "outbound_sales_agent")

    # Stage 4c: Content Engine (Content SEO)
    banner("STAGE 4c — Content Engine")
    (REPORTS / "comms").mkdir(parents=True, exist_ok=True)
    _q_before_content = _snapshot_queue()
    try:
        from agents.comms.content_seo_agent import run as run_content_seo
        cs_result = run_content_seo()
        results["content_seo"] = cs_result.get("report_path")
        run_stats["content_created"] = cs_result.get("content_artifacts_queued", 0)
        if not cs_result.get("enforcement_passed"):
            print(f"  [WARN] Content SEO enforcement FAILED: {cs_result.get('enforcement_reason')}")
        else:
            types_str = ", ".join(cs_result.get("artifact_types", []))
            print(f"  [OK] Content SEO -- {cs_result.get('total_artifacts_queued')} artifact(s) "
                  f"queued ({types_str})")
    except Exception as e:
        print(f"  [FAIL] Content SEO FAILED: {e}")
        traceback.print_exc()
        results["content_seo"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_content), "content_seo")

    # Stage 4d: Pre-Launch Content
    banner("STAGE 4d — Pre-Launch Content")
    (REPORTS / "growth").mkdir(parents=True, exist_ok=True)
    (DATA / "growth").mkdir(parents=True, exist_ok=True)
    _q_before_growth = _snapshot_queue()
    plc_report_path = run_division(
        "Pre-Launch Content", "prelaunch_content",
        "agents/growth/prelaunch_content.md", "growth",
        data_prelaunch_content, "Clarion Pre-Launch Content Agent",
    )
    results["prelaunch_content"] = plc_report_path
    if plc_report_path and plc_report_path.exists():
        from shared.report_parser import parse_and_queue as _paq
        _plc_text = plc_report_path.read_text(encoding="utf-8", errors="replace")
        _plc_ids = _paq(_plc_text, default_agent="Pre-Launch Content Agent",
                        allowed_types={"linkedin_post", "thought_leadership_article", "founder_thread"})
        if _plc_ids:
            run_stats["content_created"] = run_stats.get("content_created", 0) + len(_plc_ids)
            print(f"  [OK] Pre-Launch Content -- {len(_plc_ids)} artifact(s) queued: {', '.join(_plc_ids)}")
        else:
            print("  [WARN] Pre-Launch Content -- 0 QUEUE_JSON blocks found. Report is narrative-only.")
    _route_new_artifacts(_new_since_snapshot(_q_before_growth), "prelaunch_content")

    # Stage 4e: Product Experience
    banner("STAGE 4e — Product Experience (Conversion Optimization)")
    (REPORTS / "product").mkdir(parents=True, exist_ok=True)
    _q_before_product = _snapshot_queue()
    try:
        from agents.product.product_experience_agent import run as run_product_experience
        pe_result = run_product_experience()
        results["product_experience_agent"] = pe_result.get("report_path")
        run_stats["product_artifacts_created"] = pe_result.get("artifacts_queued", 0)
        if not pe_result.get("enforcement_passed"):
            print(f"  [WARN] Product Experience enforcement FAILED: "
                  f"{pe_result.get('enforcement_reason')}")
        else:
            types_str = ", ".join(pe_result.get("artifact_types", []))
            print(f"  [OK] Product Experience -- {pe_result.get('artifacts_queued')} artifact(s) "
                  f"queued ({types_str})")
    except Exception as e:
        print(f"  [FAIL] Product Experience FAILED: {e}")
        traceback.print_exc()
        results["product_experience_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_product), "product_experience_agent")

    # Stage 4f: Queue output enforcement check
    banner("STAGE 4f — Queue Output Check")
    try:
        _queue_items_now = len(_load_queue())
    except Exception:
        _queue_items_now = _queue_depth_at_start
    new_items_this_run = _queue_items_now - _queue_depth_at_start
    run_stats["new_queue_items"] = new_items_this_run

    if new_items_this_run == 0:
        print("  [ACTIVATION STALLED] Zero new approval queue items produced this run.")
        _stall_note_for_brief = (
            f"\n\n## RUNNER ENFORCEMENT — ACTIVATION STALLED\n\n"
            f"**Zero new approval queue items were produced during this run ({DATE}).**\n\n"
            "All active agents are required to queue at least one item per run.\n"
            "**Action required:** Review agent reports above for blocking conditions.\n"
        )
    else:
        print(f"  [OK] {new_items_this_run} new approval queue item(s) produced this run.")

    # Stage 5: Execute Approved Actions
    banner("STAGE 5 — Execute Approved Actions")
    run_stats["approved_actions_executed"] = _run_approved_actions()

    # Stage 6: Follow-Up Scan + Generation
    banner("STAGE 6 — Follow-Up Scan (7-day pipeline check)")
    fu_result = None
    _q_before_followup = _snapshot_queue()
    try:
        from agents.sales.followup_sales_agent import run as run_followup
        fu_result = run_followup()
        results["followup_sales_agent"] = fu_result.get("report_path")
        run_stats["followups_drafted"] = fu_result.get("drafts_queued", 0)
        if fu_result.get("candidates_found", 0) == 0:
            print("  [FollowUp] No firms due for follow-up this run.")
        elif not fu_result.get("enforcement_passed"):
            print(f"  [WARN] Follow-Up enforcement FAILED: "
                  f"{fu_result.get('enforcement_reason')}")
        else:
            print(f"  [OK] Follow-Up — "
                  f"{fu_result.get('candidates_found')} candidate(s), "
                  f"{fu_result.get('drafts_queued')} draft(s) queued")
    except Exception as e:
        print(f"  [FAIL] Follow-Up Sales FAILED: {e}")
        traceback.print_exc()
        results["followup_sales_agent"] = None
    _route_new_artifacts(_new_since_snapshot(_q_before_followup), "followup_sales_agent")


    # ─────────────────────────────────────────────────────────────────────────
    # FULL-OFFICE ONLY: Chief of Staff synthesis
    # ─────────────────────────────────────────────────────────────────────────
    cos_path = None
    if full_mode:
        banner("STAGE 6 — Executive Synthesis (Chief of Staff)")
        print("  Building executive brief...")
        try:
            from workflows.chief_of_staff_runner import build_data_context as cos_data_context
            cos_path = run_agent(
                agent_key       = "chief_of_staff",
                prompt_rel_path = "agents/executive/chief_of_staff.md",
                report_subdir   = "ceo_brief",
                data_context    = cos_data_context(),
                agent_title     = "Clarion Chief of Staff",
            )
            print(f"  [OK] Executive brief -> {cos_path.name}")
        except Exception as e:
            print(f"  [FAIL] Chief of Staff FAILED: {e}")
            traceback.print_exc()

        # Write executive_brief_latest.md
        banner("STAGE 7 — Writing executive_brief_latest.md")
        latest_path = REPORTS / "executive_brief_latest.md"
        if cos_path and cos_path.exists():
            shutil.copy2(cos_path, latest_path)
            if _stall_note_for_brief:
                with open(latest_path, "a", encoding="utf-8") as f:
                    f.write(_stall_note_for_brief)
                with open(cos_path, "a", encoding="utf-8") as f:
                    f.write(_stall_note_for_brief)
            print(f"  [OK] Copied to: {latest_path}")
        else:
            fallback = (
                f"# Clarion Executive Brief — {DATE}\n\n"
                "**Chief of Staff did not complete this cycle.**\n\n"
                "## Division Reports Filed This Run\n"
            )
            for name, path in results.items():
                if path and hasattr(path, "name"):
                    fallback += f"- {name}: OK {path.name}\n"
                elif path:
                    fallback += f"- {name}: OK (report path)\n"
                else:
                    fallback += f"- {name}: FAIL Not produced\n"
            latest_path.write_text(fallback, encoding="utf-8")
            print(f"  Fallback brief written to: {latest_path}")

        # Update office_health_log
        banner("STAGE 8 — Updating office_health_log.md")
        try:
            import re as _re
            health_log = MEMORY / "office_health_log.md"
            now_iso = datetime.datetime.now().isoformat(timespec="seconds")
            llm_count = sum(1 for v in results.values() if v) + (1 if cos_path else 0)
            log_text = health_log.read_text(encoding="utf-8")
            log_text = _re.sub(r"last_trigger_check:\s+\S+",
                               f"last_trigger_check:  {now_iso}", log_text)
            log_text = _re.sub(r"daily_llm_count:\s+\d+",
                               f"daily_llm_count:     {llm_count}", log_text)
            health_log.write_text(log_text, encoding="utf-8")
            print(f"  [OK] office_health_log.md updated - last_trigger_check: {now_iso}")
        except Exception as e:
            print(f"  [WARN] Could not update office_health_log.md: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # FINAL SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    _print_lean_summary(run_stats)


if __name__ == "__main__":
    main()
