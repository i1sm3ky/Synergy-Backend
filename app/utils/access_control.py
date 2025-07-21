from functools import wraps
from flask import jsonify, g

from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt,
    get_jwt_identity,
)
from jwt import ExpiredSignatureError


def jwt_required(func=None, **outer_kwargs):
    """
    Custom jwt_required decorator supporting: optional, refresh, fresh, and token locations.
    Compatible with older versions of flask_jwt_extended.
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            is_optional = outer_kwargs.get("optional", False)
            locations = outer_kwargs.get("locations", ["headers"])
            refresh_required = outer_kwargs.get("refresh", False)
            fresh_required = outer_kwargs.get("fresh", False)

            token_present = False
            try:
                # Attempt to verify token (if present in allowed locations)
                verify_jwt_in_request(
                    refresh=refresh_required, fresh=fresh_required, locations=locations
                )
                token_present = True
            except Exception as e:
                if not is_optional:
                    return jsonify({"error": f"Token error: {str(e)}"}), 401
                else:
                    return f(*args, **kwargs)  # Allow access without a token

            if token_present:
                try:
                    claims = get_jwt()

                    # Check token type
                    token_type = claims.get("type", "access")
                    if refresh_required and token_type != "refresh":
                        return jsonify({"error": "Refresh token required"}), 401
                    if not refresh_required and token_type == "refresh":
                        return jsonify({"error": "Access token required"}), 401

                    # Set context
                    g.org_id = claims.get("org_id")
                    g.user_id = get_jwt_identity()
                    g.role = claims.get("role")

                except ExpiredSignatureError:
                    return jsonify({"error": "Token has expired"}), 401
                except Exception as e:
                    return jsonify({"error": f"Token decode error: {str(e)}"}), 401

            return f(*args, **kwargs)

        return decorated

    if func:
        return decorator(func)
    return decorator


def requires_tier(required_tier):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not g.db:
                return jsonify({"msg": "Org DB not available"}), 500

            user_email = g.get("user_email") or g.get("identity")
            user = g.db.execute(
                "SELECT tier FROM employee_data WHERE email = %s", (user_email,)
            ).fetchone()

            if not user:
                return jsonify({"msg": "User not found in org DB"}), 404

            if user["tier"] != required_tier:
                return (
                    jsonify(
                        {
                            "msg": f"Insufficient tier. Required: {required_tier}, You have: {user['tier']}"
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def requires_tool(required_tool):
    """
    Decorator to ensure the logged-in user has access to a specific tool,
    based on org-specific data stored in g.db.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            if not identity:
                return jsonify({"msg": "Missing JWT identity"}), 401

            if not g.get("db"):
                return jsonify({"msg": "Org database not set"}), 500

            # Assuming `employee_data` table exists in org-specific DB
            try:
                result = g.db.execute(
                    "SELECT tools_access FROM employee_data WHERE email = :email",
                    {"email": identity},
                ).fetchone()
            except Exception as e:
                return jsonify({"msg": "Error querying org DB", "detail": str(e)}), 500

            if not result:
                return jsonify({"msg": "User not found in org DB"}), 404

            tools_str = result[0] or ""
            tools_list = tools_str.split("|")

            if required_tool not in tools_list:
                return (
                    jsonify(
                        {
                            "msg": f"Access denied. Tool '{required_tool}' is not available to your account."
                        }
                    ),
                    403,
                )

            return fn(*args, **kwargs)

        return wrapper

    return decorator
