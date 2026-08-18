# Job Search Strategy

This document explains *why* the agent searches, classifies, and ranks the
way it does. Read it before changing anything in `jobs_agent/core.py`,
`jobs_agent/sources.py`, or `jobs_agent/publish.py` — those modules implement
the rules below, and a change that looks like a bug fix in isolation can
silently break the strategy (e.g. "manager" filtering, German-language
tolerance, or the Telegram anti-spam cap).

## Candidate context

- Computer Science student, Lancaster University Leipzig.
- Final examinations: June 2027. **Full-time availability: July 2027.**
  The October 2027 formal graduation ceremony is not the availability date
  and must never be treated as one — do not penalize "Graduate 2027" /
  "Full-Time Analyst 2027" style postings for mentioning a later ceremony
  date.
- Based in Leipzig, Germany. English fluent, German ~B2.
- Nigerian citizen studying legally in Germany. Work authorization outside
  Germany is UNKNOWN unless independently verified — the agent never assumes
  it, but also never rejects an otherwise strong non-German-EU role purely
  for missing sponsorship information.
- Active campaign window: **August 18 – October 31, 2026**, targeting
  internships, working-student roles, and graduate/entry-level programmes
  for immediate or July-2027-start positions.

## Primary objective

Secure a viable early-career professional role that establishes a career in
Germany/Europe and provides a realistic path to remaining and working in
Germany after graduation. This is explicitly **not** SWE-only or
prestige-only. Adjacent technology/product/project/IT-service/
implementation/support/business-technology roles are valid, sometimes
better, entry points. Balance, in order the scoring model weights them:
probability of securing the role, career development value, compensation
and employment viability, relevance to the CS degree, and potential to lead
to stronger technical/product/data/management roles later.

## Role families

`jobs_agent/core.py` classifies every job into one of:

- **CORE_TECH** — SWE, backend/frontend/full-stack, data engineering/science/
  analytics, AI/ML, cloud, DevOps, platform, cybersecurity, QA/test
  automation, solutions engineering, quant technology.
- **PRODUCT_PROJECT** — product/project management (incl. intern/associate/
  junior), product analyst/operations, project coordination, PMO,
  requirements engineering, digital/business transformation.
- **BUSINESS_TECH** — business analyst, technology analyst, technical/
  technology consulting, digital consultant.
- **ENTERPRISE_IT** — ITSM, service delivery, IT operations, application
  support/management/analysis, systems analysis, implementation/integration
  consulting, ERP/CRM, change/release/incident/problem management.
- **BROADER_PROFESSIONAL** — operations/business/digital operations,
  supply chain, customer success, rotational/graduate programmes — anything
  that's a credible technology-adjacent professional entry point but doesn't
  fit the families above.
- **IRRELEVANT** — genuinely outside the funnel, or rejected for seniority
  (see below).

Classification is **title-first, by design**. Job titles are short and
curated; full descriptions are long, noisy, and full of boilerplate. Early
iterations that matched family keywords against the full description text
produced real false positives in production testing — e.g. a *Sales Account
Executive* got classified `CORE_TECH` at 92/100 purely because its
employer's About-Us blurb called itself an "AI-native" company. The fix: a
job only gets a family via description text if its *title* already carries
a weak topical hint (`data`, `digital`, `tech`, `IT`, `cloud`, `cyber`,
`system(s)`, `analytics`, `platform`, `KI`) **and** the description then
confirms it with a real CORE_TECH signal. A title with zero tech-adjacent
words never gets promoted into CORE_TECH just because "AI" or "cloud"
appears somewhere in three paragraphs of marketing copy.

Known remaining edge case (accepted, not fixed): a title that itself
contains "AI" as company branding rather than a role descriptor (e.g. "...at
AI Audit-Tech Startup") can still title-match directly. This is narrower and
rarer than the description-boilerplate problem and is left as a documented
limitation rather than adding more special-casing.

## Seniority filtering ("the manager rule")

**"Manager" alone is never a rejection signal.** Junior Project Manager,
Product Manager Intern, Application Manager, and Junior IT Service Manager
are all legitimate entry points and must classify normally.

Hard title-level rejection triggers only on unambiguous seniority markers:
`senior`, `sr.`, `lead`, `principal`, `staff`, `head of`, `director`, `vp`,
`vice president`, `chief`, `extensive leadership experience`, or an explicit
`N+ years` pattern with N ≥ 3 anywhere in the title. See
`tests/test_core.py::ManagerRegressionTests` for the exact regression list —
extend it, don't work around it, if you touch this logic.

## Scoring model

Deterministic, additive, out of 100. It is a **ranking heuristic**, not a
calibrated probability — the weights are opinionated defaults, not a
scientific model:

| Component | Points | What it captures |
|---|---|---|
| Role/career fit | 20 | Is this a credible professional entry point? CORE_TECH scores highest but the families are deliberately close (14–20) so a strong ITSM/PM/BA role isn't automatically buried under a mediocre SWE listing. |
| Experience/eligibility fit | 20 | Intern/Werkstudent/junior/graduate/Berufseinsteiger language scores highest; explicit 3+/5+/7+ years or senior-leadership requirements score lowest. |
| Probability/realism | 15 | Employer selectivity (small known-employer map: Reach/Core/Accessible, default Core) and family/seniority signals. Prevents keyword-dense elite roles from auto-topping the list over a realistic mid-size-company match. |
| Location | 10 | Germany (any city, not a fixed shortlist — nationwide) or remote-Germany scores highest; other listed EU hubs (Amsterdam, Luxembourg, Dublin, Warsaw, Prague, Stockholm, London, Zurich, Paris) score moderately with a work-authorization caveat; elsewhere scores low. |
| Language | 10 | English-only or B1/B2-friendly German scores highest; native/C1+/verhandlungssicher-mandatory German scores lowest. German is never an automatic rejection. |
| Skills/technology relevance | 10 | Keyword overlap with the matched role family. |
| Career progression value | 10 | Enterprise/stakeholder/implementation/platform/cloud/agile/API/CRM/ERP/SaaS-type signals — proxies for whether the role builds transferable experience, not company prestige. |
| Recency/urgency | 5 | Recently posted roles rank slightly higher. |

A job below **65** is discarded entirely — never written to `docs/jobs.json`,
never shown on the dashboard. `role_family == IRRELEVANT` is discarded
regardless of score.

### Notify tiers (used only for Telegram, not for the dashboard)

| Score | Tier |
|---|---|
| 90–100 | EXCEPTIONAL |
| 82–89 | APPLY |
| 75–81 | REVIEW |
| 65–74 | SILENT (dashboard only) |
| <65 | DISCARD (not published at all) |

## Telegram anti-spam rules

The morning briefing is capped at **5** jobs, always the highest-scoring
*genuinely new* jobs (not previously published), and only from EXCEPTIONAL/
APPLY/REVIEW tiers. SILENT-tier jobs are never sent, even if the cap has
spare slots — the threshold is never lowered just to fill five slots.
Zero qualifying new jobs produces zero Telegram messages.

Critically: **every** passing job (all tiers ≥65) is still written to
`docs/jobs.json` on every run, regardless of the Telegram cap. Once a job's
stable ID exists in a previously-published `jobs.json`, `publish_jobs()`
never treats it as "new" again — so a job that misses the cap on day 1
appears on the dashboard immediately but does not resurface in Telegram on
day 2, day 3, etc. See `tests/test_publish.py::test_jobs_omitted_by_telegram_cap_do_not_reappear_as_new_next_run`.

## Deduplication

`stable_job_id()` (SHA-256 of normalized company+title+location) is
unchanged from the original design. `fetch_all()` now dedupes across **all**
candidates from all sources *before* applying the score threshold, keeping
whichever variant scored higher — so a thinner listing from one source
doesn't win over a richer, higher-scoring listing of the same job from
another source.

## Source coverage and known limitations

Sources: Bundesagentur für Arbeit (curated German+English query set spanning
all five role families), Arbeitnow, Remotive. All three are unauthenticated
public APIs — no scraping framework, no headless browser, no per-employer
crawlers in this iteration.

**Likely under-covered by BA/Arbeitnow/Remotive today:**

- Structured campus/graduate recruiting programmes at large multinationals
  (Google, SAP, Siemens, Deutsche Bank, McKinsey/BCG, etc.) — these are
  almost always hosted on dedicated ATS platforms (Workday, SmartRecruiters,
  Greenhouse, SuccessFactors) and rarely syndicate to Arbeitnow/BA.
- 2027-dated "Graduate 2027" / "Technology Analyst 2027" postings — most
  employers don't open next year's cohort until roughly 9–12 months ahead,
  so visibility should improve through late 2026/early 2027; it is
  deliberately not faked in the meantime.
- English-language graduate schemes based outside Germany (Amsterdam,
  Dublin, Luxembourg, Zurich, etc.) — the current three sources skew
  German/DACH; broader EU coverage is limited.
- ENTERPRISE_IT and BUSINESS_TECH roles specifically at large corporates and
  consultancies, which more often post directly on their own career sites
  than through Arbeitnow/BA/Remotive.

Direct employer career-page/watchlist monitoring is a deliberate **future
enhancement**, not implemented here — it would require per-employer scraping
that conflicts with this iteration's "small, dependency-free, three-source"
scope. If it's added later, keep it additive (a 4th lightweight source
adapter, not a scraping framework).
