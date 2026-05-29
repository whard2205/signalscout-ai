"""Bright Data integration layer.

Real calls go to SERP API, Web Unlocker, and Web Scraper API.
Every method returns (data, latency_ms, status) — errors are caught and
surfaced as status="error" or status="fallback" so the demo never crashes.

Live call chain:
1. serp_news_evidence(company) — SERP API, structured news + organic results
2. unlocker_fetch(url)         — Web Unlocker, JS-heavy pages
3. scraper_dataset(...)        — Web Scraper API, pre-built datasets (LinkedIn etc.)

Docs:
- https://docs.brightdata.com/scraping-automation/serp-api/introduction
- https://docs.brightdata.com/scraping-automation/web-unlocker/introduction
- https://docs.brightdata.com/scraping-automation/web-scraper-api/overview
"""
from __future__ import annotations

import json
import os
import re as _re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import quote_plus, urlparse

import httpx


def _current_year() -> int:
    return datetime.now(timezone.utc).year


# Months — used by both query-builder and freshness-aware confidence
_MONTH_TOKENS = {
    "jan", "feb", "mar", "apr", "may", "jun",
    "jul", "aug", "sep", "oct", "nov", "dec",
    "january", "february", "march", "april", "june",
    "july", "august", "september", "october", "november", "december",
}


def _try_parse_date(text: str) -> datetime | None:
    """Best-effort parser for SERP date strings like 'May 7, 2026' or 'Mar 1 2025'.

    Returns None if no parseable date pattern is found.
    """
    if not text:
        return None
    t = text.strip().rstrip(",.")
    # Try the most common Google SERP formats
    for fmt in ("%b %d, %Y", "%B %d, %Y", "%Y-%m-%d", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(t, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _freshness_aware_confidence(
    base_confidence: str,
    date_str: str | None,
) -> str:
    """Down-rank confidence for stale evidence.

    Rules:
      - No date → keep base confidence (we can't tell).
      - <= 90 days old → keep base confidence.
      - 90-180 days → cap at 'medium'.
      - 180-365 days → cap at 'low'.
      - > 365 days → 'low' (never high-confidence on year-old news).
    """
    if not date_str:
        return base_confidence
    parsed = _try_parse_date(date_str)
    if parsed is None:
        return base_confidence
    now = datetime.now(timezone.utc)
    age_days = (now - parsed).days
    if age_days <= 90:
        return base_confidence
    if age_days <= 180:
        return "medium" if base_confidence == "high" else base_confidence
    if age_days <= 365:
        return "low" if base_confidence in {"high", "medium"} else base_confidence
    return "low"


def _unwrap_serp_body(raw: Any) -> dict:
    """Bright Data wraps SERP JSON inside {status_code, headers, body:str}.
    Some zone configs return the parsed object directly. Handle both.
    """
    if not isinstance(raw, dict):
        return {}
    if "body" in raw and isinstance(raw["body"], str):
        try:
            inner = json.loads(raw["body"])
            return inner if isinstance(inner, dict) else {}
        except Exception:
            return {}
    return raw


def _date_from_extensions(extensions: Any) -> str | None:
    """Organic results carry dates inside extensions: [{type:'text', text:'May 7, 2026'}]."""
    if not isinstance(extensions, list):
        return None
    for ext in extensions:
        if isinstance(ext, dict) and ext.get("type") == "text":
            text = ext.get("text") or ""
            if any(m in text for m in ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")):
                return text
    return None


BD_API_BASE = "https://api.brightdata.com"


_KNOWN_COMPANY_CONTEXT: dict[str, dict[str, tuple[str, ...]]] = {
    "bank central asia": {
        "aliases": ("bank central asia", "bca", "pt bank central asia", "bbca"),
        "domains": ("bca.co.id",),
        "context": ("indonesia", "indonesian", "jakarta"),
    },
    "bca": {
        "aliases": ("bank central asia", "bca", "pt bank central asia", "bbca"),
        "domains": ("bca.co.id",),
        "context": ("indonesia", "indonesian", "jakarta"),
    },
    "telkomsel": {
        "aliases": ("telkomsel", "pt telekomunikasi selular"),
        "domains": ("telkomsel.com",),
        "context": ("indonesia", "indonesian", "jakarta", "telco", "telecom"),
    },
    "openai": {
        "aliases": ("openai", "open ai"),
        "domains": ("openai.com",),
        "context": ("artificial intelligence", "ai"),
    },
}


def _company_key(company: str) -> str:
    return _re.sub(r"[^a-z0-9]+", " ", company.lower()).strip()


def _company_context(company: str) -> dict[str, tuple[str, ...]]:
    key = _company_key(company)
    return _KNOWN_COMPANY_CONTEXT.get(key, {
        "aliases": (company.lower(),),
        "domains": (),
        "context": (),
    })


def _has_known_context(company: str) -> bool:
    return _company_key(company) in _KNOWN_COMPANY_CONTEXT


def _target_aliases(company: str) -> tuple[str, ...]:
    ctx = _company_context(company)
    aliases = [a.strip().lower() for a in ctx["aliases"] if a.strip()]
    raw = company.strip().lower()
    if raw and raw not in aliases:
        aliases.insert(0, raw)
    return tuple(aliases)


def _target_domains(company: str) -> tuple[str, ...]:
    return _company_context(company)["domains"]


def _quoted(s: str) -> str:
    return f'"{s}"'


def _build_news_query(company: str) -> str:
    ctx = _company_context(company)
    aliases = _target_aliases(company)
    alias_part = " OR ".join(_quoted(a) for a in aliases[:3])
    context_part = " ".join(ctx["context"][:2])
    return (
        f"({alias_part}) {context_part} latest news funding product launch "
        f"{_current_year()} recent"
    ).strip()


def _build_competitor_query(company: str) -> str:
    ctx = _company_context(company)
    aliases = _target_aliases(company)
    alias_part = " OR ".join(_quoted(a) for a in aliases[:2])
    context_part = " ".join(ctx["context"][:2])
    return f"({alias_part}) {context_part} competitors alternatives".strip()


def _mentions_target_company(company: str, title: str, snippet: str, url: str = "") -> bool:
    """True only when a SERP result is actually about the requested company.

    This prevents ambiguous names such as "Bank Central Asia" from matching
    generic "Central Asia" regional news, and prevents competitor pages for a
    different market from polluting Telkomsel-style queries.
    """
    host = _extract_domain(url) if url else ""
    if host and any(host == d or host.endswith("." + d) for d in _target_domains(company)):
        return True

    text = f"{title} {snippet}".lower()
    for alias in _target_aliases(company):
        if len(alias) < 3:
            continue
        pattern = r"(?<![a-z0-9])" + _re.escape(alias) + r"(?![a-z0-9])"
        if _re.search(pattern, text):
            return True

    # Generic fallback: for multi-word companies, require the full normalized
    # phrase. Do not accept partial token overlap (e.g. "Central Asia").
    phrase = _company_key(company)
    return bool(phrase and phrase in _company_key(text))


# ── Config ──────────────────────────────────────────────────────────────────

@dataclass
class BrightDataConfig:
    token: Optional[str]
    serp_zone: str
    unlocker_zone: str
    use_mock: bool

    @classmethod
    def from_env(cls) -> "BrightDataConfig":
        token = os.getenv("BRIGHT_DATA_API_TOKEN") or None
        use_mock = os.getenv("USE_MOCK", "true").lower() in {"1", "true", "yes"}
        return cls(
            token=token,
            serp_zone=os.getenv("BRIGHT_DATA_SERP_ZONE", "serp_api1"),
            unlocker_zone=os.getenv("BRIGHT_DATA_UNLOCKER_ZONE", "unblocker"),
            use_mock=use_mock or not token,
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower().replace("www.", "")
        return host or url[:40]
    except Exception:
        return url[:40] if url else "unknown"


_SKIP_DOMAINS: frozenset[str] = frozenset({
    # Review aggregators / listing sites
    "g2.com", "capterra.com", "trustpilot.com", "getapp.com", "softwareadvice.com",
    "peerspot.com", "crozdesk.com", "producthunt.com", "sourceforge.net",
    "alternativeto.net", "trustradius.com", "comparably.com",
    # Research / data aggregators
    "semrush.com", "similarweb.com", "cbinsights.com", "bullfincher.io",
    "owler.com", "marketing91.com", "tracxn.com", "growjo.com",
    "example.com", "example.org", "example.net",
    "craft.co", "pitchbook.com", "crunchbase.com",
    # News / press
    "pcmag.com", "techradar.com", "forbes.com", "techcrunch.com",
    "businessinsider.com", "gartner.com", "venturebeat.com", "zdnet.com",
    "businesswire.com", "prnewswire.com", "hollywoodreporter.com",
    "nytimes.com", "wsj.com", "washingtonpost.com", "bloomberg.com",
    "cnbc.com", "cnn.com", "bbc.com", "reuters.com", "ft.com", "npr.org",
    "theguardian.com", "axios.com", "engadget.com", "theverge.com",
    "wired.com", "ars-technica.com", "fastcompany.com", "fortune.com",
    # Social / general
    "reddit.com", "quora.com", "medium.com", "linkedin.com", "twitter.com",
    "youtube.com", "wikipedia.org", "facebook.com",
})


# Common terms that look capitalized but aren't real company names
_NOT_COMPANY = frozenset({
    "Inc", "Corp", "Corporation", "Group", "Co", "Ltd", "LLC",
    "Read More", "Read more", "Discover", "Compare",
    "Top", "More", "Other", "Various", "Best", "Free",
    "United States", "North America", "Europe", "Asia",
    "Click", "Here", "Learn", "More", "View",
})


def _clean_company_name(name: str) -> str:
    """Trim trailing junk and stop-words from extracted competitor names."""
    name = name.strip(" .,;:\"'")
    # Drop trailing corporate suffixes for cleaner display
    for suffix in (" Corporation", " Corp.", " Corp", " Inc.", " Inc", " LLC",
                   " Group", " Wholesale Corporation"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


# Match intro phrase + slice everything after it (up to ~250 chars).
# Examples that should match:
#   "Walmart competitors include Costco Wholesale, Target..."
#   "Top 10 Walmart competitors · Walgreens · Poshmark · ..."
#   "Walmart's top competitors are Amazon, Target, Costco..."
#   "competitors to walmart.com are amazon.com, target.com..."
_COMPETITOR_INTRO_RE = _re.compile(
    r"(?:top\s+\d+\s+)?"
    r"(?:competitors?|alternatives?|rivals?)"
    r"(?:\s+(?:are|include|to))?"
    r"\s*[:\-–·•]?\s+"
    r"(.{20,250}?)(?:\.\s|$|\bRead\s+more\b)",
    _re.IGNORECASE | _re.DOTALL,
)


# Hard reject list — capitalized phrases that look like names but aren't.
# Includes common UI/CTA words, article/listicle fragments, language codes.
_NOT_COMPANY_HARD = frozenset({
    # Language codes / locale labels
    "en", "es", "fr", "de", "pt", "zh", "ja",
    # UI / nav / CTA
    "play", "watch", "listen", "subscribe", "follow", "share",
    "read more", "see more", "learn more", "view all",
    "click here", "shop now", "sign in", "sign up", "log in",
    # Social platforms (rarely a competitor)
    "instagram", "facebook", "twitter", "tiktok", "youtube", "linkedin",
    "snapchat", "whatsapp", "telegram", "discord", "pinterest",
    # Generic pronouns / phrases that creep into snippets
    "the company", "the business", "the brand", "the firm",
    "we ", "our ", "your ", "their ",
    # Article / listicle junk
    "top", "best", "alternatives", "competitors", "rivals",
    "guide", "review", "reviews", "pricing", "stock", "news",
    "market", "here", "watch list", "guide to", "list of",
    "artificial intelligence", "artificialintelligence", "artificialinteligence",
    "main", "key", "leading", "popular", "more", "other",
    "this year", "this month", "this week", "today",
    "options", "vendors", "tools", "platforms", "solutions",
    "services", "products", "companies", "businesses",
    # Generic positional fragments
    "first", "second", "third", "next", "previous",
    # Common dangling phrases
    "sellers should watch", "should watch", "to watch",
    "to consider", "worth considering",
    "in 2024", "in 2025", "in 2026",
    # Data-infrastructure / web-scraping platforms — these are the "shovels",
    # not B2B competitors of any specific application company. Bright Data
    # in particular appears in SERP listicles about AI data pipelines but is
    # never a competitor of an AI assistant company. Reject outright.
    "bright data", "brightdata", "bright-data",
    "scraperapi", "scrapingbee", "zenrows", "oxylabs", "smartproxy",
    "apify", "diffbot", "octoparse", "phantombuster",
    # Sub-product fragments — feature-level mentions, not separate companies.
    # We keep the PARENT product names ("ChatGPT", "Microsoft Copilot",
    # "Gemini") as valid competitors; only the feature variants are dropped.
    "chatgpt search", "chatgpt enterprise", "chatgpt team", "chatgpt pro",
    "claude code", "claude desktop", "claude pro",
    "gemini advanced", "gemini pro", "gemini ultra",
    "copilot pro", "copilot enterprise",
    # Business-analysis framework names — these appear in SERP articles
    # ABOUT a company ("PESTEL analysis of Telkomsel") and the parser
    # mis-extracts the framework name as a competitor. None of these are
    # companies; they're MBA frameworks / consulting models.
    "pestel-analysis", "pestel analysis", "pestleanalysis", "pestle analysis",
    "portersfiveforce", "porters five force", "porter's five forces",
    "porter five forces", "swot analysis", "swot-analysis",
    "matrixbcg", "bcg matrix", "bcg-matrix", "growth-share matrix",
    "value chain analysis", "ansoff matrix",
    # Research / academic platforms that get name-extracted from "cited on X"
    "researchgate", "research-gate", "academia.edu", "scholar",
    "tabinsights", "tab insights", "ibisworld", "ibis-world",
    "statista", "datanyze", "owler",
    # Indonesian BUMN/PT suffix that gets stripped and becomes "Persero"
    # ("PT Pertamina (Persero)" → "Persero" via parser). Persero is the
    # state-enterprise legal suffix, not a company name.
    "persero", "tbk", "perseroan",
})


# Per-company "self-product" reject list — products that belong to the
# analyzed company and must never appear in its own competitor list. The
# normal self-rejection rule covers the company NAME ("Anthropic" inside
# "Anthropic" lookup) but not its product brands ("Claude" inside
# "Anthropic" lookup). Keys are lowercase company name; values are lowercase
# product brand names to filter.
_SELF_PRODUCTS: dict[str, frozenset[str]] = {
    "anthropic": frozenset({"claude"}),
    "openai":    frozenset({"chatgpt", "chat gpt", "gpt-4", "gpt-5", "sora", "dall-e", "dalle"}),
    "google":    frozenset({"gemini", "bard", "duet ai"}),
    "microsoft": frozenset({"copilot", "microsoft copilot", "github copilot", "bing"}),
    "meta":      frozenset({"llama", "meta ai"}),
    "amazon":    frozenset({"alexa", "aws bedrock", "titan", "nova"}),
}


# Countries, regions, continents, languages, major cities. A competitor name
# that normalizes to any of these is rejected outright — geography is never a
# B2B competitor. Lowercase. Covers the typical SERP noise where SEO listicles
# leak "Top Companies in Malaysia" or "China Energy" type fragments.
_GEOGRAPHY = frozenset({
    # Continents / regions
    "asia", "europe", "africa", "north america", "south america",
    "oceania", "antarctica", "middle east", "southeast asia",
    "apac", "emea", "latam", "anz",
    # Country / area abbreviations
    "us", "usa", "uk", "eu", "uae", "ksa",
    # Major countries
    "united states", "united kingdom", "united arab emirates",
    "china", "india", "indonesia", "malaysia", "singapore",
    "japan", "korea", "south korea", "north korea", "taiwan",
    "vietnam", "thailand", "philippines", "myanmar", "cambodia",
    "laos", "bangladesh", "pakistan", "sri lanka", "nepal",
    "hong kong", "macau", "mongolia",
    "australia", "new zealand",
    "germany", "france", "italy", "spain", "portugal",
    "netherlands", "belgium", "switzerland", "austria",
    "sweden", "norway", "denmark", "finland", "iceland",
    "ireland", "scotland", "wales", "england",
    "poland", "czech republic", "hungary", "romania", "greece",
    "russia", "ukraine", "belarus", "turkey",
    "brazil", "argentina", "chile", "colombia", "peru", "venezuela",
    "mexico", "canada", "cuba", "panama",
    "egypt", "morocco", "tunisia", "algeria", "libya",
    "nigeria", "kenya", "south africa", "ghana", "ethiopia",
    "saudi arabia", "iran", "iraq", "israel", "jordan", "lebanon",
    "syria", "qatar", "kuwait", "bahrain", "oman", "yemen",
    "afghanistan",
    # Major cities (the ones that recur in B2B SERP noise)
    "jakarta", "manila", "bangkok", "kuala lumpur", "singapore city",
    "mumbai", "delhi", "new delhi", "bangalore", "chennai", "hyderabad",
    "tokyo", "osaka", "kyoto", "seoul", "beijing", "shanghai",
    "shenzhen", "guangzhou", "dubai", "abu dhabi", "riyadh", "doha",
    "tehran", "istanbul", "cairo", "lagos", "nairobi",
    "london", "paris", "berlin", "madrid", "rome", "amsterdam",
    "moscow", "kyiv", "warsaw", "prague",
    "new york", "los angeles", "san francisco", "chicago",
    "boston", "seattle", "miami", "houston", "dallas",
    "toronto", "vancouver", "montreal",
    "sydney", "melbourne", "auckland",
    "são paulo", "sao paulo", "rio de janeiro", "buenos aires",
    "mexico city",
    # Programming-language names commonly mistaken for companies, and the
    # Indonesian island "Java" — frequently appears in Pertamina/Telkomsel
    # SEO listicles as a region.
    "java", "python", "ruby", "scala", "rust", "kotlin", "swift",
    "perl", "php", "lua",
    # Misc geographic noise common in SERP titles
    "world", "global", "international", "domestic", "regional", "local",
    "national",
})


# Generic common nouns that look capitalized in listicle SEO but are not
# B2B company names by themselves. Rejected when they appear as standalone
# single-word "competitor" candidates. Multi-word names that happen to
# contain one of these (e.g. "Snowflake Cloud") are not rejected here.
_GENERIC_SINGLE_NOUNS = frozenset({
    # Industry words
    "cloud", "data", "ai", "ml", "search", "app", "apps", "platform",
    "network", "wireless", "telecom", "telecoms", "telco",
    "energy", "oil", "gas", "petrol", "petroleum", "fuel",
    "power", "electricity", "utilities", "utility",
    "mining", "metals", "steel", "chemicals", "pharma", "pharmaceutical",
    "agriculture", "food", "retail", "wholesale",
    "auto", "automotive", "logistics", "shipping", "freight",
    "finance", "fintech", "insurance", "banking", "bank",
    "media", "entertainment", "music", "video", "streaming",
    "gaming", "games", "sports", "fitness", "health", "healthcare",
    "education", "training", "tourism", "travel", "hospitality",
    # Software/tech building blocks
    "software", "hardware", "service", "system", "systems",
    "solution", "infrastructure",
    "consulting", "consultant", "consultancy",
    # Common single product words mistakenly extracted
    "search", "browser", "email", "messaging", "chat",
    "calendar", "drive", "docs", "sheet", "sheets", "slide", "slides",
    # Already covered as junk fragments
    "brick", "parallel", "screen",
})


# Word-level reject — any name STARTING with one of these is rejected.
# Catches listicle constructions like "Sellers Should Watch", "Top Companies", etc.
_REJECT_HEAD_WORDS = frozenset({
    "sellers", "buyers", "vendors", "tools", "platforms", "solutions",
    "options", "alternatives", "competitors", "rivals", "companies",
    "top", "best", "leading", "popular", "main", "key", "more", "other",
    "various", "several", "many", "few", "all", "any", "some",
    "guide", "review", "reviews", "list", "watch", "watching", "consider",
    "shop", "buy", "compare", "search", "find", "discover",
    "read", "see", "learn", "view", "click",
    "free", "premium", "enterprise", "business", "consumer",
    "this", "that", "these", "those", "such", "any",
    # adjectives commonly extracted as standalone words
    "happy", "fast", "easy", "smart", "powerful", "scalable",
    # specific fragments that creep in from B2C / retail SERP snippets
    "brick", "parallel", "happyrobot", "happy robot",
    "mortar", "click", "screen", "platform", "service",
})


# Phrases that look like company names but aren't — exact normalized match.
_REJECT_PHRASES = frozenset({
    "sellers should watch", "buyers should watch", "things to watch",
    "watch list", "should watch", "to watch", "to consider",
    "happy robot",   # "HappyRobot" type fragment if extracted weirdly
    "should know", "must know", "need to know",
    "click read", "read read", "click learn",
    "the parallel", "parallel imports",   # for Amazon "Parallel" fragment
    "the brick", "brick and",              # for "Brick and Mortar" fragment
    "great brand", "best brand",
})


def _looks_like_competitor_name(name: str, company: str) -> bool:
    """Quality gate for an extracted competitor candidate.

    Returns False (reject) for listicle/article junk like "Sellers Should Watch",
    "Top Companies", "Brick", single-word stop terms, geography (China,
    Malaysia, Java), and generic common nouns (Cloud, Data, Energy).

    Principle: when in doubt, reject. We'd rather show "no competitors found"
    than fake competitors. The trust failure of junk competitors is worse than
    the absence of a populated table.
    """
    if not name or len(name) < 3 or len(name) > 35:
        return False
    lc = name.lower().strip()
    company_lower = company.lower()
    # Never include the analyzed company in its own competitor list
    if company_lower and (company_lower in lc or lc in company_lower):
        return False
    # Strip a corporate suffix before comparing so "Amazon Inc" matches "Amazon"
    suffix_stripped = _re.sub(
        r"\s+(?:inc|corp(?:oration)?|co|ltd|llc|group|plc|sa|nv|ag|gmbh)\.?$",
        "", lc,
    ).strip()
    if company_lower and (suffix_stripped == company_lower or
                          suffix_stripped in company_lower or
                          company_lower in suffix_stripped):
        return False
    if lc in _NOT_COMPANY_HARD or name in _NOT_COMPANY or lc in _REJECT_PHRASES:
        return False
    # Reject geography outright — countries, regions, cities, languages
    if lc in _GEOGRAPHY or suffix_stripped in _GEOGRAPHY:
        return False
    # Reject the analyzed company's own product brands (e.g. "Claude" when
    # analyzing Anthropic, "ChatGPT" when analyzing OpenAI). These names
    # would otherwise pass the generic gate and pollute the competitor set.
    self_products = _SELF_PRODUCTS.get(company_lower, frozenset())
    if self_products and (lc in self_products or suffix_stripped in self_products):
        return False
    letters = sum(1 for ch in name if ch.isalpha())
    if letters < 3:
        return False
    words = lc.split()
    # Reject if first word is a known stopword/article-frame head
    if words and words[0] in _REJECT_HEAD_WORDS:
        return False
    # Single-word names are higher-risk — apply stricter gating.
    if len(words) == 1:
        if words[0] in _REJECT_HEAD_WORDS:
            return False
        # Generic single-word industry/tech/geography nouns — Cloud, Data, AI,
        # Energy, Oil, Search, etc. Allow them only when used as part of a
        # multi-word brand name (handled in the >1-word branch).
        if words[0] in _GENERIC_SINGLE_NOUNS:
            return False
        # Allow 3-letter ALL-CAPS acronyms (AMD, IHG, IBM, SAP) — they're real
        # company names. Reject 3-letter mixed-case (rare; usually fragments).
        if len(name) < 3:
            return False
        if len(name) == 3 and not name.isupper():
            return False
    # Multi-word candidate that is JUST geography + a generic industry noun
    # (e.g. "China Energy", "Malaysia Telecom", "Indonesia Oil") — these are
    # SERP listicle headers, not real company names. Reject when every word
    # is either geography or a generic industry noun.
    if len(words) > 1:
        if all(w in _GEOGRAPHY or w in _GENERIC_SINGLE_NOUNS for w in words):
            return False
    # Reject if any word is a clearly-non-company token (catches mid-sentence
    # fragments like "Buyers Should Watch")
    bad_mid_tokens = {"should", "must", "could", "would", "will", "shall",
                       "watch", "consider", "evaluate", "review",
                       "know", "find", "buy", "shop"}
    if any(w in bad_mid_tokens for w in words):
        return False
    return True


def _extract_competitors_from_snippet(snippet: str, company: str,
                                       seen: set[str]) -> list[str]:
    """Pull competitor company names mentioned inside a SERP snippet.

    Strategy: only fire after an explicit intro phrase like 'competitors are X,
    Y, Z' or 'Top 10 X competitors · A · B · C'. Then split the captured chunk
    on comma/bullet separators. Quality gate `_looks_like_competitor_name`
    rejects listicle junk and stopword-starting phrases.
    """
    if not snippet:
        return []
    found: list[str] = []

    m = _COMPETITOR_INTRO_RE.search(snippet)
    if not m:
        return []

    raw_chunk = m.group(1)
    # Split on common list separators: comma, bullet, semicolon, " and ", " or ", " · ", " | "
    pieces = _re.split(
        r"\s*(?:,|·|•|;|\||\s+and\s+|\s+or\s+)\s*",
        raw_chunk,
    )

    cap_pattern = _re.compile(
        r"([A-Z][A-Za-z0-9&\.\-']*(?:\s+[A-Z][A-Za-z0-9&\.\-']*){0,3})"
    )

    for piece in pieces:
        # Multi-pass: try EACH capital phrase in the piece (not just the first).
        # Comma-splits sometimes leave lowercase fragments at the start, or
        # mix junk + a real name in the same piece (e.g. "Sellers Should
        # Watch eBay" — we want to find eBay even though "Sellers Should
        # Watch" comes first and gets rejected).
        for raw in cap_pattern.findall(piece):
            name = _clean_company_name(raw)
            # Strip a domain suffix if present (".com" → "")
            if name.endswith(".com") or name.endswith(".net") or name.endswith(".org"):
                name = name.rsplit(".", 1)[0]
            # Drop trailing stop-word tail
            words = name.split()
            while words and words[-1].lower() in {
                "and", "the", "a", "for", "with", "stock", "jumps",
                "competitors", "alternatives", "includes", "more",
            }:
                words.pop()
            name = " ".join(words)
            if not _looks_like_competitor_name(name, company):
                continue
            key = name.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(name)
            if len(found) >= 5:
                return found
            break  # first valid name per piece; move to next piece
    return found


def _domain_to_name(domain: str) -> str:
    """'brex.com' → 'Brex', 'salesforce.com' → 'Salesforce'."""
    name = domain.split(".")[0] if domain else ""
    return name.capitalize() if name else ""


def _infer_overlap(text: str, company: str | None = None) -> str:
    """Classify the competitive overlap from snippet text.

    Order matters: more specific categories first, generic 'Finance & ERP'
    last (was previously matching too aggressively on words like 'finance').
    Company name hint also routes obvious AI labels to the AI category.
    """
    t = text.lower()
    company_l = (company or "").lower()

    # AI / LLM space (Anthropic, OpenAI, Cohere, etc.) — check FIRST so 'finance'
    # in body text doesn't beat the AI signal.
    if any(k in t for k in ["llm", "large language model", "ai assistant",
                              "ai chatbot", "generative ai", "ai model", "claude",
                              "chatgpt", "gemini", "copilot", "foundation model"]):
        return "AI assistants & LLMs"
    if company_l in {"anthropic", "openai", "cohere", "mistral", "perplexity"}:
        return "AI assistants & LLMs"
    if any(k in t for k in ["expense", "spend", "corporate card", "reimburs"]):
        return "Expense management"
    if any(k in t for k in ["sales", "crm", "outreach", "prospecting", "pipeline"]):
        return "Sales intelligence"
    if any(k in t for k in ["payroll", "recruiting", "people ops", "hr software"]):
        return "HR & people ops"
    if any(k in t for k in ["project", "task", "workflow", "productivity"]):
        return "Workflow tools"
    if any(k in t for k in ["erp", "accounting", "billing", "invoic"]):
        return "Finance & ERP"
    if any(k in t for k in ["market", "email campaign", "growth marketing"]):
        return "Marketing tech"
    if any(k in t for k in ["cloud", "infra", "platform", "devops"]):
        return "Infrastructure"
    if any(k in t for k in ["analytics", "data warehouse", "business intelligence"]):
        return "Data & analytics"
    return "Competing market"


def _parse_competitor_serp_response(raw: Any, company: str) -> list[dict]:
    """Parse organic SERP results for competitor query into CompetitorRow-compatible dicts.

    Two-pass strategy, confidence-aware:
      Pass 1 (PRIMARY/STRONG): explicit "competitors are X, Y, Z" snippet matches.
        Tagged threat="high" — these are names the source text NAMED as competitors.
      Pass 2 (FALLBACK/WEAK): organic-result domain → company name. Useful for B2B
        SaaS where each top result is a vendor homepage. Tagged threat="low" so
        scoring downstream can apply a confidence penalty.

    The threat field doubles as a strength tag here. Downstream
    (`_inject_live_signals`) reads it to decide how much weight to give the
    competitor signal — strong-majority sets get high confidence + positive
    impact; weak-only sets get low confidence + neutral impact.

    Returns [] when fewer than 2 *strong* (explicit-list) competitors AND the
    fallback pass didn't recover at least 3 clean domain-based candidates. That
    way we never publish a single-row junk competitor table.
    """
    raw = _unwrap_serp_body(raw)
    if not raw:
        return []

    strong: list[dict] = []     # Pass 1 — explicit competitor lists
    weak: list[dict] = []       # Pass 2 — domain-only fallback
    seen: set[str] = set()
    strong_source_urls: set[str] = set()
    company_lower = company.lower()

    # Cap raised from 5 to 8 so scoring can differentiate competitively-dense
    # companies (saturated retail/e-comm: 8 strong) from niche markets
    # (specialist verticals: 2-4 strong). UI displays only top-5 visually
    # ("+N more used in scoring") — see CompetitorTable.tsx.
    _MAX = 8

    # Pass 1 (PRIMARY): scan snippets for explicit competitor lists.
    for result in raw.get("organic", [])[:14]:
        if len(strong) >= _MAX:
            break
        snippet = result.get("description", result.get("snippet", "")) or ""
        title = result.get("title", "") or ""
        url = result.get("link", "")
        if not _mentions_target_company(company, title, snippet, url):
            continue
        names_in_snippet = _extract_competitors_from_snippet(
            snippet + " " + title, company, seen,
        )
        for name in names_in_snippet:
            if url:
                strong_source_urls.add(url)
            strong.append({
                "name": name,
                "overlap": _infer_overlap(snippet + " " + title, company),
                "recent_move": f"Listed as a top competitor of {company} in market research.",
                "threat": "high",        # strong: explicit competitor-list evidence
                "mode": "live",
                "source_url": url or None,
                "source_title": title or None,
            })
            if len(strong) >= _MAX:
                break

    # Pass 2 (FALLBACK): organic result domains (B2B SaaS competitor homepages).
    for result in raw.get("organic", [])[:14]:
        if len(strong) + len(weak) >= _MAX:
            break
        url = result.get("link", "")
        title = result.get("title", "")
        snippet = result.get("description", result.get("snippet", ""))
        domain = _extract_domain(url) if url else ""

        if url and url in strong_source_urls:
            continue
        if not domain or domain in _SKIP_DOMAINS:
            continue
        if _has_known_context(company) and not _mentions_target_company(company, title, snippet, ""):
            continue
        name = _domain_to_name(domain)
        if not name or name.lower() in seen:
            continue
        if company_lower in name.lower() or name.lower() in company_lower:
            continue
        # Apply the same quality gate (catches "Brick", geography, generic nouns)
        if not _looks_like_competitor_name(name, company):
            continue

        seen.add(name.lower())
        weak.append({
            "name": name,
            "overlap": _infer_overlap(title + " " + snippet, company),
            "recent_move": (snippet[:120] if snippet else title[:120]) or "No recent signal.",
            "threat": "low",   # weak: domain-only inference, no explicit "competitor" mention
            "mode": "live",
            "source_url": url or None,
            "source_title": title or None,
        })

    # Quality thresholds (anti-noise rules):
    #   - Strong-only path: 1 strong → []. ≥2 strong → publish.
    #   - Mixed: ≥1 strong + any weak → publish (strong validates the set).
    #   - Weak-only: need ≥3 to publish (single/double domain hits without any
    #     explicit competitor-list mention is too thin to claim "competitors").
    if len(strong) >= 2:
        # Strong-first; fill with weak up to _MAX
        return (strong + weak)[:_MAX]
    if len(strong) == 1 and weak:
        return (strong + weak)[:_MAX]
    if not strong and len(weak) >= 3:
        return weak[:_MAX]
    return []


# Source-authority tiers — used to badge evidence rows in the UI.
# Tier 1: verified press wire, major financial/business outlets, primary sources
# Tier 2: mainstream tech/business media, established news outlets
# Tier 3: niche blogs, aggregators, lesser-known sites
_TIER_1_DOMAINS: frozenset[str] = frozenset({
    "bloomberg.com", "wsj.com", "reuters.com", "ft.com", "nytimes.com",
    "cnbc.com", "washingtonpost.com", "economist.com", "marketwatch.com",
    "prnewswire.com", "businesswire.com", "globenewswire.com",
    "sec.gov", "investor.gov",
    # Known primary company domains (press rooms / investor pages)
    "press.aboutamazon.com", "ir.aboutamazon.com", "aboutamazon.com",
    "amazon.science",
    "nvidianews.nvidia.com",
    "corporate.walmart.com", "news.walmart.com",
    "news.marriott.com",
    "investors.affirm.com",
    "anthropic.com",  # anthropic.com/news, anthropic.com/research are primary
})

_TIER_2_DOMAINS: frozenset[str] = frozenset({
    "techcrunch.com", "forbes.com", "businessinsider.com", "axios.com",
    "fortune.com", "fastcompany.com", "wired.com", "theverge.com",
    "engadget.com", "venturebeat.com", "zdnet.com", "theinformation.com",
    "pcmag.com", "techradar.com", "crn.com", "thenewstack.io",
    "networkworld.com", "theguardian.com", "bbc.com", "cnn.com",
    "yahoo.com", "msn.com", "ap.org", "npr.org",
})

# Subdomain prefixes that signal a primary/company source. When these appear
# on ANY domain (e.g. `ir.example.com`, `investor.example.com`, `news.example.com`),
# we promote at least to tier-2 (verified primary source — not a random blog).
_PRIMARY_SOURCE_SUBDOMAINS: frozenset[str] = frozenset({
    "ir", "investor", "investors", "investorrelations",
    "news", "press", "newsroom", "media",
    "corporate", "about", "blog", "research",
})


def _classify_source_tier(domain: str | None) -> str:
    """Return 'tier-1' | 'tier-2' | 'tier-3' based on domain authority.

    Rules (first match wins):
      1. Exact-match against Tier-1 → tier-1
      2. Exact-match against Tier-2 → tier-2
      3. Subdomain of a known Tier-1 domain → tier-1
      4. Known primary-source subdomain prefix (ir.*, investor.*, news.*,
         press.*, corporate.*, about.*, blog.*) → tier-1 (treat company
         primary IR/press as authoritative)
      5. Default → tier-3
    """
    if not domain:
        return "tier-3"
    d = domain.lower().replace("www.", "")
    if d in _TIER_1_DOMAINS:
        return "tier-1"
    if d in _TIER_2_DOMAINS:
        return "tier-2"
    # Subdomain of a known Tier-1 domain (e.g. "investor.bloomberg.com")
    for t1 in _TIER_1_DOMAINS:
        if d.endswith("." + t1):
            return "tier-1"
    # Primary-source subdomain heuristic. We only promote if the first label is
    # one of the known primary-source prefixes AND there are at least 2 more
    # labels (so we don't accidentally promote single-label domains).
    parts = d.split(".")
    if len(parts) >= 3 and parts[0] in _PRIMARY_SOURCE_SUBDOMAINS:
        return "tier-1"
    return "tier-3"


# Phrase-level signal detection — checked in priority order, first match wins.
# This replaces a naive substring approach that misclassified "NVIDIA investing
# in UK AI infrastructure" as `funding` (the company is the INVESTOR, not the
# investee). We check `expansion` BEFORE `funding` so outbound-investment
# language wins; `funding` requires phrases that imply the company RECEIVED
# capital (raised, Series X, valuation, IPO).
#
# Earnings/financial results are routed to `news` (not `product`) so periodic
# financial disclosures don't fake a product-launch signal.
_SIGNAL_PATTERNS: list[tuple[str, list[str]]] = [
    # Earnings / financial results FIRST so they don't get caught by
    # broader "release" / "announce" patterns lower in the list.
    # Also catches corporate disclosure pages (investor relations, sustainable
    # finance framework, company profile, ESG report) so they don't get
    # misclassified as product launches or funding rounds.
    ("news", [
        r"\bearnings\b", r"\bearnings call\b", r"\bearnings report\b",
        r"\bq[1-4](?:\s+(?:fiscal|fy))?\s+\d{2,4}\b",  # Q1 2026, Q3 FY2026
        r"\bquarter(?:ly)? results\b", r"\bquarterly earnings\b",
        r"\bfinancial results\b", r"\bannual results\b",
        r"\bnet sales\b", r"\boperating income\b", r"\bnet income\b",
        r"\brevenue (?:grew|increased|of|rose|jumped|up\b)\b",
        r"\bguidance\b", r"\b10-q\b", r"\b10-k\b", r"\b8-k\b",
        r"\bshareholder (?:letter|report)\b",
        # Corporate-disclosure / static-content pages — NOT capital events.
        # Listed here (highest priority) so funding patterns can't later
        # mis-classify "sustainable finance framework" as a funding round.
        r"\bsustainable finance(?:\s+framework)?\b",
        r"\bsustainability (?:framework|report|policy|disclosures?)\b",
        r"\besg (?:framework|report|policy|disclosures?|score)\b",
        r"\bcompany profile\b", r"\bcorporate profile\b",
        r"\binvestor relations\b", r"\bcorporate governance\b",
        r"\bannual report\b", r"\bproxy statement\b",
        r"\bcsr report\b", r"\bsustainability page\b",
        r"\bfinance framework\b", r"\bfinancing framework\b",
        r"\binvestment program\b", r"\binvestor day\b",
        r"\bfinancial community\b", r"\bupcoming events\b",
        r"\bpresent at (?:the )?following events\b",
    ]),
    ("expansion", [
        # "investing in X" / "investing $5B in X" / "invests in" / "investments in"
        r"\binvest(?:s|ed|ing|ment|ments)?\b(?:\s+[\$\w][\w.,]*){0,4}\s+in\b",
        r"\bbuild(?:s|ing)? (?:new )?(?:infrastructure|facility|facilities|data\s?center|campus|office|plant|factory|plant)\b",
        r"\bpartnership\b", r"\bpartner(?:s|ed|ing)? with\b", r"\balliance\b",
        r"\bexpand(?:s|ing|ed|ion)?\b", r"\bnew region\b", r"\binternational expansion\b",
        r"\bacqui(?:re|red|res|sition)\b", r"\bmerger\b", r"\bjoint venture\b",
        r"\bnew (?:market|country|geography)\b", r"\bopen(?:s|ed|ing) (?:new )?(?:office|hub)\b",
    ]),
    ("funding", [
        r"\braised? \$\d", r"\braising \$\d", r"\braise[ds]? (?:[\w$]+\s+){0,3}round\b",
        r"\bseries [a-h](?:[-\s]?\d)?\b",
        r"\bfunding round\b", r"\bfinancing round\b",
        r"\bvaluation of\b", r"\bvalued at \$\d", r"\bvaluation (?:hits?|reaches|tops)\b",
        r"\bipo\b", r"\binitial public offering\b",
        r"\bventure capital\b", r"\bvc-backed\b", r"\bvc round\b",
        r"\bseed (?:round|funding)\b", r"\bbridge round\b",
        r"\bsecondary sale\b", r"\btender offer\b", r"\bgrant raised\b",
    ]),
    ("hiring", [
        r"\bhiring\b", r"\bjob (?:openings?|posting)\b",
        r"\bnew roles?\b", r"\bopen positions?\b", r"\bopen roles?\b",
        r"\bheadcount\b", r"\brecruit(?:s|ed|ing)?\b",
        r"\bworkforce\b", r"\btalent acquisition\b", r"\bbuild(?:s|ing) team\b",
    ]),
    ("product", [
        r"\blaunch(?:es|ed|ing)?\b", r"\bnew product\b", r"\bnew feature\b",
        r"\b(?:product )?announce(?:d|s|ment)\b",
        r"\brelease(?:d|s)?\b", r"\brolled out\b",
        r"\bbeta\b", r"\bga release\b", r"\bgeneral availability\b",
        r"\bships?\b", r"\bunveil(?:s|ed|ing)?\b",
    ]),
    ("review", [
        r"\bg2 reviews?\b", r"\bcapterra\b", r"\btrustpilot\b",
        r"\bcustomer feedback\b", r"\buser reviews?\b", r"\bcomplaints?\b",
    ]),
    ("competitor", [
        r"\bcompetitors?\b", r"\bvs\.?\s", r"\balternatives?\b", r"\brival(?:s|ry)?\b",
        r"\bcompetes? with\b",
    ]),
]


def _detect_signal(text: str) -> str:
    """Classify a snippet into one signal kind. Order-sensitive (first match wins).

    Conservative defaults — if no specific pattern matches, falls back to "news".
    """
    if not text:
        return "news"
    t = text.lower()
    for signal, patterns in _SIGNAL_PATTERNS:
        for pat in patterns:
            if _re.search(pat, t, _re.IGNORECASE):
                return signal
    return "news"


def _parse_serp_response(raw: Any, company: str) -> list[dict]:
    """Convert Bright Data SERP JSON to a list of evidence dicts.

    Handles both the brd_json=1 response (organic + news blocks) and
    gracefully degrades if the shape differs.
    """
    raw = _unwrap_serp_body(raw)
    if not raw:
        return []

    items: list[dict] = []
    seen_urls: set[str] = set()

    def _add(source: str, title: str, url: str, snippet: str, date: str | None,
             confidence: str, idx: int) -> None:
        if not title and not snippet:
            return
        if not _mentions_target_company(company, title, snippet, url):
            return
        url = url or ""
        if url in seen_urls:
            return
        seen_urls.add(url)
        signal = _detect_signal(f"{title} {snippet}")
        domain_for_tier = _extract_domain(url) if url else source
        # Down-rank confidence for stale evidence — old articles shouldn't pump
        # the why-now score just because they had a high base confidence.
        adjusted_confidence = _freshness_aware_confidence(confidence, date)
        items.append({
            "id": f"live_{idx}",
            "source": domain_for_tier,
            "source_title": title or None,
            "url": url or None,
            "signal": signal,
            "summary": (snippet or title)[:300],
            "timestamp": date,
            "tool": "SERP API",
            "confidence": adjusted_confidence,
            "mode": "live",
            "tier": _classify_source_tier(domain_for_tier),
        })

    idx = 1

    # News block (high priority — most recent, most relevant)
    news_block = raw.get("news", {})
    if isinstance(news_block, dict):
        news_items = news_block.get("results", [])
    elif isinstance(news_block, list):
        news_items = news_block
    else:
        news_items = []

    for item in news_items[:4]:
        _add(
            source="Google News",
            title=item.get("title", ""),
            url=item.get("link", ""),
            snippet=item.get("description", item.get("snippet", "")),
            date=item.get("date", item.get("published", None)),
            confidence="high",
            idx=idx,
        )
        idx += 1

    # Organic results — Bright Data SERP returns rich news-like items here
    # even when 'news' block is absent. Extract date from extensions when present.
    for result in raw.get("organic", [])[:7]:
        _add(
            source=result.get("source") or _extract_domain(result.get("link", "")),
            title=result.get("title", ""),
            url=result.get("link", ""),
            snippet=result.get("description", result.get("snippet", "")),
            date=_date_from_extensions(result.get("extensions")),
            confidence="high" if _date_from_extensions(result.get("extensions")) else "medium",
            idx=idx,
        )
        idx += 1

    return items[:7]  # cap at 7 live evidence items


# ── Client ───────────────────────────────────────────────────────────────────

class BrightDataClient:
    """Thin wrapper. Always returns (data, latency_ms, status)."""

    def __init__(self, cfg: Optional[BrightDataConfig] = None) -> None:
        self.cfg = cfg or BrightDataConfig.from_env()

    @property
    def is_live(self) -> bool:
        return not self.cfg.use_mock and bool(self.cfg.token)

    async def serp_news_evidence(self, company: str) -> tuple[list[dict], int, str]:
        """Return (evidence_list, latency_ms, status).

        Live: calls Bright Data SERP API and parses results into evidence dicts.
        Mock / no token: returns ([], 0, 'mock').
        Error: returns ([], latency_ms, 'fallback').
        """
        if not self.is_live:
            return [], 0, "mock"

        # Recency-biased query — uses the CURRENT year dynamically so the system
        # doesn't go stale next year. Google ranks fresh results higher when
        # 'latest' and 'recent' appear alongside the current year.
        query = _build_news_query(company)
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    f"{BD_API_BASE}/request",
                    headers={"Authorization": f"Bearer {self.cfg.token}"},
                    json={
                        "zone": self.cfg.serp_zone,
                        "url": f"https://www.google.com/search?q={quote_plus(query)}&brd_json=1",
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()
                ms = int((time.perf_counter() - t0) * 1000)
                items = _parse_serp_response(raw, company)
                if not items:
                    return [], ms, "fallback"
                return items, ms, "ok"
        except httpx.HTTPStatusError as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            return [], ms, "error" if exc.response.status_code >= 500 else "fallback"
        except Exception:
            return [], int((time.perf_counter() - t0) * 1000), "fallback"

    async def serp_competitor_evidence(self, company: str) -> tuple[list[dict], int, str]:
        """Return (competitor_list, latency_ms, status) from a competitor SERP query.

        Queries '{company} alternatives competitors' and parses organic domains.
        """
        if not self.is_live:
            return [], 0, "mock"

        query = _build_competitor_query(company)
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=25.0) as client:
                resp = await client.post(
                    f"{BD_API_BASE}/request",
                    headers={"Authorization": f"Bearer {self.cfg.token}"},
                    json={
                        "zone": self.cfg.serp_zone,
                        "url": f"https://www.google.com/search?q={quote_plus(query)}&brd_json=1",
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                raw = resp.json()
                ms = int((time.perf_counter() - t0) * 1000)
                items = _parse_competitor_serp_response(raw, company)
                return items, ms, "ok"
        except httpx.HTTPStatusError as exc:
            ms = int((time.perf_counter() - t0) * 1000)
            return [], ms, "error" if exc.response.status_code >= 500 else "fallback"
        except Exception:
            return [], int((time.perf_counter() - t0) * 1000), "fallback"

    async def unlocker_fetch(self, url: str) -> tuple[Any, int, str]:
        if not self.is_live or not url:
            return None, 0, "mock"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(
                    f"{BD_API_BASE}/request",
                    headers={"Authorization": f"Bearer {self.cfg.token}"},
                    json={"zone": self.cfg.unlocker_zone, "url": url, "format": "raw"},
                )
                resp.raise_for_status()
                return resp.text, int((time.perf_counter() - t0) * 1000), "ok"
        except Exception:
            return None, int((time.perf_counter() - t0) * 1000), "fallback"

    async def unlocker_extract_article(self, url: str) -> tuple[Optional[str], int, str]:
        """Fetch URL via Web Unlocker and extract clean readable text.

        Returns (text, latency_ms, status).
          - status="ok"       : strong extraction (≥200 chars of body text)
          - status="partial"  : page returned but text is title-only / very short
          - status="fallback" : strip returned empty
          - status=<error>    : the underlying HTTP fetch failed

        Caller decides whether to publish 'partial' results — typically they
        should be labeled as title/partial-text + low confidence, not
        "Full article text".
        """
        raw_html, ms, status = await self.unlocker_fetch(url)
        if status != "ok" or not raw_html:
            return None, ms, status
        text = _strip_html_to_text(raw_html)
        if not text:
            return None, ms, "fallback"
        # Quality gate: anything under ~200 chars is a title/landing page,
        # NOT a real article body.
        if len(text) < 200:
            return text[:600], ms, "partial"
        return text[:600], ms, "ok"

    # ── Web Scraper API (async dataset trigger + polling) ──────────────────
    # Used by /warmup and /scraper/refresh, NOT by /analyze (too slow).
    # /analyze loads pre-warmed snapshots from disk instead.

    async def scraper_dataset(self, dataset_id: str, payload: dict) -> tuple[Any, int, str]:
        """Trigger a Web Scraper dataset job (returns snapshot_id immediately)."""
        if not self.is_live or not dataset_id:
            return None, 0, "mock"
        t0 = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{BD_API_BASE}/datasets/v3/trigger?dataset_id={dataset_id}",
                    headers={"Authorization": f"Bearer {self.cfg.token}"},
                    json=payload,
                )
                resp.raise_for_status()
                return resp.json(), int((time.perf_counter() - t0) * 1000), "ok"
        except Exception:
            return None, int((time.perf_counter() - t0) * 1000), "fallback"

    async def scraper_poll_snapshot(self, snapshot_id: str,
                                     max_wait_s: int = 120,
                                     interval_s: float = 3.0) -> tuple[Any, int, str]:
        """Poll a triggered Web Scraper snapshot until ready or timeout.

        Returns (records, latency_ms, status). status in {ok, fallback, error}.
        Designed for offline /warmup — NOT to be called from /analyze synchronously.
        """
        if not self.is_live or not snapshot_id:
            return None, 0, "mock"
        t0 = time.perf_counter()
        deadline = t0 + max_wait_s
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                while time.perf_counter() < deadline:
                    resp = await client.get(
                        f"{BD_API_BASE}/datasets/v3/snapshot/{snapshot_id}?format=json",
                        headers={"Authorization": f"Bearer {self.cfg.token}"},
                    )
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                        except Exception:
                            data = None
                        ms = int((time.perf_counter() - t0) * 1000)
                        return data, ms, "ok"
                    if resp.status_code == 202:
                        # Still running — wait then retry
                        import asyncio as _aio
                        await _aio.sleep(interval_s)
                        continue
                    # Any other status = error
                    ms = int((time.perf_counter() - t0) * 1000)
                    return None, ms, "fallback"
        except Exception:
            pass
        return None, int((time.perf_counter() - t0) * 1000), "fallback"

    async def scraper_collect_for_company(self, dataset_id: str, company: str,
                                          domain: str | None = None) -> tuple[list[dict], int, str]:
        """High-level: trigger + poll → normalized list of records for one company.

        Payload schema is dataset-dependent. We use a sensible default that
        works for LinkedIn-jobs / LinkedIn-company-employees datasets.
        Override via env if dataset expects different inputs.
        """
        if not self.is_live or not dataset_id:
            return [], 0, "mock"
        # Default payload — most LinkedIn-flavored datasets accept "url" or "company"
        company_url = f"https://www.linkedin.com/company/{company.lower().replace(' ', '-')}"
        payload = [{"url": company_url, "company": company}]
        triggered, trigger_ms, t_status = await self.scraper_dataset(dataset_id, payload)
        if t_status != "ok" or not triggered:
            return [], trigger_ms, t_status
        snapshot_id = (
            triggered.get("snapshot_id")
            or triggered.get("id")
            or (triggered[0].get("snapshot_id") if isinstance(triggered, list) and triggered else None)
        )
        if not snapshot_id:
            return [], trigger_ms, "fallback"
        records, poll_ms, p_status = await self.scraper_poll_snapshot(snapshot_id)
        if p_status != "ok":
            return [], trigger_ms + poll_ms, p_status
        # Normalize: ensure list
        if isinstance(records, dict):
            records = records.get("data") or records.get("results") or [records]
        if not isinstance(records, list):
            return [], trigger_ms + poll_ms, "fallback"
        return records, trigger_ms + poll_ms, "ok"


# ── HTML extraction ─────────────────────────────────────────────────────────

_TAG_RE = _re.compile(r"<[^>]+>")
_WS_RE = _re.compile(r"\s+")
_SCRIPT_STYLE_RE = _re.compile(
    r"<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>", _re.DOTALL | _re.IGNORECASE
)
# Drop common chrome blocks: nav, header, footer, aside, form
_CHROME_RE = _re.compile(
    r"<(nav|header|footer|aside|form|menu)[^>]*>.*?</\1>", _re.DOTALL | _re.IGNORECASE
)
_BLOCK_BREAK_RE = _re.compile(r"</(p|div|h[1-6]|li|br|tr)>", _re.IGNORECASE)
_META_TAG_RE = _re.compile(r"<(meta|link|input|button)[^>]*>", _re.IGNORECASE)

# Article body containers (in priority order) — extracts the inner HTML of the
# first matching block so we drop site chrome surrounding it.
_ARTICLE_PATTERNS = [
    _re.compile(r'<article[^>]*>(.*?)</article>', _re.DOTALL | _re.IGNORECASE),
    _re.compile(r'<main[^>]*>(.*?)</main>', _re.DOTALL | _re.IGNORECASE),
    _re.compile(
        r'<div[^>]*\b(?:class|id)\s*=\s*["\'][^"\']*'
        r'(?:article|post-body|entry-content|story|release-body|prntext)'
        r'[^"\']*["\'][^>]*>(.*?)</div>',
        _re.DOTALL | _re.IGNORECASE,
    ),
]

# Lines that smell like nav/menu boilerplate — short, generic.
_BOILERPLATE_LINE_PATTERNS = [
    _re.compile(r'^(home|about|contact|search|news|products|services|resources|sign in|log in|menu|skip[ to]*|accessibility)\b', _re.IGNORECASE),
    _re.compile(r'^(all news|press release|investor relations|journalists|agencies|client login|send a release)\b', _re.IGNORECASE),
    _re.compile(r'^(privacy|terms|cookies?|policy|copyright|©|all rights reserved)\b', _re.IGNORECASE),
    _re.compile(r'^(follow us|share this|subscribe|newsletter)\b', _re.IGNORECASE),
]


def _looks_like_boilerplate(line: str) -> bool:
    if len(line) < 25:
        return True
    return any(p.match(line) for p in _BOILERPLATE_LINE_PATTERNS)


def _strip_html_to_text(html: str) -> str:
    """HTML → clean readable article text.

    Strategy:
    1. Drop scripts, styles, svgs, iframes outright.
    2. Try to extract the article body — <article>/<main>/post-body containers.
       If found, only process that; everything else (nav, footer, menus) is gone.
    3. Otherwise drop common chrome blocks (<nav>, <header>, <footer>, <aside>).
    4. Strip remaining tags, collapse whitespace, drop boilerplate lines.
    """
    if not html:
        return ""

    # 1. Drop script/style/svg/iframe blocks
    html = _SCRIPT_STYLE_RE.sub(" ", html)

    # 2. Prefer article body if we can find one
    body_html = None
    for pat in _ARTICLE_PATTERNS:
        m = pat.search(html)
        if m and len(m.group(1)) > 200:
            body_html = m.group(1)
            break
    if body_html is None:
        # 3. Fallback: drop chrome blocks from full page
        body_html = _CHROME_RE.sub(" ", html)

    # 4. Strip leftover meta/buttons/links
    body_html = _META_TAG_RE.sub(" ", body_html)
    # Convert block-closes to sentence breaks for readability
    body_html = _BLOCK_BREAK_RE.sub("\n", body_html)
    text = _TAG_RE.sub(" ", body_html)

    # 5. Collapse whitespace per line, drop short/boilerplate lines, rejoin
    lines = [_WS_RE.sub(" ", ln).strip() for ln in text.split("\n")]
    kept = [ln for ln in lines if ln and not _looks_like_boilerplate(ln)]
    return " ".join(kept).strip()
