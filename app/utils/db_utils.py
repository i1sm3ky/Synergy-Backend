import random
import string
from app.firebase_init import db


def generate_emp_id(org_code: str):
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{org_code}-{suffix}"


def get_org_collection(org_id: str, collection_name: str):
    return db.collection("Organizations").document(org_id).collection(collection_name)


def get_emp_id_from_firestore(org_id, email):
    employees_ref = (
        db.collection("Organizations").document(org_id).collection("Employee_data")
    )

    # Query Firestore for employee with matching email
    query = employees_ref.where("email", "==", email).limit(1).stream()

    for doc in query:
        return doc.id  # Firestore doc ID is your emp_id

    return None  # Not found


def ensure_employee_in_firestore(email, org_id):
    employees_ref = (
        db.collection("Organizations").document(org_id).collection("Employee_data")
    )

    # Check if employee already exists
    existing_query = employees_ref.where("email", "==", email).limit(1).stream()
    for doc in existing_query:
        return doc.id  # Already exists, return emp_id

    # Create a new employee document
    emp_id = generate_emp_id(org_id)
    employees_ref.document(emp_id).set(
        {
            "emp_ID": emp_id,
            "email": email,
            "name": email.split("@")[0],
            "role": "employee",
            "features_availed": [],  # Or set defaults here
        }
    )

    return emp_id
