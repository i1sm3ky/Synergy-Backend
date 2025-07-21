from app.extensions import redis_blacklist


def is_token_blacklisted(jti):
    return redis_blacklist.get(f"BLACKLISTED:{jti}") is not None


def add_to_blacklist(jti, token_type, expiration_seconds):
    redis_blacklist.setex(f"BLACKLISTED:{jti}", expiration_seconds, token_type)
