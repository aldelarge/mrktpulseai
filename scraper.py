import requests
from bs4 import BeautifulSoup
import random
import time

def random_wait():
    delay = random.uniform(2, 5)  # Random wait between 2-5 seconds
    time.sleep(delay)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
]
def scrape_yahoo_finance():
    url = "https://finance.yahoo.com/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = requests.get(url, headers=headers)
    random_wait()

    #Error response
    if response.status_code == 403 or response.status_code == 429:
        print("Warning: Yahoo Finance may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Yahoo Finance data. Status code:", response.status_code)
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    articles = soup.find_all("h3", class_=["clamp"])
    if not articles:
        print("No articles found!")
        return []

    news = [{"headline": article.get_text(strip=True)} for article in articles[:20]]  # <-- Changed to dictionary format
    return news

def scrape_yahoo_indices():
    url = "https://finance.yahoo.com/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    response = requests.get(url, headers=headers)
    random_wait()

    #Error response
    if response.status_code == 403 or response.status_code == 429:
        print("Warning: Yahoo Finance may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Yahoo Finance data. Status code:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    indices = []
    
    for li in soup.find_all("li", class_="box-item"):
        name_tag = li.find("a")
        value_tag = li.find("fin-streamer", {"data-field": "regularMarketPrice"})
        change_tag = li.find("fin-streamer", {"data-field": "regularMarketChange"})
        percent_change_tag = li.find("fin-streamer", {"data-field": "regularMarketChangePercent"})

        name = name_tag.text.strip() if name_tag else "N/A"
        value = value_tag.text.strip() if value_tag else "N/A"
        change = change_tag.text.strip() if change_tag else "N/A"
        percent_change = percent_change_tag.text.strip() if percent_change_tag else "N/A"

        indices.append({"name": name, "value": value, "change": change, "percent_change": percent_change})
    
    return indices

def scrape_yahoo_sectors():
    url = "https://finance.yahoo.com/sectors"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = requests.get(url, headers=headers)
    random_wait()

    if response.status_code == 403 or response.status_code == 429:
        print("Warning: Yahoo Finance may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Yahoo Finance data. Status code:", response.status_code)
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    heatmap = soup.find("div", class_="heatMap-container")
    
    if not heatmap:
        print("Heatmap section not found")
        return []

    sectors = []
    for sector_div in heatmap.find_all("div", class_="rect-container"):
        sector_name = sector_div.find("div", class_="ticker-div").text.strip()
        percent_change = sector_div.find("div", class_="percent-div").text.strip()
        
        sectors.append({
            "sector": sector_name,
            "percent_change": percent_change
        })
    return sectors

def scrape_cnbc_news():
    url = "https://www.cnbc.com/markets/"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = requests.get(url, headers=headers)
    random_wait()

    #Error response
    if response.status_code == 403 or response.status_code == 429:
        print("Warning: CNBC may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch CNBC Finance data. Status code:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    found_articles = soup.select("div.Card-titleContainer")

    if not found_articles:
        print("Warning: No articles found. CNBC may have changed its structure.")

    for item in found_articles[:20]:
        headline_tag = item.select_one("a")
        summary_tag = item.select_one("div.Card-description")

        if not headline_tag:
            print("Warning: Missing headline tag in an article.")
            continue  # Skip this iteration if there's no headline

        headline = headline_tag.text.strip()
        link = headline_tag["href"]
        summary = summary_tag.text.strip() if summary_tag else "No summary available"

        articles.append({
            "headline": headline,
            "summary": summary,
            "link": link
        })
    return articles

def scrape_investing_news():
    url = "https://www.investing.com/news/latest-news"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1"}

    response = requests.get(url, headers=headers)

    #Error response
    if response.status_code == 403 or response.status_code == 429:
        print("Warning: Investing.com may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Investing.com data. Status code:", response.status_code)
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    news_items = soup.select("article.js-article-item")

    if not news_items:
        print("Warning: No articles found. Investing.com may have changed its structure.")

    for item in news_items[:20]:  # Limit to top 20 headlines
        headline_tag = item.select_one("a.title")
        link_tag = item.select_one("a.title")
        summary_tag = item.select_one("p.articleDetails")

        if not headline_tag or not link_tag:
            print("Warning: Missing headline or link tag in an article.")
            continue  # Skip this iteration if there's no headline

        headline = headline_tag.text.strip()
        link = "https://www.investing.com" + link_tag["href"]
        summary = summary_tag.text.strip() if summary_tag else "No summary available"

        articles.append({
            "headline": headline,
            "summary": summary,
            "link": link
        })

    return articles

def scrape_marketwatch():
    url = "https://www.marketwatch.com/latest-news?mod=side_nav"
    headers = {"User-Agent": random.choice(USER_AGENTS)}

    response = requests.get(url, headers=headers)
    random_wait()

    if response.status_code == 403 or response.status_code == 429:
        print("Warning: MarketWatch may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Marketwatch data. Status code:", response.status_code)
        return []

    soup = BeautifulSoup(response.text, "html.parser")

    articles = []
    found_articles = soup.select("div.article__content")

    if not found_articles:
        print("Warning: No articles found. MarketWatch may have changed its structure.")

    for item in found_articles[:20]:  # Limit to 20 articles
        headline_tag = item.select_one("h3.article__headline a")
        if not headline_tag:
            continue  # Skip if no headline

        headline = headline_tag.text.strip()
        link = headline_tag["href"]

        articles.append({"headline": headline, "link": link})

    return articles

def scrape_marketwatch_bond_yields():
    url = "https://www.marketwatch.com/market-data/rates"
    headers = {"User-Agent": random.choice(USER_AGENTS)}    
    response = requests.get(url, headers=headers)
    random_wait()

    if response.status_code == 403 or response.status_code == 429:
        print("Warning: MarketWatch may be blocking the scraper. Status code:", response.status_code)
        return []
    if response.status_code != 200:
        print("Failed to fetch Marketwatch data. Status code:", response.status_code)
        return []
    
    soup = BeautifulSoup(response.text, "html.parser")
    bond_data = []
    
    tables = soup.find_all("table")  # Find all tables on the page
    if not tables:
        print("No tables found on MarketWatch bonds page.")
        return []
    
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            columns = row.find_all("td")
            if len(columns) < 3:
                continue  # Skip rows without enough columns
            
            bond_name = columns[0].get_text(strip=True)  # Extract bond name
            bond_yield = columns[1].get_text(strip=True)  # Extract yield value
            change = columns[2].get_text(strip=True)  # Extract change value
            
            # Ensure the bond name is valid and not just empty data
            if bond_name and bond_yield.replace('.', '', 1).isdigit():
                bond_data.append({
                    "name": bond_name,
                    "yield": bond_yield,
                    "change": change
                })
    
    if not bond_data:
        print("Warning: No bond data extracted. MarketWatch structure may have changed.")
    
    return bond_data



# print(scrape_marketwatch_bond_yields())