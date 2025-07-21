from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
    get_jwt,
    verify_jwt_in_request,
    set_refresh_cookies,
    unset_refresh_cookies,
)
from app.models.user import get_user_by_email, add_user, check_password, update_password
from app.blacklist import add_to_blacklist, is_token_blacklisted
from app.utils.rate_limit_keys import ip_only, ip_email_combined
from app.utils.otp import (
    generate_otp,
    save_otp,
    verify_otp,
    is_email_verified,
    clear_email_verification,
    save_org_id,
    get_org_id,
    clear_org_id,
)
from app.utils.forgot_password import send_reset_email, verify_reset_token
from app.services.mail_util import send_mail
from app.extensions import limiter
from app.config import Config
from app.utils.access_control import jwt_required
from app.utils.db_utils import get_emp_id_from_firestore, ensure_employee_in_firestore

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per hour", key_func=ip_email_combined)
@limiter.limit("20 per day", key_func=ip_email_combined)
def start_registration():
    data = request.get_json()
    email = data.get("email")
    org_id = request.args.get("org_id")
    if not email or not org_id:
        return jsonify({"msg": "Email and org_id are required"}), 400
    if get_user_by_email(email):
        return jsonify({"msg": "Email already registered"}), 409
    otp = generate_otp()
    save_otp(email, otp)
    save_org_id(email, org_id)
    html = f"<p>Your OTP is <strong>{otp}</strong>. It expires in 1 minutes.</p>"
    send_mail(email, "Verify your email", html)
    return jsonify({"msg": "OTP sent to email"}), 200


@auth_bp.route("/verify-otp", methods=["POST"])
@limiter.limit("5 per hour", key_func=ip_email_combined)
@limiter.limit("20 per day", key_func=ip_email_combined)
def verify_email_otp():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")
    if not email or not otp:
        return jsonify({"msg": "Email and OTP are required"}), 400
    result = verify_otp(email, otp)
    if result == "expired":
        return jsonify({"msg": "OTP expired"}), 410
    elif result == "invalid":
        return jsonify({"msg": "Invalid OTP"}), 401
    elif result == "valid":
        return jsonify({"msg": "OTP verified"}), 200
    return jsonify({"msg": "Unexpected error"}), 500


@auth_bp.route("/complete-registration", methods=["POST"])
@limiter.limit("5 per hour", key_func=ip_only)
@limiter.limit("20 per day", key_func=ip_only)
def complete_registration():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400
    if get_user_by_email(email):
        return jsonify({"msg": "Email already registered"}), 409
    if not is_email_verified(email):
        return jsonify({"msg": "Email not verified"}), 403

    org_id = get_org_id(email)
    if org_id is None:
        return jsonify({"msg": "Organization info expired"}), 410

    # Add user to auth DB
    add_user(email, password, org_id)
    clear_email_verification(email)
    clear_org_id(email)

    user = get_user_by_email(email)
    role = user.get("role", "employee")

    # Ensure employee is added to Firestore and fetch emp_id
    emp_id = ensure_employee_in_firestore(email, org_id)

    access_token = create_access_token(
        identity=email,
        additional_claims={"org_id": org_id, "role": role, "emp_id": emp_id},
    )
    refresh_token = create_refresh_token(
        identity=email,
        additional_claims={"org_id": org_id, "role": role, "emp_id": emp_id},
    )

    response = jsonify({"msg": "Registration complete", "access_token": access_token})
    set_refresh_cookies(response, refresh_token)
    return response, 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per hour", key_func=ip_email_combined)
@limiter.limit("20 per day", key_func=ip_email_combined)
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = get_user_by_email(email)
    if not user or not check_password(user["hashed_password"], password):
        return jsonify({"msg": "Invalid credentials"}), 401

    org_id = user.get("org_id")
    role = user.get("role", "employee")
    emp_id = get_emp_id_from_firestore(org_id, email)

    access_token = create_access_token(
        identity=email,
        additional_claims={"org_id": org_id, "role": role, "emp_id": emp_id},
    )
    refresh_token = create_refresh_token(
        identity=email,
        additional_claims={"org_id": org_id, "role": role, "emp_id": emp_id},
    )

    response = jsonify(access_token=access_token)
    set_refresh_cookies(response, refresh_token)
    return response


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    email = get_jwt_identity()
    user = get_user_by_email(email)

    if not user:
        return jsonify({"msg": "User not found"}), 404

    return jsonify(
        {
            # "id": str(user["id"]),
            "name": user["email"].split("@")[0],
            "email": user["email"],
            "role": user.get("role", "employee"),
        }
    )


@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour", key_func=ip_email_combined)
@limiter.limit("10 per day", key_func=ip_email_combined)
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    send_reset_email(email)
    return jsonify({"message": "Password reset link sent"}), 200


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per hour", key_func=ip_email_combined)
@limiter.limit("10 per day", key_func=ip_email_combined)
def reset_password(token):
    email = verify_reset_token(token)
    if not email:
        return jsonify({"error": "The link is invalid or has expired."}), 400

    if request.method == "GET":
        return jsonify({"message": "Valid reset token", "email": email}), 200

    data = request.get_json()
    if not data or "password" not in data:
        return jsonify({"error": "Password is required."}), 400

    new_password = data["password"]
    success = update_password(email, new_password)

    if success:
        return jsonify({"message": "Password has been reset successfully."}), 200
    else:
        return jsonify({"error": "Password reset failed. User may not exist."}), 500


@auth_bp.route("/logout", methods=["POST"])
@jwt_required(locations=["headers", "cookies"])
def logout():
    jwt_data = get_jwt()
    jti = jwt_data["jti"]
    token_type = jwt_data["type"]

    if token_type == "access":
        expiration = int(Config.JWT_ACCESS_TOKEN_EXPIRES)
    else:
        expiration = int(Config.JWT_REFRESH_TOKEN_EXPIRES)

    add_to_blacklist(jti, token_type, expiration)

    try:
        verify_jwt_in_request(locations=["cookies"])
        jwt_data = get_jwt()
        refresh_jti = jwt_data["jti"]
        refresh_exp = int(Config.JWT_REFRESH_TOKEN_EXPIRES)
        add_to_blacklist(refresh_jti, "refresh", refresh_exp)
    except Exception:
        pass

    response = jsonify({"msg": "Access and refresh tokens blacklisted"})
    unset_refresh_cookies(response)
    return response


@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True, locations=["cookies"])
def refresh():
    jti = get_jwt()["jti"]
    if is_token_blacklisted(jti):
        return (
            jsonify({"msg": "Refresh token is blacklisted. Please login again."}),
            401,
        )

    current_user_email = get_jwt_identity()
    claims = get_jwt()

    access_token = create_access_token(
        identity=current_user_email,
        additional_claims={
            "org_id": claims["org_id"],
            "role": claims["role"],
            "emp_id": claims["emp_id"],
        },
    )

    return jsonify(access_token=access_token), 200
