import pandas as pd
import datetime
from google_play_scraper import reviews, Sort
from app_store_scraper import AppStore

ANDROID_PKG = 'com.example.acme'
IOS_APP_ID = 1234567890
IOS_APP_NAME = 'acme-mobile'

today = datetime.datetime.now().strftime("%Y-%m-%d")

def get_android_reviews():
    print("Fetching Android Reviews...")
    try:
        result, _ = reviews(ANDROID_PKG, lang='en', country='us', sort=Sort.NEWEST, count=50)
        df = pd.DataFrame(result)[['userName', 'score', 'at', 'content']]
        df['Platform'] = 'Google Play'
        return df
    except Exception as e:
        print(f"Android Error: {e}")
        return pd.DataFrame()

def get_ios_reviews():
    print("Fetching iOS Reviews...")
    try:
        app = AppStore(country='us', app_name=IOS_APP_NAME, app_id=IOS_APP_ID)
        app.review(how_many=50)
        df = pd.DataFrame(app.reviews)[['userName', 'rating', 'date', 'review']]
        df.columns = ['userName', 'score', 'at', 'content']
        df['Platform'] = 'App Store'
        return df
    except Exception as e:
        print(f"iOS Error: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    print("Starting Multi-Platform Scraper...")
    df_android = get_android_reviews()
    df_ios = get_ios_reviews()
    
    all_data = pd.concat([df_android, df_ios], ignore_index=True)
    
    if not all_data.empty:
        filename = f"all_reviews_{today}.csv"
        all_data.to_csv(filename, index=False)
        print(f"Success! {len(all_data)} total reviews saved to {filename}")
    else:
        print("No data found.")
