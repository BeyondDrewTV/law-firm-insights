"""
run_clarion_agent_office.py
Clarion — Pre-Launch Agent Office Runner

Runs the active pre-launch division agents, then synthesizes the executive brief.
Double-click run_clarion_agent_office.bat, or run this directly:

    cd C:\\Users\\beyon\\OneDrive\\Desktop\\CLARION\\law-firm-insights-main\\Clarion-Agency
    python run_clarion_agent_office.py

Output:
    reports\\executive_brief_latest.md   (always overwritten with latest)
    reports\\ceo_brief\\chief_of_staff_YYYY-MM-DD.md  (timestamped archive)

Active pre-launch divisions:
    Market Intelligence  — customer_discovery, competitive_intelligence
    Product Insight      — usage_analyst
    Comms & Content      — content_seo  (Foundation Mode — no external posting)
    Revenue (light)      — head_of_growth
    Executive            — chief_of_staff  (synthesizes all of the above)

Inactive (skipped):
    Customer, Operations, People, Product Integrity
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


# ── Data resilience ────────────────────────────────────────────────────────────
# Auto-create required data files if missing so agents always receive a clear
# signal rather than a crash.  Never overwrites existing content.
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
    ]
    for path, placeholder in required:
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(placeholder, encoding="utf-8")
            print(f"  [DATA] Created placeholder: {path.relative_to(BASE_DIR)}")


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

# ── Data builders ──────────────────────────────────────────────────────────────

def data_customer_discovery():
    return "\n".join([
        f"### {label}\n{_load_file(DATA / path, label)}\n"
        for label, path in [
            ("Discovery Interview Notes", "market/discovery_interviews.md"),
            ("VoC Raw Signals",           "market/voc_signals.csv"),
            ("ICP Snapshot",              "market/icp_snapshot.md"),
        ]
    ])

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
    # content_seo reads the two market reports filed this run (or latest available)
    def _latest(subdir, prefix):
        d = REPORTS / subdir
        matches = sorted(d.glob(f"{prefix}_*.md"), reverse=True) if d.exists() else []
        return matches[0] if matches else d / f"{prefix}_not_found.md"

    return "\n".join([
        f"### {label}\n{_load_file(path, label)}\n"
        for label, path in [
            ("Customer Discovery Report (latest)",       _latest("market", "customer_discovery")),
            ("Competitive Intelligence Report (latest)", _latest("market", "competitive_intelligence")),
            ("SEO Keyword Data",                         DATA   / "comms/seo_keywords.csv"),
            ("Published Content Log",                    DATA   / "comms/content_log.csv"),
            ("Discovered Conversations (latest)",        DATA   / "comms/discovered_conversations.md"),
            ("Brand Canon",                              MEMORY / "brand_canon.md"),
        ]
    ])

def data_head_of_growth():
    return "\n".join([
        f"### {label}\n{_load_file(DATA / path, label)}\n"
        for label, path in [
            ("Pipeline Snapshot",        "revenue/pipeline_snapshot.csv"),
            ("Closed/Lost (30 days)",    "revenue/closed_lost.csv"),
            ("New Activations",          "revenue/activations.csv"),
            ("MRR/ARR Snapshot",         "revenue/mrr_arr.csv"),
        ]
    ])

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"\nStarting Clarion Agent Office...")
    print(f"Date   : {DATE}")
    print(f"Root   : {BASE_DIR}")

    # Ensure all required data files exist before any agent runs
    _ensure_data_files()

    print(f"\nRunning pre-launch divisions...")

    results = {}

    # 1. Market Intelligence
    banner("STAGE 1 — Market Intelligence")
    results["customer_discovery"] = run_division(
        "Customer Discovery", "customer_discovery",
        "agents/market/customer_discovery.md",
        "market", data_customer_discovery,
        "Clarion Customer Discovery Agent",
    )
    results["competitive_intelligence"] = run_division(
        "Competitive Intelligence", "competitive_intelligence",
        "agents/market/competitive_intelligence.md",
        "market", data_competitive_intelligence,
        "Clarion Competitive Intelligence Agent",
    )

    # 2. Product Insight
    banner("STAGE 2 — Product Insight")
    results["usage_analyst"] = run_division(
        "Usage Analyst", "usage_analyst",
        "agents/product_insight/usage_analyst.md",
        "product_insight", data_usage_analyst,
        "Clarion Product Usage Analyst Agent",
    )

    # 3. Conversation Discovery (runs before Comms so the agent has fresh signals)
    banner("STAGE 3 — Conversation Discovery")
    try:
        discovery_path = run_conversation_discovery()
        print(f"  ✓ Conversation discovery complete → {discovery_path.name}")
    except Exception as e:
        print(f"  ✗ Conversation discovery FAILED: {e}")
        traceback.print_exc()
        print("  [INFO] Comms agent will note data as unavailable — run continues.")

    # 4. Comms & Content (Foundation Mode — no external posting)
    banner("STAGE 4 — Comms & Content (Foundation Mode)")
    results["content_seo"] = run_division(
        "Content & SEO", "content_seo",
        "agents/comms/content_seo.md",
        "comms", data_content_seo,
        "Clarion Content & SEO Agent",
    )

    # 5. Revenue (light mode)
    banner("STAGE 5 — Revenue (Light Mode)")
    results["head_of_growth"] = run_division(
        "Head of Growth", "head_of_growth",
        "agents/revenue/head_of_growth.md",
        "revenue", data_head_of_growth,
        "Clarion Head of Growth Agent",
    )

    # 6. Executive synthesis — runs after all divisions
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

    # 7. Write executive_brief_latest.md
    banner("STAGE 7 — Writing executive_brief_latest.md")
    latest_path = REPORTS / "executive_brief_latest.md"
    if cos_path and cos_path.exists():
        shutil.copy2(cos_path, latest_path)
        print(f"  ✓ Copied to: {latest_path}")
    else:
        # Write a fallback so the file always exists
        fallback = (
            f"# Clarion Executive Brief — {DATE}\n\n"
            "**No major signals this run.**\n\n"
            "The Chief of Staff agent did not produce a report this cycle.\n"
            "Check the console output above for errors.\n\n"
            "## Division Reports Filed This Run\n"
        )
        for name, path in results.items():
            status = f"✓ {path}" if path else "✗ Not produced"
            fallback += f"- {name}: {status}\n"
        latest_path.write_text(fallback, encoding="utf-8")
        print(f"  Fallback brief written to: {latest_path}")

    # 7. Summary
    banner("RUN COMPLETE")
    succeeded = sum(1 for v in results.values() if v is not None)
    total     = len(results)
    print(f"\n  Done.")
    print(f"\n  Divisions run   : {succeeded} / {total}")
    print(f"\n  Report written to:")
    print(f"  {latest_path}\n")

    if succeeded < total:
        failed = [k for k, v in results.items() if v is None]
        print(f"  [WARN] Some divisions failed: {', '.join(failed)}")
        print( "  Check console output above for error details.")

    if not cos_path:
        print("\n  [WARN] Chief of Staff did not complete.")
        print( "  The executive_brief_latest.md contains a fallback summary.")


if __name__ == "__main__":
    main()
