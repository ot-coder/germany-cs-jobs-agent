from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import re


# ---------------------------------------------------------------------------
# Role families
#
# The old model (werkstudent / entry-level / other) was too narrow: it only
# recognised software-engineering-shaped titles and rejected anything with
# "manager" in it. The candidate strategy is to use ANY credible early-career
# professional-technology role as an entry point, not just pure SWE. See
# docs/JOB_SEARCH_STRATEGY.md for the reasoning behind these families and the
# scoring model below.
# ---------------------------------------------------------------------------

CORE_TECH = "CORE_TECH"
PRODUCT_PROJECT = "PRODUCT_PROJECT"
BUSINESS_TECH = "BUSINESS_TECH"
ENTERPRISE_IT = "ENTERPRISE_IT"
BROADER_PROFESSIONAL = "BROADER_PROFESSIONAL"
IRRELEVANT = "IRRELEVANT"

# Checked against the TITLE only, in this order. The first family whose any
# keyword appears in the title wins. Order matters where a title could match
# more than one family (e.g. "IT Business Analyst" should land in
# BUSINESS_TECH, not ENTERPRISE_IT, even though "it" appears in both).
FAMILY_TERMS: dict[str, tuple[str, ...]] = {
    CORE_TECH: (
        "software", "developer", "engineer", "backend", "frontend", "front end",
        "full stack", "fullstack", "data engineer", "data scientist", "data analyst",
        "machine learning", " ai ", "artificial intelligence", "cloud engineer",
        "devops", "platform engineer", "site reliability", " sre ", "cybersecurity",
        "cyber security", "security engineer", "qa engineer", "test automation",
        "quality assurance", "solutions engineer", "quant", "python", "java developer",
        "javascript", "typescript", "informatik", "computer science", "web development",
    ),
    PRODUCT_PROJECT: (
        "product manager", "product management", "product analyst", "product operations",
        "project manager", "project management", "project coordinator", "projektmanage",
        "projektkoordinat", " pmo ", "digital transformation", "business transformation",
        "requirements engineer", "process analyst", "scrum master", "agile coach",
    ),
    BUSINESS_TECH: (
        "business analyst", "technology analyst", "technical consultant",
        "technology consulting", "digital consultant", "it consultant",
        "junior consultant", "strategy consultant",
    ),
    ENTERPRISE_IT: (
        "service management", "itsm", "service delivery", "it operations",
        "technical operations", "application support", "application management",
        "application analyst", "application manager", "systems analyst",
        "system analyst", "business systems", "enterprise application",
        "implementation consultant", "implementation specialist",
        "integration specialist", "saas implementation", " erp ", " crm ",
        "cloud support", "infrastructure operations", "it governance",
        "change management", "release management", "incident management",
        "problem management", "it service",
    ),
    BROADER_PROFESSIONAL: (
        "operations analyst", "business operations", "digital operations",
        "supply chain", "customer success", "rotational", "graduate programme",
        "graduate program", "trainee programme", "trainee program",
    ),
}
FAMILY_ORDER = (CORE_TECH, PRODUCT_PROJECT, BUSINESS_TECH, ENTERPRISE_IT, BROADER_PROFESSIONAL)

# Title-scoped hard rejection. "Manager" alone is deliberately absent here —
# only unambiguous seniority markers disqualify a role.
_SENIOR_TITLE_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in (
        r"\bsenior\b", r"\bsr\.?\b", r"\blead\b", r"\bprincipal\b", r"\bstaff\b",
        r"\bhead of\b", r"\bdirector\b", r"\bvp\b", r"\bvice president\b", r"\bchief\b",
        r"extensive leadership experience",
    )
)
_YEARS_PATTERN = re.compile(r"(\d+)\+\s*years?")

JUNIOR_TERMS = (
    "intern", "internship", "praktikum", "working student", "werkstudent",
    "student assistant", "studentische hilfskraft", "graduate", "trainee",
    "entry level", "entry-level", "berufseinsteiger", "new grad", "junior",
    "associate", "0-1 year", "0-2 year", "0 to 2 year",
)
_MODERATE_EXPERIENCE_PATTERN = re.compile(r"\b1\s*[-–to]{1,4}\s*2\s*years?\b|\b2\s*years?\s*(preferred|desired|plus)\b")
_STRONG_NEGATIVE_TERMS = ("senior leadership", "extensive leadership experience", "people management")

GERMANY_LOCATION_TERMS = (
    "germany", "deutschland", "berlin", "munich", "münchen", "munchen", "frankfurt",
    "hamburg", "cologne", "köln", "koln", "düsseldorf", "duesseldorf", "stuttgart",
    "leipzig", "dresden", "nuremberg", "nürnberg", "nurnberg", "hannover", "hanover",
    "bremen", "dortmund", "essen", "duisburg", "bochum", "wuppertal", "bielefeld",
    "bonn", "münster", "munster", "karlsruhe", "mannheim", "augsburg", "wiesbaden",
    "mönchengladbach", "gelsenkirchen", "braunschweig", "kiel", "chemnitz", "aachen",
    "halle", "magdeburg", "freiburg", "krefeld", "lübeck", "luebeck", "erfurt",
    "rostock", "kassel", "potsdam", "saarbrücken", "saarbruecken", "mainz",
    "regensburg", "ingolstadt", "würzburg", "wurzburg", "ulm", "heidelberg", "jena",
    "darmstadt", "göttingen", "goettingen",
)
EU_HUB_TERMS = (
    "amsterdam", "luxembourg", "dublin", "warsaw", "prague", "stockholm", "london",
    "zurich", "paris", "netherlands", "ireland", "poland", "czech", "sweden",
    "united kingdom", "switzerland", "france",
)

_STRICT_GERMAN_TERMS = (
    "muttersprachlich", "native german", "verhandlungssicheres deutsch",
    "german c1", "german c2", "c1 deutsch", "c2 deutsch", "deutsch c1", "deutsch c2",
    "fließend deutsch zwingend",
)
_MODERATE_GERMAN_TERMS = ("fluent german", "deutsch fließend", "verhandlungssicher")
_OPEN_GERMAN_TERMS = (
    "german b1", "german b2", "deutsch b1", "deutsch b2", "gute deutschkenntnisse",
    "deutschkenntnisse von vorteil", "conversational german", "basic german",
)

_CAREER_VALUE_TERMS = (
    "enterprise", "stakeholder", "cross-functional", "cross functional",
    "implementation", "platform", "cloud", "agile", "scrum", "roadmap", " api ",
    " crm ", " erp ", "saas", "data-driven", "automation", "integration",
)

# Small, intentionally short known-employer map. Anything not listed defaults
# to "Core" rather than inventing false precision. See docs/JOB_SEARCH_STRATEGY.md.
KNOWN_EMPLOYERS: dict[str, str] = {
    "google": "Reach", "amazon": "Reach", "microsoft": "Reach", "meta": "Reach",
    "apple": "Reach", "netflix": "Reach", "mckinsey": "Reach", "bcg": "Reach",
    "boston consulting group": "Reach", "goldman sachs": "Reach", "sap": "Reach",
    "siemens": "Reach", "deutsche bank": "Reach", "bmw": "Reach",
    "mercedes-benz": "Reach", "mercedes benz": "Reach", "porsche": "Reach",
    "bosch": "Core", "allianz": "Core", "deutsche bahn": "Core", "telekom": "Core",
    "volkswagen": "Core", "zalando": "Core", "delivery hero": "Accessible",
    "n26": "Accessible", "trade republic": "Accessible", "personio": "Accessible",
    "check24": "Accessible", "celonis": "Accessible", "flixbus": "Accessible",
    "spryker": "Accessible",
}

# Score weights (see docs/JOB_SEARCH_STRATEGY.md). These sum to 100 and are a
# ranking heuristic, not a precise probability model.
_ROLE_FIT_POINTS = {
    CORE_TECH: 20, PRODUCT_PROJECT: 18, BUSINESS_TECH: 17,
    ENTERPRISE_IT: 17, BROADER_PROFESSIONAL: 14,
}


@dataclass(slots=True)
class Job:
    id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    source: str
    role_family: str = ""
    seniority: str = "neutral"
    employer_category: str = "Core"
    language_requirement: str = "open"
    remote: bool = False
    published_at: str = ""
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    first_seen_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def stable_job_id(company: str, title: str, location: str) -> str:
    key = "|".join(_normalized(v) for v in (company, title, location))
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]


def _is_senior_title(title_text: str) -> bool:
    if any(pattern.search(title_text) for pattern in _SENIOR_TITLE_PATTERNS):
        return True
    return any(int(match) >= 3 for match in _YEARS_PATTERN.findall(title_text))


def _match_family(text: str) -> str | None:
    for family in FAMILY_ORDER:
        if any(term in text for term in FAMILY_TERMS[family]):
            return family
    return None


# Two-factor description fallback used ONLY when the title alone doesn't
# identify a family (e.g. "Werkstudent Data"). Matching the full family
# keyword lists against free-text descriptions ALONE produced false
# positives in practice — e.g. a Sales Account Executive at an "AI-native"
# company got classified CORE_TECH purely because "AI" appears in every
# modern SaaS company's About-Us boilerplate, regardless of the actual role.
# The title must first carry its own weak tech-adjacent hint before the
# (much richer, otherwise-risky) CORE_TECH description terms are trusted.
CORE_TECH_TITLE_HINTS = (
    " data ", " digital ", " tech ", " it ", " ki ", " cloud ", " cyber ",
    " system ", " systems ", " analytics ", " platform ",
)


def classify_role(title: str, description: str = "") -> tuple[str, str]:
    """Returns (role_family, seniority). seniority is 'senior', 'junior', or 'neutral'."""
    title_text = f" {_normalized(title)} "
    if _is_senior_title(title_text):
        return IRRELEVANT, "senior"
    description_text = f" {_normalized(description)} "
    combined = f"{title_text}{description_text}"
    role_family = _match_family(title_text)
    if role_family is None and any(hint in title_text for hint in CORE_TECH_TITLE_HINTS):
        if any(term in combined for term in FAMILY_TERMS[CORE_TECH]):
            role_family = CORE_TECH
    role_family = role_family or IRRELEVANT
    seniority = "junior" if any(term in combined for term in JUNIOR_TERMS) else "neutral"
    return role_family, seniority


def classify_employer(company: str) -> str:
    name = f" {_normalized(company)} "
    for known, category in KNOWN_EMPLOYERS.items():
        if f" {known} " in name or name.strip() == known:
            return category
    return "Core"


def _years_required(text: str) -> int:
    matches = _YEARS_PATTERN.findall(text)
    return max((int(value) for value in matches), default=0)


def _eligibility_score(text: str) -> tuple[int, str]:
    if _years_required(text) >= 3 or any(term in text for term in _STRONG_NEGATIVE_TERMS):
        return 4, "Experience requirement likely exceeds candidate profile"
    if any(term in text for term in JUNIOR_TERMS):
        return 20, "Clear entry-level/student framing"
    if _MODERATE_EXPERIENCE_PATTERN.search(text):
        return 13, "Light experience expectation (1-2 years)"
    return 9, "Experience level not clearly stated"


def _realism_score(role_family: str, employer_category: str, seniority: str) -> tuple[int, str]:
    base = 10
    if employer_category == "Reach":
        reason = "Highly selective employer — realistic odds are lower"
        base -= 4
    elif employer_category == "Accessible":
        reason = "Accessible employer — realistic odds are healthier"
        base += 3
    else:
        reason = "Moderate competitiveness expected"
    if role_family in (ENTERPRISE_IT, BUSINESS_TECH, BROADER_PROFESSIONAL, PRODUCT_PROJECT):
        base += 2
    if seniority == "junior":
        base += 2
    return max(0, min(15, base)), reason


def _location_score(location_text: str, remote: bool) -> tuple[int, str]:
    if any(term in location_text for term in GERMANY_LOCATION_TERMS):
        return 10, "Located in Germany"
    if remote or "remote" in location_text:
        return 6, "Remote role — Germany eligibility unclear"
    if any(term in location_text for term in EU_HUB_TERMS):
        return 5, "Other European hub — work authorization unverified"
    return 2, "Location outside primary target markets"


def _language_score(text: str) -> tuple[int, str, str]:
    if any(term in text for term in _STRICT_GERMAN_TERMS):
        return 1, "Native/C1+ German required", "strict"
    if any(term in text for term in _MODERATE_GERMAN_TERMS):
        return 5, "Fluent German requested — mandatoriness unclear", "moderate"
    if any(term in text for term in _OPEN_GERMAN_TERMS):
        return 8, "German B1/B2 friendly wording", "open"
    if "german" not in text and "deutsch" not in text:
        return 10, "English-only role", "open"
    return 9, "No strict German requirement detected", "open"


def _skills_score(role_family: str, text: str) -> tuple[int, str, str]:
    terms = FAMILY_TERMS.get(role_family, ())
    hits = sum(1 for term in terms if term in text)
    if hits >= 2:
        return 10, "Strong keyword relevance to role family", "strong"
    if hits == 1:
        return 6, "Some keyword relevance", "some"
    return 2, "Limited keyword overlap", "low"


def _career_value_score(text: str) -> tuple[int, str, str]:
    hits = sum(1 for term in _CAREER_VALUE_TERMS if term in text)
    points = min(10, 4 + hits * 2)
    if hits >= 2:
        return points, "Builds transferable enterprise/technical experience", "high"
    return points, "Standard progression value", "base"


def _parse_published(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _recency_score(published_at: str) -> tuple[int, str]:
    parsed = _parse_published(published_at)
    if parsed is None:
        return 3, "Publish date unknown"
    age_days = (datetime.now(timezone.utc) - parsed).days
    if age_days <= 14:
        return 5, "Recently posted"
    if age_days <= 30:
        return 3, "Posted within the last month"
    return 1, "Posted over a month ago"


def score_job(job: Job) -> tuple[int, list[str]]:
    """Scores a job 0-100 and returns (score, reasons). Also fills in
    job.role_family, job.seniority, job.employer_category, and
    job.language_requirement as a side effect, matching the source
    normalizers' existing `job.score, job.reasons = score_job(job)` pattern.
    """
    role_family, seniority = classify_role(job.title, job.description)
    job.role_family = role_family
    job.seniority = seniority
    if role_family == IRRELEVANT:
        job.employer_category = classify_employer(job.company)
        return 0, ["Senior-level or out-of-scope role"]

    title_text = f" {_normalized(job.title)} "
    text = f"{title_text} {_normalized(job.description)} "
    location_text = f" {_normalized(job.location)} "
    employer_category = classify_employer(job.company)
    job.employer_category = employer_category

    role_fit_points = _ROLE_FIT_POINTS[role_family]
    role_fit_reason = f"Credible {role_family.replace('_', ' ').title()} entry point"
    eligibility_points, eligibility_reason = _eligibility_score(text)
    realism_points, realism_reason = _realism_score(role_family, employer_category, seniority)
    location_points, location_reason = _location_score(location_text, job.remote)
    language_points, language_reason, language_label = _language_score(text)
    job.language_requirement = language_label
    skills_points, skills_reason, skills_label = _skills_score(role_family, text)
    career_points, career_reason, career_label = _career_value_score(text)
    recency_points, recency_reason = _recency_score(job.published_at)

    score = (
        role_fit_points + eligibility_points + realism_points + location_points
        + language_points + skills_points + career_points + recency_points
    )

    reasons = [role_fit_reason, eligibility_reason, location_reason, language_reason]
    if skills_label == "strong":
        reasons.append(skills_reason)
    elif career_label == "high":
        reasons.append(career_reason)
    elif realism_reason.startswith("Highly selective"):
        reasons.append(realism_reason)
    elif recency_reason == "Recently posted":
        reasons.append(recency_reason)

    return max(0, min(100, score)), reasons[:5]


def plain_text(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()
