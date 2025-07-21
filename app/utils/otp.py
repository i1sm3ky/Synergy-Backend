import random
from app.extensions import redis_otp
from app.config import Config


def generate_otp(length=6):
    return "".join(str(random.randint(0, 9)) for _ in range(length))


def save_otp(email, otp, ttl=Config.OTP_TTL):
    redis_otp.setex(f"OTP:{email}", ttl, otp)


def verify_otp(email, submitted_otp):
    key = f"OTP:{email}"
    stored_otp = redis_otp.get(key)

    if stored_otp is None:
        return "expired"

    if isinstance(stored_otp, bytes):
        stored_otp = stored_otp.decode()

    if stored_otp != submitted_otp:
        return "invalid"

    redis_otp.delete(key)
    redis_otp.setex(f"VERIFIED:{email}", Config.OTP_TTL, "true")
    return "valid"


def is_email_verified(email):
    return redis_otp.get(f"VERIFIED:{email}") is not None


def clear_email_verification(email):
    redis_otp.delete(f"VERIFIED:{email}")


def save_org_id(email, org_id, ttl=Config.OTP_TTL):
    redis_otp.setex(f"ORG_ID:{email}", 300, org_id)


def get_org_id(email):
    org_id = redis_otp.get(f"ORG_ID:{email}")
    if org_id is None:
        return None
    if isinstance(org_id, bytes):
        org_id = org_id.decode()
    return org_id


def clear_org_id(email):
    redis_otp.delete(f"ORG_ID:{email}")
