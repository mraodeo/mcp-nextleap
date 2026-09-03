import datetime
import re
from google_play_scraper import reviews, Sort
from langdetect import detect, LangDetectException

def sanitize_text(text: str) -> str:
    """Removes potential PII like emails and phone numbers from text."""
    if not text:
        return ""
    # Remove email addresses
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[EMAIL REMOVED]', text)
    # Remove 10 digit phone numbers (basic matching)
    text = re.sub(r'\b\d{10}\b', '[PHONE REMOVED]', text)
    return text

def fetch_groww_reviews(weeks_back: int = 8, max_count: int = None) -> list[dict]:
    """
    Fetches recent reviews for the Groww app from the Google Play Store.
    Filters to reviews from the last `weeks_back` weeks.
    If `max_count` is provided, stops after fetching that many reviews.
    """
    app_id = 'com.nextbillion.groww'
    
    # Calculate the cutoff date
    cutoff_date = datetime.datetime.now() - datetime.timedelta(weeks=weeks_back)
    
    sanitized_reviews = []
    continuation_token = None
    reached_cutoff = False
    
    print(f"Fetching reviews since {cutoff_date.date()}...")

    while not reached_cutoff:
        result, continuation_token = reviews(
            app_id,
            lang='en', # Focus on English language reviews
            country='in', # India region
            sort=Sort.NEWEST, # Newest first to filter by date
            count=1000, # Fetch in batches of 1000
            continuation_token=continuation_token
        )
        
        if not result:
            break
            
        for r in result:
            # 1. Filter by date
            if r['at'] < cutoff_date:
                reached_cutoff = True
                break # Sorted NEWEST, so all remaining are older
                
            # 2. Enforce limits if max_count is set
            if max_count and len(sanitized_reviews) >= max_count:
                reached_cutoff = True
                break
                
            # 3. Sanitize
            content = r.get('content', '')
            if not content:
                continue
                
            sanitized_content = sanitize_text(content)
            
            # 4. Edge Case: Skip short reviews (< 8 words)
            if len(sanitized_content.split()) < 8:
                continue
                
            # 5. Edge Case: Skip non-English reviews
            try:
                if detect(sanitized_content) != 'en':
                    continue
            except LangDetectException:
                # If langdetect fails, it usually means weird characters/emojis, skip it
                continue
                
            sanitized_review = {
                'id': r['reviewId'],
                'date': r['at'].isoformat(),
                'rating': r['score'],
                'content': sanitized_content
            }
                
            sanitized_reviews.append(sanitized_review)
            
        # If there's no continuation token left, we are done fetching
        if not continuation_token:
            break
            
    return sanitized_reviews

if __name__ == "__main__":
    import json
    # Standalone manual test
    try:
        # Fetch ALL real reviews for the last 8 weeks (no max_count limit)
        fetched_reviews = fetch_groww_reviews(weeks_back=8, max_count=None)
        print(f"Successfully fetched and sanitized {len(fetched_reviews)} total reviews.")
        
        # Save to a local JSON file for inspection
        output_file = "all_reviews_8_weeks.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(fetched_reviews, f, indent=2, ensure_ascii=False)
            
        print(f"\nSaved {len(fetched_reviews)} reviews to '{output_file}' in your project folder!")
        
    except Exception as e:
        print(f"Error fetching reviews: {e}")
