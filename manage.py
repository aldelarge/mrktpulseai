from webapp import create_app, db
from flask_migrate import Migrate
from flask.cli import FlaskGroup

app = create_app()  # Initialize the Flask app
migrate = Migrate(app, db)  # Initialize Flask-Migrate with the app and db

cli = FlaskGroup(create_app=create_app)  # Use Flask's built-in CLI

# Add Flask-Migrate commands to the Flask CLI
cli.add_command('db', migrate)

if __name__ == "__main__":
    cli()
