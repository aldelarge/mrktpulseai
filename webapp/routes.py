from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, current_app, session
from flask_login import login_user, login_required, current_user
from flask_login import logout_user
from .models import User, StockNews, StockData, UserSavedStock
from . import db, bcrypt
from .forms import SignUpForm, LoginForm, ResetPasswordForm, ForgotPasswordForm, ContactForm
import stripe
from flask import request, session
from config import Config  # Use relative import to access config from the root folder
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash
from sendgrid.helpers.mail import Mail, Email, To, Content
import sendgrid
from flask_mail import Message
import string
import random
from . import sg, mail
import secrets  # For better cryptographic token generation
from markdown import convert_markdown_to_html
import re
import time


routes = Blueprint('routes', __name__)
@routes.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))  # Redirect to home if logged in
    return render_template('landing.html')

@routes.route("/profile")
@login_required  # Ensures only logged-in users can access the profile page
def profile():
    return render_template("profile.html", user=current_user)

@routes.route('/home')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('routes.landing'))  # Redirect guests to landing page
    
     # ✅ Pull and clear the session flag for a new paid user
    new_signup = session.pop('new_signup', False)

    today = datetime.utcnow().date()
    strategy_stocks = StockData.query.filter(
        StockData.category == "strategy",
        db.func.date(StockData.last_updated) == today
    ).order_by(StockData.strategy_score.desc()).all()
    
    # Group by strategy_label
    grouped = {}
    for stock in strategy_stocks:
        label = stock.strategy_label or "Unlabeled"
        if label not in grouped:
            grouped[label] = []
        grouped[label].append(stock)

    # Trending news first (rankscore is present)
    trending_news = StockNews.query.filter(StockNews.rankscore.isnot(None))\
        .order_by(StockNews.rankscore.desc(), StockNews.date_published.desc()).all()


    # Stock-specific news (no rankscore)
    stock_news = StockNews.query.filter(StockNews.rankscore.is_(None))\
        .order_by(StockNews.date_published.desc()).all() 
    
    gainers = StockData.query.filter(StockData.category.contains("gainer")).order_by(StockData.change_percent.desc()).limit(5).all()
    losers = StockData.query.filter(StockData.category.contains("loser")).order_by(StockData.change_percent).limit(5).all()   
    market_data = StockData.query.filter_by(category="market").order_by(StockData.change_percent.desc()).limit(10).all()
    top_traded = StockData.query.filter(StockData.category.contains("top_traded")).order_by(StockData.volume.desc()).all()
    saved_stocks = UserSavedStock.query.filter_by(user_id=current_user.id).all()
    stocks_list = [stock.stock_symbol for stock in saved_stocks]

    # Fetch StockData for each saved stock
    user_stocks_data = {}
    for symbol in stocks_list:
        stock_data = StockData.query.filter_by(symbol=symbol).first()
        if stock_data:
            # Get latest news (limit 3 per stock)
            stock_news = StockNews.query.filter_by(symbol=symbol)\
                .order_by(StockNews.date_published.desc()).limit(10).all()

            user_stocks_data[symbol] = {
                "price": stock_data.price,
                "change_percent": stock_data.change_percent,
                "volume": stock_data.volume,
                "summary": stock_data.summary_text,
                "news": stock_news
            }

   # Stock news dictionary for top-traded stocks
    stock_news_dict = {}
    for stock in top_traded:
        stock_news_dict[stock.symbol] = StockNews.query.filter(
            StockNews.symbol.ilike(f"%{stock.symbol}%"),  # Match stock symbol
            StockNews.rankscore.is_(None)  # Exclude trending news
        ).order_by(StockNews.date_published.desc()).limit(3).all()

    user = User.query.filter_by(id=current_user.id).first()
    subscription_status = user.subscription_status  # 'active', 'inactive', or 'canceled'

    return render_template(
        'home.html',
        grouped=grouped,
        stocks_list=stocks_list,
        user_stocks_data=user_stocks_data,
        trending_news=trending_news,
        market_data=market_data,
        stock_news=stock_news,
        stock_news_dict=stock_news_dict,
        gainers=gainers,
        losers=losers,
        top_traded=top_traded,
        user=current_user,
        subscription_status=subscription_status,
        new_signup=new_signup)

@routes.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()

    if form.validate_on_submit():
        email = form.email.data.lower().strip()
        plan = request.form.get('plan') or 'paid'
        print(f"📩 Plan received from form: {plan}")
        
        # Check if the email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists! Please log in.', 'info')
            return redirect(url_for('routes.login'))
        
        # Create a new user with appropriate subscription status
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        subscription_status = 'free'

        user = User(email=email, password=hashed_password, subscription_status=subscription_status)
        db.session.add(user)
        db.session.commit()
        session['new_signup'] = True
        login_user(user)
        flash('You have been logged in automatically after signing up!', 'success')
        print(f"🆕 New signup: {email} | Plan selected: {plan} | Status set: {subscription_status}") 

        # Optional: redirect to Stripe for paid users only
        if plan == 'paid':
            return redirect(url_for('routes.create_checkout_session', user_id=user.id))

        # Otherwise, go to dashboard directly
        return redirect(url_for('routes.home'))

    return render_template('signup.html', form=form)

@routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.lower().strip()  # ✅ Normalize email
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('routes.home'))
        else:
            flash('Login failed. Check email and password.', 'danger')
    return render_template('login.html', form=form)

@routes.route('/logout')
@login_required  # This ensures that only logged-in users can log out
def logout():
    logout_user()  # Log the user out
    flash('You have been logged out.', 'info')  # Optional: Flash a message to the user
    return redirect(url_for('routes.landing'))  # Redirect to the landing page (or wherever you want)

@routes.route("/about")
def about():
    return render_template("about.html")

@routes.route('/checkout')
@login_required  # Make sure only logged-in users can access this page
def checkout():
    """Render the checkout page with the Stripe button."""
    return render_template("checkout.html")

# Route for creating the Stripe checkout session
@routes.route("/create-checkout-session/<int:user_id>", methods=["POST", "GET"])
def create_checkout_session(user_id):
    YOUR_DOMAIN = "http://mrktpulseai.com"  # Change to your actual domain in production

    try:
        # Make sure the secret key is set
        stripe.api_key = Config.STRIPE_SECRET_KEY  # Ensure it's set here, just in case
        
        # Get the price ID from Stripe dashboard (replace this)
        price_id = "price_1R46kRDy1cSJj1Eayc02zGCi"
        
        # Create a checkout session for the subscription
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                },
            ],
            mode="subscription",  # Subscription mode
            success_url=f"{YOUR_DOMAIN}/success?session_id={{CHECKOUT_SESSION_ID}}&user_id={user_id}",
            cancel_url=f"{YOUR_DOMAIN}/cancel",
        )

        return redirect(checkout_session.url)  # Redirect to Stripe Checkout page

    except Exception as e:
        return str(e), 400

@routes.route("/success")
def success():
    session_id = request.args.get('session_id')
    user_id = request.args.get('user_id')
    user = User.query.get(user_id)

    # Ensure the session ID exists
    if not session_id or not user:
        flash('Error: Invalid session or user.', 'danger')
        return redirect(url_for('routes.home'))

    # Retrieve the checkout session from Stripe
    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
    except stripe.error.StripeError as e:
        flash('Error retrieving payment details.', 'danger')
        return redirect(url_for('routes.home'))

    # Update the user's stripe_customer_id and subscription_status
    user.stripe_customer_id = checkout_session.customer
    user.subscription_status = "active"
    db.session.commit()

    # Log the user in automatically if they are not already logged in
    if not current_user.is_authenticated:
        login_user(user)
        flash('Logged in successfully!', 'success')  # Optional: Confirm the login success

    # Flash success message
    flash('Payment successful! Your subscription is now active.', 'success')

    # Set a session flag to track new signup
    session['new_signup'] = True

    return redirect(url_for('routes.home'))

# Route for canceling the payment
@routes.route("/cancel")
def cancel():
    """Render a cancel page if the user cancels the payment."""
    flash('Payment cancelled. Please try again.', 'danger')
    return redirect(url_for('routes.landing'))

@routes.route('/cancel_subscription', methods=['GET', 'POST'])
@login_required
def cancel_subscription():
    stripe.api_key = Config.STRIPE_SECRET_KEY
    user = User.query.filter_by(id=current_user.id).first()

    if request.method == 'POST':

        if user.subscription_status == 'free':
            user.subscription_status = 'inactive'
            db.session.commit()
            flash("You've been unsubscribed from daily emails.", 'info')
            return redirect(url_for('routes.home'))


        # Check if the user has a stripe_customer_id (this ID identifies the customer in Stripe)
        if user.stripe_customer_id:  # Ensure user has a stripe_customer_id
            try:
                # Log the user details for debugging
                print(f"Attempting to cancel subscription for user: {user.email} with Stripe Customer ID: {user.stripe_customer_id}")

                # Retrieve all subscriptions associated with the Stripe customer
                subscriptions = stripe.Subscription.list(customer=user.stripe_customer_id)

                if subscriptions.data:
                    # Cancel all active subscriptions for the user
                    for subscription in subscriptions.data:
                        print(f"Cancelling subscription with ID: {subscription.id}")  # Log the subscription ID
                        stripe.Subscription.delete(subscription.id)  # Cancel the subscription in Stripe

                    # Update the user's subscription status in the database to 'inactive'
                    user.subscription_status = 'inactive'  # Or 'canceled' if you prefer
                    db.session.commit()  # Commit the changes to the database

                    flash('Your subscription has been canceled successfully.', 'success')

                    # Log success for debugging
                    print(f"Subscription successfully canceled for {user.email}")
                else:
                    flash('No active subscriptions found for your account.', 'danger')

            except stripe.error.StripeError as e:
                # Handle Stripe errors (e.g., invalid customer ID or subscription issues)
                flash('There was an error canceling your subscription. Please try again later.', 'danger')
                print(f"Error canceling subscription: {e}")
                return redirect(url_for('routes.home'))  # Redirect back to home page in case of error

            except Exception as e:
                # Catch other errors
                flash("An unexpected error occurred. Please try again later.", 'danger')
                print(f"Unexpected error: {e}")
                return redirect(url_for('routes.home'))

        else:
            flash('No Stripe customer ID found for your account.', 'danger')

        return redirect(url_for('routes.home'))  # Redirect back to home page after cancellation

    return render_template('cancel_subscription.html') 

@routes.route('/webhook', methods=['POST'])
def stripe_webhook():
    endpoint_secret = Config.STRIPE_WEBHOOK_KEY
    stripe.api_key = Config.STRIPE_SECRET_KEY
    
    payload = request.get_data(as_text=True)  # Get the raw body of the request
    sig_header = request.headers.get('Stripe-Signature')  # Get the Stripe-Signature header

    # Verify the webhook signature to ensure the event is coming from Stripe
    try:
        # This will raise an exception if the signature is invalid
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Signature verification failed', 400

    # Handle the customer.subscription.deleted event
    if event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']  # Contains the subscription object
        customer_id = subscription['customer']  # Get the customer ID
        user = User.query.filter_by(stripe_customer_id=customer_id).first()  # Find the user by Stripe customer ID

        if user:
            # Mark the user as inactive in your database
            user.subscription_status = 'inactive'  # Or 'canceled' depending on your preference
            db.session.commit()  # Commit the change to the database
            print(f"Subscription canceled for {user.email}")  # You can also log this if needed
        else:
            print(f"User not found for customer ID {customer_id}")

    # Handle other events as necessary (e.g., invoice.payment_succeeded, etc.)

    # Return a 200 response to acknowledge receipt of the event
    return jsonify(success=True)

@routes.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    form = ForgotPasswordForm()

    if request.method == 'POST' and form.validate_on_submit():
        email = form.email.data
        user = User.query.filter_by(email=email).first()

        if user:
            reset_token = secrets.token_urlsafe(32)
            reset_token_expiration = datetime.utcnow() + timedelta(hours=1)

            user.reset_token = reset_token
            user.reset_token_expiration = reset_token_expiration
            db.session.commit()

            reset_url = url_for('routes.reset_password', token=reset_token, _external=True)

            from_email = Email("no-reply@mrktpulseai.com")
            to_email = To(email)
            subject = "Password Reset Request"
            
            dynamic_data = {
                "user_name": user.email,
                "reset_url": reset_url
            }
            
            message = Mail(from_email, to_email, subject)
            message.dynamic_template_data = dynamic_data
            message.template_id = "d-2c63bcea5f604f8cb13cbdfb05fc08a7"  # Replace with your SendGrid template ID

            try:
                response = sg.send(message)
                flash("Password reset link sent. Please check your email.", "success")
                return redirect(url_for('routes.login'))
            except Exception as e:
                flash("There was an error sending the email. Please try again.", "danger")
                print(f"Error: {e}")
        else:
            flash("No account found with that email address.", "danger")

    return render_template('forgot_password.html', form=form)

@routes.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user = User.query.filter_by(reset_token=token).first()

    if not user:
        flash('That is an invalid or expired token', 'danger')
        return redirect(url_for('routes.forgot_password'))
    
    if user.reset_token_expiration < datetime.utcnow():
        flash('The reset token has expired', 'danger')
        return redirect(url_for('routes.forgot_password'))

    form = ResetPasswordForm()  # Initialize the reset password form

    if form.validate_on_submit():
        new_password = form.password.data
        user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.reset_token = None  # Clear the reset token after resetting the password
        user.reset_token_expiration = None  # Clear the expiration
        db.session.commit()

        flash('Your password has been updated!', 'success')
        return redirect(url_for('routes.login'))

    return render_template('reset_password.html', form=form, token=token)

# Save a stock for the user
@routes.route("/save_stock", methods=["POST"])
@login_required
def save_stock():
    from webapp.models import db, StockData, UserSavedStock
    from daily_data import get_stock_snapshot
    data = request.get_json()
    symbol = data.get("symbol", "").upper().strip()

    if not symbol:
        return jsonify({"message": "Stock symbol is required."}), 400

    with current_app.app_context():
        # ✅ Check stock count limit
        max_stocks_allowed = 5
        user_stock_count = UserSavedStock.query.filter_by(user_id=current_user.id).count()

        if user_stock_count >= max_stocks_allowed:
            return jsonify({
                "message": f"You can only track up to {max_stocks_allowed} stocks. Please remove one before adding more."
            }), 400

        stock_entry = StockData.query.filter_by(symbol=symbol).first()

        if not stock_entry:
            print(f"⚠️ {symbol} not found in StockData. Fetching snapshot...")
            snapshot = get_stock_snapshot(symbol)

            if not snapshot:
                return jsonify({"message": f"Stock {symbol} could not be found or fetched."}), 404

            stock_entry = StockData.query.filter_by(symbol=symbol).first()

        existing_saved_stock = UserSavedStock.query.filter_by(user_id=current_user.id, stock_symbol=symbol).first()
        if existing_saved_stock:
            return jsonify({"message": "Stock already saved."}), 200

        saved_stock = UserSavedStock(user_id=current_user.id, stock_symbol=symbol, date_added=datetime.now(timezone.utc))
        db.session.add(saved_stock)
        db.session.commit()

        print(f"✅ Stock {symbol} saved for user {current_user.id}")
        return jsonify({"message": f"Stock {symbol} saved successfully."}), 200

    
@routes.route("/remove_stock", methods=["POST"])
@login_required
def remove_stock():
    """Allows users to remove a stock from their saved list."""
    data = request.json
    stock_symbol = data.get("symbol", "").upper()

    if not stock_symbol:
        return jsonify({"error": "No stock symbol provided"}), 400

    stock = UserSavedStock.query.filter_by(user_id=current_user.id, stock_symbol=stock_symbol).first()
    if not stock:
        return jsonify({"error": "Stock not found in saved list"}), 404

    db.session.delete(stock)
    db.session.commit()

    return jsonify({"message": f"Stock {stock_symbol} removed successfully"}), 200

@routes.route("/landing_snapshot/<symbol>")
def landing_snapshot(symbol):
    stock = StockData.query.filter_by(symbol=symbol.upper()).first()
    if not stock:
        return jsonify({"error": "Stock not found"}), 404

    raw_html = convert_markdown_to_html(stock.summary_text or "")
    stripped_html = re.sub(r'<h[1-6][^>]*>.*?</h[1-6]>', '', raw_html, flags=re.DOTALL)

    return jsonify({
        "symbol": stock.symbol,
        "price": f"${stock.price:.2f}",
        "change_percent": f"{stock.change_percent:+.2f}%",
        "summary_text": stripped_html.strip()
    })

@routes.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()

    if request.method == 'POST':
        cooldown = 60 * 5  # 5 minutes
        last_sent = session.get('last_contact_time')

        if last_sent and time.time() - last_sent < cooldown:
            flash("Please wait a few minutes before sending another message.", "warning")
            return render_template('contact.html', form=form)

        if form.validate_on_submit():
            user_email = form.email.data
            subject = form.subject.data
            message = form.message.data
            full_subject = f"[Contact Form] {subject}"
            body = f"From: {user_email}\n\n{message}"

            msg = Message(
                subject=full_subject,
                sender="newsletter@mrktpulseai.com",
                recipients=["newsletter@mrktpulseai.com"],
                body=body,
                reply_to=user_email
            )
            mail.send(msg)

            session['last_contact_time'] = time.time()
            flash("Thanks for your message! We'll get back to you soon.", "success")
            return redirect(url_for('routes.contact'))

    return render_template('contact.html', form=form)