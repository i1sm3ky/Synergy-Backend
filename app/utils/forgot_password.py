from itsdangerous import URLSafeTimedSerializer
from app.services.mail_util import send_mail
from app.config import Config
from app.models.user import get_user_by_email

SECRET_KEY = Config.SECRET_KEY
SALT = Config.SALT

serializer = URLSafeTimedSerializer(SECRET_KEY)


def generate_reset_token(email):
    return serializer.dumps(email, salt=SALT)


def verify_reset_token(token, expiration=300):
    try:
        email = serializer.loads(token, salt=SALT, max_age=expiration)
        return email
    except Exception:
        return None


def send_reset_email(email, base_url=Config.FRONTEND_URL):
    user = get_user_by_email(email)
    if user:
        token = generate_reset_token(email)
        reset_link = f"{base_url}/login/reset-password/{token}"
        html = f"""
        <p>Hi,</p>
        <p>Click the link below to reset your password:</p>
        <p><a href="{reset_link}">Reset Password</a></p>
        <p>This link will expire in 5 minutes.</p>
        """
        send_mail(email, "Reset Your Password", html)
