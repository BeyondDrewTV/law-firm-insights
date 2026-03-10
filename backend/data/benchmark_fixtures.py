"""
data/benchmark_fixtures.py

Seed dataset for the Clarion benchmark harness.

Contains 28 representative law-firm client reviews spanning all 10 governance
themes, multiple polarity combinations, edge cases (negation, contrast, mixed
sentiment), and severity gradients.

These fixtures are used by:
  - /internal/benchmark/batch  (POST with fixtures=true)
  - Unit tests in tests/test_benchmark*.py

Each fixture is a dict with keys:
  id          -- short identifier
  review_text -- raw review text as a client would write it
  rating      -- integer 1-5
  date        -- ISO date string
  notes       -- human-readable note about why this fixture is interesting
"""

BENCHMARK_FIXTURES = [
    {
        "id": "F01",
        "review_text": (
            "John was always available and responded within the hour. "
            "He clearly explained every step of the process in plain language. "
            "We won our case and I couldn't be happier with the result."
        ),
        "rating": 5,
        "date": "2025-01-10",
        "notes": "Strongly positive across communication_responsiveness, communication_clarity, outcome_satisfaction.",
    },
    {
        "id": "F02",
        "review_text": (
            "I never heard back after leaving three voicemails. "
            "Weeks went by without any contact. "
            "The fees were also a surprise -- nobody explained the billing upfront."
        ),
        "rating": 1,
        "date": "2025-01-12",
        "notes": "Severe negatives: communication_responsiveness, billing_transparency.",
    },
    {
        "id": "F03",
        "review_text": (
            "The attorney was professional and trustworthy. "
            "However, the office staff was rude when I called to check in. "
            "The case outcome was disappointing -- I expected a better settlement."
        ),
        "rating": 3,
        "date": "2025-01-15",
        "notes": "Mixed: positive professionalism_trust, negative office_staff_experience, negative outcome_satisfaction. Contrast guard test.",
    },
    {
        "id": "F04",
        "review_text": (
            "She was not responsive at all. I couldn't reach her for two weeks. "
            "When I finally got through, she didn't explain what was happening with my case."
        ),
        "rating": 2,
        "date": "2025-01-18",
        "notes": "Negation test: 'not responsive', 'didn't explain'. communication_responsiveness + communication_clarity.",
    },
    {
        "id": "F05",
        "review_text": (
            "They were not rude -- actually quite polite. "
            "The billing was not hidden at all; they were very upfront about fees. "
            "I was very happy with the result."
        ),
        "rating": 5,
        "date": "2025-01-20",
        "notes": "Negation-of-negative test. 'not rude' should flip. billing positive, outcome positive.",
    },
    {
        "id": "F06",
        "review_text": (
            "The attorney genuinely cared about my situation. "
            "She listened to all my concerns and made me feel comfortable. "
            "The fees were expensive but I think it was worth every penny."
        ),
        "rating": 5,
        "date": "2025-01-22",
        "notes": "Empathy_support positive. fee_value contrast: 'expensive' but 'worth every penny'.",
    },
    {
        "id": "F07",
        "review_text": (
            "The case took forever. There were unnecessary delays and I was never told why. "
            "I felt like just a number -- no empathy, no communication."
        ),
        "rating": 2,
        "date": "2025-01-25",
        "notes": "timeliness_progress negative, empathy_support negative, communication_clarity negative.",
    },
    {
        "id": "F08",
        "review_text": (
            "He overpromised from the start and then delivered nothing. "
            "I was guaranteed a win and lost my case completely. "
            "The fees were outrageous for what we got."
        ),
        "rating": 1,
        "date": "2025-01-28",
        "notes": "Severe: expectation_setting, outcome_satisfaction. fee_value negative.",
    },
    {
        "id": "F09",
        "review_text": (
            "Quick to respond and always kept me informed. "
            "Resolved my case quickly and the outcome was exactly what I wanted. "
            "Highly recommended."
        ),
        "rating": 5,
        "date": "2025-02-01",
        "notes": "Pure positive: communication_responsiveness, timeliness_progress, outcome_satisfaction.",
    },
    {
        "id": "F10",
        "review_text": (
            "The staff was helpful and the office was welcoming. "
            "However, I was a bit surprised by the extra charges at the end. "
            "The attorney was respectful and professional throughout."
        ),
        "rating": 4,
        "date": "2025-02-03",
        "notes": "Contrast guard: 'however' before billing surprise. Positive professionalism and staff.",
    },
    {
        "id": "F11",
        "review_text": (
            "I reported this firm to the bar association. "
            "The attorney lied to me multiple times about the status of my case. "
            "This is the worst legal experience I have ever had."
        ),
        "rating": 1,
        "date": "2025-02-05",
        "notes": "Extreme severity test: professionalism_trust severe_negative.",
    },
    {
        "id": "F12",
        "review_text": (
            "Good value for money. Reasonable fees and the work was thorough. "
            "The paralegal was incredibly helpful in keeping things moving. "
            "Would use again."
        ),
        "rating": 5,
        "date": "2025-02-07",
        "notes": "fee_value positive, office_staff_experience positive (paralegal mention).",
    },
    {
        "id": "F13",
        "review_text": (
            "Communication was okay. Not great, not terrible. "
            "The case resolved eventually but it was not as fast as I hoped. "
            "Billing was a little unclear."
        ),
        "rating": 3,
        "date": "2025-02-10",
        "notes": "Ambiguous/neutral review. Tests low-signal detection and contrast guards.",
    },
    {
        "id": "F14",
        "review_text": (
            "She missed a critical deadline which almost cost me everything. "
            "I had to hire a second attorney to fix the damage. "
            "Completely negligent."
        ),
        "rating": 1,
        "date": "2025-02-12",
        "notes": "Severe: timeliness_progress missed_critical_deadline, outcome_satisfaction malpractice/negligence.",
    },
    {
        "id": "F15",
        "review_text": (
            "Although the outcome wasn't what I hoped for, I appreciated how "
            "transparent the attorney was about the risks from the beginning. "
            "He set realistic expectations and I respect that."
        ),
        "rating": 4,
        "date": "2025-02-15",
        "notes": "Complex: 'although' contrast guard. expectation_setting positive despite negative outcome hint.",
    },
    {
        "id": "F16",
        "review_text": (
            "Felt completely dismissed every time I asked a question. "
            "The front desk was rude and disorganized. "
            "I never felt like they cared about my case at all."
        ),
        "rating": 2,
        "date": "2025-02-17",
        "notes": "empathy_support negative, office_staff_experience negative. Multiple negative signals.",
    },
    {
        "id": "F17",
        "review_text": (
            "Very fast turnaround -- they handled my case in record time. "
            "The whole team was professional and my outcome was favorable. "
            "Billing was clear and no hidden fees."
        ),
        "rating": 5,
        "date": "2025-02-19",
        "notes": "All-positive: timeliness, professionalism, outcome, billing.",
    },
    {
        "id": "F18",
        "review_text": (
            "I was surprised by a $3,000 bill I wasn't warned about. "
            "The attorney never explained the fee structure. "
            "It felt like predatory billing."
        ),
        "rating": 2,
        "date": "2025-02-21",
        "notes": "billing_transparency severe_negative (predatory billing phrase test).",
    },
    {
        "id": "F19",
        "review_text": (
            "The attorney walked me through everything step by step. "
            "I never felt kept in the dark. "
            "She gave me realistic expectations from day one."
        ),
        "rating": 5,
        "date": "2025-02-24",
        "notes": "Negation-of-negative: 'never felt kept in the dark' should resolve positive. expectation_setting positive.",
    },
    {
        "id": "F20",
        "review_text": (
            "Six months and no updates. I had to chase them constantly. "
            "When I finally got a callback the billing explanation was confusing. "
            "Not worth the money."
        ),
        "rating": 2,
        "date": "2025-02-26",
        "notes": "communication_responsiveness negative, billing_transparency negative, fee_value negative.",
    },
    {
        "id": "F21",
        "review_text": (
            "They kept me in the dark the entire time. "
            "I had no idea what was happening with my case for months."
        ),
        "rating": 2,
        "date": "2025-03-01",
        "notes": (
            "communication_clarity negative primary signal: 'kept me in the dark'. "
            "Intentional ambiguity case -- AI may reasonably tag communication_responsiveness as well "
            "since 'no idea what was happening for months' implies responsiveness failure. "
            "Useful for calibrating theme boundary between clarity and responsiveness. "
            "Expect and log AI/deterministic disagreement here; do not treat as a failure."
        ),
    },
    {
        "id": "F22",
        "review_text": (
            "I felt completely nickel and dimed every single step. "
            "Every phone call, every email -- there was a charge I wasn't warned about."
        ),
        "rating": 2,
        "date": "2025-03-03",
        "notes": "billing_transparency negative: 'nickel and dimed' idiom -- tests phrase-mining since it's not in THEME_PHRASES yet.",
    },
    {
        "id": "F23",
        "review_text": (
            "The whole process felt rushed. "
            "Important decisions were made without enough time for me to think. "
            "I was never given a chance to ask questions."
        ),
        "rating": 2,
        "date": "2025-03-05",
        "notes": "timeliness_progress / expectation_setting: 'felt rushed' idiom -- phrase mining candidate.",
    },
    {
        "id": "F24",
        "review_text": (
            "They dragged their feet for three months. "
            "Simple paperwork sat on someone's desk for weeks with no explanation."
        ),
        "rating": 2,
        "date": "2025-03-07",
        "notes": "timeliness_progress negative: 'dragged their feet' idiom -- phrase mining candidate.",
    },
    {
        "id": "F25",
        "review_text": (
            "After the initial consultation I was completely ghosted. "
            "No calls, no emails, nothing for six weeks."
        ),
        "rating": 1,
        "date": "2025-03-09",
        "notes": "communication_responsiveness severe_negative: 'ghosted' idiom -- phrase mining candidate.",
    },
    {
        "id": "F26",
        "review_text": (
            "Expensive, yes -- but absolutely worth it. "
            "The result exceeded my expectations and I would pay twice as much again."
        ),
        "rating": 5,
        "date": "2025-03-11",
        "notes": (
            "Mixed sentiment: fee_value contrast -- 'expensive' (negative signal) followed by 'worth it' "
            "(positive). Tests contrast guard + deduplication between negative and positive in same theme."
        ),
    },
    {
        "id": "F27",
        "review_text": (
            "My case moved quickly and was resolved ahead of schedule. "
            "The only frustration was that I had to chase updates constantly -- "
            "no one reached out to me proactively."
        ),
        "rating": 3,
        "date": "2025-03-13",
        "notes": (
            "timeliness_progress positive + communication_responsiveness negative co-occurring. "
            "Tests theme independence: both themes should fire independently. "
            "Validates that a positive timeliness hit is not suppressed by a co-present communication failure."
        ),
    },
    {
        "id": "F28",
        "review_text": (
            "I never heard anything unless I called first. "
            "Communication was non-existent. "
            "However, once things moved they moved fast and the outcome was great."
        ),
        "rating": 3,
        "date": "2025-03-15",
        "notes": (
            "communication_responsiveness negative + timeliness_progress positive + outcome_satisfaction positive. "
            "Communication failure WITHOUT timing failure as the dominant signal. "
            "Tests that communication_responsiveness negative does not bleed into timeliness_progress scoring."
        ),
    },
]
