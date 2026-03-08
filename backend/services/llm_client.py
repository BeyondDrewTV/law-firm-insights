# services/llm_client.py
# Thin wrapper around the Anthropic SDK.
# Single responsibility: make one API call and return raw text.
# All retry and validation logic lives in review_classifier.py.

import os
import logging
import pathlib

import anthropic

logger = logging.getLogger("llm_client")

# Pinned model version. Never use an alias (e.g. "claude-sonnet-*").
# Update only after running the golden test set and confirming >95% theme match.
MODEL_VERSION = "claude-sonnet-4-5"

# Tight cap: a valid classification JSON is ~120–180 tokens.
# 400 gives headroom while preventing runaway generation.
MAX_TOKENS = 400

SYSTEM_PROMPT = """\
You are a classification engine for a legal services client feedback platform.
Your ONLY function is to classify client reviews into structured JSON.

RULES:
1. Output ONLY valid JSON. No markdown. No explanation. No preamble. No trailing text.
2. Use ONLY theme names from the provided THEME VOCABULARY. Do not invent names.
3. Assign between 1 and 5 themes per review. Never zero. Never more than five.
4. polarity must be exactly one of: positive, neutral, negative
5. severity must be exactly one of: low, moderate, high
6. overall_sentiment must be exactly one of: positive, neutral, negative, mixed
   Use "mixed" when themes have conflicting polarities.
7. confidence is a float from 0.0 to 1.0 reflecting your certainty in the classification.
   Set confidence below 0.65 when the review is ambiguous, too short, or off-topic.
8. key_excerpt must be a verbatim snippet from the review text. Maximum 200 characters.
9. severity reflects operational risk, not tone:
   - high: systemic failure signal, ethics exposure, or explicit client harm language
   - moderate: substantive issue warranting attention
   - low: isolated minor comment
10. If the review is unintelligible, empty, or not in English, return this exact JSON:
    {"themes":[{"name":"Communication","polarity":"neutral","severity":"low"}],\
"overall_sentiment":"neutral","confidence":0.1,\
"key_excerpt":"[unclassifiable review]","flags":["unclassifiable"]}
11. The optional "flags" array may contain short string tags. Leave it empty [] if unused.
12. Never output any field not listed in the schema.
"""


def _resolve_api_key() -> str:
    """
    Resolve ANTHROPIC_API_KEY with a two-pass strategy:
      1. Read from os.environ (already populated if dotenv loaded at startup).
      2. If missing, read directly from the .env file beside app.py so that
         background threads that might not have inherited the var can still work.

    Raises RuntimeError with a clear message if the key cannot be found either way.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key

    # Belt-and-suspenders: read directly from .env beside this file's project root.
    # This handles edge cases where a background thread or subprocess did not
    # inherit the environment that was set up by load_dotenv() in app.py.
    try:
        from dotenv import dotenv_values
        env_path = pathlib.Path(__file__).resolve().parent.parent / ".env"
        if env_path.exists():
            dotenv_vars = dotenv_values(str(env_path))
            key = (dotenv_vars.get("ANTHROPIC_API_KEY") or "").strip()
            if key:
                # Inject into this process's environment so subsequent calls are fast.
                os.environ["ANTHROPIC_API_KEY"] = key
                logger.info("llm_client: ANTHROPIC_API_KEY loaded directly from %s", env_path)
                return key
    except Exception as exc:
        logger.warning("llm_client: fallback dotenv read failed: %s", exc)

    raise RuntimeError(
        "ANTHROPIC_API_KEY missing in process env; check dotenv loading. "
        "Ensure .env exists in the project root and contains ANTHROPIC_API_KEY=sk-ant-..."
    )


def call_model(user_prompt: str) -> str:
    """
    Call the Anthropic API with the given user prompt.
    Returns the raw text content of the model response.
    Raises RuntimeError if ANTHROPIC_API_KEY is not resolvable.
    Raises anthropic.APIError or anthropic.APIConnectionError on API failure.
    """
    api_key = _resolve_api_key()

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=MODEL_VERSION,
        max_tokens=MAX_TOKENS,
        temperature=0.0,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    # Extract text from first content block.
    if not message.content or message.content[0].type != "text":
        raise ValueError("Unexpected response structure from Anthropic API.")

    return message.content[0].text.strip()