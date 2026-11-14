import sys
from app import app
from database.db import (
    get_user_by_email,
    get_complaint_by_ticket_id,
    get_agent_logs_by_ticket_id,
    set_user_active_status
)

def run_auth_and_system_tests():
    print("==================================================")
    print("Running ResolveAI Role-Based Auth & Security Tests")
    print("==================================================")

    # Clean up test accounts from previous test runs for idempotency
    from database.db import get_db_connection
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM status_history WHERE ticket_id IN (SELECT ticket_id FROM complaints WHERE student_email = 'new.student@campus.edu')")
        conn.execute("DELETE FROM agent_logs WHERE ticket_id IN (SELECT ticket_id FROM complaints WHERE student_email = 'new.student@campus.edu')")
        conn.execute("DELETE FROM complaints WHERE student_email = 'new.student@campus.edu'")
        conn.execute("DELETE FROM users WHERE email IN ('new.student@campus.edu', 'new.officer@campus.edu')")
    conn.close()

    # Enable testing mode for Flask
    app.config["TESTING"] = True
    client = app.test_client()

    # ------------------------------------------------------------------
    # 1. Test Unauthorized Access (Redirect to /login)
    # ------------------------------------------------------------------
    for protected_url in ["/student/dashboard", "/staff/dashboard", "/admin", "/analytics", "/submit"]:
        res = client.get(protected_url)
        assert res.status_code == 302, f"Expected 302 redirect for unauth {protected_url}, got {res.status_code}"
        assert "/login" in res.headers["Location"], f"Expected redirect to /login for {protected_url}"
        print(f"[PASS] Unauthorized access blocked -> redirect to login: {protected_url}")

    # ------------------------------------------------------------------
    # 2. Test Student Public Registration
    # ------------------------------------------------------------------
    student_payload = {
        "name": "New Test Student",
        "email": "new.student@campus.edu",
        "student_id": "1MS22CS101",
        "password": "Password@123",
        "confirm_password": "Password@123"
    }

    res = client.post("/register", data=student_payload, follow_redirects=True)
    assert res.status_code == 200
    assert "My Grievances" in res.get_data(as_text=True)
    print("[PASS] Successful student public registration & auto-login")

    # ------------------------------------------------------------------
    # 3. Test Duplicate Email Rejection
    # ------------------------------------------------------------------
    client.get("/logout") # Logout first
    res = client.post("/register", data=student_payload, follow_redirects=True)
    assert res.status_code == 400 or "already exists" in res.get_data(as_text=True)
    print("[PASS] Duplicate email registration correctly rejected")

    # ------------------------------------------------------------------
    # 4. Test Invalid Password Rejection
    # ------------------------------------------------------------------
    res = client.post("/login", data={
        "email": "new.student@campus.edu",
        "password": "WrongPassword999"
    }, follow_redirects=True)
    assert "Invalid email or password" in res.get_data(as_text=True)
    print("[PASS] Invalid password rejection verified")

    # ------------------------------------------------------------------
    # 5. Test Successful Student Login & Redirection
    # ------------------------------------------------------------------
    res = client.post("/login", data={
        "email": "new.student@campus.edu",
        "password": "Password@123"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "My Submissions" in res.get_data(as_text=True)
    print("[PASS] Successful student login -> redirected to Student Dashboard")

    # ------------------------------------------------------------------
    # 6. Test Student Role Restrictions (Forbidden Access)
    # ------------------------------------------------------------------
    # Student cannot access /admin
    res = client.get("/admin")
    assert res.status_code == 403
    print("[PASS] Student restricted from Admin Dashboard (403 Forbidden)")

    # Student cannot access /staff/dashboard
    res = client.get("/staff/dashboard")
    assert res.status_code == 403
    print("[PASS] Student restricted from Staff Operations (403 Forbidden)")

    # Student cannot access /analytics
    res = client.get("/analytics")
    assert res.status_code == 403
    print("[PASS] Student restricted from Analytics (403 Forbidden)")

    # ------------------------------------------------------------------
    # 7. Test Student Complaint Submission (Auto-linked)
    # ------------------------------------------------------------------
    comp_res = client.post("/api/complaints/submit", json={
        "subject": "Lab 102 Power Surge tripped Desktop Machines",
        "raw_description": "A voltage spike tripped all 30 machines in Lab 102 during software development practicals.",
        "location": "Academic Block 1, Lab 102"
    })
    assert comp_res.status_code == 201
    comp_json = comp_res.get_json()["data"]
    student_ticket_id = comp_json["ticket_id"]
    print(f"[PASS] Student submitted grievance! Ticket: {student_ticket_id}")

    # Verify student can track their own ticket
    track_res = client.get(f"/api/complaints/track/{student_ticket_id}")
    assert track_res.status_code == 200
    assert track_res.get_json()["data"]["complaint"]["ticket_id"] == student_ticket_id
    print(f"[PASS] Student successfully tracked own ticket: {student_ticket_id}")

    # ------------------------------------------------------------------
    # 8. Test Student Access Restrictions (Cannot access another student's ticket)
    # ------------------------------------------------------------------
    # Seed ticket RES-20261110-WIFI1 belongs to Aarav Sharma (not new.student)
    forbidden_track_res = client.get("/api/complaints/track/RES-20261110-WIFI1")
    assert forbidden_track_res.status_code == 403
    print("[PASS] Student blocked from viewing another student's ticket (403 Forbidden)")

    # ------------------------------------------------------------------
    # 9. Test Logout
    # ------------------------------------------------------------------
    res_logout = client.get("/logout", follow_redirects=True)
    assert res_logout.status_code == 200
    assert "sign in" in res_logout.get_data(as_text=True).lower() or "login" in res_logout.get_data(as_text=True).lower()
    print("[PASS] Logout successfully cleared user session")

    # ------------------------------------------------------------------
    # 10. Test Staff Login & Scoped Access
    # ------------------------------------------------------------------
    # Login as Vikram (IT Staff)
    res_staff = client.post("/login", data={
        "email": "vikram.staff@campus.edu",
        "password": "Staff@Secure2026"
    }, follow_redirects=True)
    assert res_staff.status_code == 200
    assert "Staff Operations" in res_staff.get_data(as_text=True)
    print("[PASS] Staff login -> redirected to Staff Dashboard")

    # Staff cannot access admin staff management
    res_staff_admin = client.get("/admin/staff")
    assert res_staff_admin.status_code == 403
    print("[PASS] Staff restricted from Admin Staff Management (403 Forbidden)")

    # Staff can access IT ticket
    it_track = client.get("/api/complaints/track/RES-20261110-WIFI1")
    assert it_track.status_code == 200
    print("[PASS] IT Staff can track IT ticket: RES-20261110-WIFI1")

    # Staff CANNOT access / update non-IT ticket (e.g. Finance ticket RES-20261108-FEE03)
    fin_track = client.get("/api/complaints/track/RES-20261108-FEE03")
    assert fin_track.status_code == 403
    print("[PASS] IT Staff blocked from accessing Finance ticket (403 Forbidden)")

    # Staff updates IT ticket status
    update_res = client.post("/api/complaints/update-status", json={
        "ticket_id": "RES-20261110-WIFI1",
        "status": "In Progress",
        "notes": "Testing fiber uplink to rack C-02."
    })
    assert update_res.status_code == 200
    print("[PASS] Staff successfully updated permitted departmental complaint")

    # Staff tries to update non-IT ticket -> Blocked
    update_fail = client.post("/api/complaints/update-status", json={
        "ticket_id": "RES-20261108-FEE03",
        "status": "In Progress",
        "notes": "Unauthorized attempt."
    })
    assert update_fail.status_code == 403
    print("[PASS] Staff blocked from updating non-departmental complaint (403 Forbidden)")

    client.get("/logout")

    # ------------------------------------------------------------------
    # 11. Test Admin Login & Full Administrative Capabilities
    # ------------------------------------------------------------------
    res_admin = client.post("/login", data={
        "email": "admin@campus.edu",
        "password": "Admin@Secure2026"
    }, follow_redirects=True)
    assert res_admin.status_code == 200
    assert "Admin Grievance Operations" in res_admin.get_data(as_text=True)
    print("[PASS] Admin login -> redirected to Admin Dashboard")

    # Admin accesses Analytics
    res_analytics = client.get("/analytics")
    assert res_analytics.status_code == 200
    print("[PASS] Admin successfully accessed Analytics")

    # Admin accesses Staff Directory
    res_staff_dir = client.get("/admin/staff")
    assert res_staff_dir.status_code == 200
    print("[PASS] Admin successfully accessed Staff Management")

    # Admin creates new staff account
    new_staff_email = "new.officer@campus.edu"
    res_create_staff = client.post("/api/admin/staff/create", data={
        "name": "Officer Rajesh",
        "email": new_staff_email,
        "password": "Rajesh@Secure2026",
        "department": "Transport & Logistics"
    }, follow_redirects=True)
    assert res_create_staff.status_code == 200
    created_staff = get_user_by_email(new_staff_email)
    assert created_staff is not None
    assert created_staff["role"] == "staff"
    assert created_staff["department"] == "Transport & Logistics"
    print(f"[PASS] Admin successfully created new staff account: {new_staff_email}")

    # Admin deactivates staff account
    res_deactivate = client.post("/api/admin/staff/toggle-active", data={
        "user_id": created_staff["id"],
        "set_active": 0
    }, follow_redirects=True)
    assert res_deactivate.status_code == 200
    updated_staff = get_user_by_email(new_staff_email)
    assert updated_staff["is_active"] == 0
    print(f"[PASS] Admin successfully deactivated staff account: {new_staff_email}")

    # ------------------------------------------------------------------
    # 12. Test Inactive Account Login Rejection
    # ------------------------------------------------------------------
    client.get("/logout")
    res_inactive = client.post("/login", data={
        "email": new_staff_email,
        "password": "Rajesh@Secure2026"
    }, follow_redirects=True)
    assert "deactivated" in res_inactive.get_data(as_text=True).lower()
    print("[PASS] Inactive account login successfully blocked")

    # ------------------------------------------------------------------
    # 13. Test Existing End-to-End Workflow & Closure Summary with Auth
    # ------------------------------------------------------------------
    # Login as Admin to verify full lifecycle resolution
    client.post("/login", data={"email": "admin@campus.edu", "password": "Admin@Secure2026"})
    resolve_res = client.post("/api/complaints/update-status", json={
        "ticket_id": student_ticket_id,
        "status": "Resolved",
        "notes": "Replaced blown surge protector and power supply units. Restored 230V clean line voltage."
    })
    assert resolve_res.status_code == 200
    assert resolve_res.get_json()["closure_summary"] is not None
    print(f"[PASS] Resolution Tracking Agent generated AI closure summary for {student_ticket_id}")

    print("==================================================")
    print("ALL 13 AUTHENTICATION & SECURITY TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_auth_and_system_tests()
