from flask import Blueprint, render_template, redirect, url_for, flash, jsonify
from flask_login import login_user, login_required, current_user
from flask_login import logout_user
from .models import User
from . import db, bcrypt
from .forms import SignUpForm, LoginForm, ResetPasswordForm, ForgotPasswordForm
import stripe
from flask import request
from config import Config  # Use relative import to access config from the root folder
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from sendgrid.helpers.mail import Mail, Email, To, Content
import sendgrid
import string
import random
from . import sg
import secrets  # For better cryptographic token generation





routes = Blueprint('routes', __name__)
@routes.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('routes.home'))  # Redirect to home if logged in
    return render_template('landing.html')

@routes.route('/home')
@login_required
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('routes.landing')) 

    user = User.query.filter_by(id=current_user.id).first()

    # Get subscription status
    subscription_status = user.subscription_status  # 'active', 'inactive', or 'canceled'

    return render_template('home.html', user=current_user, subscription_status=subscription_status)

@routes.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()

    if form.validate_on_submit():
        email = form.email.data

        # Check if the email already exists in the database
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists! Please log in.', 'info')
            return redirect(url_for('routes.login'))  # Redirect to login if the user is already signed up
        
        # Create a new user
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        # Log the user in automatically after signup
        login_user(user)
        flash('You have been logged in automatically after signing up!', 'success')

        # Get the next parameter if it exists
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)  # Redirect to the next page (e.g., the success page)
        

        # After creating the user, we initiate the checkout session
        return redirect(url_for('routes.create_checkout_session', user_id=user.id))

    return render_template('signup.html', form=form)

@routes.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
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

@routes.route('/checkout')
@login_required  # Make sure only logged-in users can access this page
def checkout():
    """Render the checkout page with the Stripe button."""
    return render_template("checkout.html")

# Route for creating the Stripe checkout session
@routes.route("/create-checkout-session/<int:user_id>", methods=["POST", "GET"])
def create_checkout_session(user_id):
    YOUR_DOMAIN = "http://127.0.0.1:5000"  # Change to your actual domain in production

    try:
        # Make sure the secret key is set
        stripe.api_key = Config.STRIPE_SECRET_KEY  # Ensure it's set here, just in case
        
        # Get the price ID from Stripe dashboard (replace this)
        price_id = "price_1R1ug4Dy1cSJj1EaSETKHVvG"
        
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
    user = User.query.filter_by(id=current_user.id).first()

    if request.method == 'POST':
        # Update the subscription status to 'canceled'
        user.subscription_status = 'inactive'
        db.session.commit()  # Commit the change to the database

        flash('Your subscription has been canceled successfully.', 'success')
        return redirect(url_for('routes.home'))  # Redirect back to home page

    return render_template('cancel_subscription.html')

@routes.route('/webhook', methods=['POST'])
def stripe_webhook():
    stripe.api_key = Config.STRIPE_SECRET_KEY  # Ensure it's set here, just in case

    # The endpoint secret you received when registering your webhook in Stripe
    endpoint_secret = 'whsec_...your-secret-key...'

    # Retrieve the payload and signature from the request
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')

    # Verify the webhook signature to ensure it's from Stripe
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return 'Signature verification failed', 400

    # Handle the event type
    if event['type'] == 'invoice.payment_succeeded':
        # Payment succeeded, activate subscription
        invoice = event['data']['object']  # Contains a stripe.Invoice object
        customer_id = invoice['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()

        if user:
            user.subscription_status = 'active'
            db.session.commit()
            print(f"Subscription activated for {user.email}")
        else:
            print("User not found")

    elif event['type'] == 'invoice.payment_failed':
        # Payment failed, deactivate subscription
        invoice = event['data']['object']
        customer_id = invoice['customer']
        user = User.query.filter_by(stripe_customer_id=customer_id).first()

        if user:
            user.subscription_status = 'inactive'
            db.session.commit()
            print(f"Subscription deactivated for {user.email}")
        else:
            print("User not found")

    # More event types can be handled as needed

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