import secrets
from functools import wraps
from flask import session, request, redirect, url_for, jsonify, render_template, g
from database.db import get_user_by_id

def generate_csrf_token() -> str:
    """
    Generates or retrieves CSRF token for current session.
    """
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def validate_csrf_token(token: str) -> bool:
    """
    Validates submitted CSRF token against session token.
    """
    session_token = session.get("csrf_token")
    if not session_token or not token:
        return False
    return secrets.compare_digest(session_token, token)

def get_current_user():
    """
    Retrieves the currently authenticated user from session.
    Returns None if user is not logged in or is deactivated.
    """
    if hasattr(g, "_current_user"):
        return g._current_user

    user_id = session.get("user_id")
    if not user_id:
        g._current_user = None
        return None

    user = get_user_by_id(user_id)
    if not user or not user.get("is_active"):
        # Clear invalid or deactivated session
        session.clear()
        g._current_user = None
        return None

    g._current_user = user
    return user

def login_required(f):
    """
    Decorator to ensure user is logged in.
    Redirects to /login for HTML requests, or returns 401 for JSON API calls.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Please log in.",
                    "redirect": "/login"
                }), 401
            return redirect(url_for("login_page", next=request.path))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*allowed_roles):
    """
    Decorator to restrict access to specified roles (e.g. 'admin', 'staff', 'student').
    Returns 403 Forbidden if user lacks permitted role.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({
                        "success": False,
                        "error": "Authentication required. Please log in.",
                        "redirect": "/login"
                    }), 401
                return redirect(url_for("login_page", next=request.path))

            if user.get("role") not in allowed_roles:
                if request.is_json or request.path.startswith("/api/"):
                    return jsonify({
                        "success": False,
                        "error": f"Permission denied: this action requires one of the following roles: {list(allowed_roles)}."
                    }), 403
                return render_template(
                    "error.html",
                    error_title="403 Forbidden",
                    error_message=f"Access denied. Your role ({user.get('role').upper()}) does not have permission to access this page.",
                    user_dashboard=get_dashboard_route_for_role(user.get("role"))
                ), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_dashboard_route_for_role(role: str) -> str:
    """
    Returns the appropriate dashboard route for a given user role.
    """
    if role == "student":
        return "/student/dashboard"
    elif role == "staff":
        return "/staff/dashboard"
    elif role == "admin":
        return "/admin"
    return "/submit"

def can_access_complaint(user: dict, complaint: dict) -> bool:
    """
    Verifies if a user is authorized to view or track a specific complaint:
    - Admin: Can access all complaints.
    - Staff: Can access complaints assigned to them OR matching their department.
    - Student: Can ONLY access complaints they submitted (by user_id or email).
    """
    if not user or not complaint:
        return False

    role = user.get("role")

    if role == "admin":
        return True

    if role == "staff":
        staff_dept = user.get("department")
        complaint_dept = complaint.get("department")
        assigned_id = complaint.get("assigned_staff_id")
        # Enforce that staff can only access complaints assigned to their own department AND assigned to them
        return bool(assigned_id == user.get("id") and staff_dept and staff_dept == complaint_dept)

    if role == "student":
        user_id = user.get("id")
        user_email = user.get("email", "").lower()
        comp_user_id = complaint.get("student_user_id")
        comp_email = complaint.get("student_email", "").lower()
        return bool((comp_user_id and comp_user_id == user_id) or (comp_email and comp_email == user_email))

    return False
