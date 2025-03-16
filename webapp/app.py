from webapp import create_app, db
from webapp.models import User  # Ensure the models are imported
import stripe
from config import Config  # To get your Stripe keys

# Initialize the app
app = create_app()
# Set a secret key to enable session management (this should be unique and kept secret)
app.secret_key = Config.SECRET_KEY
# Initialize Stripe with the secret key
stripe.api_key = Config.STRIPE_SECRET_KEY


# Create tables if they don't exist
with app.app_context():
    db.create_all()

# if __name__ == "__main__":
#     app.run(debug=True)
