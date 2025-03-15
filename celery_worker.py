from celery import Celery
from celery.schedules import crontab
from main import main  # Import your existing main() function
from webapp import create_app
import pytz
import datetime  # <-- Add this import



# Setup Flask app and Celery configuration
app = create_app()
celery = Celery(app.name, broker='redis://localhost:6379/0')  # Using Redis as the broker

# Use California time zone (PST/PDT)
celery.conf.update(timezone='US/Pacific')

# This is your Celery task that will run your main function
@celery.task
def run_main():
    """Run the main function"""
    main()  # Call your existing main() function
    print("Main function completed.")
    
# Schedule the task to run every weekday at 4 PM ET
celery.conf.update(
    beat_schedule = {
        'run-main-task-at-10-10am-california-time': {
            'task': 'celery_worker.run_main',
            'schedule': crontab(minute=10, hour=20, day_of_week='mon-fri'),  # Run at 10:10 AM PST/PDT
        },
    }
)