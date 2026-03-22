"""
services/bench/deterministic_tagger.py
=======================================
Instrumented, self-contained re-implementation of Clarion's keyword-matching
theme engine.  Produces the same logical output as the _analyze_reviews_tx /
analyze() bag-of-words loop in app.py, but adds per-match evidence traces so
the calibration harness can compare them against AI labels.

Design rules
------------
- Zero imports from app.py (avoids circular deps and Flask context requirements).
- Reads the same raw keyword dicts that app.py uses, duplicated here so the
  harness never touches production state.
- Polarity is inferred from star rating + negation context (see _infer_polarity).
- Severity is inferred from a short list of severity amplifier phrases.
- Output schema mirrors the benchmark schema (theme / polarity / evidence_span /
  confidence / matched_phrases / multipliers_applied / sentence_snippet).

Calibration Wave -- 2026-03-15
-------------------------------
Changes from prior version:
- Phrase library expanded: ~70 new phrases across all 10 themes (P0 priority).
- "polite" / "very polite" moved from professionalism_trust to office_staff_experience (P3 routing fix).
- _has_negation() replaced with _has_proximal_negation() -- negation only counts if
  within NEGATION_PROXIMITY_TOKENS tokens of the phrase trigger (P1 guard fix).
- Duration-based severity escalation: "delayed N months/years" patterns -> severe_negative (P2).
- SEVERE_AMPLIFIERS expanded to cover additional high-severity terms.
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Canonical benchmark theme taxonomy
# ---------------------------------------------------------------------------
BENCH_THEMES = [
    "communication_responsiveness",
    "communication_clarity",
    "empathy_support",
    "professionalism_trust",
    "expectation_setting",
    "billing_transparency",
    "fee_value",
    "timeliness_progress",
    "office_staff_experience",
    "outcome_satisfaction",
]

# ---------------------------------------------------------------------------
# Negation proximity window
# Negation tokens must appear within this many tokens of the matched phrase
# to count as flipping polarity. Prevents cross-clause false positives like
# "if not available she returned my calls" negating "returned my call".
# ---------------------------------------------------------------------------
NEGATION_PROXIMITY_TOKENS = 6

# ---------------------------------------------------------------------------
# Duration-based severity escalation
# Matches "delayed 5 months", "waited 2 years", "over two years", etc.
# to escalate timeliness/waiting negatives -> severe_negative.
# ---------------------------------------------------------------------------
_DURATION_SEVERE_PATTERNS = re.compile(
    r"""
    (?:
        (?:delayed|waiting|waited|dragged\s+on|took|over)\s+
        (?:\d+|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|eighteen|twenty)\s*
        (?:and\s+a\s+half\s+)?
        (?:days?|weeks?|months?|years?)
    )
    |
    (?:over\s+(?:a\s+)?(?:year|two\s+years|three\s+years|four\s+years))
    |
    (?:\d+\s+and\s+a\s+half\s+years?)
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Keyword families
# Each theme maps to a list of (phrase, family_label) tuples.
# Ordering: longer/more-specific phrases before shorter overlapping ones.
# ---------------------------------------------------------------------------
THEME_PHRASE_FAMILIES: dict[str, list[tuple[str, str]]] = {
    "communication_responsiveness": [
        # negative -- more specific first
        ("never return my calls", "no_contact_neg"),
        ("never returns my calls", "no_contact_neg"),
        ("kept calling and sending messages", "no_contact_neg"),
        ("i kept calling", "no_contact_neg"),
        ("email after email without", "no_contact_neg"),
        ("send email after email", "no_contact_neg"),
        ("i send email after email", "no_contact_neg"),
        ("barely had communication", "no_contact_neg"),
        ("barely communicated", "no_contact_neg"),
        ("crickets from", "no_contact_neg"),
        ("crickets", "no_contact_neg"),
        ("without replies", "no_contact_neg"),
        ("no response", "no_contact_neg"),
        ("never called", "no_contact_neg"),
        ("didn't respond", "no_contact_neg"),
        ("did not respond", "no_contact_neg"),
        ("hard to reach", "reachability_neg"),
        ("impossible to reach", "reachability_neg"),
        ("unreachable", "reachability_neg"),
        ("never returns a call", "no_contact_neg"),
        ("no one returns", "no_contact_neg"),
        ("no one ever returns", "no_contact_neg"),
        ("no one calls back", "no_contact_neg"),
        ("never calls back", "no_contact_neg"),
        ("tell you to do it yourself", "no_contact_neg"),
        ("do it yourself", "no_contact_neg"),
        ("never even really had meetings", "no_contact_neg"),
        ("never had meetings", "no_contact_neg"),
        ("never had a meeting", "no_contact_neg"),
        ("without being judged", "no_contact_neg"),
        ("judged for having", "no_contact_neg"),
        # positive
        ("kept in close contact", "proactive_update"),
        ("stayed in contact", "proactive_update"),
        ("returned her call", "callback"),
        ("returned his call", "callback"),
        ("returned my call", "callback"),
        ("returned calls", "callback"),
        ("called me back", "callback"),
        ("calls back", "callback"),
        ("returns a call", "callback"),
        ("give you his time", "responsiveness"),
        ("give you her time", "responsiveness"),
        ("responded quickly", "responsiveness"),
        ("responded promptly", "responsiveness"),
        ("quick to respond", "responsiveness"),
        ("always available", "responsiveness"),
        ("they communicate well", "responsiveness"),
        ("communicate well", "responsiveness"),
        ("communicates well", "responsiveness"),
        ("kept me informed", "proactive_update"),
        ("kept me updated", "proactive_update"),
        ("keep me updated", "proactive_update"),
        ("kept us informed", "proactive_update"),
        ("updates", "proactive_update"),
        ("responsive", "responsiveness"),
        ("communication", "general_comm"),
        ("contact", "general_comm"),
    ],
    "communication_clarity": [
        # negative
        ("left me in the dark", "no_explanation_neg"),
        ("couldn't understand", "clarity_neg"),
        ("could not understand", "clarity_neg"),
        ("hard to follow", "clarity_neg"),
        ("never explained", "no_explanation_neg"),
        ("didn't explain", "no_explanation_neg"),
        ("did not explain", "no_explanation_neg"),
        ("no explanation", "no_explanation_neg"),
        ("unclear", "clarity_neg"),
        ("confusing", "clarity_neg"),
        ("confused", "clarity_neg"),
        ("jargon", "jargon_neg"),
        # positive
        ("thoroughly explained", "clarity_pos"),
        ("well explained", "clarity_pos"),
        ("walked me through", "clarity_pos"),
        ("explained clearly", "clarity_pos"),
        ("explained everything", "clarity_pos"),
        ("easy to understand", "clarity_pos"),
        ("clear explanation", "clarity_pos"),
        ("plain language", "plain_language_pos"),
        ("plain english", "plain_language_pos"),
    ],
    "empathy_support": [
        # negative
        ("lawyers and associate are not caring", "empathy_neg"),
        ("you are dead to them", "empathy_neg"),
        ("treated as another number", "empathy_neg"),
        ("i felt like i was just", "empathy_neg"),
        ("just a number", "empathy_neg"),
        ("barely gave me any opportunity to speak", "listening_neg"),
        ("cut me off and start rambling", "listening_neg"),
        ("cut me off", "listening_neg"),
        ("i absolutely hated", "empathy_neg"),
        ("absolutely hated", "empathy_neg"),
        ("no compassion", "empathy_neg"),
        ("not caring at all", "empathy_neg"),
        ("not caring", "empathy_neg"),
        ("didn't care", "empathy_neg"),
        ("did not care", "empathy_neg"),
        ("didn't listen", "listening_neg"),
        ("did not listen", "listening_neg"),
        ("ignored", "listening_neg"),
        ("cold", "empathy_neg"),
        ("dismissive", "empathy_neg"),
        ("failed to provide support", "empathy_neg"),
        ("failed to provide any support", "empathy_neg"),
        ("no support", "empathy_neg"),
        ("left me alone", "empathy_neg"),
        # positive
        ("handled my case with grace", "empathy_pos"),
        ("handled my case with patience", "empathy_pos"),
        ("made me feel comfortable", "support_pos"),
        ("made me feel at ease", "support_pos"),
        ("reassured me", "support_pos"),
        ("showed empathy", "empathy_pos"),
        ("listened to me", "active_listening_pos"),
        ("listened", "active_listening_pos"),
        ("heard me", "active_listening_pos"),
        ("compassionate", "empathy_pos"),
        ("empathetic", "empathy_pos"),
        ("supportive", "support_pos"),
        ("patient", "empathy_pos"),
        ("caring", "empathy_pos"),
        ("understanding", "empathy_pos"),
        ("friendly", "empathy_pos"),
        ("kind", "empathy_pos"),
        ("warm", "empathy_pos"),
        ("welcoming", "empathy_pos"),
        ("dedicated", "empathy_pos"),
        ("truly cares", "empathy_pos"),
        ("genuinely cares", "empathy_pos"),
        ("appreciate the help", "support_pos"),
        ("we appreciate the help", "support_pos"),
        ("helped me through", "support_pos"),
        ("helped us through", "support_pos"),
        ("family oriented", "empathy_pos"),
        ("family-oriented", "empathy_pos"),
        ("knowledgeable", "empathy_pos"),
        ("organized", "empathy_pos"),
        ("thorough", "empathy_pos"),
    ],
    "professionalism_trust": [
        # negative
        ("i didn't appreciate being spoken", "professionalism_neg"),
        ("didn't appreciate being spoken to", "professionalism_neg"),
        ("spoken to that way", "professionalism_neg"),
        ("crooked law office", "trust_neg"),
        ("crooked", "trust_neg"),
        ("do not trust this firm", "trust_neg"),
        ("misrepresentation", "trust_neg"),
        ("they're not even licensed", "trust_neg"),
        ("not licensed in my state", "trust_neg"),
        ("not even licensed", "trust_neg"),
        ("disrespectful", "professionalism_neg"),
        ("unprofessional", "professionalism_neg"),
        ("unethical", "ethics_neg"),
        ("rude", "professionalism_neg"),
        # positive
        ("i knew i was dealing with professionals", "professionalism_pos"),
        ("knew i was dealing with professionals", "professionalism_pos"),
        ("true professionals", "professionalism_pos"),
        ("highly professional", "professionalism_pos"),
        ("professional", "professionalism_pos"),
        ("courteous", "professionalism_pos"),
        ("respectful", "professionalism_pos"),
        ("demeanor", "professionalism_pos"),
        ("ethical", "ethics_pos"),
        ("trustworthy", "trust_pos"),
        ("trust", "trust_pos"),
        ("knowledgeable", "professionalism_pos"),
        ("kindness", "professionalism_pos"),
        ("wonderful to work with", "professionalism_pos"),
        ("wonderful attorney", "professionalism_pos"),
        ("wonderful lawyer", "professionalism_pos"),
        ("lovely experience", "professionalism_pos"),
        ("great experience", "professionalism_pos"),
        ("positive experience", "professionalism_pos"),
        ("excellent attorney", "professionalism_pos"),
        ("excellent lawyer", "professionalism_pos"),
        ("highly recommend", "professionalism_pos"),
        ("highly recommended", "professionalism_pos"),
        ("would recommend", "professionalism_pos"),
        ("i recommend", "professionalism_pos"),
        ("competent", "professionalism_pos"),
        ("thorough", "professionalism_pos"),
        ("dedicated", "professionalism_pos"),
        ("hard working", "professionalism_pos"),
        ("hardworking", "professionalism_pos"),
        ("above and beyond", "professionalism_pos"),
        ("went above and beyond", "professionalism_pos"),
        # NOTE: "polite" intentionally absent -- routed to office_staff_experience
    ],
    "expectation_setting": [
        # negative
        ("he completely let me down", "expectation_neg"),
        ("completely let me down", "expectation_neg"),
        ("let me down", "expectation_neg"),
        ("got every little detail only to be told", "expectation_neg"),
        ("only to be told", "expectation_neg"),
        ("sent his inexperienced son", "expectation_neg"),
        ("different than what i was promised", "expectation_neg"),
        ("not what i was told", "expectation_neg"),
        ("over-promised", "expectation_neg"),
        ("overpromised", "expectation_neg"),
        ("unrealistic", "expectation_neg"),
        ("misleading", "expectation_neg"),
        ("misled", "expectation_neg"),
        ("false hope", "expectation_neg"),
        ("surprised by", "surprise_neg"),
        # positive
        ("walked me through the process", "process_clarity_pos"),
        ("explained the process", "process_clarity_pos"),
        ("realistic expectations", "expectation_pos"),
        ("set expectations", "expectation_pos"),
        ("what to expect", "expectation_pos"),
        ("prepared me", "expectation_pos"),
        ("best interests in mind", "expectation_pos"),
        ("had my best interests", "expectation_pos"),
        ("had our best interests", "expectation_pos"),
        ("work hard for you", "expectation_pos"),
        ("will work hard for you", "expectation_pos"),
        ("works hard for you", "expectation_pos"),
    ],
    "billing_transparency": [
        # negative
        ("told me it was '16 hours", "billing_transparency_neg"),
        ("told me it was 16 hours of work", "billing_transparency_neg"),
        ("my rate is", "billing_transparency_neg"),
        ("rate is $", "billing_transparency_neg"),
        ("wouldn't be getting anything back", "billing_transparency_neg"),
        ("not getting anything back", "billing_transparency_neg"),
        ("charged me the full amount", "billing_transparency_neg"),
        ("excessive fees", "billing_transparency_neg"),
        ("excess charges", "billing_transparency_neg"),
        ("charged for consultation", "billing_transparency_neg"),
        ("charged a fee", "billing_transparency_neg"),
        ("billing dispute", "billing_transparency_neg"),
        ("double billed", "billing_transparency_neg"),
        ("overcharged", "billing_transparency_neg"),
        ("surprise bill", "billing_transparency_neg"),
        ("unexpected charges", "billing_transparency_neg"),
        ("hidden charges", "billing_transparency_neg"),
        ("hidden fees", "billing_transparency_neg"),
        # positive
        ("transparent billing", "billing_transparency_pos"),
        ("itemized", "billing_transparency_pos"),
        # general
        ("consultation fee", "billing_general"),
        ("billing", "billing_general"),
        ("invoice", "billing_general"),
        ("invoiced", "billing_general"),
    ],
    "fee_value": [
        # negative
        ("not worth the money", "value_neg"),
        ("waste of money", "value_neg"),
        ("not worth", "value_neg"),
        ("overpriced", "value_neg"),
        ("too much", "value_neg"),
        ("expensive", "value_neg"),
        # positive
        ("worth every penny", "value_pos"),
        ("worth it", "value_pos"),
        ("great value", "value_pos"),
        ("good value", "value_pos"),
        ("fair price", "value_pos"),
        ("fair fee", "value_pos"),
        ("affordable", "value_pos"),
        ("reasonable fee", "value_pos"),
        ("reasonable cost", "value_pos"),
        # general
        ("fees", "fee_general"),
        ("cost", "fee_general"),
        ("price", "fee_general"),
        ("value", "value_general"),
    ],
    "timeliness_progress": [
        # negative
        ("over two years and still waiting", "waiting_neg"),
        ("went 2 and a half years to lose all", "waiting_neg"),
        ("2 and a half years", "waiting_neg"),
        ("only heard from the actual attorney a day before", "waiting_neg"),
        ("a day before the hearing", "waiting_neg"),
        ("still waiting", "waiting_neg"),
        ("nothing has been done", "waiting_neg"),
        ("no progress", "waiting_neg"),
        ("took too long", "timeliness_neg"),
        ("dragged on", "timeliness_neg"),
        ("last minute", "timeliness_neg"),
        ("delayed", "timeliness_neg"),
        ("delays", "timeliness_neg"),
        ("waiting", "waiting_neg"),
        ("waited", "waiting_neg"),
        ("slow", "timeliness_neg"),
        # positive
        ("made sure everything was done correctly and on time", "timeliness_pos"),
        ("met all deadlines", "timeliness_pos"),
        ("met deadlines", "timeliness_pos"),
        ("ahead of schedule", "timeliness_pos"),
        ("in a timely manner", "timeliness_pos"),
        ("timely manner", "timeliness_pos"),
        ("on time", "timeliness_pos"),
        ("timely", "timeliness_pos"),
        ("promptly", "timeliness_pos"),
        ("quickly", "timeliness_pos"),
        ("efficient", "efficiency_pos"),
    ],
    "office_staff_experience": [
        # positive -- "polite" routed here (not professionalism_trust) per calibration finding
        ("very polite staff", "staff_pos"),
        ("polite staff", "staff_pos"),
        ("very polite", "staff_pos"),
        ("polite", "staff_pos"),
        ("wonderful staff", "staff_pos"),
        ("amazing staff", "staff_pos"),
        ("great staff", "staff_pos"),
        ("friendly staff", "staff_pos"),
        ("helpful staff", "staff_pos"),
        ("kind staff", "staff_pos"),
        # negative
        ("phone assistant was hired to tell people", "staff_neg"),
        ("their phone assistant", "staff_neg"),
        ("sent his inexperienced son", "staff_neg"),
        ("incompetent staff", "staff_neg"),
        ("unhelpful staff", "staff_neg"),
        ("rude staff", "staff_neg"),
        ("inexperienced", "staff_neg"),
        # general
        ("legal assistant", "staff_general"),
        ("legal aide", "staff_general"),
        ("office staff was", "staff_general"),
        ("office staff", "staff_general"),
        ("our office", "office_general"),
        ("this office", "office_general"),
        ("the office", "office_general"),
        ("paralegal", "staff_general"),
        ("receptionist", "staff_general"),
        ("front desk", "staff_general"),
        ("secretary", "staff_general"),
        ("assistant", "staff_general"),
        ("staff", "staff_general"),
        ("team", "team_general"),
        # NOTE: bare "office" removed -- too broad, causes false routing
    ],
    "outcome_satisfaction": [
        # negative
        ("went 2 and a half years to lose all", "outcome_neg"),
        ("2 and a half years to lose", "outcome_neg"),
        ("failed me during my appeal", "outcome_neg"),
        ("failed during appeal", "outcome_neg"),
        ("they failed me", "outcome_neg"),
        ("never got proper legal help from him", "outcome_neg"),
        ("never got proper legal help", "outcome_neg"),
        ("still lost my license", "outcome_neg"),
        ("worst outcome", "outcome_neg"),
        ("bad outcome", "outcome_neg"),
        ("did not get the outcome", "outcome_neg"),
        ("lost my case", "outcome_neg"),
        ("didn't win", "outcome_neg"),
        ("did not win", "outcome_neg"),
        ("dismissed", "outcome_neg"),
        ("lost", "outcome_neg"),
        ("case was forgotten", "outcome_neg"),
        ("forgotten about", "outcome_neg"),
        ("case forgotten", "outcome_neg"),
        ("did not even work there anymore", "outcome_neg"),
        ("stuck without legal", "outcome_neg"),
        ("charged me the full amount", "outcome_neg"),
        ("got nothing", "outcome_neg"),
        ("wouldn't be getting anything back", "outcome_neg"),
        ("not getting anything back", "outcome_neg"),
        # positive
        ("satisfied with the outcome", "outcome_pos"),
        ("very satisfying", "outcome_pos"),
        ("great outcome", "outcome_pos"),
        ("favorable outcome", "outcome_pos"),
        ("got my case handled", "outcome_pos"),
        ("finally got justice", "outcome_pos"),
        ("got justice", "outcome_pos"),
        ("helped me be approved", "outcome_pos"),
        ("got approved", "outcome_pos"),
        ("approved", "outcome_pos"),
        ("case was resolved", "outcome_pos"),
        ("favorable", "outcome_pos"),
        ("resolved", "outcome_pos"),
        ("successful", "outcome_pos"),
        ("settlement", "outcome_general"),
        ("verdict", "outcome_general"),
        ("victory", "outcome_pos"),
        ("won my case", "outcome_pos"),
        ("won", "outcome_pos"),
        ("result", "outcome_general"),
        ("outcome", "outcome_general"),
    ],
}


# ---------------------------------------------------------------------------
# Negation context tokens
# ---------------------------------------------------------------------------
NEGATION_TOKENS = frozenset([
    "not", "never", "no", "didn't", "did not", "wasn't", "was not",
    "couldn't", "could not", "wouldn't", "would not", "barely",
    "hardly", "lack", "lacking", "lacks", "failed", "fail", "fails",
    "without", "absence",
])

# Contrast guards: signal the rest of the sentence reverses prior tone.
CONTRAST_TOKENS = frozenset(["but", "however", "although", "though", "except", "despite"])

# ---------------------------------------------------------------------------
# Severity amplifiers
# ---------------------------------------------------------------------------
SEVERE_AMPLIFIERS = [
    "worst", "terrible", "awful", "nightmare", "disaster",
    "completely", "absolutely", "totally", "ruined", "destroyed",
    "never again", "waste of money", "scam", "fraud", "lied",
    "threatened", "illegal", "malpractice", "negligent",
    "incompetent", "unacceptable", "horrific", "disgusting",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sentences(text: str) -> list[str]:
    """Split review text into sentences on [.!?] followed by whitespace."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _has_proximal_negation(sentence_lower: str, phrase: str, before_only: bool = False) -> bool:
    """
    Return True only if a negation token appears within NEGATION_PROXIMITY_TOKENS
    tokens of the matched phrase.

    Prevents cross-clause false positives such as:
      "if not available she returned my calls"
    where "not" belongs to a different clause and should NOT negate
    "returned my call".

    before_only=True: only check tokens that precede the phrase (used for _neg
    families so that "crooked law office, do not trust" does not let "not" from
    the second clause flip "crooked" to positive).
    """
    if phrase not in sentence_lower:
        tokens = set(re.split(r"\W+", sentence_lower))
        return bool(tokens & NEGATION_TOKENS)

    all_tokens = re.split(r"\W+", sentence_lower)
    phrase_tokens = re.split(r"\W+", phrase)
    first_phrase_tok = phrase_tokens[0] if phrase_tokens else ""

    phrase_idx = None
    for i, tok in enumerate(all_tokens):
        if tok == first_phrase_tok:
            phrase_idx = i
            break

    if phrase_idx is None:
        tokens = set(all_tokens)
        return bool(tokens & NEGATION_TOKENS)

    window_start = max(0, phrase_idx - NEGATION_PROXIMITY_TOKENS)
    if before_only:
        # Only look at tokens before the phrase start
        window_end = phrase_idx
    else:
        window_end = min(len(all_tokens), phrase_idx + len(phrase_tokens) + NEGATION_PROXIMITY_TOKENS)
    window_tokens = set(all_tokens[window_start:window_end])
    return bool(window_tokens & NEGATION_TOKENS)


def _has_negation(sentence_lower: str, phrase: str = "") -> bool:
    """Compatibility wrapper. Uses proximal negation when phrase is provided."""
    if phrase:
        return _has_proximal_negation(sentence_lower, phrase)
    tokens = set(re.split(r"\W+", sentence_lower))
    return bool(tokens & NEGATION_TOKENS)


def _has_contrast(sentence_lower: str) -> bool:
    tokens = set(re.split(r"\W+", sentence_lower))
    return bool(tokens & CONTRAST_TOKENS)


def _has_duration_severity(text_lower: str) -> bool:
    """
    Return True if the text contains a duration-based delay pattern
    warranting severe_negative escalation (e.g. "delayed 5 months").
    """
    return bool(_DURATION_SEVERE_PATTERNS.search(text_lower))


def _infer_polarity(
    rating: int,
    sentence_lower: str,
    family_label: str,
    text_lower: str,
    phrase: str = "",
) -> str:
    """
    Infer polarity from star rating + linguistic context.

    Returns: "positive" | "negative" | "severe_negative"

    Guard order:
    1. Duration-based severity escalation (timeliness delay + long span -> severe_negative)
    2. Severity amplifier check
    3. Inherently-negative family (with proximal negation guard)
    4. Inherently-positive family
    5. Ambiguous family -- use star rating
    """
    # 1. Duration-based severity escalation for timeliness themes
    if family_label in ("timeliness_neg", "waiting_neg") and _has_duration_severity(text_lower):
        return "severe_negative"

    # 2. Severity amplifier check
    if any(amp in text_lower for amp in SEVERE_AMPLIFIERS):
        if rating <= 2 or family_label.endswith("_neg"):
            return "severe_negative"

    # 3. Inherently negative family
    if family_label.endswith("_neg"):
        # Double-negative guard: phrase already encodes negation, don't flip back.
        # NOTE: "without" is intentionally excluded here -- it is the negative
        # trigger itself in phrases like "without replies", not a double-negation.
        phrase_is_compound_negative = any(
            neg in phrase for neg in ("not ", "n't ", "never ", "no ")
        )
        # Use before_only=True: only allow negation tokens that appear BEFORE
        # the phrase to flip it positive (e.g. "not responsive"). Negation tokens
        # in subsequent clauses (e.g. "crooked law office, do NOT trust") should
        # not retroactively flip an already-negative phrase to positive.
        if (
            _has_proximal_negation(sentence_lower, phrase, before_only=True)
            and not _has_contrast(sentence_lower)
            and not phrase_is_compound_negative
        ):
            return "positive"
        return "negative"

    # 4. Inherently positive family
    if family_label.endswith("_pos"):
        if _has_proximal_negation(sentence_lower, phrase):
            return "negative"
        return "positive"

    # 5. Ambiguous family -- use rating
    if rating >= 4:
        return "positive"
    if rating <= 2:
        return "negative"
    # 3-star: trust contrast/negation, otherwise positive
    if _has_contrast(sentence_lower) or _has_proximal_negation(sentence_lower, phrase):
        return "negative"
    return "positive"


def _confidence(
    match_count: int,
    rating: int,
    polarity: str,
    family_label: str,
) -> str:
    """
    Coarse confidence estimate.

    high   -> multiple phrase hits, or rating strongly confirms polarity
    medium -> single hit with weak signal
    low    -> ambiguous (e.g. 3-star with neutral family)
    """
    strongly_confirmed = (
        (polarity == "positive" and rating >= 4)
        or (polarity in ("negative", "severe_negative") and rating <= 2)
    )
    if match_count >= 2 or (match_count == 1 and strongly_confirmed):
        return "high"
    if match_count == 1 and (
        rating == 3
        or not (family_label.endswith("_pos") or family_label.endswith("_neg"))
    ):
        return "low"
    return "medium"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def tag_review(
    review_text: str,
    rating: int,
    review_date: str | None = None,
) -> dict[str, Any]:
    """
    Run the deterministic theme tagger on a single review.

    Parameters
    ----------
    review_text : str   Raw review text.
    rating      : int   Star rating (1-5).
    review_date : str | None  ISO date string, carried through for traceability.

    Returns
    -------
    dict with keys:
        review_text  : str
        rating       : int
        review_date  : str | None
        themes       : list[ThemeResult]   -- one per matched theme
        evidence_log : list[EvidenceEntry] -- one per phrase match

    ThemeResult keys : theme, polarity, evidence_span, confidence
    EvidenceEntry keys: theme, matched_phrase, pattern_family,
                        sentence_snippet, polarity, severity,
                        multipliers_applied, final_impact
    """
    text_lower = review_text.lower()
    sentences = _sentences(review_text)

    theme_hits: dict[str, dict] = {}
    evidence_log: list[dict] = []

    for theme, phrase_families in THEME_PHRASE_FAMILIES.items():
        for phrase, family in phrase_families:
            if phrase not in text_lower:
                continue

            # Find the sentence containing this phrase
            containing_sentence = next(
                (s for s in sentences if phrase in s.lower()),
                review_text[:120],
            )
            sent_lower = containing_sentence.lower()

            polarity = _infer_polarity(rating, sent_lower, family, text_lower, phrase)

            severity = (
                "severe" if polarity == "severe_negative"
                else "moderate" if polarity == "negative"
                else "low"
            )

            multipliers: list[str] = []
            if any(amp in text_lower for amp in SEVERE_AMPLIFIERS):
                multipliers.append("severe_amplifier")
            if _has_proximal_negation(sent_lower, phrase):
                multipliers.append("negation_present")
            if _has_contrast(sent_lower):
                multipliers.append("contrast_guard")
            if _has_duration_severity(text_lower) and family in ("timeliness_neg", "waiting_neg"):
                multipliers.append("duration_severity_escalation")

            final_impact = (
                "severe_hit" if polarity == "severe_negative"
                else "negative_hit" if polarity == "negative"
                else "positive_hit"
            )

            evidence_log.append({
                "theme": theme,
                "matched_phrase": phrase,
                "pattern_family": family,
                "sentence_snippet": containing_sentence[:200],
                "polarity": polarity,
                "severity": severity,
                "multipliers_applied": multipliers,
                "final_impact": final_impact,
            })

            if theme not in theme_hits:
                theme_hits[theme] = {
                    "hits": 0,
                    "evidence_span": containing_sentence[:200],
                    "polarity_votes": [],
                    "families": set(),
                }
            theme_hits[theme]["hits"] += 1
            theme_hits[theme]["polarity_votes"].append(polarity)
            theme_hits[theme]["families"].add(family)

    # Collapse per-theme hits into ThemeResult objects
    themes: list[dict] = []
    for theme, acc in theme_hits.items():
        votes = acc["polarity_votes"]
        if "severe_negative" in votes:
            final_polarity = "severe_negative"
        elif votes.count("negative") > votes.count("positive"):
            final_polarity = "negative"
        else:
            final_polarity = "positive"

        dominant_family = next(
            (f for f in acc["families"] if f.endswith("_neg") or f.endswith("_pos")),
            next(iter(acc["families"]), ""),
        )
        conf = _confidence(acc["hits"], rating, final_polarity, dominant_family)

        themes.append({
            "theme": theme,
            "polarity": final_polarity,
            "evidence_span": acc["evidence_span"],
            "confidence": conf,
        })

    return {
        "review_text": review_text,
        "rating": rating,
        "review_date": review_date,
        "themes": themes,
        "evidence_log": evidence_log,
    }
