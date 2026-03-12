# tool_permissions.md
# Clarion Agent Office — Tool & File Permissions Matrix
# Version: 1.0 | 2026-03-12
# Agents may read. Agents may never modify.

---

## PURPOSE
Defines which agents and divisions may read, write, or require approval to touch
each system, file, or capability. Unlisted access is prohibited by default.

---

## KEY

read: May read this file to inform their work
write: May append or update this file as part of normal authorized work
approval_required: Must have an entry in approved_actions.md before writing
prohibited: This agent/division may not touch this file or system under any circumstances

---

## FILE: leads_pipeline.csv

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Sales Development        | yes  | yes   | no (append only)  | Delete rows, change status of other agents' leads |
| Customer Discovery       | yes  | no    | —                 | Any write                  |
| Head of Growth           | yes  | no    | —                 | Any write                  |
| Funnel Conversion        | yes  | no    | —                 | Any write                  |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| All other agents         | no   | no    | —                 | Read or write              |

---

## FILE: lead_research_queue.csv

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Customer Discovery       | yes  | yes   | no (append only)  | Remove entries, reorder queue |
| Sales Development        | yes  | no    | —                 | Any write                  |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| All other agents         | no   | no    | —                 | Read or write              |

---

## FILE: memory/conversion_friction.md

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Funnel Conversion        | yes  | yes   | no (append only)  | Overwrite or delete prior entries |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| Head of Growth           | yes  | no    | —                 | Any write                  |
| All other agents         | no   | no    | —                 | Read or write              |

---

## FILE: memory/incidents_log.md (or data/incidents/)

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Internal Process Analyst | yes  | yes   | no (append only)  | Close or delete incidents  |
| Scoring Quality          | yes  | yes   | no (append only)  | Close or delete incidents  |
| Data Quality             | yes  | yes   | no (append only)  | Close or delete incidents  |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| All other agents         | yes  | no    | —                 | Any write                  |

---

## FILE: memory/competitor_tracking.md

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Competitive Intelligence | yes  | yes   | no (append only)  | Downgrade threat level, delete entries |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| Head of Growth           | yes  | no    | —                 | Any write                  |
| All other agents         | yes  | no    | —                 | Any write                  |

---

## FILE: memory/proof_assets.md

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| VoC & Product Demand     | yes  | yes   | no (append only)  | Name a customer without CEO approval |
| Customer Health          | yes  | yes   | no (append only)  | Name a customer without CEO approval |
| Content & SEO Agent      | yes  | no    | yes               | Write or use for publishing without approval |
| Chief of Staff           | yes  | no    | —                 | Any write                  |
| All other agents         | yes  | no    | —                 | Any write                  |

---

## FILE: memory/division_lead_approvals.md

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| Chief of Staff           | yes  | yes   | no                | Grant approvals outside defined authority |
| Division Leads           | yes  | no    | —                 | Self-approve own actions   |
| All other agents         | yes  | no    | —                 | Any write                  |

---

## FILE: memory/approved_actions.md

| Division / Agent         | Read | Write | Approval Required | Prohibited Actions          |
|--------------------------|------|-------|-------------------|----------------------------|
| CEO only                 | yes  | yes   | n/a               | —                          |
| All agents               | yes  | no    | —                 | Add, modify, or remove entries |

---

## CAPABILITY: Website Inspection (public)

| Division / Agent         | Allowed | Approval Required | Prohibited Actions             |
|--------------------------|---------|-------------------|-------------------------------|
| Customer Discovery       | yes     | no                | Interact with or submit forms |
| Competitive Intelligence | yes     | no                | Interact with or submit forms |
| Content & SEO Agent      | yes     | no                | Interact with or submit forms |
| All other agents         | no      | —                 | Any inspection                |

---

## CAPABILITY: Public-Source Research (web reading, LinkedIn, forums)

| Division / Agent         | Allowed | Approval Required | Prohibited Actions                      |
|--------------------------|---------|-------------------|-----------------------------------------|
| Customer Discovery       | yes     | no                | Contact, message, or interact with anyone |
| Competitive Intelligence | yes     | no                | Contact, message, or interact with anyone |
| Market Trends (if active)| yes     | no                | Contact, message, or interact with anyone |
| All other agents         | no      | —                 | Any external reading                    |

---

## CAPABILITY: Outreach Drafting (internal draft only — not sending)

| Division / Agent         | Allowed | Approval Required | Prohibited Actions              |
|--------------------------|---------|-------------------|---------------------------------|
| Sales Development        | yes     | no (draft only)   | Send, post, or publish anything |
| Content & SEO Agent      | yes     | no (draft only)   | Send, post, or publish anything |
| All other agents         | no      | —                 | Draft outreach copy             |

---

## CAPABILITY: Public Posting Drafts (for CEO review — not live)

| Division / Agent         | Allowed | Approval Required | Prohibited Actions              |
|--------------------------|---------|-------------------|---------------------------------|
| Content & SEO Agent      | yes     | yes (to publish)  | Post to any live channel without approval |
| All other agents         | no      | —                 | Prepare any public content      |

---

## GLOBAL PROHIBITION
No agent may execute any of the following without an explicit entry in approved_actions.md with STATUS: approved:
- Send any email, message, or communication externally
- Post to any social media or content platform
- Create any external account, profile, or registration
- Commit to any financial, legal, or contractual obligation
- Modify any backend code, scoring engine, phrase dictionary, or database
