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


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\nStarting Clarion Agent Office...")
    print(f"Date   : {DATE}")
    print(f"Root   : {BASE_DIR}")

    _ensure_data_files()

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

    # ── STAGE 4: Comms & Content ───────────────────────────────────────────────
    banner("STAGE 4 — Comms & Content (Foundation Mode)")

    comms_inputs = [DATA / "comms/discovered_conversations.md", DATA / "comms/seo_keywords.csv"]
    comms_real, comms_missing = _has_real_input(comms_inputs)
    if comms_real:
        results["content_seo"] = run_division(
            "Content & SEO", "content_seo",
            "agents/comms/content_seo.md",
            "comms", data_content_seo,
            "Clarion Content & SEO Agent",
        )
    else:
        print(f"  [GATE] Content & SEO — skipping (no real input)")
        results["content_seo"] = _write_skip_report(
            "comms", "content_seo", "Content & SEO Agent",
            comms_missing,
            [
                "data/comms/discovered_conversations.md — run conversation discovery first",
                "data/comms/seo_keywords.csv — add real keyword research data",
            ],
        )

    # ── STAGE 5: Revenue — DISABLED (pre-launch) ──────────────────────────────
    banner("STAGE 5 — Revenue (disabled — pre-launch)")
    print("  [SKIP] Head of Growth — disabled until real pipeline reporting begins.")
    results["head_of_growth"] = _write_skip_report(
        "revenue", "head_of_growth", "Head of Growth",
        ["Revenue division disabled for pre-launch cycle"],
        ["Enable when real MRR/ARR reporting from paying customers begins"],
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
    print(f"\n  LLM calls made  : {len(llm_ran) + 1} (divisions: {', '.join(llm_ran) or 'none'} + chief_of_staff)")
    print(f"  Skipped (no data): {len(llm_skip)} ({', '.join(llm_skip) or 'none'})")
    if llm_fail:
        print(f"  Failed          : {', '.join(llm_fail)}")
    print(f"\n  Report written to:")
    print(f"  {latest_path}\n")

    if not cos_path:
        print("\n  [WARN] Chief of Staff did not complete.")
        print( "  The executive_brief_latest.md contains a fallback summary.")


if __name__ == "__main__":
    main()
