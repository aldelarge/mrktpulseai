from datetime import datetime, time
import pytz
from daily_data import (
    fetch_and_store_top_traded,
    fetch_and_store_gainers_losers,
    fetch_and_store_top_news,
    fetch_market_snapshot,
    update_user_saved_stocks,
    find_market_breakouts,
    delete_old_news,
)

def is_eastern_between(start_hour, end_hour):
    eastern = pytz.timezone('US/Eastern')
    now_eastern = datetime.now(eastern).time()
    return time(start_hour, 0) <= now_eastern < time(end_hour, 0)

def is_weekday():
    eastern = pytz.timezone('US/Eastern')
    now_eastern = datetime.now(eastern)
    return now_eastern.weekday() < 5  # Mon–Fri

from webapp import create_app  # Import your Flask app factory


app = create_app()  # Ensure this matches your Flask factory method

if __name__ == "__main__":
    with app.app_context():
        if is_eastern_between(5, 23):  # 23 = 11PM
            delete_old_news(days_old=1)
            fetch_and_store_top_news()
        else:
            print("🕒 Outside news update window. Skipping news tasks.")

        # ✅ Only run stock stuff during weekday market hours (8AM to 5PM ET)
        if is_weekday() and is_eastern_between(9, 17):
            fetch_and_store_gainers_losers()
            update_user_saved_stocks()
            snapshot = fetch_market_snapshot()
            top_traded = fetch_and_store_top_traded(snapshot=snapshot)
            # breakouts = find_market_breakouts(snapshot=snapshot)
        else:
            print("📉 Outside stock task hours. Skipping stock-related tasks.")