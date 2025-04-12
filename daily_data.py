import os
from polygon import StocksClient
from dotenv import load_dotenv
from webapp import create_app  # Import your Flask app factory
from webapp.models import db, StockNews, UserSavedStock  # Import models
from flask import current_app
from webapp.models import StockData  # Ensure you have this model
import requests
from polygon_api import get_news_for_ticker
from datetime import datetime, timezone, timedelta, date
import openai
import time
import statistics
from dateutil import tz
import pytz  # at the top of your file if needed



load_dotenv()


api_key = os.getenv('STOCKNEWSAPI_KEY')
MAX_TICKERS_PER_CALL = 20  # ✅ Start with 20 tickers per request (adjustable)
api_key2 =os.getenv('POLYGON_API_KEY')
api_key3 =os.getenv('OPENAI_API_KEY')

client = StocksClient(api_key2)
OpenAIClient = openai.OpenAI(api_key=api_key3)

BASE_URL = "https://api.polygon.io"

# Create Flask app and set up application context
app = create_app()  # Ensure this matches your Flask factory method

def fetch_rsi(symbol, timespan="day", window=14):
    """Fetch RSI (Relative Strength Index) for a stock."""
    url = f"{BASE_URL}/v1/indicators/rsi/{symbol}?timespan={timespan}&window={window}&apiKey={api_key2}"
    response = requests.get(url)
    data = response.json()

    # print("DEBUG: API Response:", data)  # Print full response for debugging

    # ✅ Check if "values" exist in "results"
    if "results" in data and "values" in data["results"] and isinstance(data["results"]["values"], list):
        last_value = data["results"]["values"][-1]["value"]  # Get the latest RSI
        return round(last_value, 2) if last_value else None

    print(f"⚠️ Warning: No RSI data available for {symbol}")
    return None

def fetch_moving_averages(symbol):
    """Fetches 50-day and 200-day moving averages (SMA)"""
    url_50 = f"https://api.polygon.io/v1/indicators/sma/{symbol}?timespan=day&adjusted=true&window=50&series_type=close&order=desc&limit=1&apiKey={api_key2}"
    url_200 = f"https://api.polygon.io/v1/indicators/sma/{symbol}?timespan=day&adjusted=true&window=200&series_type=close&order=desc&limit=1&apiKey={api_key2}"

    
    try:
        response_50 = requests.get(url_50)
        response_200 = requests.get(url_200)

        # Ensure requests were successful
        if response_50.status_code != 200 or response_200.status_code != 200:
            print("⚠️ Error: API returned non-200 response. Check API key or plan limits.")
            return None, None

        data_50 = response_50.json()
        data_200 = response_200.json()

        # Extract and return the moving average values
        ma_50 = round(data_50["results"]["values"][0]["value"], 2) if data_50.get("results") and "values" in data_50["results"] else None
        ma_200 = round(data_200["results"]["values"][0]["value"], 2) if data_200.get("results") and "values" in data_200["results"] else None

        return ma_50, ma_200

    except requests.exceptions.JSONDecodeError as e:
        print(f"⚠️ JSON Decode Error: {e}")
        return None, None
    except Exception as e:
        print(f"⚠️ Error fetching moving averages: {e}")
        return None, None

def fetch_macd(symbol):
    """Fetches MACD value and signal line."""
    url = f"https://api.polygon.io/v1/indicators/macd/{symbol}?timespan=day&adjusted=true&short_window=12&long_window=26&signal_window=9&series_type=close&order=desc&limit=1&apiKey={api_key2}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code != 200:
            print(f"⚠️ API Error for {symbol}: {response.status_code} - {response.text}")
            return None, None

        if 'results' in data and 'values' in data['results']:
            macd_value = round(data['results']['values'][0]['value'], 2)  # MACD line
            signal_line = round(data['results']['values'][0]['signal'], 2)  # Signal line
            histogram = round(data['results']['values'][0]['histogram'], 2)  # MACD Histogram
            return macd_value, signal_line, histogram

    except requests.exceptions.JSONDecodeError as e:
        print(f"⚠️ JSON Decode Error: {e}")
    except Exception as e:
        print(f"⚠️ Error fetching MACD for {symbol}: {e}")

    return None, None, None

def fetch_relative_volume(symbol):
    """Fetches Relative Volume (RVOL)"""
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev?apiKey={api_key2}"
    data = requests.get(url).json()

    start_date = (datetime.now().date() - timedelta(days=60))
    end_date = datetime.now().date()

    if 'results' in data:
        volume_today = data['results'][0]['v']
        avg_volume_url =     f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{end_date}?apiKey={api_key2}"

        avg_volume_data = requests.get(avg_volume_url).json()

        avg_volume = sum(day['v'] for day in avg_volume_data['results']) / len(avg_volume_data['results'])
        rvol = round(volume_today / avg_volume, 2)
        return rvol
    return None

def fetch_bollinger_bands(symbol):
    """Manually calculates Bollinger Bands from recent closing prices."""
    today = date.today()
    start_date = today - timedelta(days=40)  # Get extra days in case of weekends
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{today}?adjusted=true&sort=desc&limit=25&apiKey={api_key2}"

    try:
        response = requests.get(url)
        data = response.json()

        if 'results' in data and len(data['results']) >= 20:
            closes = [day['c'] for day in data['results'][:20]]
            sma = statistics.mean(closes)
            std_dev = statistics.stdev(closes)
            upper_band = round(sma + (2 * std_dev), 2)
            lower_band = round(sma - (2 * std_dev), 2)
            return upper_band, lower_band
        else:
            print("⚠️ Not enough data to calculate Bollinger Bands")
    except Exception as e:
        print(f"⚠️ Error calculating Bollinger Bands: {e}")

    return None, None

def fetch_support_resistance(symbol):
    """Estimates support and resistance levels using recent highs/lows."""
    try:
        start_date = date.today() - timedelta(days=30)
        url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{start_date}/{date.today()}?apiKey={api_key2}"
        
        response = requests.get(url)
        data = response.json()

        if 'results' in data:
            highs = [day['h'] for day in data['results']]
            lows = [day['l'] for day in data['results']]
            resistance = round(max(highs), 2)
            support = round(min(lows), 2)
            return resistance, support
    except Exception as e:
        print(f"⚠️ Error fetching Support & Resistance: {e}")

    return None, None

def fetch_and_store_top_news(limit=100):
    """Fetches top stock market news and ensures every article is stored, regardless of tickers."""
    with app.app_context():
        print("📡 Fetching stock market news...")

         # 🗑️ Delete only trending news (identified by having a rankscore)
        db.session.query(StockNews).filter(StockNews.rankscore.isnot(None)).delete()
        db.session.commit()
        print("🗑️ Deleted old trending news from database.")

        market_news_url = f'https://stocknewsapi.com/api/v1/category?section=general&items={limit}&sortby=rank&extra-fields=id,eventid,rankscore&page=1&token={api_key}'
        response = requests.get(market_news_url)

        if response.status_code != 200:
            print(f"❌ Error fetching news: {response.status_code}")
            return
        
        news_data = response.json()

        if 'data' not in news_data:
            print("⚠️ No 'data' key found in API response.")
            return

        # ✅ Get all valid stock symbols from `StockData`
        stored_symbols = {row.symbol for row in db.session.query(StockData.symbol).all()}
        print(f"✅ Found {len(stored_symbols)} stocks in StockData.")

        added_count = 0  # Track successfully added news articles

        for article in news_data['data']:
            title = article.get('title', '').upper()
            text = article.get('text', '').upper()

            # ✅ Extract tickers from API response (if available)
            tickers = article.get('tickers', [])  

            # ✅ Check if any tickers exist in `StockData`
            matched_tickers = [symbol for symbol in stored_symbols if symbol in title or symbol in text]
            all_tickers = list(set(tickers + matched_tickers))  # Merge found tickers
            valid_tickers = [ticker for ticker in all_tickers if ticker in stored_symbols]

            # ✅ Store the **first valid ticker**, otherwise NULL
            ticker_string = valid_tickers[0] if valid_tickers else None  

            # ✅ Force save the article even if no tickers are present
            try:
                news_item = StockNews(
                    symbol=ticker_string,  # Store a single valid ticker OR None
                    headline=article.get('title', 'No headline available'),
                    description=article.get('text', 'No description available'),
                    source=article.get('source_name', 'Unknown'),
                    rankscore=float(article.get('rank_score', 0.0)),  
                    news_type=article.get('type', 'General'),
                    date_published=article.get('date'),
                    url=article.get('news_url', 'https://example.com'),
                )
                db.session.add(news_item)
                db.session.commit()  # ✅ Save every article, even if tickers are missing
                added_count += 1
            except Exception as e:
                db.session.rollback()  # ✅ Prevent any single error from stopping others
                print(f"⚠️ Skipping article due to DB error: {e}")

        print(f"✅ Stored {added_count} news articles in the database (ignoring tickers).")
        
def fetch_and_store_bulk_stock_news():
    """Fetches news for multiple tickers in one API call, reducing API usage and only storing top-ranked articles."""
    with app.app_context():
        tickers = {row.stock_symbol for row in UserSavedStock.query.all()}
        if not tickers:
            print("⚠️ No tracked stocks found. Skipping news fetch.")
            return

        print(f"📡 Fetching news for {len(tickers)} tickers...")

        tickers_list = list(tickers)  # Convert set to list for slicing
        batch_size = MAX_TICKERS_PER_CALL  # Start with the max batch size

        for i in range(0, len(tickers_list), batch_size):
            batch = tickers_list[i:i + batch_size]
            tickers_param = ",".join(batch)

            url = f"https://stocknewsapi.com/api/v1?tickers={tickers_param}&items=50&page=1&token={api_key}"
            response = requests.get(url)

            if response.status_code != 200:
                print(f"❌ Error fetching news (Status {response.status_code}). Retrying with smaller batch size...")
                batch_size = max(5, batch_size - 5)  # Reduce batch size but never below 5
                time.sleep(1)
                continue  # Skip this batch and retry smaller next time

            news_data = response.json()
            if "data" not in news_data:
                print("⚠️ No 'data' key in API response. Skipping batch.")
                continue

            added_count = 0
            print(f"🔍 DEBUG: Processing {len(news_data['data'])} articles for batch {batch}...\n")

            # ✅ Group news by ticker
            news_by_ticker = {}
            for article in news_data["data"]:
                tickers_in_article = article.get("tickers", [])
                rankscore = float(article.get("rankscore", 0))  # Default to 0 if missing
                print(rankscore)
                for ticker in tickers_in_article:
                    if ticker in tickers:
                        if ticker not in news_by_ticker:
                            news_by_ticker[ticker] = []
                        news_by_ticker[ticker].append((article, rankscore))

            # ✅ Store only top 5 ranked news per ticker
            for ticker, articles in news_by_ticker.items():
                sorted_articles = sorted(articles, key=lambda x: x[1], reverse=True)[:5]  # Sort by rankscore DESC, take top 5

                for article, rankscore in sorted_articles:
                    title = article.get("title", "No title").strip()
                    description = article.get("text", "No description").strip()
                    source = article.get("source_name", "Unknown")
                    url = article.get("news_url", "https://example.com")
                    date_published = article.get("date")

                    # ✅ Convert to proper datetime format
                    try:
                        date_published = datetime.strptime(date_published, "%a, %d %b %Y %H:%M:%S %z")
                    except ValueError:
                        print(f"⚠️ Invalid date format for {title}: {date_published}. Skipping article.")
                        continue

                    # ✅ Store news in database
                    existing_news = StockNews.query.filter_by(symbol=ticker, headline=title).first()
                    if not existing_news:
                        news_entry = StockNews(
                            symbol=ticker,
                            headline=title,
                            description=description,
                            source=source,
                            date_published=date_published,
                            url=url
                        )
                        db.session.add(news_entry)
                        added_count += 1
                    else:
                        print(f"⚠️ Skipping duplicate news for {ticker}: {title}")

            db.session.commit()
            print(f"✅ Stored {added_count} news articles for batch: {batch}")

            time.sleep(2)  # ✅ Avoid hitting API rate limits
 
def get_top_market_movers(direction='gainers', min_volume=10000):
    """
    Fetch top gainers/losers using Polygon's StocksClient.
    Filters stocks with a minimum trading volume.
    """
    tickers = client.get_gainers_and_losers(direction=direction)

    top_movers = []
    if 'tickers' not in tickers:
        print(f"⚠️ ERROR: 'tickers' key missing in API response. Full response: {tickers}")
        return []

    # 🔥 Debug: Print API response structure
    print(f"✅ API Response ({direction}): {tickers}")

    for item in tickers['tickers']:
        # Ensure required keys are present
        if 'todaysChangePerc' in item and 'day' in item and 'v' in item['day']:
            if isinstance(item['todaysChangePerc'], float) and item['day']['v'] >= min_volume:
                top_movers.append({
                    'symbol': item['ticker'],
                    'name': item.get('name', 'Unknown'),
                    'price': item['day']['c'],  # Closing price
                    'change_percent': item['todaysChangePerc'],
                    'change_amount': item['todaysChange'],
                    'volume': item['day']['v']
                })

    # Sort movers by % change
    return sorted(top_movers, key=lambda x: x['change_percent'], reverse=(direction == 'gainers'))[:5]

def format_number(value):
    """Formats numbers into human-readable format."""
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.2f}B"
    elif value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    elif value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:,.0f}"

def find_market_breakouts(snapshot=None, limit=10, min_price=10, min_volume=2_000_000, min_market_cap=100_000_000_000):
    """
    Scans the full market snapshot and returns top breakout candidates.
    """
    if snapshot is None:
        snapshot = fetch_market_snapshot()
    if not snapshot:
        return []

    breakout_candidates = []
    
    # ✅ First: gather prequalified stocks
    prequalified_stocks = []
    for stock in snapshot:
        try:
            symbol = stock['ticker']
            price = stock['day']['c']
            volume = stock['day']['v']
            market_cap = stock.get('market_cap')

            if price >= min_price and volume >= min_volume and (not market_cap or market_cap >= min_market_cap):
                prequalified_stocks.append({
                    "symbol": symbol,
                    "price": price,
                    "volume": volume,
                    "market_cap": market_cap
                })
        except Exception as e:
            print(f"⚠️ Skipping stock during pre-filtering: {e}")
            continue

    print(f"🔍 {len(prequalified_stocks)} stocks passed initial filters. Running indicator analysis...")

    # ✅ Then: run API calls only on prequalified list
    for stock in prequalified_stocks:
        try:
            symbol = stock["symbol"]
            price = stock["price"]

            rsi = fetch_rsi(symbol)
            macd, signal, histogram = fetch_macd(symbol)
            rvol = fetch_relative_volume(symbol)
            support, resistance = fetch_support_resistance(symbol)

            near_resistance = resistance and price >= resistance * 0.95
            macd_bullish = macd and signal and (macd > signal or (histogram and histogram > 0))

            if rsi and 50 < rsi < 70 and rvol and rvol > 1.2 and near_resistance and macd_bullish:
                breakout_candidates.append({
                    "symbol": symbol,
                    "price": price,
                    "rsi": rsi,
                    "rvol": rvol,
                    "macd": macd,
                    "signal": signal,
                    "histogram": histogram,
                    "resistance": resistance
                })

        except Exception as e:
            print(f"⚠️ Skipping {symbol}: {e}")
            continue

    print(f"✅ Found {len(breakout_candidates)} breakout candidates.")
    return breakout_candidates[:limit]

def fetch_and_store_breakouts(snapshot=None, limit=10):
    """
    Identifies breakout candidates and stores them in the database under the 'breakout' category.
    """
    with app.app_context():
        print("🚀 Fetching Breakout Candidates...")

        breakouts = find_market_breakouts(snapshot=snapshot, limit=limit)
        breakout_symbols = {stock['symbol'] for stock in breakouts}

        # ✅ Step 1: Remove 'breakout' tag from stocks that are no longer breakout candidates
        outdated_breakouts = db.session.query(StockData).filter(StockData.category.like('%breakout%')).all()
        for stock_entry in outdated_breakouts:
            if stock_entry.symbol not in breakout_symbols:
                existing_categories = set(stock_entry.category.split(","))
                existing_categories.discard("breakout")

                if existing_categories:
                    stock_entry.category = ",".join(existing_categories)
                else:
                    db.session.delete(stock_entry)  # Remove if no other tags

        # ✅ Step 2: Add or update new breakout stocks
        for stock in breakouts:
            stock_entry = db.session.query(StockData).filter_by(symbol=stock['symbol']).first()

            if stock_entry:
                # Update existing record
                stock_entry.price = stock['price']
                stock_entry.rsi = stock['rsi']
                stock_entry.volume = stock['rvol']  # Treating RVOL as volume proxy here
                existing_categories = set(stock_entry.category.split(",")) if stock_entry.category else set()
                existing_categories.add("breakout")
                stock_entry.category = ",".join(existing_categories)
            else:
                # Insert new stock
                stock_entry = StockData(
                    symbol=stock['symbol'],
                    name="Unknown",  # Optional: You can fetch names elsewhere
                    price=stock['price'],
                    rsi=stock['rsi'],
                    volume=stock['rvol'],
                    category="breakout"
                )
                db.session.add(stock_entry)

            # ✅ Fetch and store latest news
            news_articles = get_news_for_ticker(stock['symbol'])
            for article in news_articles:
                if not db.session.query(StockNews).filter_by(url=article['url']).first():
                    news_entry = StockNews(
                        symbol=stock['symbol'],
                        headline=article['headline'],
                        description=article['description'],
                        url=article['url'],
                        source=article['source'],
                        date_published=article['published_date']
                    )
                    db.session.add(news_entry)

        db.session.commit()
        print(f"✅ Stored or updated {len(breakouts)} breakout stocks in the database.")

def get_top_traded_stocks(snapshot=None, limit=10, min_price=5):
    """
    Fetches most actively traded stocks, ensuring correct data types.
    """
    if snapshot is None:
        print("📡 Fetching Top Traded Stocks...")
        snapshot = fetch_market_snapshot()
    if not snapshot:
        return []

    filtered_stocks = []

    for stock in snapshot:
        try:
            price = stock['day']['c']
            volume = stock['day']['v']

            if volume > 1_000_000 and price >= min_price:
                filtered_stocks.append({
                    'symbol': stock['ticker'],
                    'name': stock.get('name') or stock.get('company_name', 'Unknown'),
                    'volume': volume,
                    'price': price,
                    'change_percent': float(stock.get('todaysChangePerc', 0.0)),
                    'change_amount': stock.get('todaysChange', 0.0),
                })
        except Exception as e:
            print(f"⚠️ Skipping stock due to error: {e}")
            continue

    sorted_stocks = sorted(filtered_stocks, key=lambda x: x['volume'], reverse=True)[:limit]
    print(f"✅ Found {len(sorted_stocks)} top traded stocks after filtering.")
    return sorted_stocks

def fetch_and_store_top_traded(snapshot=None):
    """Fetches and stores top traded stocks and updates database correctly."""
    with app.app_context():
        top_traded = get_top_traded_stocks(snapshot)
        top_traded_symbols = {stock['symbol'] for stock in top_traded}  # ✅ Store only the latest symbols

        # ✅ Step 1: Remove "top_traded" from stocks that are no longer in the list
        outdated_stocks = db.session.query(StockData).filter(StockData.category.like('%top_traded%')).all()
        for stock_entry in outdated_stocks:
            if stock_entry.symbol not in top_traded_symbols:
                existing_categories = set(stock_entry.category.split(","))
                existing_categories.discard("top_traded")  # ✅ Remove the "top_traded" category
                
                # ✅ If no more categories, remove the stock from the DB (optional)
                if existing_categories:
                    stock_entry.category = ",".join(existing_categories)
                else:
                    db.session.delete(stock_entry)  # ✅ Remove stock if it has no categories left

        # ✅ Step 2: Add or update new top traded stocks
        for stock in top_traded:
            stock_entry = db.session.query(StockData).filter_by(symbol=stock['symbol']).first()

            if stock_entry:
                # ✅ Update existing stock record
                stock_entry.name = stock['name']
                stock_entry.price = stock['price']
                stock_entry.change_percent = stock['change_percent']
                stock_entry.change_amount = stock['change_amount']
                stock_entry.volume = stock['volume']

                # ✅ Ensure "top_traded" stays in category
                existing_categories = set(stock_entry.category.split(",")) if stock_entry.category else set()
                existing_categories.add("top_traded")
                stock_entry.category = ",".join(existing_categories)

            else:
                # ✅ Insert new stock
                stock_entry = StockData(
                    symbol=stock['symbol'],
                    name=stock['name'],
                    price=stock['price'],
                    change_percent=stock['change_percent'],
                    change_amount=stock['change_amount'],
                    volume=stock['volume'],
                    category="top_traded",  # ✅ New stock gets "top_traded" only
                )
                db.session.add(stock_entry)
            # ✅ Fetch and store latest news for this stock
            news_articles = get_news_for_ticker(stock['symbol'])

            for article in news_articles:
                if not db.session.query(StockNews).filter_by(url=article['url']).first():
                    news_entry = StockNews(
                        symbol=stock['symbol'],
                        headline=article['headline'],
                        description=article['description'],
                        url=article['url'],
                        source=article['source'],
                        date_published=article['published_date']
                    )
                    db.session.add(news_entry)

        db.session.commit()
    print(f"✅ Stored or updated {len(top_traded)} top traded stocks in the database.")

def fetch_and_store_gainers_losers():
    """Fetch and store top gainers & losers in the database using StocksClient."""
    with app.app_context():
        print("📊 Fetching gainers and losers...")

        gainers = get_top_market_movers(direction='gainers')
        losers = get_top_market_movers(direction='losers')

        for stock in gainers + losers:
            stock_entry = db.session.query(StockData).filter_by(symbol=stock['symbol']).first()

            new_category = "gainer" if stock in gainers else "loser"

            if stock_entry:
                # ✅ Update existing stock entry
                stock_entry.name = stock['name']
                stock_entry.price = stock['price']
                stock_entry.change_percent = stock['change_percent']
                stock_entry.change_amount = stock['change_amount']
                stock_entry.volume = stock['volume']

                # ✅ Append category instead of overwriting
                existing_categories = stock_entry.category.split(",") if stock_entry.category else []
                stock_entry.category = ",".join(set(existing_categories + [new_category]))

            else:
                # ✅ Insert new stock
                stock_entry = StockData(
                    symbol=stock['symbol'],
                    name=stock['name'],
                    price=stock['price'],
                    change_percent=stock['change_percent'],
                    change_amount=stock['change_amount'],
                    volume=stock['volume'],
                    category=new_category  # ✅ New stock gets a single category
                )
                db.session.add(stock_entry)

        db.session.commit()
        print(f"✅ Stored or updated {len(gainers)} gainers and {len(losers)} losers in the database.")

def fetch_market_snapshot():
    """
    Fetches full market snapshot and ensures it contains ticker data.
    """
    print("FETCHING SNAPSHOT......")
    try:
        data = client.get_snapshot_all()

        if not data or 'tickers' not in data:
            print("⚠️ ERROR: No 'tickers' key in API response.")
            return []

        tickers = data['tickers']
        print(f"✅ Snapshot contains {len(tickers)} tickers.")
        return tickers

    except Exception as e:
        print(f"❌ Error fetching market snapshot: {e}")
        return []

def get_stock_snapshot(symbol):
    """Fetches latest stock price, volume, change percentage, saves to StockData, and fetches news once per day."""
    from flask import current_app

    with current_app.app_context():
        try:
            snapshot = client.get_snapshot(symbol)
            if not snapshot or "ticker" not in snapshot:
                print(f"⚠️ No snapshot data for {symbol}.")
                return None

            ticker_data = snapshot["ticker"]
            stock_price = ticker_data["day"]["c"]  # Closing price
            price_change = ticker_data.get("todaysChangePerc", 0.0)
            change_amount = ticker_data.get("todaysChange", 0.0)
            volume = ticker_data["day"]["v"]

            categories = []
            if price_change > 0:
                categories.append("gainer")
            elif price_change < 0:
                categories.append("loser")

            stock_name = f"{symbol} (No name found)"

            stock_entry = StockData.query.filter_by(symbol=symbol).first()

            now_utc = datetime.now(timezone.utc)

            if stock_entry:
                print(f"🔄 Updating stock entry for {symbol}...")
                stock_entry.last_updated = now_utc
                stock_entry.price = stock_price
                stock_entry.change_percent = price_change
                stock_entry.change_amount = change_amount
                stock_entry.volume = volume

                existing_categories = set(stock_entry.category.split(",")) if stock_entry.category else set()
                existing_categories.update(categories)
                stock_entry.category = ",".join(existing_categories) if existing_categories else "neutral"

            else:
                print(f"💾 Creating new stock entry for {symbol}...")
                stock_entry = StockData(
                    symbol=symbol,
                    name=stock_name,
                    last_updated=now_utc,
                    price=stock_price,
                    change_percent=price_change,
                    change_amount=change_amount,
                    volume=volume,
                    category=",".join(categories) if categories else "neutral",
                )
                db.session.add(stock_entry)

            db.session.commit()

            hour = now_utc - timedelta(hours=5)

            fetched_dt = stock_entry.date_fetched
            if fetched_dt and (fetched_dt.tzinfo is None):
                fetched_dt = fetched_dt.replace(tzinfo=timezone.utc)

            if fetched_dt and fetched_dt > hour:
                print(f"⏩ Skipping news fetch for {symbol} (already fetched in the last hour).")
            else:
                print(f"📰 Fetching news for {symbol}...")
                news_articles = get_news_for_ticker(symbol)

                if news_articles:
                    for news in news_articles:
                        headline = news["headline"]
                        description = news["description"]
                        source = news.get("source", "Unknown")
                        url = news.get("url", "No URL available")
                        date_published = news.get("date", None)

                        existing_news = StockNews.query.filter_by(
                            symbol=symbol, headline=headline, date_published=date_published
                        ).first()

                        if not existing_news:
                            news_entry = StockNews(
                                symbol=symbol,
                                headline=headline,
                                description=description,
                                source=source,
                                date_published=date_published,
                                url=url
                            )
                            db.session.add(news_entry)
                        else:
                            print(f"⚠️ Skipping duplicate news for {symbol}: {headline}")

                    stock_entry.date_fetched = now_utc
                    db.session.commit()
                    print(f"✅ Stored news for {symbol}.")
                else:
                    print(f"⚠️ No news found for {symbol}.")

            return {
                "symbol": symbol,
                "name": stock_name,
                "price": stock_price,
                "change_percent": price_change,
                "change_amount": change_amount,
                "volume": volume,
                "category": stock_entry.category
            }

        except Exception as e:
            print(f"❌ Error fetching snapshot or news for {symbol}: {e}")
            db.session.rollback()
            return None

def fetch_and_summarize_stock_news():
    """Fetches news from the database & generates GPT summaries."""
    print("📡 Fetching & summarizing stock news...")

    fetch_and_store_bulk_stock_news()  # ✅ Pull fresh news before summarizing

    with app.app_context():
        tracked_stocks = {row.stock_symbol for row in UserSavedStock.query.all()}
        print(f"✅ Found {len(tracked_stocks)} unique tracked stocks.")

        for symbol in tracked_stocks:
            print(f"🔄 Fetching fresh snapshot for {symbol}...")
            if not get_stock_snapshot(symbol):
                print(f"❌ Failed to fetch snapshot for {symbol}. Skipping.")
                continue

            stock_entry = StockData.query.filter_by(symbol=symbol).first()
            if not stock_entry:
                print(f"❌ {symbol} not found in StockData after snapshot. Skipping.")
                continue

            now_utc = datetime.now(timezone.utc)

            if stock_entry.summary_text and stock_entry.summary_last_updated:
                last_updated = stock_entry.summary_last_updated

                if last_updated.tzinfo is None:
                    # Treat naive timestamp as LOCAL time and convert to UTC
                    local_tz = pytz.timezone("America/New_York")  # or your actual local timezone
                    last_updated = local_tz.localize(last_updated).astimezone(pytz.utc)

                now_utc = datetime.now(timezone.utc)
                time_diff = now_utc - last_updated

                print(f"🕒 Last updated for {symbol}: {last_updated}")
                print(f"⏳ Time since last update for {symbol}: {time_diff.total_seconds() / 60:.2f} minutes")

                if time_diff < timedelta(hours=2):
                    print(f"⚠️ Skipping {symbol}, summary is already fresh.")
                    continue

            def safe_call(func, *args):
                try:
                    return func(*args)
                except Exception as e:
                    print(f"❌ Error in {func.__name__} for {symbol}: {e}")
                    return None

            rsi_value = safe_call(fetch_rsi, symbol)
            ma_result = safe_call(fetch_moving_averages, symbol) or (None, None)
            macd_result = safe_call(fetch_macd, symbol) or (None, None, None)
            rvol = safe_call(fetch_relative_volume, symbol)
            support, resistance = safe_call(fetch_support_resistance, symbol) or (None, None)

            ma_50, ma_200 = ma_result
            macd_value, signal_line, histogram = macd_result

            news_articles = StockNews.query.filter(
                StockNews.symbol == symbol,
                StockNews.date_published >= now_utc - timedelta(days=1)
            ).order_by(StockNews.rankscore.desc()).all()

            recent_news = [f"{news.headline}: {news.description}" for news in news_articles[:3]]
            combined_text = " ".join(recent_news)

            prompt = f"""
            You are a sharp financial analyst summarizing {symbol}'s market behavior. Write for beginner-to-intermediate investors, with insights smart enough to impress pros.

            Use the data below to craft a short, actionable summary. Be concise — focus only on what stands out. Skip fluff or repetition:

            - **Price**: ${stock_entry.price:.2f} ({stock_entry.change_percent:.2f}%)
            - **Volume**: {stock_entry.volume:,}
            - **Key News**: {combined_text}
            - **RSI**: {rsi_value} ({'Oversold — rebound potential' if rsi_value and rsi_value < 30 else 'Overbought — possible pullback' if rsi_value and rsi_value > 70 else 'Neutral'})
            - **50-day MA**: {ma_50}
            - **200-day MA**: {ma_200}
            - **MACD**: Line {macd_value}, Signal {signal_line}, Histogram {histogram}
            - **RVOL**: {rvol}
            - **Support / Resistance**: Support near ${support}, Resistance near ${resistance}

            ---

            ### Output Style:

            Write a concise 2-paragraph stock snapshot. Focus only on what stands out — skip fluff and repetition.

            - **Trend Check** – Summarize technical momentum (MACD, RSI, MAs, etc.) in 1–2 clear sentences.
            - **News Pulse** – Only mention news if it's materially driving price, sentiment, or volume.

            Wrap with a **forward-looking insight** (e.g. key level, setup, or likely next move).

            If the stock was quiet:
            > "{symbol} showed no meaningful changes today. No actionable signal."

            Avoid repeating raw inputs unless they directly support the insight. Aim for clarity, brevity, and signal.
            """

            try:
                response = OpenAIClient.chat.completions.create(
                    model="gpt-4-turbo",
                    messages=[
                        {"role": "system", "content": "You are a seasoned financial analyst providing concise yet insightful stock updates for investors. Your analysis should be strategic, forward-looking, and impactful."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1
                )
                summary_text = response.choices[0].message.content.strip()

                stock_entry.summary_text = summary_text
                stock_entry.summary_last_updated = now_utc
                db.session.commit()

                print(f"✅ Saved GPT summary for {symbol}.")

            except Exception as e:
                print(f"❌ Error summarizing {symbol}: {e}")
                db.session.rollback()



def delete_old_news(days_old=1):
    """
    Deletes news articles older than the given number of days (default: 30).
    """
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)

    old_news = db.session.query(StockNews).filter(StockNews.date_published < cutoff_date).all()

    deleted_count = len(old_news)

    for article in old_news:
        db.session.delete(article)

    db.session.commit()
    print(f"🧹 Deleted {deleted_count} news articles older than {days_old} days.")

def update_user_saved_stocks():
    """
    Refreshes price, volume, and news for all stocks saved by users.
    Ensures user dashboards and summaries stay up-to-date.
    """
    with app.app_context():
        print("🔄 Updating user-saved stocks...")
        symbols = {row.stock_symbol for row in UserSavedStock.query.all()}

        for symbol in symbols:
            print(f"📥 Updating snapshot for {symbol}")
            get_stock_snapshot(symbol)  # Already handles DB updates + news


if __name__ == "__main__":
    update_user_saved_stocks()
    # fetch_rsi("NVDA")

    # print(fetch_support_resistance("NVDA"))
    # fetch_and_store_gainers_losers()
    # fetch_and_store_top_news()
    # fetch_and_store_top_traded()

    # with app.app_context():
        # print(get_stock_snapshot("NVDA"))
        # fetch_and_summarize_stock_news()
        # delete_old_news()