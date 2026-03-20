# Clarion V3 Landing Architecture

## Purpose
This document defines the founder-usable messaging and page architecture for Clarion V3.

It is grounded in the product workflow that has already been smoke-tested:

`upload feedback -> structure governance signal -> assign action -> review progress -> bring brief/workspace into meetings`

Clarion should not be positioned as a generic analytics dashboard or an IT-style data product.

## Primary Buyer
- Managing partner or firm leader responsible for client experience, service quality, and partner-meeting review

## Secondary Buyer / Internal Champion
- Operations lead, client-experience lead, or reputation owner who runs the review cycle and keeps follow-through visible

## One-Sentence Value Proposition
Clarion turns law-firm client feedback into partner-ready governance briefs, assigned actions, and visible follow-through.

## What Clarion Is
- A law-firm-specific governance and follow-through product
- A structured operating loop for client feedback review
- A meeting-ready system that helps firm leadership see recurring issues and decide what happens next

## What Clarion Is Not
- Not a generic analytics dashboard
- Not an IT-style data exploration tool
- Not a review-monitoring vanity product
- Not a replacement for partner judgment
- Not a generic professional-services platform

## Product Pillars
1. Easy intake
   One upload should be enough to start. The opening promise is low-friction feedback intake, not implementation complexity.

2. Structured governance signal
   Clarion turns scattered client comments into recurring issues a partner can review without reading every line.

3. Action ownership
   The value is not only seeing the issues. It is assigning owners, due dates, and next steps inside the same operating record.

4. Meeting-ready visibility
   Clarion should feel useful in leadership review: a brief, a workspace, and a clear sense of what moved and what did not.

5. Follow-through over time
   The story does not end at one report. Clarion supports repeated cycles so firms can review whether action changed the client experience.

## Core Workflow Story
1. Upload client feedback from reviews, surveys, or internal exports
2. Clarion structures recurring service and governance signals
3. The firm reviews what deserves partner attention now
4. Owners and deadlines are assigned to the right actions
5. The governance brief and workspace are used in meetings
6. The next cycle shows whether the firm is improving or stalling

## Proof / Trust / Credibility Strategy
- Lead with law-firm specificity, not broad professional-services language
- Show the actual operating outputs:
  - governance brief
  - action tracking
  - partner review workspace
  - PDF / email brief path
- Emphasize low-friction start:
  - CSV upload
  - no heavy integration requirement
  - read-only sample brief or demo cycle
- Use proof statements that support operational trust:
  - built for partner review
  - designed for firms without large analytics teams
  - produces a brief and owned follow-through, not just charts

## CTA Strategy
- Primary CTA:
  - Review a sample brief
  - or Start a pilot with your firm's recent feedback
- Secondary CTA:
  - See how the workflow runs
- Avoid:
  - pricing-first framing in the hero
  - generic "book a demo" as the only action
  - dashboard-tour-first CTAs

## V3 Landing Architecture

### 1. Hero
Purpose:
Frame Clarion as a partner-facing governance product, not a dashboard.

Content:
- Headline about turning client feedback into partner-ready review
- Subhead that names the workflow outcome: brief, actions, follow-through
- Primary CTA to sample brief / pilot
- Secondary CTA to see workflow
- Preview should bias toward a governance brief or meeting-ready summary, not a chart wall

### 2. Trust / Fit Strip
Purpose:
Establish that Clarion is made for law firms and for leadership review.

Content:
- law-firm-specific language
- no-heavy-setup message
- partner-meeting-ready output
- narrow, credible operating claims

### 3. Workflow Section
Purpose:
Make the product legible in one pass.

Content:
- Upload feedback
- Structure governance signals
- Assign actions
- Review progress
- Bring the brief into meetings

This should read as an operating loop, not a feature inventory.

### 4. Outputs Section
Purpose:
Show what the firm actually gets.

Content:
- governance brief preview
- workspace/report detail preview
- action list / ownership preview
- PDF / email output references

The emphasis is "what leadership can use immediately."

### 5. Action + Accountability Section
Purpose:
Separate Clarion from passive reporting tools.

Content:
- owners
- due dates
- statuses
- overdue visibility
- operating follow-through language

### 6. Meeting-Ready Visibility Section
Purpose:
Show how Clarion enters a real partner or operations meeting.

Content:
- what can be seen at a glance
- what changed since the last cycle
- where action is lagging
- how the brief/workspace supports review without deep tool training

### 7. Sample Brief / Pilot Section
Purpose:
Close with a believable next step.

Content:
- open a sample brief
- run a pilot on recent firm feedback
- language should reduce perceived setup burden

## Dashboard Restraint Rules
- Do not lead with dashboards, charts, or analytics language
- Do not present Clarion as a tool for exploring data
- If charts appear, they must support the governance story rather than dominate the page
- Preview one operating record, not five disconnected widgets
- Prefer brief excerpts, issue summaries, action ownership, and meeting-review cues over KPI walls
- Avoid copy like:
  - "AI-powered insights dashboard"
  - "advanced analytics for firms"
  - "explore your data"
- Prefer copy like:
  - "bring a brief to the meeting"
  - "see what requires partner attention"
  - "assign follow-through and review progress"

## Preview / Visual Direction
- Premium, calm, and credible
- More review-room than control-room
- Typography should feel editorial and legal-professional, not startup-generic
- Section rhythm should alternate:
  - statement
  - proof
  - workflow
  - output
  - accountability
  - CTA
- Product previews should feature:
  - governance brief cover/state
  - issue summary blocks
  - action ownership rows
  - meeting-readiness cues

## Existing Concepts To Ignore Or Archive
- Treat the legacy Flask marketing templates as archive-only contamination:
  - `backend/templates/index.html`
  - `backend/templates/how_it_works.html`
- Those templates lean on generic professional-services and analytics framing that should not drive V3.
- The current React marketing route structure is a better reference for workflow shape than for final hierarchy or hero emphasis.
- The hero should move away from a dashboard-first preview and toward a governance-brief-centered preview.

## Figma Direction
- If using Figma, build one V3 landing architecture board rather than multiple disconnected concepts.
- Start with low-to-mid fidelity wireframes or a component plan:
  - hero
  - trust strip
  - workflow rail
  - outputs preview
  - accountability module
  - meeting-ready section
  - pilot CTA
- The board should clarify hierarchy, spacing, section rhythm, and preview emphasis before any polished visual system work begins.

## Recommended V3 Implementation Sequence
1. Replace the current landing message hierarchy with the partner-facing V3 architecture
2. Rework the hero preview from dashboard-first to governance-brief-first
3. Tighten public copy around law-firm governance and follow-through
4. Remove remaining legacy generic-professional-services language from any public surfaces still in play
5. Only after the structure is approved, implement the production landing page
