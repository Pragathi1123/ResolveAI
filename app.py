import os
from flask import (
    Flask, render_template, request, jsonify, redirect,
    url_for, session, flash, g
)
from config import Config
from database.db import (
    init_db,
    bootstrap_admin,
    create_user,
    get_user_by_id,
    get_user_by_email,
    authenticate_user,
    update_user,
    set_user_active_status,
    get_all_users,
    create_complaint,
    get_all_complaints,
    get_complaint_by_ticket_id,
    get_agent_logs_by_ticket_id,
    get_all_agent_logs,
    get_status_history,
    get_dashboard_stats
)
from database.seed_data import seed_database
from agents.orchestrator import CentralOrchestrator
from agents.tracking_agent import ResolutionTrackingAgent
from auth import (
    generate_csrf_token,
    validate_csrf_token,
    get_current_user,
    login_required,
    role_required,
    get_dashboard_route_for_role,
    can_access_complaint
)

app = Flask(__name__)
app.config.from_object(Config)

# Ensure database is initialized, migrated, and seeded on startup
init_db()
seed_database(force_reseed=False)

orchestrator = CentralOrchestrator()
tracking_agent = ResolutionTrackingAgent()

# ---------------------------------------------------------
# Security & CSRF Middleware
# ---------------------------------------------------------
@app.before_request
def csrf_protect():
    """
    Enforces CSRF protection on state-changing HTTP requests.
    Exempts test environments only when app.testing is explicitly configured without a token.
    """
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        # Allow test client bypass only if explicitly in testing mode and no token was passed
        if app.testing and not request.headers.get("X-CSRFToken") and not request.form.get("csrf_token"):
            return None

        token = (
            request.headers.get("X-CSRFToken")
            or request.form.get("csrf_token")
            or (request.get_json(silent=True) or {}).get("csrf_token")
        )

        if not validate_csrf_token(token):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "error": "Invalid or missing CSRF token. Request aborted."
                }), 400

            flash("Security check failed (CSRF token missing or expired). Please try again.", "error")
            return redirect(request.referrer or url_for("login_page"))

@app.context_processor
def inject_global_template_context():
    """
    Injects current user, CSRF token, and system status to all Jinja templates.
    """
    return {
        "current_user": get_current_user(),
        "csrf_token": generate_csrf_token,
        "is_gemini_active": Config.is_gemini_configured(),
        "app_departments": Config.DEPARTMENTS,
        "app_priorities": Config.PRIORITIES,
        "app_statuses": Config.STATUSES
    }

# ---------------------------------------------------------
# Authentication Routes (Login, Register, Logout)
# ---------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login_page():
    """
    User login for Students, Staff, and Administrators.
    """
    user = get_current_user()
    if user:
        return redirect(get_dashboard_route_for_role(user["role"]))

    next_url = request.args.get("next", "")

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        next_destination = request.form.get("next", "").strip()

        authenticated_user, err_msg = authenticate_user(email, password)

        if not authenticated_user:
            flash(err_msg or "Invalid email or password.", "error")
            return render_template("login.html", active_tab="login", email=email, next_url=next_destination), 401

        # Session Fixation Protection: clear and reinitialize session
        session.clear()
        session["user_id"] = authenticated_user["id"]
        session["user_role"] = authenticated_user["role"]
        session["user_name"] = authenticated_user["name"]
        session["user_email"] = authenticated_user["email"]
        session["department"] = authenticated_user.get("department")
        session.permanent = True
        generate_csrf_token()

        flash(f"Welcome back, {authenticated_user['name']}!", "success")

        # Validate safe relative next URL
        if next_destination and next_destination.startswith("/") and not next_destination.startswith("//"):
            return redirect(next_destination)

        return redirect(get_dashboard_route_for_role(authenticated_user["role"]))

    return render_template("login.html", active_tab="login", next_url=next_url)

@app.route("/register", methods=["GET", "POST"])
def register_page():
    """
    Public student registration.
    Staff and Admin accounts are provisioned exclusively through admin management.
    """
    user = get_current_user()
    if user:
        return redirect(get_dashboard_route_for_role(user["role"]))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        student_id = request.form.get("student_id", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Server-side validation
        if not name or not email or not student_id or not password:
            flash("All registration fields are required.", "error")
            return render_template("register.html", active_tab="register", name=name, email=email, student_id=student_id), 400

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("register.html", active_tab="register", name=name, email=email, student_id=student_id), 400

        if password != confirm_password:
            flash("Password and confirmation password do not match.", "error")
            return render_template("register.html", active_tab="register", name=name, email=email, student_id=student_id), 400

        try:
            # Force role to 'student' - public registration only permits student creation
            user_id = create_user(
                name=name,
                email=email,
                password=password,
                role="student",
                student_id=student_id
            )

            # Auto-login the new student securely
            session.clear()
            session["user_id"] = user_id
            session["user_role"] = "student"
            session["user_name"] = name
            session["user_email"] = email.lower()
            session.permanent = True
            generate_csrf_token()

            flash("Student account registered successfully! Welcome to ResolveAI.", "success")
            return redirect(url_for("student_dashboard_page"))

        except ValueError as ve:
            flash(str(ve), "error")
            return render_template("register.html", active_tab="register", name=name, email=email, student_id=student_id), 400
        except Exception as e:
            flash("An unexpected registration error occurred. Please try again.", "error")
            return render_template("register.html", active_tab="register", name=name, email=email, student_id=student_id), 500

    return render_template("register.html", active_tab="register")

@app.route("/logout", methods=["GET", "POST"])
def logout_page():
    """
    Safely clears user session and redirects to sign in.
    """
    session.clear()
    flash("You have been securely signed out.", "info")
    return redirect(url_for("login_page"))

# ---------------------------------------------------------
# Role-Based Dashboard Routes
# ---------------------------------------------------------
@app.route("/")
def index():
    user = get_current_user()
    if user:
        return redirect(get_dashboard_route_for_role(user["role"]))
    return redirect(url_for("login_page"))

@app.route("/student/dashboard")
@login_required
@role_required("student")
def student_dashboard_page():
    """
    Student Dashboard: Lists only complaints owned by the authenticated student.
    """
    user = get_current_user()
    my_complaints = get_all_complaints(
        student_user_id=user["id"],
        student_email=user["email"]
    )
    return render_template(
        "student_dashboard.html",
        active_tab="student_dashboard",
        my_complaints=my_complaints
    )

@app.route("/staff/dashboard")
@login_required
@role_required("staff")
def staff_dashboard_page():
    """
    Staff Dashboard: Displays complaints assigned to the officer's department.
    """
    user = get_current_user()
    department = user.get("department")
    department_complaints = get_all_complaints(department=department)

    return render_template(
        "staff_dashboard.html",
        active_tab="staff_dashboard",
        department_complaints=department_complaints
    )

@app.route("/admin")
@app.route("/admin/dashboard")
@login_required
@role_required("admin")
def admin_page():
    """
    Admin Command Center: Global oversight, full complaints directory, and operational controls.
    """
    return render_template(
        "admin.html",
        active_tab="admin",
        departments=Config.DEPARTMENTS,
        priorities=Config.PRIORITIES,
        statuses=Config.STATUSES
    )

@app.route("/admin/staff")
@login_required
@role_required("admin")
def admin_staff_page():
    """
    Admin-Only Staff Management: Create, inspect, and toggle departmental staff accounts.
    """
    staff_users = get_all_users(role="staff")
    return render_template(
        "admin_staff.html",
        active_tab="admin_staff",
        staff_users=staff_users,
        departments=Config.DEPARTMENTS
    )

@app.route("/api/admin/staff/create", methods=["POST"])
@login_required
@role_required("admin")
def api_admin_create_staff():
    """
    Admin endpoint to provision a new staff account.
    """
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()
    department = request.form.get("department", "").strip()

    if not name or not email or not password or not department:
        flash("All staff fields (Name, Email, Password, Department) are required.", "error")
        return redirect(url_for("admin_staff_page"))

    if len(password) < 6:
        flash("Staff temporary password must be at least 6 characters.", "error")
        return redirect(url_for("admin_staff_page"))

    if department not in Config.DEPARTMENTS:
        flash("Selected department is invalid.", "error")
        return redirect(url_for("admin_staff_page"))

    try:
        create_user(
            name=name,
            email=email,
            password=password,
            role="staff",
            department=department
        )
        flash(f"Staff account for '{name}' ({department}) provisioned successfully.", "success")
    except ValueError as ve:
        flash(str(ve), "error")
    except Exception as e:
        flash("Failed to create staff account.", "error")

    return redirect(url_for("admin_staff_page"))

@app.route("/api/admin/staff/toggle-active", methods=["POST"])
@login_required
@role_required("admin")
def api_admin_toggle_staff_active():
    """
    Admin endpoint to activate or deactivate a staff member.
    """
    try:
        user_id = int(request.form.get("user_id", 0))
        set_active = int(request.form.get("set_active", 1))

        target_user = get_user_by_id(user_id)
        if not target_user or target_user["role"] != "staff":
            flash("Staff user not found.", "error")
            return redirect(url_for("admin_staff_page"))

        set_user_active_status(user_id, is_active=bool(set_active))
        action_word = "activated" if set_active else "deactivated"
        flash(f"Staff account for {target_user['name']} has been {action_word}.", "info")
    except Exception as e:
        flash("Unable to update account status.", "error")

    return redirect(url_for("admin_staff_page"))

# ---------------------------------------------------------
# Complaint Submission & Tracking Pages
# ---------------------------------------------------------
@app.route("/submit")
@login_required
@role_required("student", "admin")
def submit_page():
    """
    Grievance submission page. Auto-fills authenticated student's details.
    """
    return render_template(
        "submit.html",
        active_tab="submit",
        departments=Config.DEPARTMENTS
    )

@app.route("/track")
@app.route("/track/<ticket_id>")
@login_required
def track_page(ticket_id: str = ""):
    """
    Ticket tracking view. Enforces role-based ownership:
    Students can only track their own complaints.
    Staff can track complaints in their department.
    Admin can track all complaints.
    """
    user = get_current_user()

    if ticket_id:
        complaint = get_complaint_by_ticket_id(ticket_id)
        if not complaint:
            flash(f"Ticket '{ticket_id}' does not exist.", "error")
            return redirect(get_dashboard_route_for_role(user["role"]))

        if not can_access_complaint(user, complaint):
            flash(f"Access denied: you are not authorized to view ticket {ticket_id}.", "error")
            return render_template(
                "error.html",
                error_title="403 Access Denied",
                error_message=f"Access denied. Ticket {ticket_id} does not belong to your account.",
                user_dashboard=get_dashboard_route_for_role(user["role"])
            ), 403

    return render_template(
        "track.html",
        active_tab="track",
        initial_ticket_id=ticket_id
    )

@app.route("/analytics")
@login_required
@role_required("admin")
def analytics_page():
    """
    Visual analytics dashboard for administrators.
    """
    return render_template(
        "analytics.html",
        active_tab="analytics"
    )

# ---------------------------------------------------------
# Secure REST API Endpoints
# ---------------------------------------------------------
@app.route("/api/complaints/submit", methods=["POST"])
@login_required
@role_required("student", "admin")
def api_submit_complaint():
    """
    Intake endpoint for student complaint submissions.
    Automatically links complaint to the authenticated student's user account.
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}

        subject = data.get("subject", "").strip()
        raw_description = data.get("raw_description", "").strip()

        if not subject or not raw_description:
            return jsonify({
                "success": False,
                "error": "Complaint subject and description are required fields."
            }), 400

        # Enforce student ownership: attach authenticated user information
        data["student_name"] = user["name"]
        data["student_email"] = user["email"]
        data["student_user_id"] = user["id"]

        result = orchestrator.process_complaint_submission(data)
        return jsonify({
            "success": True,
            "data": result
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/complaints/track/<ticket_id>", methods=["GET"])
@login_required
def api_track_ticket(ticket_id: str):
    """
    Retrieves live tracking status, history timeline and agent logs.
    Strictly verifies ownership: students can only access their own tickets.
    """
    user = get_current_user()
    complaint = get_complaint_by_ticket_id(ticket_id)

    if not complaint:
        return jsonify({
            "success": False,
            "error": f"Ticket '{ticket_id}' not found."
        }), 404

    # Authorization Check
    if not can_access_complaint(user, complaint):
        return jsonify({
            "success": False,
            "error": "Access denied. You are not authorized to view this ticket."
        }), 403

    tracking_data = tracking_agent.track_ticket(ticket_id)
    return jsonify({
        "success": True,
        "data": tracking_data
    })

@app.route("/api/complaints", methods=["GET"])
@login_required
def api_get_complaints():
    """
    Lists complaints scoped strictly to user role:
    - Student: Only their own submitted complaints
    - Staff: Complaints assigned to their department
    - Admin: All complaints (with search/filter options)
    """
    user = get_current_user()
    status = request.args.get("status")
    department = request.args.get("department")
    priority = request.args.get("priority")
    search = request.args.get("search")

    student_user_id = None
    student_email = None

    if user["role"] == "student":
        student_user_id = user["id"]
        student_email = user["email"]
    elif user["role"] == "staff":
        # Force department filter to staff member's department
        department = user.get("department")

    complaints = get_all_complaints(
        status=status,
        department=department,
        priority=priority,
        search=search,
        student_user_id=student_user_id,
        student_email=student_email
    )

    return jsonify({
        "success": True,
        "count": len(complaints),
        "data": complaints
    })

@app.route("/api/complaints/update-status", methods=["POST"])
@login_required
@role_required("staff", "admin")
def api_update_status():
    """
    Updates status and generates verified closure summary if resolved.
    Staff can only update complaints within their assigned department.
    """
    try:
        user = get_current_user()
        data = request.get_json() or {}
        ticket_id = data.get("ticket_id")
        new_status = data.get("status")
        notes = data.get("notes", "")
        updated_by = user["name"]

        if not ticket_id or not new_status:
            return jsonify({
                "success": False,
                "error": "Ticket ID and new status are required."
            }), 400

        complaint = get_complaint_by_ticket_id(ticket_id)
        if not complaint:
            return jsonify({"success": False, "error": f"Ticket {ticket_id} not found."}), 404

        # Staff department check
        if user["role"] == "staff":
            if not can_access_complaint(user, complaint):
                return jsonify({
                    "success": False,
                    "error": "Permission denied: you cannot modify complaints outside your department."
                }), 403

        assigned_staff_id = user["id"] if user["role"] == "staff" else complaint.get("assigned_staff_id")

        res = tracking_agent.update_resolution(
            ticket_id=ticket_id,
            new_status=new_status,
            updated_by=updated_by,
            notes=notes,
            assigned_staff_id=assigned_staff_id
        )

        if not res.get("success"):
            return jsonify(res), 400

        return jsonify(res)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/analytics/stats", methods=["GET"])
@login_required
@role_required("admin", "staff")
def api_get_stats():
    """
    Returns aggregated dashboard statistics.
    Staff receives department-scoped metrics; Admin receives global metrics.
    """
    user = get_current_user()
    dept = user.get("department") if user["role"] == "staff" else None
    stats = get_dashboard_stats(department=dept)
    return jsonify({
        "success": True,
        "data": stats
    })

@app.route("/api/logs", methods=["GET"])
@login_required
@role_required("admin")
def api_get_all_logs():
    """
    Returns global agent activity trace (Admin only).
    """
    logs = get_all_agent_logs(limit=50)
    return jsonify({
        "success": True,
        "count": len(logs),
        "data": logs
    })

@app.route("/api/system/reseed", methods=["POST"])
@login_required
@role_required("admin")
def api_reseed():
    """
    Reseeds sample demonstration complaints (Admin only).
    """
    seed_database(force_reseed=True)
    return jsonify({
        "success": True,
        "message": "Demonstration database reseeded successfully."
    })

if __name__ == "__main__":
    print(f"Starting ResolveAI on http://127.0.0.1:{Config.FLASK_PORT}")
    app.run(
        host="0.0.0.0",
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )
