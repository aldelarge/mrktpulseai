from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate  # Import Migrate
from config import Config
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
import os 

# Initialize the extensions
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
migrate = Migrate()  # Initialize Migrate

SENDGRID_API_KEY = Config.SENDGRID_API_KEY
sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

def create_app():
    app = Flask(__name__)
    
    # Load the app configuration
    app.config.from_object(Config)

    # Set the SQLALCHEMY_DATABASE_URI based on DATABASE_URL from environment
    if 'DATABASE_URL' in os.environ:
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://")
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/stock_newsletter'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize the extensions
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)  # Initialize Flask-Migrate

    login_manager.login_view = 'routes.login'

    # Import routes and models
    from .routes import routes
    from .models import User

    # Register blueprints or routes
    app.register_blueprint(routes)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register custom Jinja filters
    def comma_format(value):
        try:
            return "{:,}".format(int(value))
        except (ValueError, TypeError):
            return value

    app.jinja_env.filters['comma_format'] = comma_format


    return app
