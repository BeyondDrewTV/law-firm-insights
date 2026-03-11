#!/usr/bin/env python3
"""
Clarion Engine — Synthetic Review Top-Up Generator

Generates additional synthetic reviews targeting specific star ratings
and themes that are thin in your current dataset. Output is a JSON file
that can be merged with merge_calibration_data.py.

Usage:
    python scripts/generate_synthetic_topup.py \
        --star 2 --count 20 --theme billing \
        --output data/synthetic_topup.json

    # Generate multiple star ratings at once:
    python scripts/generate_synthetic_topup.py \
        --batch "2:15,3:20,4:15" \
        --output data/synthetic_topup.json

Notes:
    - Uses purely local template-based generation (no API calls)
    - Reviews are clearly tagged source=synthetic
    - Designed to fill gaps without skewing theme distribution
"""

import argparse
import json
import random
import sys
from pathlib import Path

# ─────────────────────────────────────────────
# THEME TEMPLATES BY STAR RATING
# Each entry: (review_text_template, owner_response_template_or_None)
# {lawyer} and {firm} are filled with random names
# ─────────────────────────────────────────────

LAWYER_NAMES = [
    "Mr. Harris", "Ms. Chen", "Attorney Davis", "Mr. Patel", "Ms. Okonkwo",
    "Mr. Rivera", "Ms. Thompson", "Attorney Walsh", "Mr. Kim", "Ms. Reyes",
    "Mr. Nguyen", "Ms. Goldstein", "Attorney Brooks", "Mr. Castillo", "Ms. Huang"
]

FIRM_NAMES = [
    "this firm", "their office", "the practice", "their team", "this law office"
]

TEMPLATES = {
    2: [
        # Billing complaints
        ("{lawyer} handled my case but the billing was confusing and I felt overcharged for routine phone calls. The outcome was acceptable but I left feeling like I was nickel-and-dimed throughout the process.", 
         "We appreciate your feedback and take billing transparency seriously. We would welcome the opportunity to review your itemized statement with you."),
        ("Had a frustrating experience with {firm}. The attorney seemed competent but communication was poor. I often had to chase them down for updates. Took much longer than expected.",
         None),
        ("{lawyer} got the job done but barely. I had to repeat myself multiple times and felt like I wasn't a priority. For the money I paid I expected more attentiveness.",
         "Thank you for taking the time to share this. Client communication is something we continuously work to improve."),
        ("The legal work was fine but {firm} overcharged and was slow to respond to emails. I've worked with other attorneys who were more proactive. Wouldn't use them again.",
         None),
        ("I felt dismissed during consultations with {lawyer}. My questions were answered quickly without much depth. The case resolved okay but I never felt confident in the representation.",
         "We're sorry to hear you felt this way. We strive to make every client feel heard and supported throughout their matter."),
        # Outcome disappointment
        ("The result of my case was not what {lawyer} led me to expect. I understand outcomes aren't guaranteed but the disconnect between early expectations and reality was significant.",
         "We understand how difficult unexpected outcomes can be. We always aim to set realistic expectations, and we welcome the chance to speak further."),
        ("I gave {firm} two stars because while they were professional, the strategy they took on my case felt wrong in hindsight. Not sure I'd trust them with anything complex again.",
         None),
        # Timeliness
        ("Months went by with no meaningful progress. {lawyer} always had a reason for the delays but it got old fast. Eventually things worked out but the timeline was unacceptable.",
         "Timelines in legal matters are often outside our direct control, but we hear your frustration and appreciate you sharing it."),
        # Empathy
        ("The attorney handling my divorce case through {firm} was technically skilled but emotionally cold. Going through a divorce is already devastating — I needed more compassion than I got.",
         None),
        ("I felt like just a file number to {lawyer}. Got my matter resolved, but the experience left a lot to be desired in terms of personal attention and empathy.",
         "We're sorry the experience felt impersonal. We truly do care about each client's situation and will reflect on how to better convey that."),
    ],
    3: [
        # Balanced / ambiguous
        ("{lawyer} did okay work on my case. Nothing exceptional but nothing terrible either. Communication was average and the outcome was roughly what I expected. Decent but not memorable.",
         None),
        ("Mixed experience with {firm}. Some of the staff were very helpful, others seemed indifferent. The final result was satisfactory. Might use them again for a simpler matter.",
         "Thank you for sharing a balanced perspective. We're committed to providing consistent quality across our entire team."),
        ("Three stars feels right. {lawyer} was professional and prepared, but I felt like I could have gotten the same result for less money somewhere else. The value wasn't quite there.",
         None),
        ("The good: {lawyer} clearly knows the law. The bad: response times were slow and the office was sometimes hard to reach. Net result — a fine but unremarkable experience.",
         "We appreciate the honest feedback. We are actively working on improving our response times for all client communications."),
        ("I got what I hired {firm} for but the process was bumpier than it needed to be. A few miscommunications along the way made things stressful. Outcome was fine.",
         None),
        # Billing neutral
        ("Average experience. {lawyer} was thorough but the billing felt a bit opaque. I'm not sure every hour billed was truly necessary. Would want more clarity next time.",
         "We take billing transparency seriously and are happy to walk through any invoice in detail. Please don't hesitate to reach out."),
        # Professionalism neutral
        ("{firm} handled my matter adequately. The attorney was knowledgeable but seemed stretched thin between cases. Not bad, not great — right in the middle.",
         None),
        ("I hired {lawyer} for a business contract dispute. The representation was competent but the strategy felt conservative. We settled, which was probably the right call, but I left wanting more.",
         None),
        # Communication neutral
        ("Communication was hit or miss with {firm}. When I could get someone on the phone they were helpful, but getting to that point sometimes took longer than it should. Results were acceptable.",
         "Thank you for this feedback — communication consistency is an area we are actively improving across the board."),
        ("Solid but not spectacular. {lawyer} handled the basics well but I expected more strategic guidance. For straightforward matters I'd return. For complex litigation I'd look elsewhere.",
         None),
    ],
    4: [
        # Mostly positive with one caveat
        ("{lawyer} did excellent work on my personal injury claim. The only reason I'm not giving 5 stars is that communication during the middle months of the case dropped off significantly.",
         "Thank you so much for the kind words. We hear you on communication and are implementing new check-in procedures for long-running cases."),
        ("Very happy with the outcome of my case thanks to {firm}. They were professional and prepared. Docking one star only because the billing statements were hard to read and felt disorganized.",
         None),
        ("{lawyer} is clearly a skilled attorney. Got a great result for our business dispute. Communication was excellent. Knocking off one star because the timeline ran about 2 months longer than estimated.",
         "We appreciate your kind review and understand the timeline concern. We strive to give accurate projections and will work to improve that."),
        ("Great experience overall with {firm}. The attorney was empathetic, thorough, and aggressive when needed. The only hiccup was an administrative mix-up early on that caused some unnecessary stress.",
         "Thank you for the wonderful review! We apologize for the early administrative issue and are glad it didn't affect the final outcome."),
        ("{lawyer} fought hard for me and delivered a strong result. I'd recommend them to friends. The one thing I'd change is more frequent proactive updates — I had to initiate most check-ins myself.",
         None),
        # Outcome positive, process caveat
        ("Won my case with the help of {firm}. The legal strategy was spot-on. I'm giving 4 stars instead of 5 because the paralegal team seemed overloaded and dropped the ball on a few document requests.",
         "We're thrilled with your outcome and take your staffing feedback seriously. Thank you for helping us identify areas to strengthen."),
        ("Really pleased with {lawyer}'s representation. Knowledgeable, honest, and genuinely cared about my situation. Billing was on the higher end of what I expected, hence 4 stars instead of 5.",
         "Thank you for this generous review. We always aim to provide value that justifies our fees and appreciate your candor."),
        ("Strong recommend for {firm} with one caveat — the intake process was slow and confusing. Once the case got rolling, everything was excellent. End result exceeded my expectations.",
         None),
        ("4 stars. {lawyer} handled my immigration case with professionalism and care. My only complaint is the waiting room and office setup felt outdated and unprofessional compared to the legal work quality.",
         None),
        ("{lawyer} was fantastic to work with. Clear communicator, aggressive negotiator, and always available. Slight billing surprise at the end keeps this at 4 stars, but I'd use them again without hesitation.",
         "Thank you for the kind words! We're looking into how we can improve billing estimate accuracy for future clients."),
    ],
    1: [
        ("Do not use {firm}. They took my retainer, did almost no work, and stopped returning my calls. I had to hire a new attorney to fix the mess they left. An absolute nightmare.",
         "We take these concerns seriously and would like the opportunity to speak with you directly. Please contact our office."),
        ("{lawyer} cost me thousands of dollars and made my situation significantly worse. Missed a critical filing deadline that tanked my case. Zero accountability, zero apology.",
         None),
        ("Worst legal experience of my life. {firm} was disorganized, unresponsive, and frankly incompetent. I'm pursuing a bar complaint and a fee dispute. Stay away.",
         "We are deeply sorry to hear about your experience. Please reach out to our managing partner directly so we can address this matter."),
        ("I paid a hefty retainer to {lawyer} and got almost nothing in return. My case was handed off to a junior associate who had no idea what was going on. Complete waste of money.",
         None),
        ("{firm} left me hanging at the worst possible moment. No communication for weeks, then a rushed settlement push that clearly benefited them more than me. Felt completely betrayed.",
         "We understand your frustration and want to assure you that client interests always come first. We'd welcome the chance to discuss this directly."),
    ],
    5: [
        ("{lawyer} is exceptional. From the first consultation to the final resolution, I felt fully supported and informed. The outcome exceeded my expectations. Highly recommended.",
         None),
        ("I can't say enough good things about {firm}. Professional, compassionate, and incredibly effective. They turned a terrifying situation into a manageable one. 10/10.",
         "Thank you so much for this wonderful review! It means the world to our entire team."),
        ("{lawyer} handled my case with expertise and genuine care. Always available, always prepared, always honest. The result was outstanding. I've already referred two friends.",
         None),
        ("Outstanding experience from start to finish with {firm}. Clear communication, transparent billing, and a fantastic outcome. This is what great legal representation looks like.",
         "We are so grateful for your kind words and your referrals. Thank you for trusting us."),
        ("Five stars without hesitation. {lawyer} is everything you want in an attorney — smart, strategic, and deeply human. Made me feel like my case actually mattered.",
         None),
    ],
}

THEME_TAGS = {
    2: ["billing", "communication", "outcome_disappointment", "timeliness", "empathy"],
    3: ["balanced", "billing_neutral", "communication_neutral", "professionalism_neutral", "value"],
    4: ["mostly_positive", "communication_caveat", "billing_caveat", "process_caveat", "outcome_positive"],
    1: ["severe_negative", "misconduct", "abandonment", "deadline_miss", "overcharge"],
    5: ["strong_positive", "referral_worthy", "exceptional_outcome", "full_service"],
}


def generate_reviews(star: int, count: int, theme: str | None = None) -> list[dict]:
    if star not in TEMPLATES:
        sys.exit(f"❌ No templates for {star}-star reviews")

    templates = TEMPLATES[star]
    reviews = []
    used_indices = set()

    for i in range(count):
        # Cycle through templates to avoid exact duplicates
        available = [j for j in range(len(templates)) if j not in used_indices]
        if not available:
            used_indices.clear()
            available = list(range(len(templates)))

        idx = random.choice(available)
        used_indices.add(idx)
        text_template, owner_template = templates[idx]

        lawyer = random.choice(LAWYER_NAMES)
        firm = random.choice(FIRM_NAMES)

        text = text_template.format(lawyer=lawyer, firm=firm)
        owner_response = ""
        if owner_template:
            # ~60% chance of including owner response for 2-4 star
            if star in [2, 3, 4] and random.random() < 0.6:
                owner_response = owner_template.format(lawyer=lawyer, firm=firm)
            elif star == 1 and random.random() < 0.8:
                owner_response = owner_template.format(lawyer=lawyer, firm=firm)

        tag = theme or random.choice(THEME_TAGS.get(star, ["general"]))

        reviews.append({
            "review_text": text,
            "rating": star,
            "owner_response": owner_response,
            "date": "2025-01-01",
            "source": "synthetic",
            "theme": tag,
            "subtype": f"{star}star_topup"
        })

    return reviews


def main():
    parser = argparse.ArgumentParser(description="Clarion Synthetic Review Top-Up Generator")
    parser.add_argument("--star", type=int, choices=[1, 2, 3, 4, 5], help="Star rating to generate")
    parser.add_argument("--count", type=int, default=10, help="Number of reviews to generate (default: 10)")
    parser.add_argument("--theme", type=str, help="Optional theme tag to apply")
    parser.add_argument("--batch", type=str, help="Batch mode: comma-separated star:count pairs, e.g. '2:15,3:20,4:15'")
    parser.add_argument("--output", default="data/synthetic_topup.json", help="Output JSON file path")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if not args.star and not args.batch:
        sys.exit("❌ Provide either --star or --batch")

    all_reviews = []

    if args.batch:
        print(f"\nBatch mode: {args.batch}")
        for pair in args.batch.split(","):
            pair = pair.strip()
            try:
                star_str, count_str = pair.split(":")
                star = int(star_str.strip())
                count = int(count_str.strip())
            except ValueError:
                sys.exit(f"❌ Invalid batch format '{pair}' — use star:count e.g. '2:15'")
            reviews = generate_reviews(star, count, args.theme)
            all_reviews.extend(reviews)
            print(f"  → Generated {len(reviews)} {star}★ reviews")
    else:
        reviews = generate_reviews(args.star, args.count, args.theme)
        all_reviews.extend(reviews)
        print(f"\nGenerated {len(reviews)} {args.star}★ reviews")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, indent=2, ensure_ascii=False)

    print(f"\n✅ {len(all_reviews)} synthetic reviews written → {output_path}")
    print(f"   Merge with: python scripts/merge_calibration_data.py --csv <real.csv> --json {output_path}")


if __name__ == "__main__":
    main()
