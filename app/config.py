from dotenv import load_dotenv

load_dotenv()

import os


class Config:
    FRONTEND_URL = os.getenv("FRONTEND_URL")
    SELF_URL = os.getenv("SELF_URL")
    SECRET_KEY = os.getenv("SECRET_KEY")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    # Access token expiration in seconds (15 minutes)
    JWT_ACCESS_TOKEN_EXPIRES = 900
    # Refresh token expiration in seconds (7 days)
    JWT_REFRESH_TOKEN_EXPIRES = 3600 * 24 * 7
    SALT = os.getenv("SALT")
    REDIS_URL = os.getenv("REDIS_URL")
    REDIS_DB_LIMITER = 0
    REDIS_DB_BLACKLIST = 1
    REDIS_DB_OTP = 2
    # OTP expiration in seconds (1 minutes)
    OTP_TTL = 60
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_COOKIE_SECURE = False  # TODO Change to True for production
    JWT_COOKIE_SAMESITE = "Lax"
    JWT_COOKIE_CSRF_PROTECT = True
    EMAIL_HOST = os.getenv("EMAIL_HOST")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
