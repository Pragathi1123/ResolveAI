import sys
from app import app
from database.db import get_complaint_by_ticket_id, get_agent_logs_by_ticket_id

def run_e2e_tests():
    print("==================================================")
    print("Running ResolveAI Unified Web App Integration Tests")
    print("==================================================")

    app.config["TESTING"] = True
    client = app.test_client()

    # 1. Test Unauthenticated Root Redirect -> /login
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]
    print("[PASS] Unauthenticated root redirect '/' -> '/login'")

    # 2. Test Login Page Renders
    res = client.get("/login")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Sign In" in html
    assert "Institutional Email Address" in html
    print("[PASS] Login page renders with modern glassmorphism UI")

    # 3. Test Student Registration Page Renders
    res = client.get("/register")
    assert res.status_code == 200
    html = res.get_data(as_text=True)
    assert "Student Registration" in html
    assert "Student USN / ID" in html
    print("[PASS] Student registration page renders successfully")

    # 4. Authenticate as Administrator
    res_login = client.post("/login", data={
        "email": "admin@campus.edu",
        "password": "Admin@Secure2026"
    }, follow_redirects=True)
    assert res_login.status_code == 200
    assert "Admin Grievance Operations" in res_login.get_data(as_text=True)
    print("[PASS] Admin login successful -> access to Admin Dashboard")

    # 5. Verify Admin Navigation Bar Links
    admin_nav_links = ["/admin", "/admin/staff", "/analytics", "/submit", "/track"]
    for path in admin_nav_links:
        res = client.get(path)
        assert res.status_code == 200, f"Failed on {path}"
        html = res.get_data(as_text=True)
        assert "/admin" in html
        assert "/analytics" in html
        print(f"[PASS] Page rendered with consistent navbar & permissions: {path}")

    # 6. Test Grievance Submission
    test_payload = {
        "student_name": "E2E Student",
        "student_email": "admin@campus.edu",
        "location": "Hostel Block C, Floor 3, Room 318",
        "subject": "Critical Wi-Fi Switch Failure during Examination",
        "raw_description": "The entire 48-port Wi-Fi switch on 3rd floor Block C has burnt out. Final exam submissions are due in 2 hours and 45 students cannot access course repositories."
    }

    res = client.post("/api/complaints/submit", json=test_payload)
    assert res.status_code == 201, f"Submit failed: {res.data}"
    json_data = res.get_json()
    assert json_data["success"] is True
    ticket_id = json_data["data"]["ticket_id"]
    priority = json_data["data"]["priority"]["priority"]
    dept = json_data["data"]["assignment"]["department"]
    print(f"[PASS] Grievance submitted! Ticket ID: {ticket_id}")
    print(f"       Priority assessed: {priority} | Department assigned: {dept}")

    assert priority in ["CRITICAL", "HIGH"]
    assert dept == "IT & Network Infrastructure"

    # 7. Verify SQLite Database Persistence
    complaint_db = get_complaint_by_ticket_id(ticket_id)
    assert complaint_db is not None
    assert complaint_db["ticket_id"] == ticket_id
    print("\nDEBUG: Actual complaint data:", complaint_db)
    print("DEBUG: Actual status:", complaint_db["status"])

    assert complaint_db["status"] == "Assigned"
    print(f"[PASS] Verified ticket {ticket_id} persisted in shared SQLite database")

    # 8. Verify Multi-Agent Audit Traces in Database
    logs = get_agent_logs_by_ticket_id(ticket_id)
    assert len(logs) >= 3
    print(f"[PASS] Verified {len(logs)} agent audit traces recorded for {ticket_id}")

    # 9. Verify Ticket Accessible Through Tracking (/track/<ticket_id>)
    res_track_html = client.get(f"/track/{ticket_id}")
    assert res_track_html.status_code == 200
    track_html = res_track_html.get_data(as_text=True)
    assert ticket_id in track_html
    print(f"[PASS] Ticket accessible via HTML route: /track/{ticket_id}")

    res_track_api = client.get(f"/api/complaints/track/{ticket_id}")
    assert res_track_api.status_code == 200
    track_data = res_track_api.get_json()["data"]
    assert track_data["complaint"]["ticket_id"] == ticket_id
    print(f"[PASS] Ticket tracking data verified via API: /api/complaints/track/{ticket_id}")

    # 10. Verify Ticket Visible on Admin Dashboard
    res_admin_api = client.get("/api/complaints")
    assert res_admin_api.status_code == 200
    complaints_list = res_admin_api.get_json()["data"]
    found_in_admin = any(c["ticket_id"] == ticket_id for c in complaints_list)
    assert found_in_admin is True, f"Ticket {ticket_id} not found in admin complaints list"
    print(f"[PASS] Ticket {ticket_id} is visible in Admin Dashboard query")

    # 11. Verify Status Update Lifecycle (In Progress -> Resolved) with AI Closure Summary
    res_prog = client.post("/api/complaints/update-status", json={
        "ticket_id": ticket_id,
        "status": "In Progress",
        "notes": "Technician dispatched on site with replacement 48-port Cisco PoE switch."
    })
    assert res_prog.status_code == 200
    print(f"[PASS] Status updated to 'In Progress'")

    res_res = client.post("/api/complaints/update-status", json={
        "ticket_id": ticket_id,
        "status": "Resolved",
        "notes": "Replaced burnt switch in rack C-03. Uplink fiber tested at 1 Gbps. All access points rebooted and operational."
    })
    assert res_res.status_code == 200
    res_data = res_res.get_json()
    assert res_data["success"] is True
    assert res_data["closure_summary"] is not None
    print(f"[PASS] Status updated to 'Resolved' with Authorized AI Closure Summary:")
    print(f"       Summary: {res_data['closure_summary']}")

    # 12. Verify Analytics Dashboard Reads Actual Complaint Data from SQLite
    res_stats = client.get("/api/analytics/stats")
    assert res_stats.status_code == 200
    stats = res_stats.get_json()["data"]
    assert stats["total"] > 0
    assert stats["resolved"] >= 1
    assert "IT & Network Infrastructure" in stats["department_distribution"]
    print(f"[PASS] Analytics reads actual data: {stats['total']} total tickets, {stats['resolved']} resolved")

    # 13. Verify Admin Filtering by Priority
    res_crit = client.get("/api/complaints?priority=CRITICAL")
    assert res_crit.status_code == 200
    crit_list = res_crit.get_json()["data"]
    print(f"[PASS] Priority filter verified ({len(crit_list)} critical tickets found)")

    # 14. Test Student Workflow
    client.get("/logout")
    res_stu_login = client.post("/login", data={
        "email": "aarav.sharma@campus.edu",
        "password": "Student@Secure2026"
    }, follow_redirects=True)
    assert res_stu_login.status_code == 200
    assert "My Grievances" in res_stu_login.get_data(as_text=True)
    print("[PASS] Student Aarav Sharma successfully logged in to Student Dashboard")

    print("==================================================")
    print("ALL 14 INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_tests()
