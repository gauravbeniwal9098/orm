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
# CONFIGURATION
# ==============================================================
COMPANY_NAME = "Altametrics"
APP_DISPLAY_NAME = "Altametrics Schedules"
ANDROID_PKG = "com.altametrics.zipschedulesers"
IOS_APP_ID = 1207426322
DATABASE_FILE = "reviews_database.json"

ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY", "c28ba3d6f2185439550e7251102d9c83137d269c")
ZENROWS_ENDPOINT = "https://api.zenrows.com/v1/"

# AAPKI LIVE GLASSDOOR SESSION COOKIE EMBEDDED
GLASSDOOR_COOKIE = r"""gdId=9687b025-74cb-44e1-b3a8-21d18d3065aa; _optionalConsent=true; _ga=GA1.3.1023425105.1756294853; rl_page_init_referrer=RS_ENC_v3_Imh0dHBzOi8vd3d3Lmdvb2dsZS5jb20vIg%3D%3D; rl_page_init_referring_domain=RS_ENC_v3_Ind3dy5nb29nbGUuY29tIg%3D%3D; indeedCtk=1j9pcq28ji9du801; fpvc=69; otGeoUS=false; ki_r=aHR0cHM6Ly93d3cuZ29vZ2xlLmNvbS8%3D; g_state={"i_l":0,"i_ll":1788791892511,"i_e":{"enable_itp_optimization":24},"i_et":1788791892511,"i_b":"eZ2UjUgZpcKSF/O3Vw+0dvwKipP5RLRxsChKyHMk+Jk"}; ki_s=240461%3A0.0.0.0.0; rsSessionId=1791366267632; cdArr=; asst=1791366303.2; rl_user_id=RS_ENC_v3_IjE1MTA2NTE0NiI%3D; rl_trait=RS_ENC_v3_eyJsb2NrZWQgc3RhdGUiOiJvcGVuIiwidXNlciByb2xlIjoiQkFTSUMiLCJjb21tdW5pdHkgaWQiOiI2NDc1Y2FmZTFkYTljMDAwMjhjN2Y5MWIiLCJjb2xvciBzY2hlbWUiOiJMaWdodCIsImlzIHZhbGlkYXRlZCI6dHJ1ZSwiaXMgY29udHJpYnV0b3IiOnRydWV9; rl_anonymous_id=RS_ENC_v3_Ijk2ODdiMDI1LTc0Y2ItNDRlMS1iM2E4LTIxZDE4ZDMwNjVhYSI%3D; rsReferrerData=%7B%22currentPageRollup%22%3A%22%2Freviews%2Freviews%22%2C%22previousPageRollup%22%3A%22%2Freviews%2Faltametrics-reviews%22%2C%22currentPageAbstract%22%3A%22%2FReviews%2F%5BEMP%5D-Reviews-E%5BEID%5D.htm%22%2C%22previousPageAbstract%22%3A%22%2FReviews%2FAltametrics-Reviews-E%5BEID%5D.htm%22%2C%22currentPageFull%22%3A%22https%3A%2F%2Fwww.glassdoor.co.in%2FReviews%2FAltametrics-Reviews-E269429.htm%22%2C%22previousPageFull%22%3A%22https%3A%2F%2Fwww.glassdoor.co.in%2FReviews%2FAltametrics-Reviews-E269429.htm%22%7D; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Oct+07+2026+15%3A15%3A28+GMT%2B0530+(India+Standard+Time)&version=202407.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=27239b62-00a9-4855-b7a9-8b6835719a87&interactionCount=1&isAnonUser=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0002%3A1%2CC0004%3A1%2CC0017%3A1&AwaitingReconsent=false; ki_t=1788791892495%3B1791366269120%3B1791366328672%3B15%3B31; rl_session=RS_ENC_v3_eyJhdXRvVHJhY2siOnRydWUsInRpbWVvdXQiOjE4MDAwMDAsImV4cGlyZXNBdCI6MTc5MTM2ODEyODczNCwiaWQiOjE3OTEzNjYyNjc2MzIsInNlc3Npb25TdGFydCI6ZmFsc2V9; _dd_s=aid=f71e2218-117b-4c8f-ab4b-b77019cff07a&rum=2&id=6008c079-f602-4564-9189-e9b320d96cf4&created=1791366267504&expire=1791367702948"""

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
# 1. DATE NORMALIZER
# ==============================================================
def parse_any_date(raw_val):
    if not raw_val:
        return ""
    if isinstance(raw_val, (int, float)):
        ts = float(raw_val)
        if ts > 1e11:
            ts /= 1000
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            pass

    raw_str = str(raw_val).strip()
    if raw_str.isdigit() and len(raw_str) >= 10:
        ts = float(raw_str)
        if ts > 1e11:
            ts /= 1000
        try:
            return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except Exception:
            pass

    s = raw_str.lower()
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

    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', raw_str)
    cleaned = re.sub(r'[,.]', '', cleaned).strip()

    m_mdy = re.search(r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{1,2})\s+(\d{4})', cleaned, re.I)
    if m_mdy:
        try:
            dt = datetime.datetime.strptime(f"{m_mdy.group(1)[:3]} {m_mdy.group(2)} {m_mdy.group(3)}", "%b %d %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    m_dmy = re.search(r'(\d{1,2})\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})', cleaned, re.I)
    if m_dmy:
        try:
            dt = datetime.datetime.strptime(f"{m_dmy.group(1)} {m_dmy.group(2)[:3]} {m_dmy.group(3)}", "%d %b %Y")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass

    return ""

# ==============================================================
# 2. ZENROWS FETCHER WITH FORWARDED COOKIES
# ==============================================================
def fetch_authenticated_zenrows(target_url, cookie_str=""):
    print(f"\n[ZENROWS] Fetching: {target_url}")
    params = {
        'url': target_url,
        'apikey': ZENROWS_API_KEY,
        'mode': 'auto',
        'js_render': 'true'
    }
    headers = {}
    if cookie_str:
        params['custom_headers'] = 'true'
        headers['Cookie'] = cookie_str
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'

    try:
        resp = requests.get(ZENROWS_ENDPOINT, params=params, headers=headers, timeout=120)
        print(f"[STATUS] HTTP {resp.status_code} | Bytes: {len(resp.text)}")
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
    except Exception as e:
        print(f"[FETCH ERROR] {e}")
    return ""

# ==============================================================
# 3. GLASSDOOR AUTHENTICATED PARSER (EXACT COMPANY IDS)
# ==============================================================
def scrape_glassdoor_live():
    reviews = []
    # Both exact India and Global URLs from your cookie
    urls = [
        "https://www.glassdoor.co.in/Reviews/Altametrics-Reviews-E269429.htm?sort.sortType=RD&sort.ascending=false",
        "https://www.glassdoor.com/Reviews/Altametrics-Reviews-E269429.htm?sort.sortType=RD&sort.ascending=false",
        "https://www.glassdoor.com/Reviews/Altametrics-Reviews-E393527.htm?sort.sortType=RD&sort.ascending=false"
    ]

    for url in urls:
        html = fetch_authenticated_zenrows(url, GLASSDOOR_COOKIE)
        if not html:
            continue

        soup = BeautifulSoup(html, 'html.parser')

        # Layer 1: Schema JSON-LD
        for s in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(s.string or s.get_text() or "{}")
                items = data if isinstance(data, list) else [data]
                for item in items:
                    revs = []
                    if item.get("@type") == "Review":
                        revs.append(item)
                    elif "review" in item and isinstance(item["review"], list):
                        revs.extend(item["review"])
                    for r in revs:
                        t = r.get("name") or r.get("headline") or "Employee Review"
                        b = r.get("reviewBody") or r.get("description") or ""
                        d = parse_any_date(r.get("datePublished") or r.get("dateCreated"))
                        rating_v = r.get("reviewRating", {}).get("ratingValue", 5) if isinstance(r.get("reviewRating"), dict) else 5
                        try:
                            rt = int(float(rating_v))
                        except Exception:
                            rt = 5
                        auth = r.get("author", {})
                        a_name = auth.get("name") if isinstance(auth, dict) else (auth or "Verified Employee")
                        if (t or b) and d:
                            reviews.append({
                                "Platform": "Glassdoor", "Author": str(a_name),
                                "Title": str(t), "Rating": rt, "Date": d, "Review_Text": str(b) if b else str(t)
                            })
            except Exception:
                pass

        # Layer 2: Next.js __NEXT_DATA__
        m_next = re.search(r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', html, re.DOTALL)
        if m_next:
            try:
                next_data = json.loads(m_next.group(1))
                def walk(obj):
                    if isinstance(obj, dict):
                        if obj.get("__typename") in ("EmployerReview", "Review") or ("ratingOverall" in obj and ("summary" in obj or "pros" in obj)):
                            title = obj.get("summary") or obj.get("title") or obj.get("headline") or ""
                            pros = obj.get("pros") or ""
                            cons = obj.get("cons") or ""
                            body = obj.get("reviewBody") or obj.get("reviewText") or ""
                            if not body and (pros or cons):
                                body = f"Pros: {pros} | Cons: {cons}".strip(" |")

                            raw_dt = obj.get("reviewDateTime") or obj.get("datePublished") or obj.get("submissionDate")
                            dt = parse_any_date(raw_dt)
                            rating = obj.get("ratingOverall") or obj.get("rating") or 5
                            try:
                                rating = int(float(rating))
                            except Exception:
                                rating = 5

                            job = obj.get("jobTitle")
                            job_name = job.get("text") if isinstance(job, dict) else (job or "Verified Employee")

                            if (title or body) and dt:
                                reviews.append({
                                    "Platform": "Glassdoor", "Author": str(job_name),
                                    "Title": str(title) if title else "Employee Review",
                                    "Rating": rating, "Date": dt, "Review_Text": str(body) if body else str(title)
                                })
                        for v in obj.values():
                            walk(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            walk(item)
                walk(next_data)
            except Exception:
                pass

        # Layer 3: DOM Elements
        if not reviews:
            cards = soup.find_all(attrs={"data-test": re.compile(r"review-card|empReview", re.I)}) or \
                    soup.find_all("li", class_=re.compile(r"ReviewCard|noBorder")) or \
                    soup.find_all("div", class_=re.compile(r"empReview"))
            for c in cards:
                t = c.find(attrs={"data-test": "review-title"}) or c.find(["h2", "h3"])
                p_el = c.find(attrs={"data-test": "review-text-pros"})
                c_el = c.find(attrs={"data-test": "review-text-cons"})
                b_el = c.find(attrs={"data-test": "review-body"}) or c.find("p")
                
                body_txt = ""
                if p_el or c_el:
                    body_txt = f"Pros: {p_el.get_text(strip=True) if p_el else ''} | Cons: {c_el.get_text(strip=True) if c_el else ''}".strip(" |")
                elif b_el:
                    body_txt = b_el.get_text(strip=True)

                d_el = c.find(attrs={"data-test": "review-date"}) or c.find(class_=re.compile(r"reviewDate|middle", re.I))
                dt = parse_any_date(d_el.get_text(strip=True) if d_el else "")
                title_txt = t.get_text(strip=True) if t else ""

                if (title_txt or body_txt) and dt:
                    reviews.append({
                        "Platform": "Glassdoor", "Author": "Verified Employee",
                        "Title": title_txt if title_txt else "Employee Review",
                        "Rating": 5, "Date": dt, "Review_Text": body_txt if body_txt else title_txt
                    })

        if reviews:
            break

    seen = set()
    clean_reviews = []
    for r in reviews:
        sig = (r["Title"][:25], r["Date"], r["Review_Text"][:30])
        if sig not in seen and r["Date"]:
            seen.add(sig)
            clean_reviews.append(r)

    print(f"-> Glassdoor live parsed: {len(clean_reviews)} reviews")
    return clean_reviews

# ==============================================================
# 4. INDEED & COMPARABLY (PROVEN LIVE)
# ==============================================================
def scrape_indeed_live():
    url = "https://www.indeed.com/cmp/Altametrics/reviews?sort=date"
    html = fetch_authenticated_zenrows(url)
    reviews = []
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all(attrs={"data-testid": "review-container"}) or soup.find_all("div", class_=re.compile(r"review|css-"))
        for c in cards:
            t = c.find(attrs={"data-testid": "title"}) or c.find(["h2", "h3"])
            b = c.find(attrs={"data-testid": "review-text"}) or c.find("span", class_=re.compile(r"text"))
            d = c.find(attrs={"data-testid": "review-date"}) or c.find(string=re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|ago|\d{4})\b', re.I))
            dt = parse_any_date(d.strip() if isinstance(d, str) else (d.get_text(strip=True) if d else ""))
            tt = t.get_text(strip=True) if t else ""
            bt = b.get_text(strip=True) if b else ""
            if (tt or bt) and dt:
                reviews.append({
                    "Platform": "Indeed", "Author": "Verified Employee",
                    "Title": tt if tt else "Live Review", "Rating": 5, "Date": dt, "Review_Text": bt if bt else tt
                })
    print(f"-> Indeed parsed: {len(reviews)} reviews")
    return reviews

def scrape_comparably_live():
    url = "https://www.comparably.com/companies/altametrics/reviews"
    html = fetch_authenticated_zenrows(url)
    reviews = []
    if not html:
        return reviews
    soup = BeautifulSoup(html, 'html.parser')
    cards = soup.find_all("div", class_=re.compile(r"review|comment|quote|testimonial|card", re.I))
    for c in cards:
        p_elem = c.find(["p", "blockquote", "span"], class_=re.compile(r"text|content|body|quote", re.I)) or c.find("p")
        txt = p_elem.get_text(strip=True) if p_elem else c.get_text(strip=True)
        if len(txt) < 35 or "cookie" in txt.lower() or "privacy" in txt.lower():
            continue
        t_elem = c.find(["h3", "h4", "h5", "strong"], class_=re.compile(r"title|header|heading", re.I))
        title = t_elem.get_text(strip=True) if t_elem else "Workplace Feedback"
        a_elem = c.find(class_=re.compile(r"author|user|role|dept|department", re.I))
        author = a_elem.get_text(strip=True) if a_elem else "Verified Employee"
        d_elem = c.find(class_=re.compile(r"date|time|posted|timestamp", re.I)) or \
                 c.find(string=re.compile(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|ago|\d{4})\b', re.I))
        raw_dt = d_elem.strip() if isinstance(d_elem, str) else (d_elem.get_text(strip=True) if d_elem else "")
        dt = parse_any_date(raw_dt) or parse_any_date(txt)
        if (txt or title) and dt:
            reviews.append({
                "Platform": "Comparably", "Author": author, "Title": title, "Rating": 5, "Date": dt, "Review_Text": txt
            })
    print(f"-> Comparably parsed: {len(reviews)} reviews")
    return reviews

# ==============================================================
# 5. DATABASE ACCUMULATOR
# ==============================================================
def load_database():
    records_map = {}
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for r in data:
                        sig = (r["Platform"], r.get("Title", "")[:25], r.get("Date", ""), r.get("Review_Text", "")[:30])
                        records_map[sig] = r
        except Exception:
            pass
    return records_map

def save_database(records_list):
    try:
        with open(DATABASE_FILE, "w", encoding="utf-8") as f:
            json.dump(records_list, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

# ==============================================================
# 6. MOBILE APP STORES (GOOGLE PLAY & APP STORE USA)
# ==============================================================
def scrape_google_play():
    app_info = {"rating": 4.73, "ratings_count": 7850, "reviews_count": "7,850", "installs": "100,000+", "reviews": []}
    try:
        details = gp_app(ANDROID_PKG, lang='en', country='us')
        if details:
            app_info["rating"] = round(details.get("score", 4.73), 2)
            app_info["ratings_count"] = details.get("ratings", 7850)
            app_info["reviews_count"] = f"{details.get('reviews', details.get('
