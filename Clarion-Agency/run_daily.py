"""
run_daily.py
Clarion — Daily Lean Office Run

This IS the real daily lean office run.
It executes the full lean pipeline:

    Prospect Intelligence → Outbound Sales → Content Engine →
    Product Experience → Execute Approved Actions → Summary

To run:
    cd C:\\Users\\beyon\\OneDrive\\Desktop\\CLARION\\law-firm-insights-main\\Clarion-Agency
    python run_daily.py
    -- OR --
    Double-click run_daily.bat

For the full weekly synthesis (all stages including Chief of Staff):
    python run_clarion_agent_office.py --full-office
    -- OR --
    Double-click run_clarion_agent_office.bat

Naming:
    run_daily.py / run_daily.bat         → LEAN office (daily, revenue-first)
    run_clarion_agent_office.py --full-office → FULL office (weekly synthesis)
"""

import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def main():
    """Delegate to run_clarion_agent_office.py in lean mode (no --full-office flag)."""
    runner = BASE_DIR / "run_clarion_agent_office.py"
    result = subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(BASE_DIR),
    )
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
