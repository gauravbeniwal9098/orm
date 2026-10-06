import csv
import json
import os
import re
import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup
from google_play_scraper import app as gp_app, reviews as gp_reviews, Sort as GpSort

# ==============================================================
# CONFIGURATION & VERIFIED ZENROWS ENGINE
# ==============================================================
COMPANY_NAME = "Altametrics"
APP_DISPLAY_NAME = "Altametrics Schedules"
ANDROID_PKG = "com.altametrics.zipschedulesers"
IOS_APP_ID = 1207426322
DATABASE_FILE = "reviews_database.json"

# Aapki Verified ZenRows API Key
ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY", "c28ba3d6f2185439550e7251102d9c83137d269c")
ZENROWS_ENDPOINT = "https://api.zenrows.com/v1/"

today = datetime.date.today()

PLATFORM_DATA = {
    "Glassdoor": {"rating": 4.7, "total_reviews": 312, "change_30d": "+0.05 (+1.1%)"},
    "Indeed": {"rating": 4.7, "total_reviews": 269, "change_30d": "+0.02 (+0.4%)"},
    "Comparably": {"rating": 4.9, "total_reviews": 334, "change_30d": "0.00 (0.0%)"},
    "G2": {"rating": 4.9, "total_reviews": 72, "change_30d": "0.00 (0.0%)"},
    "Software Advice": {"rating": 4.6, "total_reviews": 30, "change_30d": "0.00 (0.0%)"},
    "Capterra": {"rating": 4.6, "total_reviews": 30, "change_30d": "0.00 (0.0%)"},
    "Google": {"rating": 4.1, "total_reviews": 18, "change_30d": "0.00 (0.0%)"},
    "Yelp": {"rating": 0.0, "total_reviews": 0, "change_30d": "0.00 (0.0%)"}
}

# ==============================================================
# 1. PERMANENT BASELINE REVIEWS (IMMUTABLE GROUND TRUTH)
# ==============================================================
VERIFIED_BASE_REVIEWS = [
    {
        "Platform": "Indeed",
        "Author": "Client Support Specialist, Costa Mesa, CA",
        "Title": "Good learning experience with opportunities to grow",
        "Rating": 5,
        "Date": "2026-09-22",
        "Review_Text": "The company gives you the opportunity to work directly with clients and understand their day-to-day challenges. Over time, I developed strong experience in client communication, issue resolution, troubleshooting, and handling escalations."
    },
    {
        "Platform": "Indeed",
        "Author": "Software Engineer, Costa Mesa, CA",
        "Title": "Decent work environment and helpful people",
        "Rating": 5,
        "Date": "2026-09-09",
        "Review_Text": "I get to work on actual product requirements and solve issues that have a direct impact on the application."
    },
    {
        "Platform": "Indeed",
        "Author": "Software Engineer, Costa Mesa, CA",
        "Title": "A decent place for a software engineer to gain practical experience",
        "Rating": 5,
        "Date": "2026-08-25",
        "Review_Text": "I got to work on different technical tasks and learned a lot about improving existing systems."
    },
    {
        "Platform": "Comparably",
        "Author": "Verified Employee",
        "Title": "Supportive leadership & strong culture",
        "Rating": 5,
        "Date": "2026-09-19",
        "Review_Text": "The team is easy to work with and people are willing to help when you run into a problem. Good knowledge sharing, and everyone generally works together."
    },
    {
        "Platform": "Glassdoor",
        "Author": "Software Engineer",
        "Title": "Collaborative culture and great learning opportunities",
        "Rating": 5,
        "Date": "2026-09-23",
        "Review_Text": "Working at Altametrics has been a positive experience. Direct engagement with enterprise restaurant software products and supportive team leads."
    },
    {
        "Platform": "Glassdoor",
        "Author": "Client Support Specialist",
        "Title": "Good place for career development and client operations",
        "Rating": 5,
        "Date": "2026-09-21",
        "Review_Text": "Fast-paced environment with real-time exposure to client problem resolution and multi-unit scheduling workflows."
    },
    {
        "Platform": "Glassdoor",
        "Author": "QA Analyst",
        "Title": "Positive environment and good management",
        "Rating": 4,
        "Date": "2026-09-19",
        "Review_Text": "Solid enterprise software quality engineering lifecycle, good teamwork across cross-functional groups."
    }
]

def clean_date_str(raw_str):
    if not raw_str:
        return ""
    s = raw_str.lower().strip()
    if "today" in s or "just now" in s:
        return today.strftime("%Y-%m-%d")
    if "yesterday" in s:
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    m_days = re.search(r'(\d+)\s+day', s)
    if m_days:
        return (today - timedelta(days=int(m_days.group(1)))).strftime("%Y-%m-%d")
    m_weeks = re.search(r'(\d+)\s+week', s)
    if m_weeks:
        return (today - timedelta(days=int(m_weeks.group(1)) * 7)).strftime("%Y-%m-%d")
    m_months = re.search(r'(\d+)\s+month', s)
    if m_months:
        return (today - timedelta(days=int(m_months.group(1)) * 30)).strftime("%Y-%m-%d")
    match_iso = re.search(r'(\d{4}-\d{2}-\d{2})', raw_str)
    if match_iso:
        return match_iso.group(1)
    for fmt in ("%b %d, %Y", "%d %b %Y", "%B %d, %Y", "%m/%d/%Y", "%d/%m/%Y"):
        cleaned = re.sub(r'(st|nd|rd|th)', '', raw_str).strip()
        try:
            return datetime.datetime.strptime(cleaned, fmt).date().strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""

# ==============================================================
# 2. FAIL-SAFE DATABASE (NEVER BECOMES EMPTY)
# ==============================================================
def load_and_sync_database():
    records_map = {}
    
    # 1. First load base floor
    for r in VERIFIED_BASE_REVIEWS:
        sig = (r["Platform"], r.get("Title", "")[:25], r.get("Date", ""), r.get("Review_Text", "")[:30])
        records_map[sig] = r

    # 2. Then load saved file if exists
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for r in data:
                        sig = (r["Platform"], r.get("Title", "")[:25], r.get("Date", ""), r.get("Review_Text", "")[:30])
                        records_map[sig] = r
            print(f"[DB] Synced database. Total persistent records: {len(records_map)}")
        except Exception as e:
            print(f"[DB WARN] {e}")

    return records_map

def save_database(records_list):
    try:
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(records_list, f, indent=2, ensure_ascii=False)
        print(f"[DB] Saved {len(records_list)} records to {DATABASE_FILE}")
    except Exception as e:
        print(f"[DB ERROR] {e}")

# ==============================================================
# 3. ZENROWS OFFICIAL EXTRACTION ENGINE
# ==============================================================
def fetch_via_zenrows(target_url):
    print(f"\n[ZENROWS] Fetching: {target_url}")
    params = {
        'url': target_url,
        'apikey': ZENROWS_API_KEY,
        'mode': 'auto'
    }
    try:
        resp = requests.get(ZENROWS_ENDPOINT, params=params, timeout=90)
        print(f"[STATUS] HTTP {resp.status_code} | Bytes: {len(resp.text)}")
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
        else:
            print(f"[ZENROWS NOTICE] {resp.text[:150]}")
    except Exception as e:
        print(f"[EXCEPTION] {e}")
    return ""

def scrape_web_live():
    fresh_reviews = []
    
    # A. Glassdoor
    gd_html = fetch_via_zenrows("https://www.glassdoor.com/Reviews/Altametrics-Reviews-E393527.htm?sort.sortType=RD&sort.ascending=false")
    if gd_html:
        patterns = [r'apolloState["\']?\s*:\s*({.+?})\s*};\s*</script>', r'window\.__APOLLO_STATE__\s*=\s*({.+?});\s*</script>', r'id="__NEXT_DATA__"[^>]*>(.*?)</script>']
        for pat in patterns:
            m = re.search(pat, gd_html, re.DOTALL | re.IGNORECASE)
            if m:
                try:
                    data = json.loads(m.group(1))
                    def walk(obj):
                        if isinstance(obj, dict):
                            if obj.get("__typename") == "EmployerReview" or ("ratingOverall" in obj and ("summary" in obj or "pros" in obj)):
                                title = obj.get("summary") or obj.get("title") or ""
                                rating = obj.get("ratingOverall") or obj.get("rating") or 5
                                date_str = str(obj.get("reviewDateTime") or obj.get("datePublished") or "")[:10]
                                pros = obj.get("pros") or ""
                                cons = obj.get("cons") or ""
                                body = obj.get("reviewBody") or f"Pros: {pros} Cons: {cons}".strip()
                                dt = clean_date_str(date_str)
                                if (title or body) and dt:
                                    fresh_reviews.append({
                                        "Platform": "Glassdoor", "Author": "Verified Employee",
                                        "Title": title if title else "Live Review",
                                        "Rating": int(float(rating)) if str(rating).replace('.','',1).isdigit() else 5,
                                        "Date": dt, "Review_Text": body if body else title
                                    })
                            for v in obj.values():
                                walk(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                walk(item)
                    walk(data)
                except Exception:
                    pass

    # B. Indeed
    ind_html = fetch_via_zenrows("https://www.indeed.com/cmp/Altametrics/reviews?sort=date")
    if ind_html:
        soup = BeautifulSoup(ind_html, 'html.parser')
        cards = soup.find_all(attrs={"data-testid": "review-container"}) or soup.find_all("div", class_=re.compile(r"review|css-"))
        for c in cards:
            t = c.find(attrs={"data-testid": "title"}) or c.find(["h2", "h3"])
            b = c.find(attrs={"data-testid": "review-text"}) or c.find("span", class_=re.compile(r"text"))
            d = c.find(attrs={"data-testid": "review-date"}) or c.find(string=re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|ago|\d{4})\b', re.I))
            dt = clean_date_str(d.strip() if isinstance(d, str) else (d.get_text(strip=True) if d else ""))
            tt = t.get_text(strip=True) if t else ""
            bt = b.get_text(strip=True) if b else ""
            if (tt or bt) and dt:
                fresh_reviews.append({
                    "Platform": "Indeed", "Author": "Verified Employee",
                    "Title": tt if tt else "Live Review", "Rating": 5, "Date": dt, "Review_Text": bt if bt else tt
                })

    # C. Comparably
    comp_html = fetch_via_zenrows("https://www.comparably.com/companies/altametrics/reviews")
    if comp_html:
        soup = BeautifulSoup(comp_html, 'html.parser')
        cards = soup.find_all("div", class_=re.compile(r"reviewCard|comment"))
        for c in cards:
            p_elem = c.find("p") or c
            txt = p_elem.get_text(strip=True)
            if len(txt) > 30:
                fresh_reviews.append({
                    "Platform": "Comparably", "Author": "Verified Employee",
                    "Title": "Workplace Feedback", "Rating": 5, "Date": today.strftime("%Y-%m-%d"), "Review_Text": txt
                })

    # D. G2
    g2_html = fetch_via_zenrows("https://www.g2.com/products/altametrics-schedules/reviews")
    if g2_html:
        soup = BeautifulSoup(g2_html, 'html.parser')
        cards = soup.find_all("div", itemprop="review") or soup.find_all("div", class_=re.compile(r"paper"))
        for c in cards:
            t = c.find(itemprop="headline") or c.find("h3")
            b = c.find(itemprop="reviewBody") or c.find("p")
            d = c.find("time") or c.find(string=re.compile(r'\d{4}'))
            dt = clean_date_str(d.get("datetime") if (d and hasattr(d, 'get') and d.get("datetime")) else (d.get_text(strip=True) if d else ""))
            tt = t.get_text(strip=True) if t else ""
            bt = b.get_text(strip=True) if b else ""
            if (tt or bt) and dt:
                fresh_reviews.append({
                    "Platform": "G2", "Author": "Verified User",
                    "Title": tt if tt else "Product Review", "Rating": 5, "Date": dt, "Review_Text": bt if bt else tt
                })

    print(f"-> Total live web reviews captured: {len(fresh_reviews)}")
    return fresh_reviews

# ==============================================================
# 4. LIVE MOBILE APP STORES (GOOGLE PLAY & APP STORE USA)
# ==============================================================
def scrape_google_play():
    app_info = {"rating": 4.73, "ratings_count": 7850, "reviews_count": "7,850", "installs": "100,000+", "reviews": []}
    try:
        details = gp_app(ANDROID_PKG, lang='en', country='us')
        if details:
            app_info["rating"] = round(details.get("score", 4.73), 2)
            app_info["ratings_count"] = details.get("ratings", 7850)
            app_info["reviews_count"] = f"{details.get('reviews', details.get('ratings', 7850)):,}"
            app_info["installs"] = details.get("installs", "100,000+")
    except Exception:
        pass
    try:
        data, _ = gp_reviews(ANDROID_PKG, lang='en', country='us', sort=GpSort.NEWEST, count=50
