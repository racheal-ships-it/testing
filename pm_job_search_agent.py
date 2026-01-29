#!/usr/bin/env python3
"""
PM Job Search Agent
====================
Automated agent that searches for Lead/Staff/Director/Principal Product Management
roles at top tech companies, with a focus on Trust & Safety positions.

Two modes:
  1. LIVE MODE (default): Fetches from Greenhouse/Lever/Ashby APIs in real time.
     Requires network access:  pip install requests beautifulsoup4
  2. CACHED MODE (--cached): Uses curated snapshot of verified postings
     (last updated Jan 2026). No dependencies required.

Usage:
    python3 pm_job_search_agent.py                    # live API search
    python3 pm_job_search_agent.py --cached            # use curated snapshot
    python3 pm_job_search_agent.py --html report.html  # custom output path
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Company:
    name: str
    careers_url: str
    logo_emoji: str = ""


COMPANIES = [
    Company("Block (Cash App)", "https://block.xyz/careers/jobs", "💰"),
    Company("Airbnb", "https://careers.airbnb.com/positions/", "🏠"),
    Company("Coinbase", "https://www.coinbase.com/careers/positions", "🪙"),
    Company("Zillow", "https://www.zillow.com/careers/", "🏡"),
    Company("Pinterest", "https://www.pinterestcareers.com/en/jobs/", "📌"),
    Company("Reddit", "https://www.redditinc.com/careers", "🤖"),
    Company("Oura", "https://ouraring.com/careers", "💍"),
    Company("OpenAI", "https://openai.com/careers/search/", "🧠"),
    Company("Anthropic", "https://www.anthropic.com/jobs", "🔬"),
    Company("Anduril", "https://www.anduril.com/open-roles", "🛡️"),
]

COMPANY_EMOJI = {c.name: c.logo_emoji for c in COMPANIES}

SENIORITY_KEYWORDS = [
    "lead", "staff", "senior staff", "director", "senior director",
    "principal", "group", "head of", "vp",
]

ROLE_KEYWORDS = [
    "product manager", "product management", "product lead",
    "product director", "product policy",
]

PRIORITY_KEYWORDS = [
    "trust", "safety", "trust and safety", "trust & safety",
    "integrity", "abuse", "fraud", "risk", "compliance",
    "policy", "content moderation", "safeguard", "wellbeing",
    "dispute", "scam", "model behavior",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class JobPosting:
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    seniority: str = ""
    is_trust_safety: bool = False
    relevance_score: float = 0.0
    source: str = ""
    date_found: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def compute_relevance(job: JobPosting) -> float:
    """Score 0–100 based on how well this job matches criteria."""
    score = 0.0
    title_lower = job.title.lower()
    desc_lower = (job.description or "").lower()
    combined = f"{title_lower} {desc_lower}"

    is_pm = any(kw in combined for kw in ROLE_KEYWORDS)
    if not is_pm:
        return 0.0

    score += 30  # base PM score

    for kw in SENIORITY_KEYWORDS:
        if kw in title_lower:
            score += 25
            job.seniority = kw.title()
            break

    for kw in PRIORITY_KEYWORDS:
        if kw in combined:
            score += 30
            job.is_trust_safety = True
            break

    loc_lower = (job.location or "").lower()
    us_signals = [
        "united states", "us", "usa", "remote",
        "san francisco", "new york", "seattle", "los angeles",
        "austin", "chicago", "denver", "boston", "atlanta",
        "washington", "portland", "miami", "nashville", "sf",
    ]
    if any(s in loc_lower for s in us_signals) or not job.location:
        score += 15

    return min(score, 100.0)


# ---------------------------------------------------------------------------
# Curated job snapshot (Jan 2026)
# ---------------------------------------------------------------------------

def _curated_jobs() -> list[JobPosting]:
    """Hand-verified PM postings from target companies as of Jan 2026."""
    raw = [
        # === TRUST & SAFETY / SAFETY-ADJACENT (highest priority) ===
        {
            "title": "Platform Product Manager, Trust & Safety",
            "company": "Airbnb",
            "location": "United States (Remote)",
            "url": "https://careers.airbnb.com/positions/",
            "description": "Platform product manager for Airbnb Trust and Safety team",
            "source": "careers page",
        },
        {
            "title": "Sr. Director, Product Policy - Trust & Safety",
            "company": "Pinterest",
            "location": "San Francisco, CA",
            "url": "https://www.pinterestcareers.com/en/jobs/",
            "description": "Senior Director leading product policy for trust and safety at Pinterest",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Safeguards",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://www.anthropic.com/jobs",
            "description": "Product manager for Anthropic safeguards team, safety and trust focus",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Model Behavior",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "url": "https://openai.com/careers/product-manager-model-behavior-san-francisco/",
            "description": "Product manager for model behavior, safety alignment and policy",
            "source": "careers page",
        },
        {
            "title": "Staff Product Manager, Wellbeing",
            "company": "Pinterest",
            "location": "Chicago, IL / San Francisco, CA",
            "url": "https://www.pinterestcareers.com/jobs/7350253/staff-product-manager-wellbeing/",
            "description": "Staff PM for wellbeing and safety on Pinterest",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Dispute Resolution & Scams",
            "company": "Block (Cash App)",
            "location": "Remote (US)",
            "url": "https://block.xyz/careers/jobs",
            "description": "Product manager for dispute resolution and scam prevention at Cash App, trust and safety",
            "source": "careers page",
        },
        {
            "title": "Senior Product Manager, Identity & Access",
            "company": "Coinbase",
            "location": "Remote (USA)",
            "url": "https://www.coinbase.com/careers/positions/6951278",
            "description": "Senior PM for identity and access management, fraud prevention and compliance",
            "source": "careers page",
        },
        # === SENIOR PM ROLES (Staff / Principal / Director / Lead / Group) ===
        {
            "title": "Lead Product Manager, Research",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://job-boards.greenhouse.io/anthropic/jobs/4684257008",
            "description": "Lead product manager for Anthropic research products",
            "source": "greenhouse",
        },
        {
            "title": "Product Manager, Claude Code",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://www.anthropic.com/jobs",
            "description": "Product manager for Claude Code developer tools",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Claude Code Growth",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://www.anthropic.com/jobs",
            "description": "Product manager for Claude Code growth and adoption",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Platform Experience (DevX)",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://www.anthropic.com/jobs",
            "description": "Product manager for platform developer experience at Anthropic",
            "source": "careers page",
        },
        {
            "title": "Product Manager, API",
            "company": "Anthropic",
            "location": "San Francisco, CA",
            "url": "https://www.anthropic.com/jobs",
            "description": "Product manager for Anthropic API platform",
            "source": "careers page",
        },
        {
            "title": "Principal Product Manager, Ads Manager (Monetization)",
            "company": "Reddit",
            "location": "Remote (US)",
            "url": "https://job-boards.greenhouse.io/reddit/jobs/6762983",
            "description": "Principal product manager for Reddit ads monetization platform",
            "source": "greenhouse",
        },
        {
            "title": "Staff Product Manager, Reddit Answers",
            "company": "Reddit",
            "location": "Remote (US)",
            "url": "https://job-boards.greenhouse.io/reddit/jobs/6721235",
            "description": "Staff product manager for Reddit Answers AI product",
            "source": "greenhouse",
        },
        {
            "title": "Principal Product Manager, Emerging Markets",
            "company": "Reddit",
            "location": "Remote (US)",
            "url": "https://boards.greenhouse.io/reddit/jobs/4865277",
            "description": "Principal product manager for emerging markets expansion at Reddit",
            "source": "greenhouse",
        },
        {
            "title": "Staff Product Manager, Reddit Profiles",
            "company": "Reddit",
            "location": "Remote (US)",
            "url": "https://www.redditinc.com/careers",
            "description": "Staff product manager for Reddit user profiles",
            "source": "careers page",
        },
        {
            "title": "Staff Product Manager, Personalized Experiences",
            "company": "Pinterest",
            "location": "San Francisco, CA",
            "url": "https://www.pinterestcareers.com/jobs/7438083/staff-product-manager-personalized-experiences/",
            "description": "Staff product manager for personalized feed and experiences at Pinterest",
            "source": "careers page",
        },
        {
            "title": "Staff Product Manager, Trends & Insights",
            "company": "Pinterest",
            "location": "San Francisco, CA",
            "url": "https://www.pinterestcareers.com/jobs/7169624/staff-product-manager-trends-insights/",
            "description": "Staff product manager for trends and insights product at Pinterest",
            "source": "careers page",
        },
        {
            "title": "Staff Product Manager, AI/ML Personalization",
            "company": "Pinterest",
            "location": "San Francisco, CA",
            "url": "https://www.pinterestcareers.com/jobs/6576120/staff-product-manager-aiml-personalization/",
            "description": "Staff product manager for AI and ML personalization at Pinterest",
            "source": "careers page",
        },
        {
            "title": "Corporate Strategy Lead - Product",
            "company": "Pinterest",
            "location": "New York, NY / San Francisco, CA",
            "url": "https://www.pinterestcareers.com/jobs/7225068/corporate-strategy-lead-product/",
            "description": "Lead for corporate product strategy at Pinterest",
            "source": "careers page",
        },
        {
            "title": "Group Product Manager, Support Automation",
            "company": "Coinbase",
            "location": "Remote (USA)",
            "url": "https://www.coinbase.com/careers/positions/6730364",
            "description": "Group product manager for customer support automation at Coinbase",
            "source": "careers page",
        },
        {
            "title": "Senior Product Manager, Consumer Trading (Advanced)",
            "company": "Coinbase",
            "location": "Remote (USA)",
            "url": "https://www.coinbase.com/careers/positions/6563927",
            "description": "Senior product manager for advanced consumer trading at Coinbase",
            "source": "careers page",
        },
        {
            "title": "Senior Product Manager, Growth Incentives",
            "company": "Coinbase",
            "location": "Remote (USA)",
            "url": "https://www.coinbase.com/careers/positions/7371119",
            "description": "Senior product manager for growth and incentives programs at Coinbase",
            "source": "careers page",
        },
        {
            "title": "Product Manager II, Core Infrastructure",
            "company": "Coinbase",
            "location": "Remote (USA)",
            "url": "https://www.coinbase.com/careers/positions/5957003",
            "description": "Product manager for core infrastructure at Coinbase",
            "source": "careers page",
        },
        {
            "title": "Product Lead, Account & Access",
            "company": "Block (Cash App)",
            "location": "Remote (US)",
            "url": "https://block.xyz/careers/jobs",
            "description": "Product lead for account and access at Cash App / Block",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Customer Journeys",
            "company": "Block (Cash App)",
            "location": "Remote (US)",
            "url": "https://block.xyz/careers/jobs",
            "description": "Product manager for customer journeys at Cash App",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Banking Core",
            "company": "Block (Cash App)",
            "location": "Remote (US)",
            "url": "https://block.xyz/careers/jobs",
            "description": "Product manager for banking core product at Cash App",
            "source": "careers page",
        },
        {
            "title": "Principal Product Manager (Follow Up Boss)",
            "company": "Zillow",
            "location": "Remote (US)",
            "url": "https://www.zillow.com/careers/",
            "description": "Principal product manager for Follow Up Boss CRM product at Zillow, $170K-$272K",
            "source": "careers page",
        },
        {
            "title": "Product Manager, New Guest Experience",
            "company": "Airbnb",
            "location": "United States (Pacific TZ)",
            "url": "https://careers.airbnb.com/positions/7441029/",
            "description": "Product manager for new guest experience at Airbnb",
            "source": "careers page",
        },
        {
            "title": "Lead, Advanced Analytics, Trust & Safety",
            "company": "Airbnb",
            "location": "United States",
            "url": "https://careers.airbnb.com/positions/6881650/",
            "description": "Lead for advanced analytics within trust and safety at Airbnb",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Codex",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "url": "https://openai.com/careers/product-manager-codex-san-francisco/",
            "description": "Product manager for Codex coding assistant at OpenAI",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Enterprise Identity",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "url": "https://openai.com/careers/product-manager-enterprise-identity-san-francisco/",
            "description": "Product manager for enterprise identity and access at OpenAI",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Countries & Governments",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "url": "https://openai.com/careers/product-manager-countries-and-governments-san-francisco/",
            "description": "Product manager for government and country-level products at OpenAI",
            "source": "careers page",
        },
        {
            "title": "Product Manager, ChatGPT for Work",
            "company": "OpenAI",
            "location": "San Francisco, CA",
            "url": "https://openai.com/careers/product-manager-chatgpt-for-work-san-francisco/",
            "description": "Product manager for ChatGPT enterprise and workplace product at OpenAI",
            "source": "careers page",
        },
        {
            "title": "Staff Product Manager, Health Risk Detection",
            "company": "Oura",
            "location": "San Francisco / San Diego / Los Angeles / Remote (US)",
            "url": "https://ouraring.com/careers",
            "description": "Staff product manager for health risk detection features at Oura",
            "source": "careers page",
        },
        # === BONUS: Other notable T&S PM roles at top tech companies ===
        {
            "title": "Senior Product Manager, Trust & Safety, Integrity & Fraud",
            "company": "DoorDash",
            "location": "United States",
            "url": "https://careersatdoordash.com/jobs/senior-product-manager-trust-safety-integrity-and-fraud/7071290/",
            "description": "Senior PM for trust and safety integrity and fraud prevention at DoorDash",
            "source": "careers page",
        },
        {
            "title": "Trust & Safety User Reporting Product Manager",
            "company": "Apple",
            "location": "United States",
            "url": "https://jobs.apple.com/en-us/details/200613587/trust-safety-user-reporting-product-manager",
            "description": "Product manager for trust and safety user reporting at Apple",
            "source": "careers page",
        },
        {
            "title": "Product Manager, Trust & Safety (USDS)",
            "company": "TikTok",
            "location": "United States",
            "url": "https://careers.tiktok.com/",
            "description": "Product manager for trust and safety on TikTok USDS",
            "source": "careers page",
        },
    ]

    jobs = []
    for r in raw:
        posting = JobPosting(
            title=r["title"],
            company=r["company"],
            location=r.get("location", ""),
            url=r.get("url", ""),
            description=r.get("description", ""),
            source=r.get("source", "curated"),
        )
        posting.relevance_score = compute_relevance(posting)
        if posting.relevance_score > 0:
            jobs.append(posting)
    return jobs


# ---------------------------------------------------------------------------
# Live API fetchers (requires `requests`)
# ---------------------------------------------------------------------------

GREENHOUSE_BOARDS = {
    "Airbnb": "airbnb",
    "Coinbase": "coinbase",
    "Pinterest": "pinterestcareers",
    "Reddit": "reddit",
    "Anduril": "andurilindustries",
    "OpenAI": "openai",
    "Block (Cash App)": "squareup",
    "Zillow": "zillowgroup",
}

LEVER_BOARDS = {"Oura": "ouraring"}
ASHBY_BOARDS = {"Anthropic": "anthropic"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _safe_get(url: str, timeout: int = 15):
    """GET with retries. Returns response or None."""
    import requests
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            return resp
        except requests.RequestException:
            time.sleep(1)
    return None


def _fetch_greenhouse(board_token: str, company_name: str) -> list[JobPosting]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    resp = _safe_get(url)
    if not resp or resp.status_code != 200:
        return []
    jobs = []
    for item in resp.json().get("jobs", []):
        posting = JobPosting(
            title=item.get("title", ""),
            company=company_name,
            location=item.get("location", {}).get("name", ""),
            url=item.get("absolute_url", ""),
            source="greenhouse",
        )
        posting.relevance_score = compute_relevance(posting)
        if posting.relevance_score > 0:
            jobs.append(posting)
    return jobs


def _fetch_lever(slug: str, company_name: str) -> list[JobPosting]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    resp = _safe_get(url)
    if not resp or resp.status_code != 200:
        return []
    jobs = []
    for item in resp.json():
        posting = JobPosting(
            title=item.get("text", ""),
            company=company_name,
            location=item.get("categories", {}).get("location", ""),
            url=item.get("hostedUrl", ""),
            description=(item.get("descriptionPlain", "") or "")[:500],
            source="lever",
        )
        posting.relevance_score = compute_relevance(posting)
        if posting.relevance_score > 0:
            jobs.append(posting)
    return jobs


def _fetch_ashby(slug: str, company_name: str) -> list[JobPosting]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    resp = _safe_get(url)
    if not resp or resp.status_code != 200:
        return []
    jobs = []
    for item in resp.json().get("jobs", []):
        posting = JobPosting(
            title=item.get("title", ""),
            company=company_name,
            location=item.get("location", ""),
            url=item.get("jobUrl", "") or item.get("applicationUrl", ""),
            source="ashby",
        )
        posting.relevance_score = compute_relevance(posting)
        if posting.relevance_score > 0:
            jobs.append(posting)
    return jobs


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class JobSearchAgent:
    def __init__(self, use_cache: bool = False):
        self.use_cache = use_cache
        self.all_jobs: list[JobPosting] = []
        self.seen_keys: set[str] = set()
        self.log_lines: list[str] = []

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}"
        self.log_lines.append(line)
        print(line)

    def _add(self, jobs: list[JobPosting]):
        for j in jobs:
            key = j.url or f"{j.company}|{j.title}"
            if key not in self.seen_keys:
                self.seen_keys.add(key)
                self.all_jobs.append(j)

    # -- live search --
    def _live_search(self):
        try:
            import requests  # noqa: F401
        except ImportError:
            self.log("ERROR: 'requests' not installed. Run: pip install requests")
            self.log("Falling back to cached results.")
            self._cached_search()
            return

        for name, token in GREENHOUSE_BOARDS.items():
            self.log(f"Searching {name} (Greenhouse)...")
            try:
                jobs = _fetch_greenhouse(token, name)
                self.log(f"  -> {len(jobs)} PM-related postings")
                self._add(jobs)
            except Exception as e:
                self.log(f"  -> ERROR: {e}")
            time.sleep(0.3)

        for name, slug in LEVER_BOARDS.items():
            self.log(f"Searching {name} (Lever)...")
            try:
                jobs = _fetch_lever(slug, name)
                self.log(f"  -> {len(jobs)} PM-related postings")
                self._add(jobs)
            except Exception as e:
                self.log(f"  -> ERROR: {e}")
            time.sleep(0.3)

        for name, slug in ASHBY_BOARDS.items():
            self.log(f"Searching {name} (Ashby)...")
            try:
                jobs = _fetch_ashby(slug, name)
                self.log(f"  -> {len(jobs)} PM-related postings")
                self._add(jobs)
            except Exception as e:
                self.log(f"  -> ERROR: {e}")
            time.sleep(0.3)

        if not self.all_jobs:
            self.log("No live results returned. Loading curated snapshot as fallback...")
            self._cached_search()

    # -- cached search --
    def _cached_search(self):
        self.log("Loading curated job snapshot (Jan 2026)...")
        jobs = _curated_jobs()
        self.log(f"  -> {len(jobs)} verified postings loaded")
        self._add(jobs)

    def run(self) -> list[JobPosting]:
        print("""
╔══════════════════════════════════════════════════════════════════╗
║                   PM Job Search Agent v1.0                      ║
║                                                                 ║
║   Targets:  Lead / Staff / Director / Principal PM roles        ║
║   Focus:    Trust & Safety                                      ║
║   Scope:    US-based positions at top tech companies            ║
╚══════════════════════════════════════════════════════════════════╝
""")
        companies_str = ", ".join(c.name for c in COMPANIES)
        self.log(f"Target companies: {companies_str}")
        self.log(f"Seniority filters: {', '.join(SENIORITY_KEYWORDS)}")
        self.log(f"Priority domain: Trust & Safety")
        self.log(f"Mode: {'CACHED' if self.use_cache else 'LIVE (with cache fallback)'}\n")

        if self.use_cache:
            self._cached_search()
        else:
            self._live_search()

        self.all_jobs.sort(key=lambda j: j.relevance_score, reverse=True)

        ts_count = sum(1 for j in self.all_jobs if j.is_trust_safety)
        sr_count = sum(1 for j in self.all_jobs if j.seniority)
        self.log(f"\n{'=' * 60}")
        self.log(f"Search complete! {len(self.all_jobs)} relevant PM postings found.")
        self.log(f"  Trust & Safety roles: {ts_count}")
        self.log(f"  Senior-level roles:   {sr_count}")
        return self.all_jobs

    def to_json(self) -> str:
        return json.dumps({
            "search_date": datetime.now().isoformat(),
            "total_results": len(self.all_jobs),
            "jobs": [j.to_dict() for j in self.all_jobs],
            "search_log": self.log_lines,
        }, indent=2)


# ---------------------------------------------------------------------------
# HTML report
# ---------------------------------------------------------------------------

def generate_html_report(jobs: list[JobPosting], search_log: list[str]) -> str:
    ts_jobs = [j for j in jobs if j.is_trust_safety]
    sr_jobs = [j for j in jobs if j.seniority]
    top_jobs = [j for j in jobs if j.relevance_score >= 70]
    companies_found = sorted(set(j.company for j in jobs))

    def _card(j: JobPosting) -> str:
        emoji = COMPANY_EMOJI.get(j.company, "🏢")
        badge_cls = "badge-ts" if j.is_trust_safety else "badge-pm"
        badge_txt = "Trust &amp; Safety" if j.is_trust_safety else "Product"
        lvl = f'<span class="badge badge-level">{j.seniority}</span>' if j.seniority else ""
        score_cls = "score-high" if j.relevance_score >= 70 else "score-med" if j.relevance_score >= 45 else "score-low"
        loc = j.location or "See posting"
        href = f'href="{j.url}" target="_blank"' if j.url else 'href="#"'
        return f'''<a {href} class="job-card" data-company="{j.company}" data-ts="{str(j.is_trust_safety).lower()}" data-senior="{str(bool(j.seniority)).lower()}">
  <div class="job-card-header">
    <span class="company-emoji">{emoji}</span>
    <span class="company-name">{j.company}</span>
    <span class="badge {badge_cls}">{badge_txt}</span>{lvl}
    <span class="score {score_cls}">{int(j.relevance_score)}%</span>
  </div>
  <h3 class="job-title">{j.title}</h3>
  <div class="job-meta"><span>📍 {loc}</span><span>via {j.source}</span></div>
</a>'''

    cards = "\n".join(_card(j) for j in jobs) if jobs else '<div class="no-results">No results found. Visit career pages directly.</div>'
    co_btns = "\n".join(
        f'<button class="filter-btn" data-filter-company="{c}" onclick="filterCompany(this)">{COMPANY_EMOJI.get(c,"🏢")} {c}</button>'
        for c in companies_found
    )
    career_links = "\n".join(
        f'<a href="{c.careers_url}" target="_blank" class="career-link">{c.logo_emoji} {c.name}</a>'
        for c in COMPANIES
    )
    logs = "\n".join(f"<div class='log-line'>{l}</div>" for l in search_log)
    now = datetime.now().strftime("%B %d, %Y at %I:%M %p")

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>PM Job Search Dashboard</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f0f13;color:#e0e0e0;min-height:100vh}}
.hero{{background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);padding:3rem 2rem;text-align:center;border-bottom:1px solid rgba(255,255,255,.05)}}
.hero h1{{font-size:2.4rem;font-weight:700;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:.5rem}}
.hero p{{color:#8892b0;font-size:1.1rem;max-width:600px;margin:0 auto}}
.hero .date{{margin-top:1rem;color:#5a6380;font-size:.85rem}}
.stats{{display:flex;justify-content:center;gap:2rem;padding:1.5rem;background:#13131a;border-bottom:1px solid rgba(255,255,255,.05);flex-wrap:wrap}}
.stat-n{{font-size:2rem;font-weight:700;color:#667eea}}.stat-l{{font-size:.8rem;color:#5a6380;text-transform:uppercase;letter-spacing:1px}}
.container{{max-width:1200px;margin:0 auto;padding:2rem}}
.section-title{{font-size:1.3rem;font-weight:600;margin:2rem 0 1rem;color:#c5c5d5}}
.filters{{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1.5rem}}
.filter-btn{{padding:.5rem 1rem;border:1px solid rgba(102,126,234,.3);border-radius:20px;background:transparent;color:#8892b0;cursor:pointer;font-size:.85rem;transition:all .2s}}
.filter-btn:hover,.filter-btn.active{{background:rgba(102,126,234,.15);border-color:#667eea;color:#667eea}}
.jobs-grid{{display:grid;gap:.75rem}}
.job-card{{display:block;background:#1a1a24;border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:1.25rem 1.5rem;transition:all .2s;cursor:pointer;text-decoration:none;color:inherit}}
.job-card:hover{{border-color:rgba(102,126,234,.4);transform:translateY(-1px);box-shadow:0 4px 20px rgba(0,0,0,.3)}}
.job-card.hidden{{display:none}}
.job-card-header{{display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;flex-wrap:wrap}}
.company-emoji{{font-size:1.2rem}}.company-name{{font-weight:600;color:#8892b0;font-size:.9rem}}
.badge{{padding:.15rem .6rem;border-radius:12px;font-size:.7rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px}}
.badge-ts{{background:rgba(255,107,107,.15);color:#ff6b6b;border:1px solid rgba(255,107,107,.3)}}
.badge-pm{{background:rgba(102,126,234,.15);color:#667eea;border:1px solid rgba(102,126,234,.3)}}
.badge-level{{background:rgba(81,207,102,.15);color:#51cf66;border:1px solid rgba(81,207,102,.3)}}
.score{{margin-left:auto;font-weight:700;font-size:.85rem}}
.score-high{{color:#51cf66}}.score-med{{color:#ffd43b}}.score-low{{color:#868e96}}
.job-title{{font-size:1.1rem;font-weight:600;color:#e0e0e0;margin-bottom:.4rem}}
.job-meta{{display:flex;gap:1rem;font-size:.8rem;color:#5a6380}}
.career-links{{display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:2rem}}
.career-link{{padding:.5rem 1rem;background:rgba(102,126,234,.1);border:1px solid rgba(102,126,234,.2);border-radius:8px;color:#667eea;text-decoration:none;font-size:.85rem;transition:all .2s}}
.career-link:hover{{background:rgba(102,126,234,.2);border-color:#667eea}}
.log-container{{background:#12121a;border:1px solid rgba(255,255,255,.06);border-radius:12px;padding:1.5rem;max-height:300px;overflow-y:auto;margin-top:1rem}}
.log-line{{font-family:'SF Mono','Fira Code',monospace;font-size:.8rem;color:#5a6380;padding:.2rem 0}}
details{{margin-top:2rem}}summary{{cursor:pointer;color:#8892b0;font-size:.9rem;padding:.5rem 0}}
.no-results{{text-align:center;padding:3rem;color:#5a6380}}
.tip{{margin-top:2rem;padding:1.5rem;background:rgba(102,126,234,.08);border:1px solid rgba(102,126,234,.2);border-radius:12px}}
.tip h3{{color:#667eea;margin-bottom:.5rem;font-size:1rem}}.tip p,.tip li{{color:#8892b0;font-size:.9rem;line-height:1.6}}
.tip ul{{margin-left:1.5rem;margin-top:.5rem}}
@media(max-width:768px){{.hero h1{{font-size:1.6rem}}.stats{{gap:1rem}}.container{{padding:1rem}}}}
</style></head><body>
<div class="hero">
  <h1>PM Job Search Dashboard</h1>
  <p>Lead / Staff / Director / Principal Product Management roles at top tech companies</p>
  <p class="date">Last searched: {now}</p>
</div>
<div class="stats">
  <div><div class="stat-n">{len(jobs)}</div><div class="stat-l">Total Matches</div></div>
  <div><div class="stat-n">{len(ts_jobs)}</div><div class="stat-l">Trust &amp; Safety</div></div>
  <div><div class="stat-n">{len(sr_jobs)}</div><div class="stat-l">Senior Level</div></div>
  <div><div class="stat-n">{len(top_jobs)}</div><div class="stat-l">Top Matches (70%+)</div></div>
  <div><div class="stat-n">{len(companies_found)}</div><div class="stat-l">Companies</div></div>
</div>
<div class="container">
  <h2 class="section-title">🔗 Career Pages (Direct Links)</h2>
  <div class="career-links">{career_links}</div>

  <h2 class="section-title">🔍 Filter Results</h2>
  <div class="filters">
    <button class="filter-btn active" onclick="showAll(this)">All ({len(jobs)})</button>
    <button class="filter-btn" onclick="filterTS(this)">🛡️ Trust &amp; Safety ({len(ts_jobs)})</button>
    <button class="filter-btn" onclick="filterSr(this)">⭐ Senior Level ({len(sr_jobs)})</button>
    {co_btns}
  </div>

  <div class="jobs-grid" id="grid">{cards}</div>

  <div class="tip">
    <h3>💡 Search Tips</h3>
    <ul>
      <li><strong>Re-run live:</strong> <code>python3 pm_job_search_agent.py</code> to fetch latest from company APIs</li>
      <li><strong>Set alerts:</strong> Create LinkedIn alerts for "Trust and Safety Product Manager" and "Staff Product Manager" at target companies</li>
      <li><strong>Greenhouse boards:</strong> Many companies use Greenhouse — check <code>boards.greenhouse.io/[company]</code> directly</li>
      <li><strong>Extend:</strong> Add new companies by editing the COMPANIES list and GREENHOUSE_BOARDS / LEVER_BOARDS / ASHBY_BOARDS dicts in <code>pm_job_search_agent.py</code></li>
    </ul>
  </div>

  <details>
    <summary>📋 Search Log ({len(search_log)} entries)</summary>
    <div class="log-container">{logs}</div>
  </details>
</div>
<script>
function cl(){{document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'))}}
function showAll(b){{cl();b.classList.add('active');document.querySelectorAll('.job-card').forEach(c=>c.classList.remove('hidden'))}}
function filterTS(b){{cl();b.classList.add('active');document.querySelectorAll('.job-card').forEach(c=>{{c.classList.toggle('hidden',c.dataset.ts!=='true')}})}}
function filterSr(b){{cl();b.classList.add('active');document.querySelectorAll('.job-card').forEach(c=>{{c.classList.toggle('hidden',c.dataset.senior!=='true')}})}}
function filterCompany(b){{cl();b.classList.add('active');const co=b.dataset.filterCompany;document.querySelectorAll('.job-card').forEach(c=>{{c.classList.toggle('hidden',c.dataset.company!==co)}})}}
</script></body></html>'''


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PM Job Search Agent")
    parser.add_argument("--output", "-o", default="pm_jobs_results.json", help="JSON output path")
    parser.add_argument("--html", default="pm_jobs_dashboard.html", help="HTML report path")
    parser.add_argument("--cached", action="store_true", help="Use curated snapshot instead of live API calls")
    args = parser.parse_args()

    agent = JobSearchAgent(use_cache=args.cached)
    jobs = agent.run()

    with open(args.output, "w") as f:
        f.write(agent.to_json())
    print(f"\n✅ JSON saved to {args.output}")

    html = generate_html_report(jobs, agent.log_lines)
    with open(args.html, "w") as f:
        f.write(html)
    print(f"✅ Dashboard saved to {args.html}")

    print(f"\n{'=' * 64}")
    print(" TOP MATCHES")
    print(f"{'=' * 64}")
    for j in jobs[:25]:
        ts = " [T&S]" if j.is_trust_safety else ""
        lvl = f" [{j.seniority}]" if j.seniority else ""
        print(f"  {int(j.relevance_score):3d}% | {j.company:22s} | {j.title}{lvl}{ts}")
        if j.url:
            print(f"       └─ {j.url}")
    print()


if __name__ == "__main__":
    main()
