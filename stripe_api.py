import stripe
from webapp import db
from webapp.models import User

# Assuming stripe.api_key is already set
def create_stripe_customer(user_email):
    customer = stripe.Customer.create(
        email=user_email,
        description="Subscription for Stock Market Newsletter",
    )
    return customer
