# decision_log.md
# Clarion — CEO Decision Log
# Version: 1.0
#
# PURPOSE
# This file is the canonical record of major CEO decisions, standing preferences,
# and strategic defaults that agents should apply when making recommendations.
#
# HOW AGENTS USE THIS FILE
# - Agents may read this file to ground their recommendations in known CEO preferences.
# - When a recommendation would conflict with a logged decision, agents must note it
#   explicitly in their report rather than silently ignoring the conflict.
# - Agents may never write to this file directly.
#
# HOW THE LOG GROWS
# 1. An agent files a DECISION PROPOSAL block in its report.
# 2. The Chief of Staff surfaces it verbatim under DECISIONS NEEDED in the CEO brief.
# 3. The CEO reviews, decides, and either:
#    a. Adds an approved entry to this log manually, or
#    b. Records the rejection/deferral in the DECISION MEMORY UPDATES section
#       of the brief so it is logged and closed.
# 4. A decision is not in force until it appears in this file.
#
# ENTRY FORMAT
# Each entry:
#   ID:          DEC-[NNN]  (sequential, never reused)
#   Date:        YYYY-MM-DD
#   Domain:      [Pricing | Product | Revenue | Customer | Operations | Integrity | Office]
#   Decision:    [One sentence. The standing preference or approved default.]
#   Rationale:   [One sentence. Why this was decided.]
#   Applies to:  [Which agents or functions this decision governs]
#   Status:      [Active | Superseded by DEC-NNN]
#
# AMENDING DECISIONS
# To amend a decision: set its Status to "Superseded by DEC-NNN" and add a new entry.
# Never delete entries. The log is append-only.
#
# -----------------------------------------------------------------------

## Active Decisions

_No decisions logged yet. The first CEO-approved entry will appear here._

---

## Superseded Decisions

_None._
