import csv
import datetime
from google_play_scraper import reviews, Sort
from app_store_scraper import AppStore

ANDROID_PKG = 'com.example.acme'
IOS_APP_ID = 1234567890
IOS_APP_NAME = 'acme-mobile'

today = datetime.datetime.now().strftime("%Y-%m-%d")

def get_android_reviews():
    print("Fetching Android Reviews...")
    review_list = []
    try:
        result, _ = reviews(ANDROID_PKG, lang='en', country='us', sort=Sort.NEWEST, count=50)
        for r in result:
            review_list.append({
                'Platform': 'Google Play',
                'Author': r.get('userName', ''),
                'Rating': r.get('score', ''),
                'Date': str(r.get('at', '')),
                'Review_Text': r.get('content', '')
            })
    except Exception as e:
        print(f"Android Info: {e}")
    return review_list

def get_ios_reviews():
    print("Fetching iOS Reviews...")
    review_list = []
    try:
        app = AppStore(country='us', app_name=IOS_APP_NAME, app_id=IOS_APP_ID)
        app.review(how_many=50)
        for r in app.reviews:
            review_list.append({
                'Platform': 'App Store',
                'Author': r.get('userName', ''),
                'Rating': r.get('rating', ''),
                'Date': str(r.get('date', '')),
                'Review_Text': r.get('review', '')
            })
    except Exception as e:
        print(f"iOS Info: {e}")
    return review_list

if __name__ == "__main__":
    print("Starting Multi-Platform Scraper...")
    all_reviews = []
    all_reviews.extend(get_android_reviews())
    all_reviews.extend(get_ios_reviews())

    filename = f"all_reviews_{today}.csv"
    fieldnames = ['Platform', 'Author', 'Rating', 'Date', 'Review_Text']

    # File har haal mein banegi taaki GitHub Actions crash na ho
    with open(filename, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        if all_reviews:
            writer.writerows(all_reviews)
            print(f"Success! {len(all_reviews)} reviews saved to {filename}")
        else:
            print(f"Template CSV created: {filename}")
