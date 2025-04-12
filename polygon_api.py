from polygon import StocksClient
import pandas as pd
import time
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import requests

# Load API Key
load_dotenv()
api_key = os.getenv("POLYGON_API_KEY")

# Initialize the RESTClient
client = StocksClient(api_key)

def calculate_monthly_change(current_price, historical_data):
    # If historical data is empty, return 0% change
    if not historical_data:
        return 0
    
    # Get the price from 30 days ago
    price_30_days_ago = historical_data[0]['c']  # The first item in historical data should be closest to 30 days ago
    
    # Calculate the monthly change
    if price_30_days_ago != 0:
        monthly_change = ((current_price - price_30_days_ago) / price_30_days_ago) * 100
    else:
        monthly_change = 0

    return monthly_change

# def calculate_30_day_moving_average(historical_data):
#     # Ensure there are enough data points for a 30-day moving average
#     if len(historical_data) < 30:
#         return None  # Not enough data points to calculate the 30-day moving average
    
#     # Get the closing prices from the historical data (last 30 days)
#     closing_prices = [item['c'] for item in historical_data[-30:]]  # Get the last 30 closing prices
    
#     # Calculate the moving average
#     sma_30_day = sum(closing_prices) / len(closing_prices)  # Simple average of the last 30 closing prices
#     return sma_30_day

def get_index_snapshot():
    snapshots = []
    etf_info = {
        'SPY': 'S&P 500 ETF (Represents the S&P 500 Index)',
        'DIA': 'Dow Jones Industrial Average ETF (Represents the Dow Jones Industrial Average)',
        'QQQ': 'Nasdaq-100 ETF (Represents the Nasdaq-100 Index)',
        'IWM': 'Russell 2000 ETF (Represents the Russell 2000 Index)',
        'IJH': 'S&P MidCap 400 ETF (Represents the S&P MidCap 400 Index)',
        'VTI': 'Vanguard Total Stock Market ETF',
        'VXX': 'iPath S&P 500 VIX Short-Term Futures ETF',
        'XLK': 'Technology Select Sector SPDR Fund',
        'XLF': 'Financial Select Sector SPDR Fund',
        'XLE': 'Energy Select Sector SPDR Fund',
        'XLV': 'Health Care Select Sector SPDR Fund',
        'XLY': 'Consumer Discretionary Select Sector SPDR Fund',
        'XLU': 'Utilities Select Sector SPDR Fund',
        'XLRE': 'Real Estate Select Sector SPDR Fund',
        'XLB': 'Materials Select Sector SPDR Fund'
    }

    for ticker, sector in etf_info.items():
        try:
            response = client.get_snapshot(ticker)

            if not response or 'ticker' not in response:
                print(f"Error: No valid data returned for {ticker}")
                continue

            current_price = response['ticker']['day']['c']
            # Get historical data for the last 30 trading days
            start_date = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')  # A larger window to account for weekends
            historical_data_month = client.get_aggregate_bars(
                ticker, 
                multiplier=1, 
                timespan="day", 
                from_date=start_date, 
                to_date=datetime.now().strftime('%Y-%m-%d'),
                adjusted=True
            ).get('results', [])

            # Filter out weekends (only include weekdays)
            weekdays_data = [
                item for item in historical_data_month
                if datetime.fromtimestamp(item['t'] / 1000, tz=timezone.utc).weekday() < 5
            ]

            # If there are fewer than 30 trading days, just use as many as available
            recent_data = weekdays_data[-30:]

            # Calculate the 30-day moving average of the closing prices
            # moving_average = calculate_30_day_moving_average(recent_data)

            # Calculate the volume change percentage (from monthly average)
            historical_volume = [item['v'] for item in recent_data]
            average_volume = sum(historical_volume) / len(historical_volume) if historical_volume else 0
            volume_change_percentage = ((response['ticker']['day']['v'] - average_volume) / average_volume) * 100 if average_volume else 0

            # Calculate monthly average volume
            monthly_average_volume = sum(historical_volume) / len(historical_volume) if historical_volume else 0

            snapshot_data = {
                'Ticker': ticker,
                'Sector/Decor': sector,
                'Current Price': current_price,
                'Change ($)': response['ticker']['todaysChange'],
                'Change (%)': response['ticker']['todaysChangePerc'],
                'High of the Day ($)': response['ticker']['day']['h'],
                'Low of the Day ($)': response['ticker']['day']['l'],
                'Volume': response['ticker']['day']['v'],
                'Previous Close ($)': response['ticker']['prevDay']['c'],
                'Monthly Change (%)': calculate_monthly_change(current_price, weekdays_data),
                'Volume Change (%)': volume_change_percentage,
                # '30-Day Moving Average': moving_average,
                'Monthly Average Volume': monthly_average_volume,  # Added monthly average volume
                'Daily Volume': response['ticker']['day']['v']  # Added daily volume
            }

            snapshots.append(snapshot_data)

        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")

    # Convert snapshots into a DataFrame
    df_snapshots = pd.DataFrame(snapshots)
    return df_snapshots

def format_etf_data(df_snapshots):
    formatted_data = ""
    for index, row in df_snapshots.iterrows():
        formatted_data += f"**{row['Ticker']}** ({row['Sector/Decor']}):\n"
        formatted_data += f" - Current Price: ${row['Current Price']}\n"
        formatted_data += f" - Change: ${row['Change ($)']} ({row['Change (%)']}%)\n"
        formatted_data += f" - High of the Day: ${row['High of the Day ($)']}\n"
        formatted_data += f" - Low of the Day: ${row['Low of the Day ($)']}\n"
        formatted_data += f" - Volume: {row['Volume']}\n"
        formatted_data += f" - Previous Close: ${row['Previous Close ($)']}\n"
        formatted_data += f" - Monthly Change: {row['Monthly Change (%)']}%\n"
        formatted_data += f" - Volume Change: {row['Volume Change (%)']}% (Change from the monthly average)\n"
        # formatted_data += f" - 30-Day Moving Average: {row['30-Day Moving Average']}\n"  # Corrected key
        formatted_data += f" - Monthly Average Volume: {row['Monthly Average Volume']}\n"  # Added monthly average volume
        formatted_data += f" - Daily Volume: {row['Daily Volume']}\n"  # Added daily volume
        formatted_data += "\n"
    return formatted_data

def get_top_market_movers(direction='gainers', min_volume=10000):
    """
    Fetch the top market movers (gainers or losers) with a minimum trading volume.
    direction: 'gainers' or 'losers'
    min_volume: Minimum trading volume to filter tickers
    """
    tickers = client.get_gainers_and_losers(direction=direction)

    top_movers = []

    # Process and print the top movers
    for item in tickers['tickers']:
        # Ensure that the relevant keys are present in the response
        if 'todaysChangePerc' in item and 'day' in item and 'v' in item['day']:
            # Check if the change percentage and volume meet the criteria
            if isinstance(item['todaysChangePerc'], float) and item['day']['v'] >= min_volume:
                # Add the relevant data to the list
                top_movers.append({
                    'Ticker': item['ticker'],
                    'Change (%)': item['todaysChangePerc'],
                    'Change ($)': item['todaysChange'],
                    'Price': item['day']['c'],  # Today's close price
                    'Volume': item['day']['v']
                })

    # Sort the top movers based on change percentage (most positive first for gainers)
    if direction == 'gainers':
        top_movers_sorted = sorted(top_movers, key=lambda x: x['Change (%)'], reverse=True)
    else:
        # For losers, sort in ascending order to get the largest (most negative) losses first
        top_movers_sorted = sorted(top_movers, key=lambda x: x['Change (%)'])

    # Return top 20 movers
    return top_movers_sorted[:5]

def get_news_for_ticker(ticker, limit=5, days_range=10):
    """
    Fetch news articles related to a stock ticker using Polygon's News API.
    Filters out articles older than today.
    """
    # URL for Polygon's News API
    url = f'https://api.polygon.io/v2/reference/news?ticker={ticker}&limit={limit}&apiKey={api_key}'

    # Send request to News API
    response = requests.get(url)
    data = response.json()

    news_articles = []
    if data.get('results'):
        # Get today's date using timezone-aware datetime
        today = datetime.now(timezone.utc).date()
        cutoff_date = today - timedelta(days=days_range)

        for article in data['results']:
            # Adjust the date format to handle missing microseconds
            try:
                # Handle datetime string without microseconds
                published_date = datetime.strptime(article['published_utc'], '%Y-%m-%dT%H:%M:%SZ').date()

                # Only include articles published today or later
                if published_date >= cutoff_date:
                    news_articles.append({
                        'headline': article.get('title', 'No headline available'),
                        'description': article.get('description', 'No description available'),
                        'url': article.get("article_url", "No URL available"),  # ✅ Extract article_url correctly
                        'source': article.get("publisher", {}).get("name", "Unknown Source"),
                        'published_date': article.get('published_utc', 'No date available')  # Add the published date
                    })
            except ValueError as e:
                print(f"Error parsing date for article: {article.get('title')}. Error: {e}")
                continue
        return news_articles
    else:
        return []

def get_top_movers_news(direction='gainers'):
    """
    Fetch the top movers and their news headlines using Polygon's News API.
    Filters out articles older than today.
    """
    top_movers = get_top_market_movers(direction=direction)

    # For each top mover, fetch news
    for mover in top_movers:
        ticker = mover['Ticker']
        print(f"\nNews for {ticker} ({'Gainer' if direction == 'gainers' else 'Loser'}):")
        news = get_news_for_ticker(ticker)
        if news:
            for article in news:
                print(f"Headline: {article['headline']}")
                print(f"Description: {article['description']}")
                print(f"URL: {article['url']}")
                print(f"Published Date: {article['published_date']}")
        else:
            print("No news found for this ticker.")

# top_gainers = get_top_market_movers(direction='gainers')
# print("Top Gainers:")
# for mover in top_gainers:
#     print(f"{mover['Ticker']}: {mover['Change (%)']:.2f}% change, Volume: {mover['Volume']}")

# # Example usage: Get top losers
# top_losers = get_top_market_movers(direction='losers')
# print("Top Losers:")
# for mover in top_losers:
#     print(f"{mover['Ticker']}: {mover['Change (%)']:.2f}% change, Volume: {mover['Volume']}")

# # Example usage: Get top gainers and their news
# get_top_movers_news(direction='gainers')

# # Example usage: Get top losers and their news
# get_top_movers_news(direction='losers')