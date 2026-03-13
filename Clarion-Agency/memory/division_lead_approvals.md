# division_lead_approvals.md
# Clarion Agent Office — Division Lead Approval Register
# Version: 2.0 | 2026-03-12

---

## Purpose

Tracks Level 2 actions approved by division leads that do NOT require CEO approval.
The runner checks this file before executing any Level 2 artifact.

Level 2 action types: create_social_account, publish_blog_post, send_outreach_batch,
upload_demo_video, post_linkedin_thread, account_setup.

Division leads are humans, not agents. An agent may not approve its own actions.

## Format

  ## DLA-NNN
  ACTION: [action type or description — one sentence]
  DIVISION: [Comms & Content | Sales | Market Intelligence | Product Insight]
  APPROVED_BY: [name or role]
  DATE: [YYYY-MM-DD]
  STATUS: [staged | approved | in_progress | completed | blocked]
  NOTES: [optional context]

STATUS must be exactly "approved" for the runner to execute.

---

## Active Approvals

## DLA-001
ACTION: send_outreach_batch — send up to 10 cold outreach emails per run to qualified law firm prospects
DIVISION: Sales
APPROVED_BY: Founder (Drew)
DATE: 2026-03-12
STATUS: staged
NOTES: Set STATUS to "approved" when email credentials are confirmed in .env. Max 10/run enforced by runner.

## DLA-002
ACTION: publish_blog_post — publish pre-written blog posts about Clarion and law firm governance
DIVISION: Comms & Content
APPROVED_BY: Founder (Drew)
DATE: 2026-03-12
STATUS: staged
NOTES: Set STATUS to "approved" to allow auto-publishing when CMS credentials are configured.

## DLA-003
ACTION: post_linkedin_thread — post Clarion content threads to LinkedIn
DIVISION: Comms & Content
APPROVED_BY: Founder (Drew)
DATE: 2026-03-12
STATUS: staged
NOTES: Set STATUS to "approved" when LINKEDIN_ACCESS_TOKEN is added to .env.

---

## Completed

(none yet)
