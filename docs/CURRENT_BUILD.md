# Current Build Scope

## Active Pass
Governance brief output unification pass.

## In Scope (This Pass)
- Align section vocabulary and order across all brief output surfaces to the canonical 5-section spine:
  Leadership Briefing → Signals That Matter Most → Assigned Follow-Through → Decisions & Next Steps → Supporting Client Evidence
- Frontend email preview modal tile order
- Inline email HTML row order (emailHtmlSummary in ReportDetail)
- Backend Jinja2 email template (partner_brief_email.html) section labels + CTA copy
- PdfDeckPreview reference layout component: add Decisions & Next Steps section + decisions prop
- DashboardPdfPreview: pass recommended_changes as decisions to PdfDeckPreview
- Backend PDF generator (pdf_generator.py): rename agenda items + section headings to canonical vocabulary (strings only, no logic)

## Out of Scope
- Backend PDF layout, data plumbing, or rendering logic
- Route architecture changes
- Auth/session/calibration/signal-engine changes
- Full single-render-model architecture (documented as remaining split)
- Bundle/code-splitting work

## Definition of Done
- Email preview modal snapshot tiles match canonical section order
- Inline email HTML row order matches canonical section order
- Backend Jinja2 email template uses canonical section labels and correct CTA text
- PdfDeckPreview reference layout shows all 5 canonical sections including Decisions & Next Steps
- Backend PDF agenda and section headings use canonical vocabulary
- Frontend build passes

## Current Verification Notes
- `npm run build` in `frontend/` — passed (large-chunk warning remains pre-existing non-blocking)
- `python -m py_compile backend/pdf_generator.py` — PARSE_OK

## Next Likely Passes
1. Signals/supporting-workflows pass so supporting views stay clearly subordinate to current cycle
2. Frontend-to-backend brief template deeper unification (PDF layout data plumbing)
3. Retire legacy Flask marketing templates if deploy constraints allow
