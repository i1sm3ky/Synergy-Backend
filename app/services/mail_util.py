import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import Config

EMAIL_HOST = Config.EMAIL_HOST
EMAIL_PORT = Config.EMAIL_PORT
EMAIL_HOST_USER = Config.EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = Config.EMAIL_HOST_PASSWORD


def send_mail(to_email, subject, html_body):
    print(to_email, subject, html_body)
    # msg = MIMEMultipart()
    # msg["From"] = EMAIL_HOST_USER
    # msg["To"] = to_email
    # msg["Subject"] = subject

    # msg.attach(MIMEText(html_body, "html"))

    # with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
    #     server.starttls()
    #     server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
    #     server.send_message(msg)
