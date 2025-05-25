import os
from dotenv import load_dotenv
from apify_client import ApifyClient
from typing import Dict, Optional, Any

load_dotenv()

def scrape_profile(profile_url: str) -> Optional[Dict[str, Any]]:
    """
    Scrapes a LinkedIn profile and returns the profile data as a dictionary.

    Args:
        profile_url (str): The LinkedIn profile URL to scrape.

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the scraped profile data,
                                  or None if scraping fails.
    """
    try:
        apify_token = os.getenv("APIFY_API_TOKEN")
        if not apify_token:
            raise ValueError("APIFY_API_TOKEN not found in .env")
        
        li_at_cookie = os.getenv("LI_AT_COOKIE")
        # Prepare input for Apify actor. The cookie is included only if available.
        run_input = {
            "url": profile_url,
            "cookie": [{"name": "li_at", "value": li_at_cookie}] if li_at_cookie else []
        }
        
        client = ApifyClient(apify_token)
        print(f"Running actor with input: {run_input}")
        # Start the LinkedIn profile scraper actor on Apify platform
        run = client.actor("pratikdani/linkedin-people-profile-scraper").call(run_input=run_input)
        print(f"Run status: {run['status']}")
        print(f"💾 Check your data here: https://console.apify.com/storage/datasets/{run['defaultDatasetId']}")
        
        dataset_id = run["defaultDatasetId"]
        # Iterate through the dataset items; return on the first result found
        for item in client.dataset(dataset_id).iterate_items():
            return dict(item)
        print("No data returned from dataset")
        return None
    except Exception as e:
        print(f"Error scraping profile: {e}")
        return None
