from flask import request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request


def ip_only():
    return request.remote_addr or "unknown"


def email_only():
    verify_jwt_in_request(optional=True)
    email = get_jwt_identity() or "unauthenticated"
    return f"{email}"


def ip_email_combined():
    ip = request.remote_addr or "unknown"
    verify_jwt_in_request(optional=True)
    email = get_jwt_identity() or "unauthenticated"
    return f"{ip}:{email}"
