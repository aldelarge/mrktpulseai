from datetime import timezone
from webapp import create_app
from webapp.models import db, StockData

app = create_app()

def backfill_summary_timestamps_to_utc():
    with app.app_context():
        updated = 0
        stocks = StockData.query.filter(StockData.summary_last_updated != None).all()

        for stock in stocks:
            if stock.summary_last_updated.tzinfo is None:
                stock.summary_last_updated = stock.summary_last_updated.replace(tzinfo=timezone.utc)
                updated += 1

        db.session.commit()
        print(f"✅ Updated {updated} timestamps with UTC tzinfo.")

if __name__ == "__main__":
    backfill_summary_timestamps_to_utc()