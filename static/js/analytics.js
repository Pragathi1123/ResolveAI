/**
 * ResolveAI - Analytics Charts & Intelligence JS
 */

let priorityChartInstance = null;
let statusChartInstance = null;
let departmentChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    loadAnalyticsData();
    loadGlobalLogs();
});

async function loadAnalyticsData() {
    try {
        const response = await fetch("/api/analytics/stats");
        const res = await response.json();
        if (res.success) {
            renderCharts(res.data);
        }
    } catch (err) {
        console.error("Error loading analytics data:", err);
    }
}

async function loadGlobalLogs() {
    const container = document.getElementById("globalLogsContainer");
    try {
        const response = await fetch("/api/logs");
        const res = await response.json();
        if (res.success && res.data) {
            const logs = res.data;
            if (logs.length === 0) {
                container.innerHTML = '<div style="color:var(--text-muted);padding:1rem;">No agent logs recorded yet.</div>';
                return;
            }

            container.innerHTML = logs.map(l => {
                return `
                    <div class="agent-log-item">
                        <div class="agent-log-header">
                            <span class="agent-name-tag">
                                <i class="fa-solid fa-microchip"></i> ${escapeHtml(l.agent_name)}
                                <a href="/track/${encodeURIComponent(l.ticket_id)}" class="ticket-id-link font-mono" style="font-size:0.75rem;margin-left:0.5rem;">
                                    ${escapeHtml(l.ticket_id)}
                                </a>
                            </span>
                            <span class="agent-timestamp">${escapeHtml(l.timestamp || '')}</span>
                        </div>
                        <div style="font-size:0.84rem;font-weight:600;color:#93C5FD;margin-bottom:0.25rem;">
                            Action: ${escapeHtml(l.action)}
                        </div>
                        <div class="agent-reasoning-text">
                            ${escapeHtml(l.reasoning || '')}
                        </div>
                    </div>
                `;
            }).join("");
        }
    } catch (err) {
        container.innerHTML = `<div style="color:#EF4444;padding:1rem;">Error loading agent logs: ${escapeHtml(err.message)}</div>`;
    }
}

function renderCharts(stats) {
    // 1. Priority Chart
    const pDist = stats.priority_distribution || {};
    const pLabels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
    const pData = pLabels.map(l => pDist[l] || 0);
    const pColors = ["#EF4444", "#F97316", "#EAB308", "#10B981"];

    if (priorityChartInstance) priorityChartInstance.destroy();
    const ctxPriority = document.getElementById("priorityChart").getContext("2d");
    priorityChartInstance = new Chart(ctxPriority, {
        type: "bar",
        data: {
            labels: pLabels,
            datasets: [{
                label: "Complaints Count",
                data: pData,
                backgroundColor: pColors,
                borderRadius: 6,
                borderWidth: 1,
                borderColor: "rgba(255, 255, 255, 0.15)"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94A3B8", font: { weight: "600" } }
                },
                y: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94A3B8", stepSize: 1 }
                }
            }
        }
    });

    // 2. Status Chart (Doughnut)
    const sDist = stats.status_distribution || {};
    const sLabels = Object.keys(sDist);
    const sData = Object.values(sDist);
    const statusColorMap = {
        "Submitted": "#94A3B8",
        "Assigned": "#38BDF8",
        "In Progress": "#F59E0B",
        "Resolved": "#10B981",
        "Closed": "#64748B"
    };
    const sColors = sLabels.map(l => statusColorMap[l] || "#3B82F6");

    if (statusChartInstance) statusChartInstance.destroy();
    const ctxStatus = document.getElementById("statusChart").getContext("2d");
    statusChartInstance = new Chart(ctxStatus, {
        type: "doughnut",
        data: {
            labels: sLabels,
            datasets: [{
                data: sData,
                backgroundColor: sColors,
                borderWidth: 2,
                borderColor: "#111C35"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { color: "#CBD5E1", font: { size: 12 } }
                }
            },
            cutout: "68%"
        }
    });

    // 3. Department Chart (Horizontal Bar)
    const dDist = stats.department_distribution || {};
    const dLabels = Object.keys(dDist);
    const dData = Object.values(dDist);

    if (departmentChartInstance) departmentChartInstance.destroy();
    const ctxDept = document.getElementById("departmentChart").getContext("2d");
    departmentChartInstance = new Chart(ctxDept, {
        type: "bar",
        data: {
            labels: dLabels,
            datasets: [{
                label: "Active Grievances",
                data: dData,
                backgroundColor: "#3B82F6",
                borderRadius: 4,
                borderWidth: 1,
                borderColor: "#60A5FA"
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: { color: "rgba(255, 255, 255, 0.05)" },
                    ticks: { color: "#94A3B8", stepSize: 1 }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: "#CBD5E1", font: { size: 11, weight: "500" } }
                }
            }
        }
    });
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
