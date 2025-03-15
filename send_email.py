import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Content
from flask import Flask
import os
from dotenv import load_dotenv

app = Flask(__name__)

load_dotenv()
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# SendGrid email sending function
def send_email(subject, body, recipient):
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
    from_email = Email("newsletter@mrktpulseai.com")  # This is your SendGrid subdomain email
    to_email = To(recipient) 

    content = Content("text/html", body)
    mail = Mail(from_email, to_email, subject, content)

    try:
        response = sg.send(mail)
        return f"Email sent to {recipient}!"
    except Exception as e:
        return f"Error: {str(e)}"

# Testing route to send an email
def send_test_email():
    subject = "Test Email from Your App"
    body = "This is a test email to verify that SendGrid is working."
    recipient = 'jacobffritz@gmail.com'  # Replace with the recipient's email
    return send_email(subject, body, recipient)

# Call the test email function