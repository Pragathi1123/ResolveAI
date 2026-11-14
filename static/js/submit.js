/**
 * ResolveAI - Grievance Submission & Multi-Agent Visualization JS
 */

const SAMPLE_SCENARIOS = {
    wifi: {
        name: "Aarav Sharma",
        email: "aarav.sharma@campus.edu",
        location: "Hostel Block C, 3rd Floor, Room 314",
        subject: "Wi-Fi down across 3rd floor during midterms submission",
        description: "The Wi-Fi access point in corridor 3C has been completely unresponsive for 6 hours. Over 40 students have submissions due tonight by 11:59 PM for Operating Systems and cannot push code to Git or access the LMS portal. Cellular data is extremely weak inside the hostel rooms."
    },
    leak: {
        name: "Priya Nair",
        email: "priya.nair@campus.edu",
        location: "Central Library, 3rd Floor, Stack 14",
        subject: "Severe ceiling water leakage dripping over reference books",
        description: "Heavy water is continuously leaking from the ceiling right above Stack 14 (Computer Science reference collection). Several rare AI handbooks are getting soaked and water is pooling on the tiled floor creating a dangerous slip hazard."
    },
    fee: {
        name: "Rohan Deshmukh",
        email: "rohan.d@campus.edu",
        location: "Campus Finance Portal",
        subject: "Duplicate semester fee deduction of ₹45,000 on gateway",
        description: "I attempted to pay the semester registration fees via NetBanking. The portal showed a 504 gateway timeout, so I retried. My bank account debited twice (Ref TXN-90281 & TXN-90282) totaling ₹90,000, but fee portal still only credits one transaction. Need urgent reversal."
    },
    food: {
        name: "Ananya Sen",
        email: "ananya.sen@campus.edu",
        location: "South Campus Dining Mess",
        subject: "Stale food and spoiled milk served at dinner",
        description: "The paneer curry and curd served at dinner tonight in South Mess tasted foul and sour. More than five hostellers are reporting sharp stomach cramps. The kitchen staff were also handling food without required hairnets or food-grade gloves."
    },
    light: {
        name: "Kavita Reddy",
        email: "kavita.reddy@campus.edu",
        location: "East Gate Perimeter Walkway near Block 4",
        subject: "Pitch black walkway due to dead high-mast streetlights",
        description: "Three consecutive high-mast streetlights along the 250m pathway between Academic Block 4 and East Gate are completely dead. It becomes pitch dark after 7:30 PM, raising serious security and physical safety concerns for students returning from late labs."
    },
    lab: {
        name: "Devansh Patel",
        email: "devansh.p@campus.edu",
        location: "CS Dept, Research Lab 204",
        subject: "HVAC failure in GPU cluster laboratory",
        description: "The split AC unit cooling GPU Lab 204 tripped this morning. Ambient temperature is now 37°C. The 8x A100 GPU workstation rack is thermal throttling and model training jobs are aborting due to overheating warning thresholds."
    }
};

function loadSampleScenario(key) {
    const s = SAMPLE_SCENARIOS[key];
    if (!s) return;

    document.getElementById("studentName").value = s.name;
    document.getElementById("studentEmail").value = s.email;
    document.getElementById("location").value = s.location;
    document.getElementById("subject").value = s.subject;
    document.getElementById("rawDescription").value = s.description;

    // Smooth scroll to form
    document.getElementById("grievanceForm").scrollIntoView({ behavior: 'smooth' });
}

async function handleGrievanceSubmit(event) {
    event.preventDefault();

    const submitBtn = document.getElementById("submitBtn");
    const visualizer = document.getElementById("pipelineVisualizer");
    const resultBanner = document.getElementById("resultBanner");
    const pipelineBadge = document.getElementById("pipelineStatusBadge");

    // Form data
    const payload = {
        student_name: document.getElementById("studentName").value.trim(),
        student_email: document.getElementById("studentEmail").value.trim(),
        location: document.getElementById("location").value.trim(),
        subject: document.getElementById("subject").value.trim(),
        raw_description: document.getElementById("rawDescription").value.trim()
    };

    // UI state: Running
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing Multi-Agent Pipeline...';

    visualizer.style.display = "block";
    resultBanner.style.display = "none";
    visualizer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Reset step cards
    resetStepCard("stepCard1", "stepIcon1", "stepOutput1");
    resetStepCard("stepCard2", "stepIcon2", "stepOutput2");
    resetStepCard("stepCard3", "stepIcon3", "stepOutput3");

    // Activate Step 1
    setStepActive("stepCard1", "stepIcon1");

    try {
        const csrfToken = document.getElementById("csrfToken") ? document.getElementById("csrfToken").value : "";
        const response = await fetch("/api/complaints/submit", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken
            },
            body: JSON.stringify(payload)
        });

        const res = await response.json();

        if (!response.ok || !res.success) {
            throw new Error(res.error || "Failed to process complaint.");
        }

        const data = res.data;
        const u = data.understanding;
        const p = data.priority;
        const a = data.assignment;

        // Render Step 1
        setStepCompleted("stepCard1", "stepIcon1");
        const out1 = document.getElementById("stepOutput1");
        out1.style.display = "block";
        out1.innerHTML = `
            <div><strong>Category:</strong> <span style="color:#60A5FA;">${escapeHtml(u.category || 'General')}</span></div>
            <div><strong>Scope:</strong> ${escapeHtml(u.affected_scope || 'Individual')}</div>
            <div><strong>Cues:</strong> ${u.urgency_cues && u.urgency_cues.length ? escapeHtml(u.urgency_cues.join(', ')) : 'None'}</div>
        `;

        // Render Step 2
        setStepCompleted("stepCard2", "stepIcon2");
        const out2 = document.getElementById("stepOutput2");
        out2.style.display = "block";
        const pBadgeClass = getPriorityBadgeClass(p.priority);
        out2.innerHTML = `
            <div><strong>Assigned Priority:</strong> <span class="badge ${pBadgeClass}">${p.priority}</span></div>
            <div><strong>Risk Score:</strong> Urg: ${p.urgency}/5 | Sev: ${p.severity}/5 | Imp: ${p.impact}/5</div>
            <div><strong>Target SLA:</strong> ${p.recommended_sla_hours} Hours</div>
        `;

        // Render Step 3
        setStepCompleted("stepCard3", "stepIcon3");
        const out3 = document.getElementById("stepOutput3");
        out3.style.display = "block";
        out3.innerHTML = `
            <div><strong>Assigned Dept:</strong> <span style="color:#A78BFA;font-weight:700;">${escapeHtml(a.department)}</span></div>
            <div><strong>Assigned Role:</strong> ${escapeHtml(a.assigned_staff_role || 'Duty Officer')}</div>
            <div><strong>Action:</strong> ${escapeHtml(a.action_plan || 'Dispatched')}</div>
        `;

        // Success banner
        pipelineBadge.className = "badge badge-low";
        pipelineBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Complete';

        document.getElementById("resTicketId").innerText = data.ticket_id;
        document.getElementById("trackTicketLink").href = `/track/${encodeURIComponent(data.ticket_id)}`;
        resultBanner.style.display = "block";

    } catch (err) {
        alert("Error submitting complaint: " + err.message);
        pipelineBadge.className = "badge badge-critical";
        pipelineBadge.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error Occurred';
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fa-solid fa-bolt"></i> Ingest & Trigger Multi-Agent Pipeline';
    }
}

function resetStepCard(cardId, iconId, outId) {
    const card = document.getElementById(cardId);
    const icon = document.getElementById(iconId);
    const out = document.getElementById(outId);

    card.className = "agent-step-card";
    icon.className = "step-status-icon fa-solid fa-clock";
    out.style.display = "none";
    out.innerHTML = "";
}

function setStepActive(cardId, iconId) {
    document.getElementById(cardId).className = "agent-step-card active";
    document.getElementById(iconId).className = "step-status-icon fa-solid fa-spinner fa-spin";
}

function setStepCompleted(cardId, iconId) {
    document.getElementById(cardId).className = "agent-step-card completed";
    document.getElementById(iconId).className = "step-status-icon fa-solid fa-circle-check";
}

function getPriorityBadgeClass(p) {
    switch ((p || '').toUpperCase()) {
        case 'CRITICAL': return 'badge-critical';
        case 'HIGH': return 'badge-high';
        case 'MEDIUM': return 'badge-medium';
        default: return 'badge-low';
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
