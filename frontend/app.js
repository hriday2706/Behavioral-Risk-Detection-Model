/**
 * SentinelFlow Interactive Demo Client.
 * Connects frontend dashboard, timeline, and risk panels to Flask backend APIs.
 */

let currentSessionId = null;

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  fetchSessionSummary();
});

function showToast(message, isError = false) {
  const toast = document.getElementById("toast-notification");
  toast.innerText = message;
  toast.style.display = "block";
  toast.style.borderColor = isError ? "var(--risk-high)" : "var(--primary)";
  setTimeout(() => {
    toast.style.display = "none";
  }, 3500);
}

// Fetch active session summary and update all UI elements
async function fetchSessionSummary() {
  try {
    const url = currentSessionId ? `/api/session/current?session_id=${currentSessionId}` : "/api/session/current";
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load session summary");
    const data = await res.json();
    renderSession(data);
  } catch (err) {
    console.error("fetchSessionSummary error:", err);
  }
}

// Render session data onto UI
function renderSession(data) {
  const session = data.session;
  currentSessionId = session.session_id;

  // Account details
  document.getElementById("session-id-display").innerText = session.session_id;
  document.getElementById("user-name").innerText = session.full_name || session.username;
  document.getElementById("user-balance").innerText = `$${Number(session.balance).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
  document.getElementById("user-acc-num").innerText = session.account_number;

  // Device & Location Context Badges
  const devBadge = document.getElementById("device-context-display");
  devBadge.innerText = session.device_familiarity.toUpperCase();
  devBadge.className = `badge ${session.device_familiarity === "unfamiliar" ? "badge-unfamiliar" : "badge-familiar"}`;

  const locBadge = document.getElementById("location-context-display");
  locBadge.innerText = session.location_context.toUpperCase();

  // Verification status badge
  const verBadge = document.getElementById("session-verification-badge");
  if (session.is_verified) {
    verBadge.innerText = "VERIFIED";
    verBadge.className = "badge-verified";
  } else {
    verBadge.innerText = "UNVERIFIED";
    verBadge.className = "badge-unverified";
  }

  // Render events timeline
  renderTimeline(data.events);

  // Render risk assessment & explainability
  renderRiskAssessment(data.risk_assessment);
}

function renderTimeline(events) {
  const list = document.getElementById("events-timeline");
  list.innerHTML = "";
  document.getElementById("event-count-badge").innerText = `${events.length} events recorded`;

  events.slice().reverse().forEach(ev => {
    const item = document.createElement("div");
    const isSensitive = ["password_change_requested", "email_update_requested"].includes(ev.event_type);
    const successClass = ev.success ? "" : "success-false";
    item.className = `timeline-item ${isSensitive ? "sensitive" : ""} ${successClass}`;

    const formattedTime = new Date(ev.timestamp_utc).toLocaleTimeString();
    item.innerHTML = `
      <div class="timeline-header">
        <span class="event-name">${formatEventType(ev.event_type)}</span>
        <span class="event-time">${formattedTime}</span>
      </div>
      <div style="font-size: 0.75rem; color: var(--text-muted);">
        ${ev.success ? "Success" : "Failed / Rejected"} ${ev.metadata && Object.keys(ev.metadata).length ? `· ${JSON.stringify(ev.metadata)}` : ""}
      </div>
      <div class="timeline-badges">
        <span class="badge ${ev.device_familiarity === 'unfamiliar' ? 'badge-unfamiliar' : 'badge-familiar'}">${ev.device_familiarity}</span>
        <span class="badge badge-location">${ev.location_context}</span>
      </div>
    `;
    list.appendChild(item);
  });
}

function formatEventType(type) {
  return type.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

function renderRiskAssessment(risk) {
  if (!risk) return;

  // Category Badge
  const catBadge = document.getElementById("risk-category-badge");
  const pClass = (risk.predicted_class || "low").toLowerCase();
  catBadge.innerText = `${pClass.toUpperCase()} RISK`;
  catBadge.className = `risk-badge risk-${pClass}`;

  // Probabilities
  const probs = risk.class_probabilities || { low: 0, medium: 0, high: 0 };
  const pLow = Math.round((probs.low || 0) * 100);
  const pMed = Math.round((probs.medium || 0) * 100);
  const pHigh = Math.round((probs.high || 0) * 100);

  document.getElementById("prob-low-val").innerText = `${pLow}%`;
  document.getElementById("prob-low-bar").style.width = `${pLow}%`;

  document.getElementById("prob-med-val").innerText = `${pMed}%`;
  document.getElementById("prob-med-bar").style.width = `${pMed}%`;

  document.getElementById("prob-high-val").innerText = `${pHigh}%`;
  document.getElementById("prob-high-bar").style.width = `${pHigh}%`;

  // Explanations
  const expList = document.getElementById("explanation-list");
  expList.innerHTML = "";
  const summaryBullets = risk.model_path_explanation || [];
  if (summaryBullets.length === 0) {
    expList.innerHTML = "<li>No active tree splits.</li>";
  } else {
    summaryBullets.forEach(txt => {
      const li = document.createElement("li");
      li.innerText = txt;
      expList.appendChild(li);
    });
  }

  // Context observations
  const ctxBox = document.getElementById("context-observations-box");
  const ctxObs = risk.context_observations || [];
  if (ctxObs.length === 0) {
    ctxBox.innerText = "No anomalous context detected.";
  } else {
    ctxBox.innerHTML = ctxObs.map(c => `<div>• ${c}</div>`).join("");
  }

  // Policy box
  const pol = risk.risk_policy || { action_allowed: true, status: "allow", message: "Allowed" };
  const polContainer = document.getElementById("policy-status-container");
  const polTitle = document.getElementById("policy-status-title");
  const polMsg = document.getElementById("policy-status-msg");
  const verActionBtn = document.getElementById("verification-action-container");

  if (pol.requires_step_up || !pol.action_allowed) {
    polContainer.className = "policy-status-box verification-required";
    polTitle.innerText = "Policy Status: Verification Required";
    polMsg.innerText = pol.message || "Sensitive action blocked until step-up challenge is completed.";
    verActionBtn.style.display = "block";
  } else {
    polContainer.className = "policy-status-box allowed";
    polTitle.innerText = "Policy Status: Allowed";
    polMsg.innerText = pol.message || "Operations allowed under active policy.";
    verActionBtn.style.display = "none";
  }
}

// User Actions
async function executeAction(actionName) {
  try {
    const res = await fetch(`/api/actions/${actionName}?session_id=${currentSessionId}`, { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      showToast(`Action performed: ${data.action}`);
    } else {
      showToast(`Error: ${data.error}`, true);
    }
    fetchSessionSummary();
  } catch (err) {
    showToast(`Network error: ${err.message}`, true);
  }
}

async function executeSecurityChange(changeType) {
  try {
    const res = await fetch(`/api/actions/security-change?session_id=${currentSessionId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ change_type: changeType }),
    });
    const data = await res.json();
    if (res.status === 403) {
      showToast(`Policy Gate: Sensitive action blocked!`, true);
      openVerificationModal();
    } else if (res.ok) {
      showToast(data.message || "Security change applied!");
    } else {
      showToast(`Error: ${data.message || data.error}`, true);
    }
    fetchSessionSummary();
  } catch (err) {
    showToast(`Network error: ${err.message}`, true);
  }
}

// Simulate failed attempt
async function simulateFailedAttempt() {
  try {
    await fetch("/api/events", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSessionId,
        event_type: "login_failure",
        success: false,
        metadata: { reason: "simulated_wrong_pin" },
      }),
    });
    showToast("Simulated failed password attempt recorded.");
    fetchSessionSummary();
  } catch (err) {
    showToast(`Error: ${err.message}`, true);
  }
}

// Preset Scenarios
async function loadScenario(scenarioKey) {
  try {
    showToast(`Loading Scenario ${scenarioKey}...`);
    const res = await fetch("/api/demo/load-scenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario: scenarioKey }),
    });
    const data = await res.json();
    if (res.ok) {
      currentSessionId = data.summary.session.session_id;
      renderSession(data.summary);
      showToast(`Scenario ${scenarioKey} loaded successfully!`);
    } else {
      showToast(`Error: ${data.error}`, true);
    }
  } catch (err) {
    showToast(`Failed to load scenario: ${err.message}`, true);
  }
}

async function resetDemoSession() {
  try {
    const res = await fetch("/api/demo/reset", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      currentSessionId = data.summary.session.session_id;
      renderSession(data.summary);
      showToast("Demo session reset to baseline!");
    }
  } catch (err) {
    showToast(`Reset error: ${err.message}`, true);
  }
}

// Verification Modal
function openVerificationModal() {
  document.getElementById("verification-modal").style.display = "flex";
}

function closeVerificationModal() {
  document.getElementById("verification-modal").style.display = "none";
}

async function submitVerification() {
  const code = document.getElementById("otp-input-field").value;
  try {
    const res = await fetch("/api/verification/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: currentSessionId, code: code }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast("Verification successful! Sensitive actions unlocked.");
      closeVerificationModal();
      fetchSessionSummary();
    } else {
      showToast("Invalid verification code! Try 123456.", true);
    }
  } catch (err) {
    showToast(`Verification error: ${err.message}`, true);
  }
}

// Model Card Modal
async function openModelModal() {
  const modal = document.getElementById("model-modal");
  const content = document.getElementById("model-modal-content");
  modal.style.display = "flex";
  content.innerText = "Loading model metadata...";

  try {
    const res = await fetch("/api/model/info");
    const meta = await res.json();
    content.innerHTML = `
      <div style="font-size: 0.85rem; line-height: 1.6;">
        <p><strong>Model:</strong> ${meta.model_name} (${meta.algorithm})</p>
        <p><strong>Tree Depth:</strong> ${meta.tree_depth} | <strong>Node Count:</strong> ${meta.node_count}</p>
        <p><strong>Training Samples:</strong> ${meta.training_samples} | <strong>Held-out Test Samples:</strong> ${meta.test_samples}</p>
        <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 0.75rem 0;">
        <h4 style="color: var(--accent); margin-bottom: 0.25rem;">Held-Out Evaluation Metrics:</h4>
        <p><strong>Macro-F1 Score:</strong> ${(meta.test_metrics.macro_f1 * 100).toFixed(1)}% (Baseline: ${(meta.baseline_metrics.macro_f1 * 100).toFixed(1)}%)</p>
        <p><strong>Balanced Accuracy:</strong> ${(meta.test_metrics.balanced_accuracy * 100).toFixed(1)}%</p>
        <p><strong>High-Risk FPR:</strong> ${(meta.test_metrics.false_positive_rate_high * 100).toFixed(2)}%</p>
        <div style="margin-top: 0.5rem; background: rgba(0,0,0,0.3); padding: 0.5rem; border-radius: 4px; font-family: monospace;">
          Per-Class F1 Scores:<br>
          • Low: ${(meta.test_metrics.per_class.low.f1_score * 100).toFixed(1)}%<br>
          • Medium: ${(meta.test_metrics.per_class.medium.f1_score * 100).toFixed(1)}%<br>
          • High: ${(meta.test_metrics.per_class.high.f1_score * 100).toFixed(1)}%
        </div>
      </div>
    `;
  } catch (err) {
    content.innerText = "Failed to load model metadata.";
  }
}

function closeModelModal() {
  document.getElementById("model-modal").style.display = "none";
}
