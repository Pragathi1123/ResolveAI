/**
 * ResolveAI - Ticket Tracking & Agent Trace Viewer JS
 */

document.addEventListener("DOMContentLoaded", () => {
    const trackInput = document.getElementById("trackInput");
    if (trackInput && trackInput.value.trim()) {
        fetchTicketTracking(trackInput.value.trim());
    }
});

function handleTrackSearch(event) {
    event.preventDefault();
    const ticketId = document.getElementById("trackInput").value.trim();
    if (ticketId) {
        fetchTicketTracking(ticketId);
    }
}

function loadSampleTicket() {
    const sampleIds = [
        "RES-20261110-WIFI1",
        "RES-20261111-LEAK2",
        "RES-20261108-FEE03",
        "RES-20261112-FOOD4",
        "RES-20261109-SEC05"
    ];
    const randomId = sampleIds[Math.floor(Math.random() * sampleIds.length)];
    document.getElementById("trackInput").value = randomId;
    fetchTicketTracking(randomId);
}

async function fetchTicketTracking(ticketId) {
    const loader = document.getElementById("trackLoader");
    const results = document.getElementById("trackResults");

    loader.style.display = "block";
    results.style.display = "none";

    try {
        const response = await fetch(`/api/complaints/track/${encodeURIComponent(ticketId)}`);
        const res = await response.json();

        if (!response.ok || !res.success) {
            throw new Error(res.error || `Ticket ${ticketId} not found.`);
        }

        renderTrackingView(res.data);
        results.style.display = "block";

        // Update URL without page reload
        window.history.pushState({}, "", `/track/${encodeURIComponent(ticketId)}`);

    } catch (err) {
        alert(err.message);
    } finally {
        loader.style.display = "none";
    }
}

function renderTrackingView(data) {
    const c = data.complaint;
    const logs = data.agent_logs || [];

    // Header Status Badge
    const headerBadge = document.getElementById("headerStatusBadge");
    headerBadge.className = `badge badge-status ${getStatusClass(c.status)}`;
    headerBadge.innerText = c.status;

    // Timeline Steps
    updateTimelineTracker(c.status);

    // Closure Summary
    const closureCard = document.getElementById("closureSummaryCard");
    if (c.closure_summary && (c.status === "Resolved" || c.status === "Closed")) {
        closureCard.style.display = "block";
        document.getElementById("closureSummaryText").innerText = c.closure_summary;
        document.getElementById("staffResolutionNotes").innerText = c.resolution_notes || "Operational actions completed.";
    } else {
        closureCard.style.display = "none";
    }

    // Complaint Details
    document.getElementById("detailTicketId").innerText = c.ticket_id;
    document.getElementById("detailSubject").innerText = c.subject;
    document.getElementById("detailLocation").querySelector("span").innerText = c.location;
    document.getElementById("detailDepartment").innerText = c.department;
    document.getElementById("detailStaffRole").innerText = c.assigned_staff_role || "Duty Staff";
    document.getElementById("detailSLA").innerText = `${c.estimated_sla_hours || 24} Hours Maximum`;
    document.getElementById("detailDescription").innerText = c.raw_description;

    const pBadge = document.getElementById("detailPriorityBadge");
    pBadge.className = `badge ${getPriorityBadgeClass(c.priority)}`;
    pBadge.innerText = `${c.priority} Priority`;

    // Render Agent Activity Logs
    const logContainer = document.getElementById("agentLogsContainer");
    logContainer.innerHTML = "";

    if (logs.length === 0) {
        logContainer.innerHTML = '<div style="color:var(--text-muted);padding:1rem;">No agent logs recorded yet.</div>';
    } else {
        logs.forEach(log => {
            const item = document.createElement("div");
            item.className = "agent-log-item";

            let iconClass = "fa-solid fa-microchip";
            if (log.agent_name.includes("Understanding")) iconClass = "fa-solid fa-brain";
            else if (log.agent_name.includes("Priority")) iconClass = "fa-solid fa-gauge-high";
            else if (log.agent_name.includes("Department")) iconClass = "fa-solid fa-building-user";
            else if (log.agent_name.includes("Tracking")) iconClass = "fa-solid fa-timeline";
            else if (log.agent_name.includes("Orchestrator")) iconClass = "fa-solid fa-network-wired";

            item.innerHTML = `
                <div class="agent-log-header">
                    <span class="agent-name-tag">
                        <i class="${iconClass}"></i> ${escapeHtml(log.agent_name)}
                    </span>
                    <span class="agent-timestamp">${escapeHtml(log.timestamp || '')}</span>
                </div>
                <div style="font-size:0.82rem;font-weight:600;color:#93C5FD;margin-bottom:0.35rem;">
                    Action: ${escapeHtml(log.action)}
                </div>
                <div class="agent-reasoning-text">
                    <strong>Reasoning:</strong> ${escapeHtml(log.reasoning || 'Executed standard operational protocol.')}
                </div>
            `;
            logContainer.appendChild(item);
        });
    }
}

function updateTimelineTracker(currentStatus) {
    const statuses = ["Submitted", "Assigned", "In Progress", "Resolved", "Closed"];
    const currentIndex = statuses.indexOf(currentStatus);

    statuses.forEach((status, idx) => {
        const stepEl = document.getElementById(`step-${status}`);
        if (!stepEl) return;

        stepEl.className = "timeline-step";

        if (idx < currentIndex) {
            stepEl.classList.add("completed");
        } else if (idx === currentIndex) {
            if (currentStatus === "Resolved" || currentStatus === "Closed") {
                stepEl.classList.add("completed");
            } else {
                stepEl.classList.add("active");
            }
        }
    });
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
