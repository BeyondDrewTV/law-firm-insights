"""
agent_runner.py
Clarion — Base Agent Runner
All individual agent runners use run_agent() from this module.
No agent runner needs to reimplement API calls, logging, or budget checks.

Usage (from an individual agent runner):
    from shared.agent_runner import run_agent

    run_agent(
        agent_key       = "head_of_growth",
        prompt_rel_path = "agents/revenue/head_of_growth.md",
        report_subdir   = "revenue",
        data_context    = data_context_string,
        agent_title     = "Clarion Head of Growth Agent",
    )
"""

import json
import datetime
from pathlib import Path

# Allow imports whether run from workflows/ or project root
import sys
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from shared.openrouter_client import call, check_budget


def _load_config() -> dict:
    config_path = BASE_DIR / "config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def _load_file(path: Path, label: str = "") -> str:
    """
    Load a file and return its text content.
    Returns a clear placeholder string on any failure so the agent
    knows data was unavailable rather than receiving empty input silently.
    """
    tag = f" ({label})" if label else ""
    if not path.exists():
        print(f"  [WARN] File not found{tag}: {path}")
        return f"[File not available: {path.name}]"
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  [WARN] Could not read{tag}: {path} — {e}")
        return f"[File unreadable: {path.name} — {e}]"
    if not text.strip():
        print(f"  [WARN] File is empty{tag}: {path}")
        return f"[File is empty: {path.name}]"
    return text


def _load_memory_file(memory_file: str, full: bool = False) -> str:
    """
    Load a memory file.
    full=True  → return entire content (for standing_orders, decision_log)
    full=False → return first 1200 chars with a summary prefix (for large files)
    """
    path = BASE_DIR / "memory" / memory_file
    text = _load_file(path, memory_file)
    if full:
        return f"### {memory_file}\n{text}\n"
    return f"### {memory_file}\n{text[:1200]}\n"


# Keep the old name as an alias so any runner that imported it directly still works.
def _load_memory_summary(memory_file: str) -> str:
    return _load_memory_file(memory_file, full=False)


def _log_run(
    report_subdir: str,
    agent_key: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    report_filename: str,
) -> None:
    log_dir = BASE_DIR / "reports" / report_subdir
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "run_log.jsonl"
    entry = {
        "date":       datetime.date.today().isoformat(),
        "agent":      agent_key,
        "model":      model,
        "tokens_in":  tokens_in,
        "tokens_out": tokens_out,
        "report":     report_filename,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def run_agent(
    agent_key: str,
    prompt_rel_path: str,
    report_subdir: str,
    data_context: str,
    agent_title: str,
    report_filename_prefix: str = "",
) -> Path:
    """
    Load config, call the model, save the report, log the run.

    agent_key           : key in config.json["agents"]
    prompt_rel_path     : relative path from BASE_DIR to the .md prompt file
    report_subdir       : subdirectory under reports/ for output
    data_context        : pre-built string of all data/inputs for this agent
    agent_title         : human-readable name for OpenRouter X-Title header
    report_filename_prefix : optional prefix (default = agent_key)

    Returns the Path of the saved report.
    """
    config = _load_config()

    if agent_key not in config["agents"]:
        raise KeyError(
            f"Agent key '{agent_key}' not found in config.json. "
            f"Available keys: {list(config['agents'].keys())}"
        )
    agent_cfg = config["agents"][agent_key]

    model      = agent_cfg["model"]
    max_tokens = agent_cfg["max_output_tokens"]
    temp       = agent_cfg["temperature"]
    date_str   = datetime.date.today().isoformat()
    prefix     = report_filename_prefix or agent_key

    print(f"\nClarion — {agent_title}")
    print(f"Run date : {date_str}")
    print(f"Model    : {model}")
    print(f"Temp     : {temp}")
    print("-" * 50)

    # Load system prompt
    prompt_path = BASE_DIR / prompt_rel_path
    system_prompt = _load_file(prompt_path, "system prompt")

    # --- Grounding context ---
    # All agents receive product_truth + standing_orders.
    # Chief of Staff additionally receives decision_log + office_learning_log
    # so it can surface conflicts and carry-forward proposals correctly.
    product_truth   = _load_memory_file("product_truth.md",   full=False)
    standing_orders = _load_memory_file("standing_orders.md", full=True)

    grounding = (
        f"## Grounding Context\n\n"
        f"{product_truth}\n\n"
        f"{standing_orders}\n\n"
    )

    if agent_key == "chief_of_staff":
        decision_log       = _load_memory_file("decision_log.md",        full=True)
        office_learning    = _load_memory_file("office_learning_log.md", full=False)
        grounding += (
            f"{decision_log}\n\n"
            f"{office_learning}\n\n"
        )

    user_message = (
        f"{grounding}"
        f"## Input Data\n\n{data_context}\n\n"
        f"## Task\n\n"
        f"Run your report for the period ending {date_str}.\n"
        f"Output the full report in the exact format specified in your prompt.\n"
        f"Do not fabricate data. If a file is unavailable, note it in INPUTS USED.\n"
        f"If any finding in your report would contradict a directive in "
        f"standing_orders.md, flag it explicitly rather than suppressing it.\n"
        f"Today's date: {date_str}\n"
    )

    approx_in = (len(system_prompt) + len(user_message)) // 4
    print(f"  Estimated input tokens : ~{approx_in}")

    max_in = config["cost_control"].get("max_input_tokens_chief_of_staff", 4000) \
        if agent_key == "chief_of_staff" \
        else config["cost_control"].get("max_input_tokens_department", 1500)

    if approx_in > max_in * 1.1:
        print(f"  [WARN] Estimated input tokens ~{approx_in} exceeds target {max_in}.")

    print("  Calling OpenRouter API...")
    result = call(
        model=model,
        system_prompt=system_prompt,
        user_message=user_message,
        max_tokens=max_tokens,
        temperature=temp,
        agent_title=agent_title,
    )

    tokens_in  = result["prompt_tokens"]
    tokens_out = result["completion_tokens"]
    print(f"  Tokens in  : {tokens_in}")
    print(f"  Tokens out : {tokens_out}")
    check_budget(agent_key, tokens_out, max_tokens)

    # Save report
    out_dir = BASE_DIR / "reports" / report_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    report_filename = f"{prefix}_{date_str}.md"
    report_path     = out_dir / report_filename
    report_path.write_text(result["content"], encoding="utf-8")
    print(f"  Report saved : {report_path}")

    _log_run(report_subdir, agent_key, model, tokens_in, tokens_out, report_filename)
    print("  Run logged.")
    print(f"  Done.\n")
    return report_path
