from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from firebase_admin import firestore
from datetime import datetime, timedelta

from app.utils.enums import WorkspaceType, BookingPattern

employee_bp = Blueprint("employee", __name__)
db = firestore.client()


def get_org_id():
    claims = get_jwt()
    return claims.get("org_id")


def today_str():
    return datetime.utcnow().strftime("%Y-%m-%d")


@employee_bp.route("/mark_wfh_tomorrow", methods=["POST"])
@jwt_required()
def mark_wfh_tomorrow():
    org_id = get_org_id()
    emp_id = get_jwt_identity()

    attendance_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Employee_attendance")
        .document(emp_id)
    )
    doc = attendance_ref.get()
    attendance_data = doc.to_dict() if doc.exists else {}

    tomorrow = datetime.utcnow().date() + timedelta(days=1)
    day_key = tomorrow.strftime("%a").lower()[:2]  # "mo", "tu", etc.

    if day_key not in BookingPattern._value2member_map_:
        return jsonify({"msg": "Invalid day"}), 400

    attendance_data[day_key] = "wfh"
    attendance_ref.set(attendance_data, merge=True)

    return jsonify({"msg": f"Marked {day_key} as WFH for employee {emp_id}"}), 200


@employee_bp.route("/get_workstation", methods=["GET"])
@jwt_required()
def get_workstation():
    org_id = get_org_id()
    w_type_str = request.args.get("type", "").strip()

    try:
        w_type = WorkspaceType(w_type_str)
    except ValueError:
        return jsonify({"msg": "Invalid workspace type"}), 400

    if w_type not in WorkspaceType:
        print("Invalid workspace type")
        return

    ws_ref = (
        db.collection("Organizations").document(org_id).collection("Workspace_data")
    )
    ws_docs = ws_ref.where("workspace_type", "==", w_type.value).stream()

    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
    )
    now = datetime.utcnow()
    now_str = now.strftime("%H:%M")
    bookings_today = (
        booking_ref.where("start_time", "<=", now_str)
        .where("end_time", ">=", now_str)
        .stream()
    )

    current_bookings = {}
    for b in bookings_today:
        bdata = b.to_dict()
        current_bookings[bdata["workspace_ID"]] = bdata

    results = []
    for ws in ws_docs:
        ws_data = ws.to_dict()
        ws_id = ws.id
        status = "available"
        occupant = None
        time_slot = None

        if ws_id in current_bookings:
            status = "booked"
            occupant = current_bookings[ws_id]["required_id"]
            time_slot = (
                current_bookings[ws_id]["start_time"],
                current_bookings[ws_id]["end_time"],
            )

        results.append(
            {
                "workspace_id": ws_id,
                "workspace_type": ws_data.get("workspace_type"),
                "status": status,
                "occupant": occupant,
                "time_slot": time_slot,
            }
        )

    return jsonify(results), 200


@employee_bp.route("/get_workstation_type_occupancy", methods=["GET"])
@jwt_required()
def get_workstation_type_occupancy():
    org_id = get_org_id()

    ws_ref = (
        db.collection("Organizations").document(org_id).collection("Workspace_data")
    )
    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
    )

    total_by_type = {t.value: 0 for t in WorkspaceType}
    occupied_by_type = {t.value: 0 for t in WorkspaceType}

    all_ws = ws_ref.stream()
    for ws in all_ws:
        ws_data = ws.to_dict()
        wtype = ws_data.get("workspace_type")
        if wtype in total_by_type:
            total_by_type[wtype] += 1

    now = datetime.utcnow()
    time_now = now.strftime("%H:%M")
    bookings_today = (
        booking_ref.where("start_time", "<=", time_now)
        .where("end_time", ">=", time_now)
        .stream()
    )

    occupied_workspace_ids = {b.to_dict()["workspace_ID"] for b in bookings_today}
    ws_map = {ws.id: ws.to_dict().get("workspace_type") for ws in ws_ref.stream()}

    for ws_id in occupied_workspace_ids:
        wtype = ws_map.get(ws_id)
        if wtype in occupied_by_type:
            occupied_by_type[wtype] += 1

    result = {}
    for wtype in WorkspaceType:
        total = total_by_type[wtype.value]
        occupied = occupied_by_type[wtype.value]
        unoccupied = total - occupied
        occupancy_pct = (occupied / total * 100) if total > 0 else 0
        result[wtype.value] = {
            "total": total,
            "occupied": occupied,
            "unoccupied": unoccupied,
            "occupancy_percent": occupancy_pct,
        }

    return jsonify(result), 200


@employee_bp.route("/my_bookings", methods=["GET"])
@jwt_required()
def my_bookings():
    org_id = get_org_id()
    emp_id = get_jwt_identity()

    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
    )
    bookings = booking_ref.where("required_id", "==", emp_id).stream()
    result = [{"booking_id": b.id, **b.to_dict()} for b in bookings]

    return jsonify(result), 200


@employee_bp.route("/delete_my_booking", methods=["POST"])
@jwt_required()
def delete_my_booking():
    org_id = get_org_id()
    emp_id = get_jwt_identity()

    data = request.get_json()
    booking_id = data.get("booking_id")
    if not booking_id:
        return jsonify({"msg": "booking_id required"}), 400

    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
        .document(booking_id)
    )
    booking = booking_ref.get()
    if not booking.exists:
        return jsonify({"msg": "Booking not found"}), 404

    booking_data = booking.to_dict()
    if booking_data.get("required_id") != emp_id:
        return jsonify({"msg": "You can only delete your own bookings"}), 403

    booking_ref.delete()
    return jsonify({"msg": "Booking deleted"}), 200


@employee_bp.route("/book_workspace", methods=["POST"])
@jwt_required()
def book_workspace():
    org_id = get_org_id()
    emp_id = get_jwt_identity()

    data = request.get_json()
    workspace_id = data.get("workspace_ID")
    required_id = emp_id
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    purpose = data.get("purpose", "")
    schedule = data.get("schedule")  # Comma-separated: "mo,tu,we"

    if not all([workspace_id, start_time, end_time]):
        return (
            jsonify({"msg": "workspace_ID, start_time and end_time are required"}),
            400,
        )

    ws_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_data")
        .document(workspace_id)
    )
    ws_doc = ws_ref.get()
    if not ws_doc.exists:
        return jsonify({"msg": "Workspace not found"}), 404

    ws_type = ws_doc.to_dict().get("workspace_type")

    if ws_type == WorkspaceType.HOT_SEAT.value:
        ws_ref_all = (
            db.collection("Organizations").document(org_id).collection("Workspace_data")
        )
        workstations = ws_ref_all.where(
            "workspace_type", "==", WorkspaceType.WORK_STATION.value
        ).stream()
        booking_ref = (
            db.collection("Organizations")
            .document(org_id)
            .collection("Workspace_booking_data")
        )

        workstation_full = True
        for ws in workstations:
            ws_id = ws.id
            bookings = booking_ref.where("workspace_ID", "==", ws_id).stream()
            if all(
                end_time <= b.to_dict()["start_time"]
                or start_time >= b.to_dict()["end_time"]
                for b in bookings
            ):
                workstation_full = False
                break

        if not workstation_full:
            return jsonify({"msg": "Workstations available, cannot book hot seat"}), 400

    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
    )
    new_booking = {
        "workspace_ID": workspace_id,
        "required_id": required_id,
        "start_time": start_time,
        "end_time": end_time,
        "purpose": purpose,
        "timestamp": firestore.SERVER_TIMESTAMP,
    }
    booking_doc_ref = booking_ref.document()
    booking_doc_ref.set(new_booking)

    if schedule:
        schedule_pattern = [s.strip() for s in schedule.split(",")]
        for day in schedule_pattern:
            if day not in BookingPattern._value2member_map_:
                return jsonify({"msg": f"Invalid booking pattern day: {day}"}), 400

        scheduling_ref = (
            db.collection("Organizations")
            .document(org_id)
            .collection("Scheduling_data")
            .document(required_id)
        )
        scheduling_ref.set(
            {
                "required_id": required_id,
                "workspace_id": workspace_id,
                "start_time": start_time,
                "end_time": end_time,
                "booking_pattern": schedule_pattern,
            }
        )

    return jsonify({"msg": "Workspace booked successfully"}), 201


@employee_bp.route("/check_workspace_availability", methods=["GET"])
@jwt_required()
def check_workspace_availability():
    org_id = get_org_id()
    ws_id = request.args.get("workspace_ID")
    date_str = request.args.get("date")

    if not ws_id:
        return jsonify({"msg": "workspace_ID param required"}), 400

    if not date_str:
        date_str = today_str()

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"msg": "Invalid date format, use YYYY-MM-DD"}), 400

    ws_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_data")
        .document(ws_id)
    )
    if not ws_ref.get().exists:
        return jsonify({"msg": "Workspace not found"}), 404

    booking_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Workspace_booking_data")
    )
    bookings = booking_ref.where("workspace_ID", "==", ws_id).stream()

    bookings_on_date = [b.to_dict() for b in bookings]  # Optional: filter by date

    if bookings_on_date:
        return jsonify({"available": False, "bookings": bookings_on_date}), 200
    else:
        return jsonify({"available": True}), 200


@employee_bp.route("/get_visitor_pass", methods=["POST"])
@jwt_required()
def get_visitor_pass():
    org_id = get_org_id()
    data = request.get_json()
    visitor_name = data.get("visitor_name")
    visitor_email = data.get("visitor_email")
    purpose = data.get("purpose", "")
    emp_id = get_jwt_identity()
    visit_date = datetime.utcnow()

    if not visitor_name or not visitor_email:
        return jsonify({"msg": "visitor_name and visitor_email required"}), 400

    visitor_ref = (
        db.collection("Organizations").document(org_id).collection("Visitor_data")
    )
    pass_doc_ref = visitor_ref.document()
    pass_id = pass_doc_ref.id

    visitor_data = {
        "visitor_name": visitor_name,
        "visitor_email": visitor_email,
        "purpose": purpose,
        "host_id": emp_id,
        "visit_date": visit_date,
        "pass_id": pass_id,
    }
    pass_doc_ref.set(visitor_data)

    return jsonify({"visitor_pass_link": f"/get_visitor_data/{pass_id}"}), 201


@employee_bp.route("/get_visitor_data/<pass_id>", methods=["GET"])
@jwt_required()
def get_visitor_data(pass_id):
    org_id = get_org_id()
    visitor_ref = (
        db.collection("Organizations")
        .document(org_id)
        .collection("Visitor_data")
        .document(pass_id)
    )
    doc = visitor_ref.get()
    if not doc.exists:
        return jsonify({"msg": "Visitor pass not found"}), 404

    return jsonify(doc.to_dict()), 200
