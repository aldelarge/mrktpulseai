from . import db
from flask_login import UserMixin
import secrets  # For generating secure random tokens
from datetime import datetime, timedelta


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    stripe_customer_id = db.Column(db.String(255), unique=True)  # Store Stripe customer ID
    subscription_status = db.Column(db.String(50), default='inactive')  # 'active', 'inactive', etc.

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
