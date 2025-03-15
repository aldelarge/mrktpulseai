import requests
import os
from dotenv import load_dotenv

# Load API Key
load_dotenv()
api_key = os.getenv("POLYGON_API_KEY")

# Request URL for general market news
url = f'https://api.polygon.io/v2/reference/news?apiKey={api_key}&limit=25'

# Fetch the data
response = requests.get(url)

# Check if the response is successful
if response.status_code == 200:
    news_data = response.json()

    # Loop through the results and display the headlines, source, description, etc.
    if 'results' in news_data:
        for article in news_data['results']:
            # Safely access the data fields, check if key exists first
            headline = article.get('title', 'No headline available')
            source = article.get('source', 'No source available')
            published = article.get('published_utc', 'No publication time available')
            url = article.get('article_url', 'No URL available')
            description = article.get('description', 'No description available')  # Adding description
            tickers = article.get('tickers', 'No tickers available')  # Access the tickers field
            # If tickers is a list, join them as a string for better readability
            tickers_str = ', '.join(tickers) if isinstance(tickers, list) else tickers

            print(f"Headline: {headline}")
            print(f"Source: {source}")
            print(f"Published At: {published}")
            print(f"Description: {description}")  # Print description
            print(f"Tickers: {tickers_str}")  # Print the tickers
            print(f"URL: {url}\n")
    else:
        print("No results found.")
else:
    print(f"Error fetching news: {response.status_code}")
