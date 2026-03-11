"""
customer_discovery_agent.py
Clarion — Customer Discovery Agent Runner
Division: Market Intelligence

Executes the Customer Discovery Agent using the OpenRouter API.
Reads the agent prompt from agents/market/customer_discovery.md.
Writes structured output to reports/market/customer_discovery_YYYY-MM-DD.md.

Usage:
    python workflows/customer_discovery_agent.py

Requirements:
    - OPENROUTER_API_KEY set in .env
    - pip install openai python-dotenv
"""

import os
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BASE_DIR     = Path(__file__).resolve().parent.parent
PROMPT_FILE  = BASE_DIR / "agents" / "market" / "customer_discovery.md"
MEMORY_DIR   = BASE_DIR / "memory"
REPORTS_DIR  = BASE_DIR / "reports" / "market"
CONFIG_FILE  = BASE_DIR / "config.json"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

with open(CONFIG_FILE) as f:
    config = json.load(f)

DISCOVERY_CONFIG = config.get("agents", {}).get("customer_discovery", {})
MODEL      = DISCOVERY_CONFIG.get("model", "anthropic/claude-3-haiku")
MAX_TOKENS = DISCOVERY_CONFIG.get("max_output_tokens", 1800)
TEMPERATURE = DISCOVERY_CONFIG.get("temperature", 0.3)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)


def load_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    print(f"  [WARN] File not found: {path}")
    return ""


def build_system_prompt() -> str:
    prompt = load_file(PROMPT_FILE)
    if not prompt:
        raise FileNotFoundError(f"Agent prompt not found: {PROMPT_FILE}")
    return prompt


def build_grounding_context() -> str:
    product_truth = load_file(MEMORY_DIR / "product_truth.md")
    return "\n".join([
        "## Grounding Context\n",
        "### Product Truth Summary\n",
        product_truth[:1200],
        "\n---\n",
    ])


def build_user_message(date_str: str) -> str:
    grounding = build_grounding_context()
    return f"""{grounding}

## Task

Run a Customer Discovery sweep for the week ending {date_str}.
Search all sources listed in your prompt. Surface every genuine signal you find.
Apply evaluation criteria strictly. Output the full report in the exact format specified.
If you cannot access a live source, note it in INPUTS USED as "unavailable this run".
Do not fabricate signals. Do not pad the report.

Today's date: {date_str}
"""


def save_report(content: str, date_str: str) -> Path:
    filename = REPORTS_DIR / f"customer_discovery_{date_str}.md"
    filename.write_text(content, encoding="utf-8")
    return filename


def log_run(date_str: str, model: str, tokens_used: dict, report_path: Path):
    log_path = REPORTS_DIR / "run_log.jsonl"
    entry = {
        "date": date_str, "agent": "customer_discovery",
        "model": model,
        "tokens_in": tokens_used.get("prompt_tokens", 0),
        "tokens_out": tokens_used.get("completion_tokens", 0),
        "report": str(report_path.name),
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_token_budget(usage: dict):
    actual_out = usage.get("completion_tokens", 0)
    if actual_out > MAX_TOKENS * 1.2:
        print(f"  [BUDGET WARNING] Output tokens {actual_out} exceeded budget {MAX_TOKENS} by >20%.")
        print("  Flag this in the next report. Do not auto-retry.")


def run():
    date_str = datetime.date.today().isoformat()
    print(f"\nClarion — Customer Discovery Agent")
    print(f"Run date : {date_str}")
    print(f"Model    : {MODEL}")
    print("-" * 50)

    system_prompt = build_system_prompt()
    user_message = build_user_message(date_str)

    approx_tokens = (len(system_prompt) + len(user_message)) // 4
    print(f"  Estimated input tokens : ~{approx_tokens}")
    if approx_tokens > 2000:
        print("  [WARN] Input token estimate exceeds 2000.")

    print("  Calling OpenRouter API...")
    response = client.chat.completions.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        extra_headers={
            "HTTP-Referer": "https://clarion.internal",
            "X-Title": "Clarion Customer Discovery Agent",
        },
    )

    report_content = response.choices[0].message.content
    usage = {
        "prompt_tokens": response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
    }

    print(f"  Tokens in  : {usage['prompt_tokens']}")
    print(f"  Tokens out : {usage['completion_tokens']}")
    check_token_budget(usage)

    report_path = save_report(report_content, date_str)
    print(f"  Report saved : {report_path}")
    log_run(date_str, MODEL, usage, report_path)
    print("  Run logged.")
    print(f"\n  Done. Review before forwarding to Sales, Content, or Product.\n")
    return report_path


if __name__ == "__main__":
    run()
