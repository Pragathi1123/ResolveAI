/**
 * ResolveAI - Admin Dashboard & Status Management JS
 */

let searchTimeout = null;

document.addEventListener("DOMContentLoaded", () => {
    fetchStats();
    fetchComplaints();
});

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        fetchComplaints();
    }, 300);
}

async function fetchStats() {
    try {
        const response = await fetch("/api/analytics/stats");
        const res = await response.json();
        if (res.success) {
            const s = res.data;
            document.getElementById("statTotal").innerText = s.total || 0;
            document.getElementById("statInProgress").innerText = s.in_progress || 0;
            document.getElementById("statCritical").innerText = s.critical_high_open || 0;
            document.getElementById("statResolvedRate").innerText = `${s.resolved} (${s.resolution_rate}%)`;
        }
    } catch (err) {
        console.error("Error fetching stats:", err);
    }
}

async function fetchComplaints() {
    const status = document.getElementById("filterStatus").value;
    const department = document.getElementById("filterDepartment").value;
    const priority = document.getElementById("filterPriority").value;
    const search = document.getElementById("filterSearch").value.trim();

    const tbody = document.getElementById("complaintsTableBody");
    const countBadge = document.getElementById("complaintsCountBadge");

    const params = new URLSearchParams();
    if (status) params.append("status", status);
    if (department) params.append("department", department);
    if (priority) params.append("priority", priority);
    if (search) params.append("search", search);

    try {
        const response = await fetch(`/api/complaints?${params.toString()}`);
        const res = await response.json();

        if (!res.success) {
            throw new Error(res.error || "Failed to load complaints.");
        }

        const items = res.data || [];
        countBadge.innerText = `${items.length} Complaints`;

        if (items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align: center; padding: 2.5rem; color: var(--text-muted);">
                        <i class="fa-solid fa-folder-open" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block;"></i>
                        No complaints match your active filter criteria.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = items.map(c => {
            const pBadgeClass = getPriorityBadgeClass(c.priority);
            const sBadgeClass = getStatusClass(c.status);

            return `
                <tr>
                    <td>
                        <a href="/track/${encodeURIComponent(c.ticket_id)}" class="ticket-id-link">
                            ${escapeHtml(c.ticket_id)}
                        </a>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: #FFFFFF;">${escapeHtml(c.student_name)}</div>
                        <div style="font-size: 0.76rem; color: var(--text-muted);">${escapeHtml(c.student_email)}</div>
                    </td>
                    <td>
                        <div style="font-weight: 600; color: #E2E8F0; max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                            ${escapeHtml(c.subject)}
                        </div>
                        <div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.2rem;">
                            <i class="fa-solid fa-location-dot" style="color: #F87171;"></i> ${escapeHtml(c.location)}
                        </div>
                    </td>
                    <td>
                        <span class="badge ${pBadgeClass}">${escapeHtml(c.priority)}</span>
                    </td>
                    <td>
                        <span style="color: #CBD5E1; font-size: 0.82rem;">${escapeHtml(c.department)}</span>
                    </td>
                    <td>
                        <span class="badge badge-status ${sBadgeClass}">${escapeHtml(c.status)}</span>
                    </td>
                    <td style="text-align: right; white-space: nowrap;">
                        <a href="/track/${encodeURIComponent(c.ticket_id)}" class="btn btn-secondary btn-sm" title="Inspect Agent Trace" style="margin-right: 0.4rem;">
                            <i class="fa-solid fa-eye"></i>
                        </a>
                        <button type="button" class="btn btn-primary btn-sm" onclick="openStatusModal('${escapeHtml(c.ticket_id)}', '${escapeHtml(c.status)}')">
                            <i class="fa-solid fa-pen"></i> Update
                        </button>
                    </td>
                </tr>
            `;
        }).join("");

    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" style="color:#EF4444;text-align:center;padding:1.5rem;">${escapeHtml(err.message)}</td></tr>`;
    }
}

// Modal handling
function openStatusModal(ticketId, currentStatus) {
    document.getElementById("modalTicketId").value = ticketId;
    document.getElementById("modalTicketIdDisplay").innerText = ticketId;
    document.getElementById("modalStatusSelect").value = currentStatus;
    document.getElementById("modalNotes").value = "";
    document.getElementById("modalStaffName").value = "Staff Operations";

    handleModalStatusChange();
    document.getElementById("statusModal").style.display = "flex";
}

function closeStatusModal() {
    document.getElementById("statusModal").style.display = "none";
}

function handleModalStatusChange() {
    const val = document.getElementById("modalStatusSelect").value;
    const warning = document.getElementById("resolutionWarning");
    if (val === "Resolved" || val === "Closed") {
        warning.style.display = "block";
    } else {
        warning.style.display = "none";
    }
}

async function submitStatusUpdate(event) {
    event.preventDefault();
    const btn = document.getElementById("modalSubmitBtn");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Recording Update...';

    const ticketId = document.getElementById("modalTicketId").value;
    const newStatus = document.getElementById("modalStatusSelect").value;
    const staff = document.getElementById("modalStaffName").value.trim();
    const notes = document.getElementById("modalNotes").value.trim();

    try {
        const csrfToken = document.getElementById("adminCsrfToken") ? document.getElementById("adminCsrfToken").value : "";
        const response = await fetch("/api/complaints/update-status", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify({
                ticket_id: ticketId,
                status: newStatus,
                updated_by: staff,
                notes: notes
            })
        });

        const res = await response.json();
        if (!response.ok || !res.success) {
            throw new Error(res.error || "Update failed.");
        }

        closeStatusModal();
        fetchStats();
        fetchComplaints();

        if (res.closure_summary) {
            alert(`Status updated to ${newStatus}!\n\nAI Closure Summary:\n${res.closure_summary}`);
        } else {
            alert(`Ticket ${ticketId} status updated to ${newStatus}.`);
        }

    } catch (err) {
        alert("Error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Save & Record Status';
    }
}

async function reseedDemoData() {
    if (!confirm("Reset database to initial demonstration complaints and agent traces?")) {
        return;
    }
    try {
        const csrfToken = document.getElementById("adminCsrfToken") ? document.getElementById("adminCsrfToken").value : "";
        const response = await fetch("/api/system/reseed", {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken
            }
        });
        const res = await response.json();
        alert(res.message || "Reset complete.");
        fetchStats();
        fetchComplaints();
    } catch (err) {
        alert("Reset failed: " + err.message);
    }
}

function getPriorityBadgeClass(p) {
    switch ((p || '').toUpperCase()) {
        case 'CRITICAL': return 'badge-critical';
        case 'HIGH': return 'badge-high';
        case 'MEDIUM': return 'badge-medium';
        default: return 'badge-low';
    }
}

function getStatusClass(s) {
    switch ((s || '').toLowerCase()) {
        case 'submitted': return 'status-submitted';
        case 'assigned': return 'status-assigned';
        case 'in progress': return 'status-in-progress';
        case 'resolved': return 'status-resolved';
        case 'closed': return 'status-closed';
        default: return 'status-assigned';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
