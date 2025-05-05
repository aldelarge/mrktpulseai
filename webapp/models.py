from . import db
from flask_login import UserMixin
import secrets  # For generating secure random tokens
from datetime import datetime, timedelta
from sqlalchemy import DateTime


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    stripe_customer_id = db.Column(db.String(255), unique=True)  # Store Stripe customer ID
    subscription_status = db.Column(db.String(50), default='inactive')  # 'active', 'free', 'inactive'

    reset_token = db.Column(db.String(255), nullable=True)  # Field to store reset token
    reset_token_expiration = db.Column(db.DateTime, nullable=True)  # Field to store expiration time

    def generate_reset_token(self):
        token = secrets.token_urlsafe(16)  # Generate a secure token
        self.reset_token = token
        self.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        db.session.commit()  # Commit the change to the database
        return token


    def get_id(self):
        return str(self.id)

class StockNews(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(10), db.ForeignKey('stock_data.symbol'), nullable=True)  # 🔄 Fix ForeignKey
    headline = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(255), nullable=False)
    rankscore = db.Column(db.Float, nullable=True)
    news_type = db.Column(db.String(50), nullable=True)  # e.g., "Breaking", "Market Update"
    date_published = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    url = db.Column(db.String(500), nullable=False)

    def __repr__(self):
        return f"<StockNews {self.headline[:50]}... from {self.source}>"

class StockData(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  # ✅ Ensure Auto-increment
    symbol = db.Column(db.String(10), unique=True, nullable=False)  # ✅ Ensure uniqueness
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    change_percent = db.Column(db.Float, nullable=False)
    change_amount = db.Column(db.Float, nullable=False)
    volume = db.Column(db.BigInteger, nullable=True)
    category = db.Column(db.String(50), nullable=False)  # 'gainer' or 'loser'
    date_fetched = db.Column(db.DateTime, default=db.func.current_timestamp())
    strategy_tags = db.Column(db.String(200), nullable=True)  # e.g. "breakout,momentum"
    strategy_score = db.Column(db.Integer, nullable=True)
    strategy_label = db.Column(db.String(100), nullable=True)  # ✅ New field for labeling multi-signal setups
    days_in_a_row = db.Column(db.Integer, default=1)
    confidence_score = db.Column(db.Float, nullable=True)
    sentiment = db.Column(db.String(20), nullable=True)  # "bullish", "bearish", or "neutral"
    summary_last_updated = db.Column(DateTime(timezone=True), nullable=True)


    # ✅ Store summary inside StockData instead of separate model
    summary_text = db.Column(db.Text, nullable=True)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


    # Add this relationship
    news = db.relationship('StockNews', backref='stock', lazy=True)

class UserSavedStock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    stock_symbol = db.Column(db.String(10), db.ForeignKey('stock_data.symbol'), nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('saved_stocks', lazy=True))
    stock = db.relationship('StockData', backref=db.backref('saved_by_users', lazy=True))