import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
# Your StockNewsAPI Key (replace with your actual key)
api_key = os.getenv('STOCKNEWSAPI_KEY')

# Define the endpoint for fetching top headlines or general market news
market_news_url = f'https://stocknewsapi.com/api/v1/market-news?token={api_key}'

# Function to fetch top headlines
def fetch_top_headlines(limit=20):
    market_news_url = f'https://stocknewsapi.com/api/v1/category?section=general&items={limit}&sortby=rank&extra-fields=id,eventid,rankscore&page=1&token={api_key}'
    response = requests.get(market_news_url)
    
    if response.status_code == 200:
        news_data = response.json()
        if 'data' in news_data:
            refined_headlines = []
            # print(f"Fetched {len(news_data['data'])} Top Headlines:\n")
            for index, article in enumerate(news_data['data'], 1):  # Start enumeration from 1
                headline = article.get('title', 'No headline available')
                source = article.get('source_name', 'No source available')
                published = article.get('date', 'No publication time available')
                description = article.get('text', 'No description available')
                url = article.get('news_url', 'No URL available')
                image_url = article.get('image_url', 'No image URL available')
                rankscore = article.get('rank_score', 'No rank score available')
                sentiment = article.get('sentiment', 'No sentiment available')
                event_id = article.get('eventid', 'No event ID available')
                news_id = article.get('news_id', 'No news ID available')
                article_type = article.get('type', 'No type available')  # Get the 'type' field


                # # Print all fields, including rank score, sentiment, and more
                # print(f"{index}. {headline}")
                # print(f"   Source: {source}")
                # print(f"   Published At: {published}")
                # print(f"   Description: {description}")
                # print(f"   URL: {url}")
                # print(f"   Image URL: {image_url}")
                # print(f"   Rank Score: {rankscore}")
                # print(f"   Sentiment: {sentiment}")
                # print(f"   Event ID: {event_id}")
                # print(f"   News ID: {news_id}\n")
                

                 # Only return relevant fields for now (headline, description, source, rankscore)
                refined_article = {
                    'headline': headline,
                    'description': description,
                    'source': source,
                    'rankscore': rankscore,
                    'type': article_type,  # Include type field in the data
                    'date': published

                }
                refined_headlines.append(refined_article)

            # Return the refined headlines with relevant fields
            print(len(refined_headlines))
            return refined_headlines

        else:
            print("No top headlines found.")
    else:
        print(f"Error fetching news: {response.status_code}")

def fetch_top_headlines_week(limit=20):
    # Modify the URL to fetch headlines for the past week (7 days)
    market_news_url = f'https://stocknewsapi.com/api/v1/category?section=general&items={limit}&sortby=rank&days=7&extra-fields=id,eventid,rankscore&page=1&token={api_key}'
    
    # Send the request to the API
    response = requests.get(market_news_url)
    
    if response.status_code == 200:
        news_data = response.json()
        if 'data' in news_data:
            refined_headlines = []
            for index, article in enumerate(news_data['data'], 1):  # Start enumeration from 1
                headline = article.get('title', 'No headline available')
                source = article.get('source_name', 'No source available')
                published = article.get('date', 'No publication time available')
                description = article.get('text', 'No description available')
                url = article.get('news_url', 'No URL available')
                image_url = article.get('image_url', 'No image URL available')
                rankscore = article.get('rank_score', 'No rank score available')
                sentiment = article.get('sentiment', 'No sentiment available')
                event_id = article.get('eventid', 'No event ID available')
                news_id = article.get('news_id', 'No news ID available')
                article_type = article.get('type', 'No type available')  # Get the 'type' field

                # Only return relevant fields for now (headline, description, source, rankscore)
                refined_article = {
                    'headline': headline,
                    'description': description,
                    'source': source,
                    'rankscore': rankscore,
                    'type': article_type,  # Include type field in the data
                    'date': published
                }
                refined_headlines.append(refined_article)

            # Return the refined headlines with relevant fields
            print(len(refined_headlines))
            return refined_headlines

        else:
            print("No top headlines found.")
    else:
        print(f"Error fetching news: {response.status_code}")

def format_market_analysis(top_headlines):
    """
    Formats the given top headlines into a structured string suitable for feeding into GPT or other analysis.
    
    Args:
    - top_headlines (list): List of article dictionaries with 'headline', 'description', 'source', 'rank_score', and 'url'.
    
    Returns:
    - str: A formatted string with each article's details, separated by two line breaks.
    """
    filtered_articles = [article for article in top_headlines if article.get('type') != 'Video']
    
    # Format each article into a string, ensuring fields are accessed safely with .get()
    formatted_text = "\n\n".join([
        f"Headline: {article.get('headline', 'No headline available')}\n"
        f"Description: {article.get('description', 'No description available')}\n"
        # f"Source: {article.get('source', 'No source available')}\n"
        f"Rank Score: {article.get('rankscore', 'No rank score available')}\n"
        for article in filtered_articles
    ])
    print(len(filtered_articles))
    return formatted_text

# news = fetch_top_headlines(limit=10)
# print(news)
# print(format_market_analysis(news))