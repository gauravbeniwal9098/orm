"""
Live scraper for Indeed, Glassdoor, Comparably, G2, Capterra, Software Advice.
Replaces the hardcoded PLATFORM_DATA numbers with values read from each page
(JSON-LD aggregateRating). UNTESTED against the live sites: run it once and
check the debug_html/ folder if any site returns 0.

Usage inside your main script:
    from sites_scraper import scrape_all_sites
    live_reviews, live_stats = scrape_all_sites()
    for name, st in live_stats.items():
        if st["total"] is not None:
            PLATFORM_DATA[name].update(rating=st["rating"], total_reviews=st["total"])
"""
import json
import os
import re

import requests
from bs4 import BeautifulSoup

ZENROWS_API_KEY = os.environ["ZENROWS_API_KEY"]  # no default: keep the key out of code
ZENROWS_ENDPOINT = "https://api.zenrows.com/v1/"
DEBUG_DIR = "debug_html"

# Fill in / confirm the exact URLs for Capterra and Software Advice (they contain product IDs).
SITES = {
    "Glassdoor": "https://www.glassdoor.com/Reviews/Altametrics-Reviews-E269429.htm?sort.sortType=RD&sort.ascending=false",
    "Indeed": "https://www.indeed.com/cmp/Altametrics/reviews?sort=date",
    "Comparably": "https://www.comparably.com/companies/altametrics/reviews",
    "G2": "https://www.g2.com/products/altametrics/reviews?order=most_recent",
    "Capterra": "https://www.capterra.com/p/XXXXX/Altametrics/reviews/",
    "Software Advice": "https://www.softwareadvice.com/p/XXXXX/altametrics/reviews/",
}


def fetch(name, url):
    params = {
        "url": url,
        "apikey": ZENROWS_API_KEY,
        "js_render": "true",
        "premium_proxy": "true",  # G2/Capterra/Glassdoor/Indeed block datacenter IPs
        "wait": "4000",
    }
    r = requests.get(ZENROWS_ENDPOINT, params=params, timeout=120)
    os.makedirs(DEBUG_DIR, exist_ok=True)
    with open(f"{DEBUG_DIR}/{name}.html", "w", encoding="utf-8") as f:
        f.write(f"<!-- status {r.status_code} -->\n{r.text}")
    if r.status_code != 200:
        raise RuntimeError(f"{name}: HTTP {r.status_code} {r.text[:200]}")
    return r.text


def _walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v)


def parse_ld(html):
    """Return (rating, total, reviews) from JSON-LD blocks."""
    soup = BeautifulSoup(html, "html.parser")
    rating = total = None
    reviews = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or tag.get_text() or "{}")
        except Exception:
            continue
        for node in _walk(data):
            agg = node.get("aggregateRating")
            if isinstance(agg, dict) and rating is None:
                try:
                    rating = float(agg.get("ratingValue"))
                    total = int(float(agg.get("reviewCount") or agg.get("ratingCount")))
                except Exception:
                    pass
            if node.get("@type") == "Review":
                rr = node.get("reviewRating") or {}
                author = node.get("author")
                reviews.append({
                    "Author": (author.get("name") if isinstance(author, dict) else author) or "Verified User",
                    "Title": node.get("name") or node.get("headline") or "",
                    "Rating": int(float(rr.get("ratingValue", 0))) if isinstance(rr, dict) and rr.get("ratingValue") else 0,
                    "Date": (node.get("datePublished") or "")[:10],
                    "Review_Text": node.get("reviewBody") or node.get("description") or "",
                })
    return rating, total, [r for r in reviews if r["Date"]]


def scrape_all_sites():
    all_reviews, stats = [], {}
    for name, url in SITES.items():
        if "XXXXX" in url:
            print(f"[SKIP] {name}: set the real URL in SITES first")
            stats[name] = {"rating": None, "total": None}
            continue
        try:
            html = fetch(name, url)
            rating, total, revs = parse_ld(html)
            for r in revs:
                r["Platform"] = name
            all_reviews.extend(revs)
            stats[name] = {"rating": rating, "total": total}
            print(f"[OK] {name}: rating={rating} total={total} reviews_parsed={len(revs)}")
            if rating is None:
                print(f"     -> no aggregateRating found, open {DEBUG_DIR}/{name}.html (likely a block/captcha page)")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            stats[name] = {"rating": None, "total": None}
    return all_reviews, stats


if __name__ == "__main__":
    revs, st = scrape_all_sites()
    print(json.dumps(st, indent=2))
    print(f"{len(revs)} reviews total")
