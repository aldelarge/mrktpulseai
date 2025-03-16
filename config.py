import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY')
    # Update the database URI for PostgreSQL
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'postgresql://localhost/stock_newsletter')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    WTF_CSRF_ENABLED = True
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
    STRIPE_WEBHOOK_KEY = os.getenv("STRIPE_WEBHOOK_KEY")
