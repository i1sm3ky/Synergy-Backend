from flask import Blueprint, request, jsonify, g
from app.utils.access_control import jwt_required
from app.utils.db_utils import generate_emp_id, get_org_collection
from app.utils.enums import WorkStatus
import random
import string
from firebase_admin import firestore

api_bp = Blueprint("api", __name__)


@api_bp.route("/add_employee", methods=["POST"])
@jwt_required
def add_employee():
    data = request.json
    emp_id = generate_emp_id(g.org_id)
    ref = get_org_collection(g.org_id, "Employee_data").document(emp_id)
    ref.set(
        {
            "emp_ID": emp_id,
            "email": data["email"],
            "name": data["name"],
            "role": data["role"],
            "features_availed": data["features_availed"],
        }
    )
    return jsonify({"message": "Employee added", "emp_id": emp_id})


@api_bp.route("/add_team", methods=["POST"])
@jwt_required
def add_team():
    data = request.json
    team_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    ref = get_org_collection(g.org_id, "Team_data").document(team_id)
    ref.set({"Team_ID": team_id, "name": data["name"]})
    return jsonify({"message": "Team added", "team_id": team_id})


@api_bp.route("/correlate_employee_team", methods=["POST"])
@jwt_required
def correlate_employee_team():
    data = request.json
    get_org_collection(g.org_id, "Employee_team_correlation").add(
        {"emp_ID": data["emp_ID"], "team_ID": data["team_ID"]}
    )
    return jsonify({"message": "Employee-Team correlation added"})


@api_bp.route("/add_attendance", methods=["POST"])
@jwt_required
def add_attendance():
    data = request.json
    emp_id = data["emp_ID"]
    attendance_data = {
        k: data.get(k, WorkStatus.NULL.value)
        for k in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    }
    attendance_data["emp_ID"] = emp_id
    get_org_collection(g.org_id, "Employee_attendance").document(emp_id).set(
        attendance_data
    )
    return jsonify({"message": "Attendance recorded"})


@api_bp.route("/add_visitor", methods=["POST"])
@jwt_required
def add_visitor():
    data = request.json
    ref = get_org_collection(g.org_id, "Visitor_data").add(
        {
            "emp_ID": data["emp_ID"],
            "visitor_name": data["visitor_name"],
            "visitor_email": data["visitor_email"],
            "visitor_img": data["visitor_img"],
            "time_allocated_start": data["time_allocated_start"],
            "time_allocated_end": data["time_allocated_end"],
            "time_utilized_start": data["time_utilized_start"],
            "time_utilized_end": data["time_utilized_end"],
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )
    return jsonify({"message": "Visitor added"})


@api_bp.route("/add_workspace", methods=["POST"])
@jwt_required
def add_workspace():
    data = request.json
    workspace_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    ref = get_org_collection(g.org_id, "Workspace_data").document(workspace_id)
    ref.set({"workspace_ID": workspace_id, "workspace_type": data["workspace_type"]})
    return jsonify({"message": "Workspace added", "workspace_ID": workspace_id})


@api_bp.route("/book_workspace", methods=["POST"])
@jwt_required
def book_workspace():
    data = request.json
    get_org_collection(g.org_id, "Workspace_booking_data").add(
        {
            "workspace_ID": data["workspace_ID"],
            "required_id": data["required_id"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "purpose": data["purpose"],
            "timestamp": firestore.SERVER_TIMESTAMP,
        }
    )
    return jsonify({"message": "Workspace booked"})


@api_bp.route("/schedule_workspace", methods=["POST"])
@jwt_required
def schedule_workspace():
    data = request.json
    ref = get_org_collection(g.org_id, "Scheduling_data").document(data["required_id"])
    ref.set(
        {
            "required_id": data["required_id"],
            "workspace_id": data["workspace_id"],
            "start_time": data["start_time"],
            "end_time": data["end_time"],
            "booking_pattern": data["booking_pattern"],  # list of enums
        }
    )
    return jsonify({"message": "Scheduling set"})
