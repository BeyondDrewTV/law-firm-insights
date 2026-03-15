"""
routes/calibration_console.py
Clarion — Internal Calibration Console
Mounted at: /internal/calibration

Local-use only.  No auth needed (internal tool, not exposed in prod).
All paths resolve relative to REPO_ROOT (two levels above backend/).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, request, redirect, url_for, jsonify

# ── Path resolution ───────────────────────────────────────────────────────────
# backend/ → law-firm-insights-main/ (repo root)
BACKEND_DIR  = Path(__file__).resolve().parent.parent
REPO_ROOT    = BACKEND_DIR.parent
WORKFLOW_PY  = REPO_ROOT / "automation" / "calibration" / "run_calibration_workflow.py"
DATA_DIR     = REPO_ROOT / "data" / "calibration"
RUNS_DIR     = DATA_DIR / "runs"
DEFAULT_CSV  = DATA_DIR / "inputs" / "real_reviews.csv"

calibration_bp = Blueprint("calibration_console", __name__, url_prefix="/internal/calibration")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _csv_info() -> dict:
    """Return metadata about the canonical input CSV."""
    if DEFAULT_CSV.exists():
        stat = DEFAULT_CSV.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        size_kb = round(stat.st_size / 1024, 1)
        # Count data rows (quick, no pandas needed)
        try:
            with open(DEFAULT_CSV, encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            row_count = max(0, len(lines) - 1)  # minus header
        except Exception:
            row_count = "?"
        return {
            "exists": True,
            "path": str(DEFAULT_CSV.relative_to(REPO_ROOT)),
            "abs_path": str(DEFAULT_CSV),
            "modified": mtime,
            "size_kb": size_kb,
            "row_count": row_count,
        }
    return {
        "exists": False,
        "path": str(DEFAULT_CSV.relative_to(REPO_ROOT)),
        "abs_path": str(DEFAULT_CSV),
    }

def _list_runs() -> list[dict]:
    """Scan RUNS_DIR and return run metadata sorted newest-first."""
    if not RUNS_DIR.exists():
        return []
    runs = []
    for d in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not d.is_dir() or not d.name[0].isdigit():
            continue
        info: dict = {"id": d.name, "path": str(d), "rel_path": str(d.relative_to(REPO_ROOT))}
        # Parse timestamp from folder name: YYYYMMDD_HHMMSS
        try:
            info["ts_display"] = datetime.strptime(d.name, "%Y%m%d_%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            info["ts_display"] = d.name
        # Load summary if available
        summary_json = d / "final_summary.json"
        summary_md   = d / "final_summary.md"
        info["has_summary"] = summary_json.exists()
        info["summary_md_path"] = str(summary_md.relative_to(REPO_ROOT)) if summary_md.exists() else None
        info["summary_json_path"] = str(summary_json.relative_to(REPO_ROOT)) if summary_json.exists() else None
        if summary_json.exists():
            try:
                with open(summary_json, encoding="utf-8") as f:
                    s = json.load(f)
                info["real"]         = s.get("total_real_reviews", "?")
                info["synthetic"]    = s.get("total_synthetic_reviews", "?")
                info["chunks_ok"]    = s.get("chunks_succeeded", "?")
                info["chunks_total"] = s.get("chunks_total", "?")
                info["chunks_fail"]  = s.get("chunks_failed", 0)
                info["ai_enabled"]   = s.get("ai_benchmark_enabled", True)
            except Exception:
                pass
        runs.append(info)
    return runs


def _latest_run_detail() -> dict | None:
    """Return detailed view of the most recent run that has a final_summary.json."""
    for d in sorted(RUNS_DIR.iterdir(), reverse=True) if RUNS_DIR.exists() else []:
        if not d.is_dir() or not d.name[0].isdigit():
            continue
        summary_json = d / "final_summary.json"
        summary_md   = d / "final_summary.md"
        if not summary_json.exists():
            continue
        try:
            with open(summary_json, encoding="utf-8") as f:
                s = json.load(f)
        except Exception:
            continue
        md_content = ""
        if summary_md.exists():
            try:
                md_content = summary_md.read_text(encoding="utf-8")
            except Exception:
                pass
        return {
            "id": d.name,
            "rel_path": str(d.relative_to(REPO_ROOT)),
            "abs_path": str(d),
            "summary_json_path": str(summary_json.relative_to(REPO_ROOT)),
            "summary_md_path":   str(summary_md.relative_to(REPO_ROOT)) if summary_md.exists() else None,
            "summary_md_content": md_content,
            "data": s,
        }
    return None


# ── Routes ────────────────────────────────────────────────────────────────────

@calibration_bp.route("/", methods=["GET"])
def console():
    return render_template(
        "internal/calibration_console.html",
        csv_info=_csv_info(),
        runs=_list_runs(),
        latest=_latest_run_detail(),
        run_result=None,
    )


@calibration_bp.route("/upload", methods=["POST"])
def upload_csv():
    """Replace the canonical input CSV with the uploaded file."""
    f = request.files.get("csv_file")
    if not f or not f.filename:
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result=None, upload_error="No file selected.",
        )
    fname = secure_filename(f.filename)
    if not fname.lower().endswith(".csv"):
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result=None, upload_error="File must be a .csv",
        )
    DEFAULT_CSV.parent.mkdir(parents=True, exist_ok=True)
    f.save(str(DEFAULT_CSV))
    return render_template(
        "internal/calibration_console.html",
        csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
        run_result=None, upload_ok=f"Uploaded and saved as {DEFAULT_CSV.name}.",
    )


@calibration_bp.route("/run", methods=["POST"])
def run_calibration():
    """
    Run the calibration workflow synchronously and return stdout/stderr.
    Uses the same Python interpreter that's running Flask (venv-safe).
    """
    dry_run = request.form.get("dry_run") == "1"
    no_ai   = request.form.get("no_ai") == "1"

    if not WORKFLOW_PY.exists():
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result={
                "success": False,
                "stdout": "",
                "stderr": f"Workflow script not found: {WORKFLOW_PY}",
                "returncode": -1,
            },
        )

    cmd = [
        sys.executable,          # venv python — guaranteed same interpreter
        str(WORKFLOW_PY),
        "--csv",    str(DEFAULT_CSV),
        "--server", "http://localhost:5000",
        "--token",  os.environ.get("INTERNAL_BENCHMARK_SECRET", "Themepark12"),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if no_ai:
        cmd.append("--no-ai")

    # Force UTF-8 I/O on the subprocess so Unicode chars in the workflow
    # script (▶ ✅ ⚠️ etc.) don't trigger a cp1252 UnicodeEncodeError on Windows.
    run_env = os.environ.copy()
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONUTF8"] = "1"

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=run_env,
            cwd=str(REPO_ROOT),
            timeout=600,   # 10 min hard cap
        )
        success = proc.returncode == 0
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result={
                "success": success,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "cmd": " ".join(cmd),
            },
        )
    except subprocess.TimeoutExpired:
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result={
                "success": False,
                "stdout": "",
                "stderr": "Process timed out after 600 seconds.",
                "returncode": -1,
            },
        )
    except Exception as exc:
        return render_template(
            "internal/calibration_console.html",
            csv_info=_csv_info(), runs=_list_runs(), latest=_latest_run_detail(),
            run_result={
                "success": False,
                "stdout": "",
                "stderr": str(exc),
                "returncode": -1,
            },
        )


@calibration_bp.route("/runs", methods=["GET"])
def list_runs():
    """JSON endpoint — returns run list."""
    return jsonify({"runs": _list_runs()})


@calibration_bp.route("/run/<run_id>", methods=["GET"])
def run_detail(run_id: str):
    """JSON endpoint — returns single run summary."""
    run_dir = RUNS_DIR / run_id
    if not run_dir.exists():
        return jsonify({"error": "Run not found"}), 404
    summary_json = run_dir / "final_summary.json"
    if not summary_json.exists():
        return jsonify({"error": "No final_summary.json for this run"}), 404
    try:
        with open(summary_json, encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"run_id": run_id, "summary": data})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
