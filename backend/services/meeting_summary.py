"""Partner meeting summary generator for governance briefs."""

from __future__ import annotations


def generate_partner_summary(brief_data):
    rating = brief_data["average_rating"]
    issue = brief_data["top_issue"]
    quote = brief_data["example_quote"]
    recommendation = brief_data["recommended_action"]

    summary = f"""
CLARION CLIENT EXPERIENCE SUMMARY

Average Rating: {rating}

Main Client Issue:
{issue}

Example Feedback:
"{quote}"

Recommended Discussion:
{recommendation}

Suggested Next Step:
Assign partner review before next meeting.
"""

    return summary
