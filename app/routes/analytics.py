from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils.access_control import requires_tier, requires_tool

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/analytics/view', methods=['GET'])
@jwt_required()
@requires_tier('pro')
@requires_tool('analytics')
def view_analytics():
    return jsonify({
        "msg": "Welcome to your analytics dashboard!",
        "data": {
            "active_users": 128,
            "usage_this_month": "24.6 hours",
            "top_features": ["desk-allocation", "heatmaps"]
        }
    })
