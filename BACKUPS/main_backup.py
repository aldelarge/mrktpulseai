import requests
from bs4 import BeautifulSoup
import openai
import os
from dotenv import load_dotenv
import random

# Load API Key securely
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


# Initialize OpenAI client
client = openai.OpenAI(api_key=api_key)

def scrape_yahoo_finance():
    url = "https://finance.yahoo.com/"
    headers = {"User-Agent": "Mozilla/5.0"}  # Helps prevent getting blocked

    response = requests.get(url, headers=headers)
    
    # Debug print to check if we got a response
    print(f"Response Status Code: {response.status_code}")  
    print(f"First 500 characters of HTML:\n{response.text[:500]}")  

    if response.status_code != 200:
        print("Failed to fetch page.")
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Check the structure of the page
    print("Looking for articles...")
    
    articles = soup.find_all("h3", class_=["clamp"])  # Class might have changed!

    for article in articles[:20]:  # Get the top 5 articles
        print(article)  # Print raw article HTML to debug
        print("----")

    if not articles:
        print("No articles found! The webpage structure might have changed.")
        return []

    news = [article.get_text(strip=True) for article in articles[:5]]  # Extract only text

    return news

def analyze_sentiment_gpt(headlines):
    if not headlines:
        return " No headlines available for analysis."
    # Initialize OpenAI client inside the function
    client = openai.OpenAI(api_key=api_key)

    market_analysis_text = " ".join(headlines) 

    request_id = random.randint(1000, 9999)

    market_analysis_text = "\n".join(headlines)  

    prompt = f"""
    Below are several stock market headlines. Provide a **detailed market summary** that captures key movements, trends, and themes. Identify any emerging patterns, major catalysts, and potential implications for investors.

    - Identify which headlines are the most **consequential** based on potential market impact. Give more weight to news about major economic events, earnings reports, Federal Reserve decisions, or geopolitical developments.

    Then, assess the **overall market sentiment** as **Bullish, Bearish, or Neutral**, explaining the reasoning behind it. If the sentiment is mixed, describe the conflicting signals.
    
    - Highlight any major **catalysts** that may influence the market today.
    
    **Do not** list or analyze each headline separately—focus on a single, in-depth market summary.

    Headlines:
    {market_analysis_text}
    """


    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3
        )

        return response.choices[0].message.content.strip()  # ✅ Returns plain text output

    except openai.RateLimitError:
        print("⚠️ GPT-4 quota exceeded. Switching to GPT-3.5-turbo...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing market summaries."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3
        )
        response.choices[0].message.content
        return response.choices[0].message.content.strip()

# Run scraper and analyze sentiment
news = scrape_yahoo_finance()
if news:
    sentiment_summary = analyze_sentiment_gpt(news)
    print(f"\n **Market Summary:**\n{sentiment_summary}")
else:
    print("No news articles found.")
