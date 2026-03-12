# lead_sources.md
# Clarion Agent Office — Lead Source Registry
# Version: 1.0 | 2026-03-12
#
# PURPOSE
# Defines where the Outbound Sales Agent should discover ICP-qualified
# law firm prospects. Each source includes what it is, how to collect from it,
# and what to watch for.
#
# RULES
# - Only collect on firms matching memory/icp_definition.md: 5-50 attorneys,
#   consumer-facing practice (family law, PI, criminal defense, immigration).
# - Skip solo practitioners, BigLaw, corporate legal departments, legal tech vendors.
#   See memory/do_not_chase.md.
# - Research and documentation are LEVEL 1 (autonomous).
#   Appending to leads_pipeline.csv requires no approval.
# - No agent may contact a discovered firm without a Level 2 entry in
#   memory/division_lead_approvals.md.
# - Prioritize sources that surface review signals. Firms with public client
#   feedback are higher signal than firms without.

---

## SOURCE-001
SOURCE:            Google Maps / Google Business Profile
TYPE:              Public review aggregator
COLLECTION_METHOD: Search Google Maps for "[practice area] law firm [city, state]".
                   Filter to firms with 10-200 reviews (enough signal, not BigLaw scale).
                   Record: firm name, city, state, practice area, review count,
                   average rating, any visible complaint clusters in recent reviews
                   (communication, responsiveness, billing, outcome disappointment),
                   and website URL if listed.
                   Log to data/revenue/lead_research_queue.csv with source: google_maps.
PRIORITY:          High. Google reviews are the primary data source Clarion analyzes.
                   A firm with public Google reviews is already a potential pilot candidate.
NOTES:             Focus on firms where recent reviews show inconsistency (4.1-4.4 range),
                   or where negative reviews mention operational complaints rather than
                   pure outcome complaints. These are highest-signal ICP indicators.
                   Skip firms with fewer than 10 reviews (insufficient pilot data).
                   Skip firms with 200+ reviews (likely outside ICP size range).

---

## SOURCE-002
SOURCE:            Avvo
TYPE:              Legal directory with attorney profiles and client reviews
URL:               https://www.avvo.com
COLLECTION_METHOD: Search by practice area and location. Filter to firms with active
                   profiles and at least 5 client reviews.
                   Record: attorney name, firm name, practice area, city/state,
                   Avvo rating, review count, and any visible review themes.
                   Cross-reference with Google Maps to check if the firm also has
                   Google reviews. Dual-source firms are higher priority.
                   Log to data/revenue/lead_research_queue.csv with source: avvo.
PRIORITY:          Medium-High. Avvo reviews are less common than Google but signal
                   an active online presence and client feedback history.
NOTES:             Avvo profiles surface attorney count and years in practice.
                   Use attorney count to filter: skip solos and firms with 50+ attorneys.
                   When managing partner name and contact info are visible, flag in
                   notes column for outreach personalization.

---

## SOURCE-003
SOURCE:            Justia
TYPE:              Legal directory with attorney and firm profiles
URL:               https://www.justia.com/lawyers
COLLECTION_METHOD: Browse by state and practice area. Filter to ICP practice areas
                   (family law, PI, criminal defense, immigration).
                   Record: firm name, attorney count, city/state, practice areas, website.
                   Justia profiles often include contact info and bio — useful for
                   identifying the managing partner.
                   Log to data/revenue/lead_research_queue.csv with source: justia.
PRIORITY:          Medium. Good for finding firms in smaller markets where Google Maps
                   coverage is thinner. Treat as discovery tool, not a signal source.
NOTES:             Cross-reference every Justia-discovered firm with Google Maps
                   to check review volume before qualifying. Do not add a firm to
                   leads_pipeline.csv from Justia alone unless Google/Avvo review data
                   confirms ICP fit.

---

## SOURCE-004
SOURCE:            Martindale-Hubbell
TYPE:              Legal directory with peer and client ratings
URL:               https://www.martindale.com
COLLECTION_METHOD: Search by practice area and geography. Filter to firms with client
                   reviews visible on the profile.
                   Record: firm name, city/state, practice area, rating, review count,
                   website, and any firm size indicators.
                   Log to data/revenue/lead_research_queue.csv with source: martindale.
PRIORITY:          Medium. Martindale skews toward established firms. Peer ratings indicate
                   credibility but do not surface operational feedback pain directly.
                   Use to validate firms already discovered via Google Maps or Avvo.
NOTES:             A firm with Google reviews, an Avvo profile, and a Martindale listing
                   is a fully validated ICP candidate. Prioritize triple-confirmed firms.
                   Martindale is best used as a verification and enrichment layer, not
                   a primary discovery source.

---

## SOURCE-005
SOURCE:            State Bar Directories
TYPE:              Official attorney licensing registries by state
EXAMPLES:
  California:    https://apps.calbar.ca.gov/attorney/LicenseeSearch/AdvancedSearch
  Florida:       https://www.floridabar.org/directories/find-mbr/
  Texas:         https://www.texasbar.com/AM/Template.cfm?Section=Find_A_Lawyer
  Illinois:      https://www.iardc.org/
  Georgia:       https://www.gabar.org/for-the-public/looking-for-an-attorney/
  New York:      https://iapps.courts.state.ny.us/attorney/AttorneySearch
  Ohio:          https://www.supremecourt.ohio.gov/attorney-services/attorney-directory
  Pennsylvania:  https://www.padisciplinaryboard.org/for-the-public/find-attorney
  Michigan:      https://www.michbar.org/member/directory
  (Add additional states as research expands per geography targeting below)
COLLECTION_METHOD: Search by practice area and city/county. Filter to licensed attorneys
                   whose firm appears to match ICP size range.
                   Record: attorney name, firm name, city/state, practice area.
                   Do not record bar numbers in the research queue.
                   Cross-reference with Google Maps and Avvo to find review presence.
                   Log to data/revenue/lead_research_queue.csv with source: state_bar_[XX].
PRIORITY:          Medium. Provides comprehensive geographic coverage but surfaces no
                   review signals. Use as a coverage layer where Google Maps and Avvo
                   discovery is thin.
NOTES:             State bar data is authoritative for firm legitimacy verification.
                   A firm with an active bar listing plus Google reviews is a confirmed
                   ICP candidate. Prioritize these over bar-directory-only discoveries.

---

## SOURCE-006
SOURCE:            Local Law Firm Directories
TYPE:              City and regional directories, local bar association listings
EXAMPLES:
  - County/city bar association member directories
  - Local chamber of commerce business directories (filter to legal services)
  - City-specific "best lawyers" guides (local magazine annual lists)
  - Legal aid referral networks listing established small firms by region
COLLECTION_METHOD: Search for city-specific legal directories in target markets.
                   Identify family law, PI, criminal defense, and immigration firms.
                   Record: firm name, city/state, practice area, and website.
                   Cross-reference with Google Maps for review presence.
                   Log to data/revenue/lead_research_queue.csv with source: local_directory.
PRIORITY:          Medium-Low. Local directories are inconsistent in coverage and quality.
                   Use to supplement Google Maps and state bar discovery in target cities,
                   not as a primary source.
NOTES:             Local bar association directories (county/city level) are often more
                   current than state bar listings for small firm contact info.
                   Best use case: Tier 2 cities where ICP density is lower and standard
                   source coverage is thinner.

---

## SOURCE-007
SOURCE:            Legal Association Member Lists
TYPE:              Professional association membership directories
EXAMPLES:
  - American Academy of Matrimonial Lawyers (AAML) — family law
  - American Immigration Lawyers Association (AILA) — immigration
  - American Association for Justice (AAJ) — plaintiff PI
  - National Association of Criminal Defense Lawyers (NACDL) — criminal defense
  - State-level equivalents of each (e.g., State Trial Lawyers Association)
COLLECTION_METHOD: Review publicly available member directories or "find a member" tools
                   on association websites. Filter by state/region.
                   Record: attorney name, firm name, city/state, specialty, website.
                   Cross-reference with Google Maps for review presence.
                   Log to data/revenue/lead_research_queue.csv with source: legal_association.
PRIORITY:          High for targeted ICP practice areas. Association membership signals
                   active practice in high-trust, client-relationship-intensive areas
                   where Clarion's governance brief is directly relevant.
NOTES:             AILA and AAML members are particularly strong ICP signals.
                   Managing partners of ICP firms are often association members.
                   Do not qualify from association membership alone — still verify
                   firm size and review presence before adding to leads_pipeline.csv.

---

## SOURCE-008
SOURCE:            Legal Conference Speaker Lists
TYPE:              Public speaker rosters from legal industry events
EXAMPLES:
  - State bar annual meeting and CLE conference agendas
  - ABA solo/small firm conference speakers
  - Practice-area conference speakers (family law symposia, PI trial academies,
    immigration law conferences, criminal defense CLEs)
COLLECTION_METHOD: Search for upcoming and recent conference agendas in ICP practice areas.
                   Identify speakers who are managing partners or firm owners at small-to-mid
                   size practices.
                   Record: name, firm, city/state, practice area, conference name and date.
                   Cross-reference with Google Maps and Avvo.
                   Log to data/revenue/lead_research_queue.csv with source: conference_speaker.
PRIORITY:          High for warm outreach. Conference speakers are public figures in their
                   practice community, giving an authentic, non-cold personalization angle.
NOTES:             Flag these leads in notes column: "conference speaker - use personalized opener."
                   Reference their session or topic in outreach. This is not cold contact --
                   it is a warm professional introduction grounded in their public work.
                   An outreach message referencing their conference topic lands meaningfully
                   better than a generic cold message with no prior signal.

---

## Source Priority Matrix

| Source | Review Signal | Contact Quality | Coverage | Overall Priority |
|---|---|---|---|---|
| Google Maps | High | Medium | High | 1 |
| Legal Association Members | Medium | High | Medium | 2 |
| Conference Speakers | Medium | Very High | Low | 3 |
| Avvo | High | Medium | Medium | 4 |
| State Bar Directories | Low | Medium | Very High | 5 |
| Martindale | Medium | Medium | Medium | 6 |
| Justia | Low | Medium | Medium | 7 |
| Local Directories | Low | Low | Low | 8 |

Work sources in priority order when time is limited.
A firm appearing in 2+ sources is a higher-confidence prospect.
A firm with Google reviews plus association membership is a near-ideal discovery target.

---

## Geography Targeting Guidance

Build coverage systematically by targeting one region at a time.
Do not spread thin across all 50 states simultaneously.

Suggested initial target markets (high ICP density, strong review culture):
1. Texas (Dallas, Houston, Austin, San Antonio) — large PI and family law market
2. Florida (Miami, Orlando, Tampa, Jacksonville) — immigration, PI, and family law
3. Illinois (Chicago metro and suburbs) — dense small firm market
4. Georgia (Atlanta metro) — growing family law and PI market
5. California (Los Angeles, San Diego, Sacramento) — high review volume, immigration heavy

Document which city and state was researched each run in WORK COMPLETED THIS RUN.
Do not re-research the same geography two runs in a row unless new sources are available.
