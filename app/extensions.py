from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_redis import FlaskRedis
from app.config import Config

jwt = JWTManager()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000 per hour"],
    storage_uri=Config.REDIS_URL + "/" + str(Config.REDIS_DB_LIMITER),
    strategy="fixed-window",
)
redis_blacklist = FlaskRedis()
redis_otp = FlaskRedis()


def init_extensions(app):
    jwt.init_app(app)
    limiter.init_app(app)
    redis_blacklist.init_app(app, db=Config.REDIS_DB_BLACKLIST)
    redis_otp.init_app(app, db=Config.REDIS_DB_OTP)
