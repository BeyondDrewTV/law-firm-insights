"""
run_daily.py
Clarion — Daily Agent Run

Runs time-sensitive pre-launch agents that need to fire every day,
not just on the weekly full-office cycle.

Double-click run_daily.bat, or run directly:

    cd C:\\Users\\beyon\\OneDrive\\Desktop\\CLARION\\law-firm-insights-main\\Clarion-Agency
    python run_daily.py

Daily agents (pre-launch active):
    Conversation Discovery   — refreshes discovered_conversations.md
    Competitive Intelligence — surfaces competitor moves same-day
    Comms & Content          — engagement drafts from fresh discovery signals

NOT run here (weekly only):
    Usage Analyst            — usage patterns don't shift daily at current scale
    Chief of Staff           — weekly executive synthesis; run via run_clarion_agent_office.bat

Output:
    reports/market/competitive_intelligence_YYYY-MM-DD.md
    reports/comms/content_seo_YYYY-MM-DD.md
    data/comms/discovered_conversations.md  (refreshed)

No executive brief is produced on daily runs.
Run run_clarion_agent_office.bat once per week for the full synthesis.
"""

import sys
import datetime
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from shared.agent_runner import run_agent, _load_file
from shared.conversation_discovery import run as run_conversation_discovery

REPORTS = BASE_DIR / "reports"
DATA    = BASE_DIR / "data"
MEMORY  = BASE_DIR / "memory"

DATE    = datetime.date.today().isoformat()
DIVIDER = "=" * 60


def banner(msg: str) -> None:
    print(f"\n{DIVIDER}")
    print(f"  {msg}")
    print(DIVIDER)


# ── Real-input gate (same logic as weekly runner) ──────────────────────────────

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
        "",
        "DIVISION SIGNAL",
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


# ── Data builders ──────────────────────────────────────────────────────────────

def data_competitive_intelligence():
    return "\n".join([
        f"### {label}\n{_load_file(DATA / path, label)}\n"
        for label, path in [
            ("Competitor Tracking Reference", "market/competitors.md"),
            ("Competitor Pricing Snapshot",   "market/competitor_pricing.md"),
        ]
    ]) + "\n### Live Sources\nAlso check G2, Capterra, and public job boards per your prompt.\n"


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
    print(f"\nStarting Clarion Daily Run...")
    print(f"Date   : {DATE}")
    print(f"Root   : {BASE_DIR}")

    results = {}

    # ── Step 1: Conversation Discovery ────────────────────────────────────────
    banner("STEP 1 — Conversation Discovery")
    try:
        discovery_path = run_conversation_discovery()
        print(f"  ✓ Discovery complete → {discovery_path.name}")
    except Exception as e:
        print(f"  ✗ Discovery FAILED: {e}")
        traceback.print_exc()
        print("  [INFO] Comms agent will note data as unavailable — run continues.")

    # ── Step 2: Competitive Intelligence ──────────────────────────────────────
    banner("STEP 2 — Competitive Intelligence")
    ci_inputs = [DATA / "market/competitors.md", DATA / "market/competitor_pricing.md"]
    ci_real, ci_missing = _has_real_input(ci_inputs)
    if ci_real:
        try:
            path = run_agent(
                agent_key       = "competitive_intelligence",
                prompt_rel_path = "agents/market/competitive_intelligence.md",
                report_subdir   = "market",
                data_context    = data_competitive_intelligence(),
                agent_title     = "Clarion Competitive Intelligence Agent",
            )
            results["competitive_intelligence"] = path
            print(f"  ✓ Competitive Intelligence → {path.name}")
        except Exception as e:
            print(f"  ✗ Competitive Intelligence FAILED: {e}")
            traceback.print_exc()
            results["competitive_intelligence"] = None
    else:
        print(f"  [GATE] Competitive Intelligence — skipping (no real input)")
        results["competitive_intelligence"] = _write_skip_report(
            "market", "competitive_intelligence", "Competitive Intelligence Agent",
            ci_missing,
            ["data/market/competitors.md — populate with real competitor entries"],
        )

    # ── Step 3: Comms & Content ────────────────────────────────────────────────
    banner("STEP 3 — Comms & Content (Foundation Mode)")
    comms_inputs = [DATA / "comms/discovered_conversations.md", DATA / "comms/seo_keywords.csv"]
    comms_real, comms_missing = _has_real_input(comms_inputs)
    if comms_real:
        try:
            path = run_agent(
                agent_key       = "content_seo",
                prompt_rel_path = "agents/comms/content_seo.md",
                report_subdir   = "comms",
                data_context    = data_content_seo(),
                agent_title     = "Clarion Content & SEO Agent",
            )
            results["content_seo"] = path
            print(f"  ✓ Comms & Content → {path.name}")
        except Exception as e:
            print(f"  ✗ Comms & Content FAILED: {e}")
            traceback.print_exc()
            results["content_seo"] = None
    else:
        print(f"  [GATE] Comms & Content — skipping (no real input)")
        results["content_seo"] = _write_skip_report(
            "comms", "content_seo", "Content & SEO Agent",
            comms_missing,
            ["data/comms/discovered_conversations.md — run discovery first"],
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    banner("DAILY RUN COMPLETE")
    ran  = [k for k, v in results.items() if v and v.exists()
            and "0  (LLM call skipped" not in v.read_text(encoding="utf-8", errors="replace")]
    skip = [k for k, v in results.items() if v and v.exists()
            and "0  (LLM call skipped" in v.read_text(encoding="utf-8", errors="replace")]
    fail = [k for k, v in results.items() if not v]

    print(f"\n  Done.")
    print(f"  LLM calls made   : {len(ran)} ({', '.join(ran) or 'none'})")
    if skip:
        print(f"  Skipped (no data): {', '.join(skip)}")
    if fail:
        print(f"  Failed           : {', '.join(fail)}")
    print(f"\n  Reports in: reports/market/  and  reports/comms/")
    print(f"  Run run_clarion_agent_office.bat on Fridays for the full weekly brief.\n")


if __name__ == "__main__":
    main()
