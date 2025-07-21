from flask import Flask, g
from flask_cors import CORS
from app.config import Config
from app.extensions import init_extensions, jwt
from app.blacklist import is_token_blacklisted
from app.routes.auth import auth_bp
from app.routes.api import api_bp
from app.routes.employee import employee_bp
from app.routes.analytics import analytics_bp

# from app.db import get_db_for_org
# from app.models.user import get_user_by_email

# Workaround for verify_jwt_in_request_optional with success flag
try:
    from flask_jwt_extended import verify_jwt_in_request_optional, get_jwt_identity
except ImportError:
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    from flask_jwt_extended.exceptions import NoAuthorizationError

    def verify_jwt_in_request_optional():
        try:
            verify_jwt_in_request()
            return True
        except NoAuthorizationError:
            return False


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        origins=[Config.SELF_URL, Config.FRONTEND_URL],
        supports_credentials=True,
    )

    init_extensions(app)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return is_token_blacklisted(jti)

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(employee_bp, url_prefix="/employee")
    app.register_blueprint(analytics_bp)

    # @app.before_request
    # def set_org_db():
    #     jwt_verified = verify_jwt_in_request_optional()
    #     if not jwt_verified:
    #         # No valid JWT found; do not call get_jwt_identity
    #         g.org_id = None
    #         g.db = None
    #         return

    #     identity = get_jwt_identity()
    #     if not identity:
    #         g.org_id = None
    #         g.db = None
    #         return

    #     user = get_user_by_email(identity)
    #     if not user:
    #         g.org_id = None
    #         g.db = None
    #         return

    #     g.org_id = user["org_id"]
    #     g.db = get_db_for_org(g.org_id)

    return app
