# social_authenticity_upgrade.md
# Clarion Agency — Social Authenticity Upgrade

**Date:** 2026-03-12
**Author:** Agency Config Session
**Status:** Complete

---

## What Was Added

A human social cadence and authenticity layer ensuring Clarion's social presence
feels like a knowledgeable practitioner, not a content machine.

---

## Files Created

### `memory/social_posting_cadence.md`
Defines cadence targets (LinkedIn 2–4/week, Twitter/X 3–6/week), organic variation
rules (no identical times or days, occasional skip days), community participation
guidance (contextual, not constant), full authenticity rules for drafting (sentence
variety, prohibited AI phrasing, format rotation, educational-over-promotional tone),
and a flagging table of five warning patterns for the Chief of Staff.

---

## Files Modified

### `agents/comms/content_seo.md`
Added `## Social Authenticity Rules` section between `## External Interaction Policy`
and `## Guardrails`. Covers: sentence length variation, prohibited AI-phrasing,
brand voice reference, format rotation, educational tone requirement, experienced-reader
framing, repetition self-check, and cadence guidance for scheduling proposals.

### `agents/revenue/head_of_growth.md`
Same `## Social Authenticity Rules` section added in the same position.

### `agents/executive/chief_of_staff.md`
Two additive changes:

**1. Section H — Social Health Check** (Office Health Evaluation block)
Added after Section G. Directs CoS to review post drafts and scheduling proposals
from Content & SEO and Head of Growth against `memory/social_posting_cadence.md`.
Flags five warning patterns: overly regular cadence, overly frequent posting,
repetitive structure, volume over quality, promotional drift. Default output:
"None detected."

**2. SOCIAL HEALTH block** (CEO Brief Report Format)
Added between MISSING REPORTS and HISTORICAL SUMMARIZATION in the report template.
Format mirrors other brief sections: agent, pattern, detail, recommendation.

---

## Files Not Modified

- All other agent files
- All backend, frontend, and production scoring files
- All existing memory files (moderation_log.md, security_incident_log.md, etc.)
- `memory/brand_voice.md` and `memory/external_interaction_policy.md` — referenced
  by name from the new rules but not edited

---

## Blocked Items

None.
