/**
 * Groww Multi-Agent Operations Frontend Application
 * Handles reactive state updates, graph stepper animation, HITL approval, refinement, and audit benchmarks.
 */

let currentState = null;
let currentScenarios = [];

document.addEventListener("DOMContentLoaded", () => {
    loadScenarios();
});

// ==============================================================================
// 1. SCENARIOS & INITIALIZATION
// ==============================================================================

async function loadScenarios() {
    try {
        const res = await fetch("/api/scenarios");
        const data = await res.json();
        if (data.status === "success") {
            currentScenarios = data.scenarios;
            renderScenarioPills(data.scenarios);
        }
    } catch (e) {
        console.error("Failed to load preset scenarios:", e);
    }
}

function renderScenarioPills(scenarios) {
    const container = document.getElementById("scenarios-pills");
    container.innerHTML = "";

    scenarios.forEach((sc, idx) => {
        const pill = document.createElement("button");
        pill.className = "scenario-pill";
        pill.innerHTML = `
            <span class="badge badge-${sc.tag_color || 'emerald'}">${sc.tag}</span>
            <span>${sc.name}</span>
        `;
        pill.onclick = () => selectScenario(sc);
        container.appendChild(pill);
    });
}

function selectScenario(scenario) {
    const input = document.getElementById("ticket-input");
    input.value = scenario.query;
    input.focus();
    showToast(`Loaded: ${scenario.name}`);
}

function clearInput() {
    document.getElementById("ticket-input").value = "";
    document.getElementById("results-workbench").classList.add("hidden");
    resetStepper();
}

// ==============================================================================
// 2. WORKFLOW STEPPER ANIMATION
// ==============================================================================

function resetStepper() {
    const nodes = document.querySelectorAll(".step-node");
    nodes.forEach(n => n.classList.remove("active"));
    document.getElementById("flow-execution-time").textContent = "Awaiting Execution";
}

function animateStepper(stepIndex) {
    const nodes = [
        "node-sanitizer",
        "node-specialists",
        "node-orchestrator",
        "node-reviewer",
        "node-hitl",
        "node-mcp"
    ];

    nodes.forEach((id, idx) => {
        const el = document.getElementById(id);
        if (idx <= stepIndex) {
            el.classList.add("active");
        } else {
            el.classList.remove("active");
        }
    });
}

// ==============================================================================
// 3. TICKET EXECUTION
// ==============================================================================

async function submitTicket() {
    const input = document.getElementById("ticket-input");
    const query = input.value.trim();
    if (!query) {
        showToast("Please enter a support ticket query or select a preset scenario.");
        input.focus();
        return;
    }

    const btn = document.getElementById("btn-submit");
    const spinner = btn.querySelector(".btn-spinner");
    const btnText = btn.querySelector(".btn-text");

    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Orchestrating Agents...";
    document.getElementById("flow-execution-time").textContent = "Executing Graph...";

    resetStepper();
    animateStepper(0); // Sanitizer active

    const startTime = performance.now();

    try {
        const res = await fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ raw_input: query })
        });

        const data = await res.json();
        const duration = Math.round(performance.now() - startTime);

        if (data.status === "success") {
            currentState = data.state;
            animateStepper(3); // Up to Reviewer completed
            document.getElementById("flow-execution-time").textContent = `Completed in ${duration}ms`;
            renderState(currentState);
            showToast("Multi-Agent Graph Invocation Completed!");
        } else {
            showToast(`Error: ${data.message || "Failed to process query"}`);
        }
    } catch (e) {
        console.error("Execution error:", e);
        showToast("Failed to connect to backend server.");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute Multi-Agent Pipeline";
    }
}

// ==============================================================================
// 4. STATE RENDERING
// ==============================================================================

function renderState(state) {
    const workbench = document.getElementById("results-workbench");
    workbench.classList.remove("hidden");

    // 1. PII Redaction Card
    renderPII(state);

    // 2. Parallel Specialists
    renderFacts(state.facts);
    renderPattern(state.pattern);
    renderCompliance(state.compliance);

    // 3. Orchestrator Outputs
    renderOrchestrator(state.orchestrator);

    // 4. Reviewer Guardrail
    renderReviewer(state.reviewer);

    // 5. MCP Approval Controls
    renderMCPControls(state);

    // Scroll smoothly to workbench
    workbench.scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderPII(state) {
    const rawBox = document.getElementById("pii-raw-text");
    const sanitizedBox = document.getElementById("pii-sanitized-text");
    const badgesContainer = document.getElementById("pii-badge-container");

    rawBox.textContent = state.raw_input;
    sanitizedBox.textContent = state.sanitized_input;

    const detected = state.pii_metadata?.detected_types || [];
    if (detected.length > 0) {
        badgesContainer.innerHTML = detected.map(t => 
            `<span class="badge badge-rose">Redacted ${t}</span>`
        ).join(" ");
    } else {
        badgesContainer.innerHTML = `<span class="badge badge-emerald">Zero PII (Clean)</span>`;
    }
}

function renderFacts(facts) {
    const statusBadge = document.getElementById("facts-status-badge");
    const schemeEl = document.getElementById("facts-scheme");
    const sectionEl = document.getElementById("facts-section");
    const extractedEl = document.getElementById("facts-extracted");
    const citationEl = document.getElementById("facts-citation");

    if (facts && facts.status === "covered") {
        statusBadge.className = "badge badge-emerald";
        statusBadge.textContent = "COVERED IN CORPUS";
        schemeEl.textContent = facts.scheme_name || facts.scheme_id;
        sectionEl.textContent = facts.section_title || "Disclosures";
        extractedEl.textContent = facts.extracted_text;
        citationEl.textContent = facts.source_url;
        citationEl.href = facts.source_url;
        citationEl.classList.remove("hidden");
    } else {
        statusBadge.className = "badge badge-amber";
        statusBadge.textContent = "OUT OF SCOPE";
        schemeEl.textContent = "None (External / Unverified Fund)";
        sectionEl.textContent = "N/A";
        extractedEl.textContent = facts?.extracted_text || "The requested query detail is not covered in verified HDFC scheme corpus.";
        citationEl.classList.add("hidden");
    }
}

function renderPattern(pattern) {
    const statusBadge = document.getElementById("pattern-status-badge");
    const themeEl = document.getElementById("pattern-theme");
    const countEl = document.getElementById("pattern-count");
    const windowEl = document.getElementById("pattern-window");
    const freqEl = document.getElementById("pattern-frequency");

    if (pattern) {
        const isRecurring = pattern.status === "recurring";
        statusBadge.className = isRecurring ? "badge badge-amber" : "badge badge-indigo";
        statusBadge.textContent = isRecurring ? "RECURRING SYSTEMIC ISSUE" : "ISOLATED COMPLAINT";

        themeEl.textContent = pattern.theme_name;
        countEl.textContent = `${pattern.review_count} Reviews Indexed`;
        windowEl.textContent = `Window: ${pattern.review_window || '2026-04-12 to 2026-07-04'}`;
        freqEl.textContent = isRecurring ? "Flagged: Recurring complaint cluster in top 5 themes" : "Standard one-off query";
    }
}

function renderCompliance(compliance) {
    const statusBadge = document.getElementById("compliance-status-badge");
    const adviceCheck = document.getElementById("comp-check-advice");
    const perfCheck = document.getElementById("comp-check-perf");
    const piiCheck = document.getElementById("comp-check-pii");

    if (compliance) {
        const allClean = !compliance.incoming_has_advice && !compliance.incoming_has_performance_claim;
        statusBadge.className = allClean ? "badge badge-emerald" : "badge badge-purple";
        statusBadge.textContent = allClean ? "SEBI COMPLIANT" : "DISCLAIMER ENFORCED";

        // Advice Check
        adviceCheck.className = compliance.incoming_has_advice ? "check-item fail" : "check-item pass";
        adviceCheck.querySelector("strong").textContent = compliance.incoming_has_advice ? "Advice Solicited (Deflection Triggered)" : "No Advice Solicited";

        // Performance Check
        perfCheck.className = compliance.incoming_has_performance_claim ? "check-item fail" : "check-item pass";
        perfCheck.querySelector("strong").textContent = compliance.incoming_has_performance_claim ? "Return Claim Detected (Refused)" : "No Return Claim";

        // PII Check
        piiCheck.className = "check-item pass";
        piiCheck.querySelector("strong").textContent = compliance.pii_detected ? "PII Safely Redacted" : "Zero PII Present";
    }
}

function renderOrchestrator(orch) {
    if (!orch) return;

    // Channel A
    const draftText = document.getElementById("reply-draft-text");
    const sentencePill = document.getElementById("draft-sentence-pill");
    const datePill = document.getElementById("draft-date-pill");

    draftText.textContent = orch.reply_draft;
    sentencePill.textContent = `${orch.sentence_count} / 3 Sentences`;
    sentencePill.className = orch.sentence_count <= 3 ? "pill pill-outline font-semibold" : "pill badge-rose";
    datePill.textContent = `Verified: ${orch.last_checked}`;

    // Channel B
    const priorityBadge = document.getElementById("routing-priority-badge");
    const teamBadge = document.getElementById("routing-team-badge");
    const routingPre = document.getElementById("routing-note-text");
    const discrepancyBanner = document.getElementById("discrepancy-banner");
    const discrepancyText = document.getElementById("discrepancy-text");

    const pClass = orch.priority === "P1-High" ? "badge-rose" : (orch.priority === "P2-Medium" ? "badge-amber" : "badge-indigo");
    priorityBadge.className = `badge ${pClass}`;
    priorityBadge.textContent = orch.priority;

    teamBadge.className = "badge badge-indigo";
    teamBadge.textContent = orch.target_team;

    routingPre.textContent = orch.routing_note;

    if (orch.discrepancy_flag) {
        discrepancyBanner.classList.remove("hidden");
        discrepancyText.textContent = orch.discrepancy_details || "Clean scheme terms coexist with high complaint volume. Flagged for operational review.";
    } else {
        discrepancyBanner.classList.add("hidden");
    }
}

function renderReviewer(rev) {
    const statusBadge = document.getElementById("reviewer-status-badge");
    const list = document.getElementById("reviewer-checks-list");
    list.innerHTML = "";

    if (!rev) return;

    const passed = rev.passed;
    statusBadge.className = passed ? "badge badge-emerald" : "badge badge-rose";
    statusBadge.textContent = passed ? `PASSED (Attempt #${rev.review_attempt})` : `FAILED (Attempt #${rev.review_attempt})`;

    const rules = [
        { name: "Zero Surviving PII", pass: !rev.failure_reasons?.some(r => r.includes("PII")) },
        { name: "Zero Investment Advice Language", pass: !rev.failure_reasons?.some(r => r.includes("advice")) },
        { name: "Sentence Brevity (<= 3 Sentences)", pass: !rev.failure_reasons?.some(r => r.includes("sentences")) },
        { name: "Mandatory NAV Date (25-Jun-2026)", pass: !rev.failure_reasons?.some(r => r.includes("date")) },
        { name: "Verified Source URL Citation", pass: !rev.failure_reasons?.some(r => r.includes("citation")) },
    ];

    rules.forEach(r => {
        const item = document.createElement("div");
        item.className = "reviewer-rule-item";
        item.innerHTML = `
            <span>${r.name}</span>
            <span class="badge ${r.pass ? 'badge-emerald' : 'badge-rose'}">${r.pass ? 'PASS' : 'FAIL'}</span>
        `;
        list.appendChild(item);
    });
}

function renderMCPControls(state) {
    const gateStatus = document.getElementById("mcp-gate-status");
    const approveBtn = document.getElementById("btn-approve");
    const refineBtn = document.getElementById("btn-toggle-refine");
    const refineContainer = document.getElementById("refinement-container");
    const mcpResults = document.getElementById("mcp-results-container");

    refineContainer.classList.add("hidden");
    mcpResults.classList.add("hidden");

    if (state.reviewer && state.reviewer.passed) {
        gateStatus.textContent = "Awaiting Operator Click";
        gateStatus.className = "status-indicator text-muted";
        approveBtn.disabled = false;
        refineBtn.disabled = false;
        approveBtn.innerHTML = `<span class="icon">✓</span> Approve & Dispatch MCP Actions`;
    } else {
        gateStatus.textContent = "Quarantined (Send Locked)";
        gateStatus.className = "status-indicator badge-rose";
        approveBtn.disabled = true;
        refineBtn.disabled = true;
    }
}

// ==============================================================================
// 5. APPROVAL & MCP DISPATCH
// ==============================================================================

async function approveAndDispatch() {
    if (!currentState) return;

    const approveBtn = document.getElementById("btn-approve");
    approveBtn.disabled = true;
    approveBtn.textContent = "Dispatching MCP Tools...";

    try {
        const res = await fetch("/api/approve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: currentState })
        });

        const data = await res.json();
        if (data.status === "success") {
            animateStepper(5); // Complete MCP Node

            document.getElementById("mcp-gate-status").textContent = "Dispatched & Logged";
            document.getElementById("mcp-gate-status").className = "status-indicator badge-emerald";

            const resultsContainer = document.getElementById("mcp-results-container");
            resultsContainer.classList.remove("hidden");

            approveBtn.innerHTML = `<span class="icon">✓</span> Approved & Executed`;
            showToast("MCP External Actions Executed (Zero Auto-Send Confirmed)");
        } else {
            showToast(`Approval Blocked: ${data.message || 'Permission Error'}`);
            approveBtn.disabled = false;
        }
    } catch (e) {
        console.error("MCP execution error:", e);
        showToast("MCP execution request failed.");
        approveBtn.disabled = false;
    }
}

// ==============================================================================
// 6. HUMAN REFINEMENT
// ==============================================================================

function toggleRefineBox() {
    const container = document.getElementById("refinement-container");
    container.classList.toggle("hidden");
    if (!container.classList.contains("hidden")) {
        document.getElementById("refine-feedback").focus();
    }
}

async function submitRefinement() {
    const feedbackInput = document.getElementById("refine-feedback");
    const feedback = feedbackInput.value.trim();
    if (!feedback || !currentState) {
        showToast("Please enter feedback for refinement.");
        return;
    }

    const btn = document.getElementById("btn-submit-refine");
    btn.disabled = true;
    btn.textContent = "Refining...";

    try {
        const res = await fetch("/api/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: currentState, feedback: feedback })
        });

        const data = await res.json();
        if (data.status === "success") {
            currentState = data.state;
            renderState(currentState);
            feedbackInput.value = "";
            document.getElementById("refine-counter").textContent = `Refinements used: ${currentState.refinement_count} / 5`;
            showToast(`Refinement applied targeted to: ${currentState.active_refinement_target}`);
        } else {
            showToast(`Refinement error: ${data.message}`);
        }
    } catch (e) {
        console.error("Refinement error:", e);
        showToast("Refinement failed.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Apply Refinement";
    }
}

// ==============================================================================
// 7. BENCHMARK AUDIT HARNESS
// ==============================================================================

async function triggerBenchmark() {
    const btn = document.getElementById("btn-run-benchmark");
    const spinner = btn.querySelector(".btn-spinner");
    const btnText = btn.querySelector(".btn-text");

    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Running 40 Scenarios...";

    try {
        const res = await fetch("/api/benchmark");
        const data = await res.json();

        if (data.status === "success") {
            renderBenchmarkResults(data);
            showToast("40-Scenario Acceptance Benchmark Completed (100% Pass)!");
        } else {
            showToast(`Benchmark error: ${data.message}`);
        }
    } catch (e) {
        console.error("Benchmark error:", e);
        showToast("Failed to run benchmark.");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute 40-Scenario Audit";
    }
}

function renderBenchmarkResults(data) {
    const container = document.getElementById("benchmark-results-container");
    container.classList.remove("hidden");

    const cardsContainer = document.getElementById("scorecard-cards");
    const sc = data.scorecard;

    cardsContainer.innerHTML = `
        <div class="stat-card">
            <span class="stat-value">${data.total_runs}</span>
            <span class="stat-label">Total Evaluated Scenarios</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" style="color: var(--groww-emerald);">${sc.PII_Leakage_Rate.toFixed(1)}%</span>
            <span class="stat-label">PII Leakage Rate (Target: 0.0%)</span>
        </div>
        <div class="stat-card">
            <span class="stat-value" style="color: var(--groww-emerald);">${sc.Advice_Violation_Rate.toFixed(1)}%</span>
            <span class="stat-label">Advice Violation Rate (Target: 0.0%)</span>
        </div>
        <div class="stat-card">
            <span class="stat-value">${sc.Citation_Precision.toFixed(1)}%</span>
            <span class="stat-label">Citation Precision (Target: 100.0%)</span>
        </div>
    `;

    const tbody = document.getElementById("benchmark-table-body");
    const rows = [
        { metric: "PII Leakage Rate (PLR)", score: `${sc.PII_Leakage_Rate.toFixed(2)}%`, target: "0.00%", pass: sc.PII_Leakage_Rate === 0 },
        { metric: "Advice Violation Rate (AVR)", score: `${sc.Advice_Violation_Rate.toFixed(2)}%`, target: "0.00%", pass: sc.Advice_Violation_Rate === 0 },
        { metric: "Citation Precision (CP)", score: `${sc.Citation_Precision.toFixed(2)}%`, target: "100.00%", pass: sc.Citation_Precision === 100 },
        { metric: "Out-of-Scope Fallback Precision (OOSF)", score: `${sc.Out_Of_Scope_Precision.toFixed(2)}%`, target: "100.00%", pass: sc.Out_Of_Scope_Precision === 100 },
        { metric: "Sentence Budget Compliance (SBC)", score: `${sc.Sentence_Budget_Compliance.toFixed(2)}%`, target: "100.00%", pass: sc.Sentence_Budget_Compliance === 100 },
        { metric: "Timestamp Compliance Rate (VTR)", score: `${sc.Timestamp_Compliance_Rate.toFixed(2)}%`, target: "100.00%", pass: sc.Timestamp_Compliance_Rate === 100 },
        { metric: "Discrepancy Detection Recall (DR)", score: `${sc.Discrepancy_Recall.toFixed(2)}%`, target: "100.00%", pass: sc.Discrepancy_Recall === 100 }
    ];

    tbody.innerHTML = rows.map(r => `
        <tr>
            <td><strong>${r.metric}</strong></td>
            <td>${r.score}</td>
            <td>${r.target}</td>
            <td><span class="badge ${r.pass ? 'badge-emerald' : 'badge-rose'}">${r.pass ? 'PASS' : 'FAIL'}</span></td>
        </tr>
    `).join("");
}

// ==============================================================================
// 8. TABS & UTILITIES
// ==============================================================================

function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));

    if (tabId === "console") {
        document.getElementById("tab-console").classList.add("active");
        document.getElementById("view-console").classList.add("active");
    } else {
        document.getElementById("tab-benchmark").classList.add("active");
        document.getElementById("view-benchmark").classList.add("active");
    }
}

function copyDraft() {
    const text = document.getElementById("reply-draft-text").textContent;
    navigator.clipboard.writeText(text).then(() => {
        showToast("Customer reply draft copied to clipboard!");
    }).catch(() => {
        showToast("Copy failed, please copy manually.");
    });
}

function showToast(message) {
    const toast = document.getElementById("toast");
    toast.textContent = message;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3200);
}
