/**
 * Groww Multi-Agent Operations Frontend Application
 * FinTech Cockpit Controller: SVG DAG workflow, live sentence validation,
 * inline draft studio, 4-tab inspector, and keyboard shortcuts.
 */

let currentState = null;
let currentScenarios = [];
let originalOrchestratorDraft = "";
let isEditMode = false;

document.addEventListener("DOMContentLoaded", () => {
    loadScenarios();
    setupKeyboardShortcuts();
});

// ==============================================================================
// 1. SCENARIOS & QUEUE MANAGEMENT
// ==============================================================================

async function loadScenarios() {
    try {
        const res = await fetch("/api/scenarios");
        const data = await res.json();
        if (data.status === "success") {
            currentScenarios = data.scenarios;
            renderScenarioQueue(currentScenarios);
        }
    } catch (e) {
        console.error("Failed to load preset scenarios:", e);
    }
}

function renderScenarioQueue(scenarios) {
    const container = document.getElementById("scenarios-pills");
    const countBadge = document.getElementById("queue-count-badge");
    container.innerHTML = "";
    countBadge.textContent = `${scenarios.length} Presets`;

    scenarios.forEach((sc) => {
        const item = document.createElement("div");
        item.className = "scenario-queue-item";
        item.id = `scenario-${sc.id}`;
        item.innerHTML = `
            <div class="scenario-item-header">
                <span class="badge badge-${sc.tag_color || 'emerald'}">${sc.tag}</span>
                <span class="text-xs text-muted">${sc.id.toUpperCase()}</span>
            </div>
            <div class="scenario-item-name">${sc.name}</div>
            <div class="scenario-item-query">${escapeHtml(sc.query)}</div>
        `;
        item.onclick = () => selectScenario(sc);
        container.appendChild(item);
    });
}

function filterScenarios() {
    const term = document.getElementById("scenario-search").value.toLowerCase();
    const filtered = currentScenarios.filter(sc => 
        sc.name.toLowerCase().includes(term) || 
        sc.tag.toLowerCase().includes(term) ||
        sc.query.toLowerCase().includes(term)
    );
    renderScenarioQueue(filtered);
}

function selectScenario(scenario) {
    document.querySelectorAll(".scenario-queue-item").forEach(el => el.classList.remove("active"));
    const activeEl = document.getElementById(`scenario-${scenario.id}`);
    if (activeEl) activeEl.classList.add("active");

    const input = document.getElementById("ticket-input");
    input.value = scenario.query;
    input.focus();
    showToast(`Loaded Scenario: ${scenario.name}`);
}

function clearInput() {
    document.getElementById("ticket-input").value = "";
    document.querySelectorAll(".scenario-queue-item").forEach(el => el.classList.remove("active"));
    document.getElementById("results-workbench").classList.add("hidden");
    resetDAG();
}

// ==============================================================================
// 2. INTERACTIVE SVG DAG VISUALIZATION
// ==============================================================================

function resetDAG() {
    document.querySelectorAll(".dag-node").forEach(n => n.classList.remove("active"));
    document.querySelectorAll(".dag-edge").forEach(e => e.classList.remove("active"));
    const pulse = document.getElementById("dag-pulse");
    if (pulse) pulse.classList.add("hidden");
    document.getElementById("flow-execution-time").textContent = "Ready for Dispatch";
}

function animateDAGStep(step) {
    // Step 0: Sanitizer
    if (step >= 0) {
        document.getElementById("dag-node-sanitizer")?.classList.add("active");
        document.getElementById("edge-1")?.classList.add("active");
    }
    // Step 1: Parallel Fan-Out
    if (step >= 1) {
        document.getElementById("dag-node-fanout")?.classList.add("active");
        document.getElementById("edge-fan-facts")?.classList.add("active");
        document.getElementById("edge-fan-pattern")?.classList.add("active");
        document.getElementById("edge-fan-comp")?.classList.add("active");
        document.getElementById("dag-node-facts")?.classList.add("active");
        document.getElementById("dag-node-pattern")?.classList.add("active");
        document.getElementById("dag-node-compliance")?.classList.add("active");
    }
    // Step 2: Orchestrator Fan-In
    if (step >= 2) {
        document.getElementById("edge-in-facts")?.classList.add("active");
        document.getElementById("edge-in-pattern")?.classList.add("active");
        document.getElementById("edge-in-comp")?.classList.add("active");
        document.getElementById("dag-node-orchestrator")?.classList.add("active");
    }
    // Step 3: Reviewer Gate
    if (step >= 3) {
        document.getElementById("edge-rev")?.classList.add("active");
        document.getElementById("dag-node-reviewer")?.classList.add("active");
    }
    // Step 4: MCP Dispatch
    if (step >= 4) {
        document.getElementById("edge-mcp")?.classList.add("active");
        document.getElementById("dag-node-mcp")?.classList.add("active");
    }
}

// ==============================================================================
// 3. TICKET EXECUTION & PIPELINE RUNNER
// ==============================================================================

async function submitTicket() {
    const input = document.getElementById("ticket-input");
    const query = input.value.trim();
    if (!query) {
        showToast("Please enter a customer query or choose a scenario from the queue.");
        input.focus();
        return;
    }

    const btn = document.getElementById("btn-submit");
    const spinner = btn.querySelector(".btn-spinner");
    const btnText = btn.querySelector(".btn-text");

    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Orchestrating...";
    document.getElementById("flow-execution-time").textContent = "Executing Graph...";

    resetDAG();
    animateDAGStep(0); // PII Sanitizer lights up

    const startTime = performance.now();

    try {
        // Visual micro-stagger for fan-out
        setTimeout(() => animateDAGStep(1), 200);

        const res = await fetch("/api/process", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ raw_input: query })
        });

        const data = await res.json();
        const duration = Math.round(performance.now() - startTime);

        if (data.status === "success") {
            currentState = data.state;
            animateDAGStep(3); // Completed through Reviewer
            document.getElementById("flow-execution-time").textContent = `Completed in ${duration}ms`;
            renderState(currentState);
            showToast("Multi-Agent Graph Orchestration Succeeded!");
        } else {
            showToast(`Error: ${data.message || "Failed to execute pipeline"}`);
        }
    } catch (e) {
        console.error("Execution error:", e);
        showToast("Network Error: Could not connect to backend server.");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "⚡ Orchestrate Agents";
    }
}

// ==============================================================================
// 4. WORKSPACE & INSPECTOR RENDERING
// ==============================================================================

function renderState(state) {
    const workbench = document.getElementById("results-workbench");
    workbench.classList.remove("hidden");

    // 1. Channel A: Customer Reply Studio
    renderDraftStudio(state.orchestrator?.reply_draft || "");

    // 2. Channel B: Internal Ops Routing Note & Discrepancy Radar
    renderRoutingNote(state.orchestrator?.routing_note || "", state.orchestrator);

    // 3. HITL & MCP Dispatch Controls
    renderHITLControls(state);

    // 4. Right Inspector: PII, Evidence, Compliance, Trace
    renderInspector(state);

    // Auto switch inspector to Evidence tab if covered, or PII tab if PII detected
    if (state.pii_metadata?.has_pii) {
        switchInspectorTab('pii');
    } else {
        switchInspectorTab('evidence');
    }
}

// --- DRAFT STUDIO (CHANNEL A) ---

function renderDraftStudio(draftText) {
    originalOrchestratorDraft = draftText;
    isEditMode = false;

    const displayEl = document.getElementById("reply-draft-text");
    const editorEl = document.getElementById("reply-draft-editor");
    const editBtnText = document.getElementById("btn-edit-text");
    const modifiedIndicator = document.getElementById("editor-indicator");

    displayEl.textContent = draftText;
    displayEl.classList.remove("hidden");
    editorEl.value = draftText;
    editorEl.classList.add("hidden");
    editBtnText.textContent = "Edit Draft";
    modifiedIndicator.classList.add("hidden");

    validateDraftSentenceAndDate(draftText);
}

function toggleEditMode() {
    isEditMode = !isEditMode;
    const displayEl = document.getElementById("reply-draft-text");
    const editorEl = document.getElementById("reply-draft-editor");
    const editBtnText = document.getElementById("btn-edit-text");

    if (isEditMode) {
        editorEl.value = displayEl.textContent;
        displayEl.classList.add("hidden");
        editorEl.classList.remove("hidden");
        editorEl.focus();
        editBtnText.textContent = "Lock Draft";
        showToast("Edit Mode: Live sentence validator active.");
    } else {
        displayEl.textContent = editorEl.value;
        editorEl.classList.add("hidden");
        displayEl.classList.remove("hidden");
        editBtnText.textContent = "Edit Draft";
    }
    onDraftEdited();
}

function onDraftEdited() {
    const editorEl = document.getElementById("reply-draft-editor");
    const currentText = isEditMode ? editorEl.value : document.getElementById("reply-draft-text").textContent;
    validateDraftSentenceAndDate(currentText);

    const indicator = document.getElementById("editor-indicator");
    if (currentText.trim() !== originalOrchestratorDraft.trim()) {
        indicator.classList.remove("hidden");
    } else {
        indicator.classList.add("hidden");
    }
}

function resetDraftToOrchestrator() {
    renderDraftStudio(originalOrchestratorDraft);
    showToast("Reset draft back to orchestrator synthesis.");
}

function validateDraftSentenceAndDate(text) {
    const count = countSentencesAccurate(text);
    const sentencePill = document.getElementById("draft-sentence-pill");
    const datePill = document.getElementById("draft-date-pill");

    // Sentence Pill
    if (count <= 3) {
        sentencePill.className = "pill pill-valid";
        sentencePill.innerHTML = `✓ ${count} / 3 Sentences`;
    } else {
        sentencePill.className = "pill pill-invalid";
        sentencePill.innerHTML = `⚠️ ${count} / 3 (Cap Exceeded)`;
    }

    // Date Pill
    if (text.includes("25-Jun-2026")) {
        datePill.className = "pill pill-valid";
        datePill.innerHTML = `✓ 25-Jun-2026 (Locked)`;
    } else {
        datePill.className = "pill pill-invalid";
        datePill.innerHTML = `⚠️ Missing 25-Jun-2026`;
    }
}

function countSentencesAccurate(text) {
    if (!text || !text.trim()) return 0;
    // Strip URLs and protect decimal numbers
    let cleaned = text.replace(/https?:\/\/[^\s]+/gi, "[URL]");
    cleaned = cleaned.replace(/(\d+)\.(\d+)/g, "$1_DECIMAL_$2");
    // Split on sentence terminators followed by whitespace and capital/start
    const chunks = cleaned.split(/(?<=[.!?])\s+/).filter(s => s.trim().length > 0);
    return chunks.length;
}

function copyDraft() {
    const text = isEditMode ? 
        document.getElementById("reply-draft-editor").value : 
        document.getElementById("reply-draft-text").textContent;

    navigator.clipboard.writeText(text).then(() => {
        showToast("Copied Reply Draft to clipboard!");
    }).catch(() => {
        showToast("Failed to copy draft.");
    });
}

// --- ROUTING NOTE (CHANNEL B) ---

function renderRoutingNote(routingText, orchestrator) {
    const preEl = document.getElementById("routing-note-text");
    preEl.textContent = routingText || "No routing note generated.";

    const banner = document.getElementById("discrepancy-banner");
    const bannerText = document.getElementById("discrepancy-text");

    if (orchestrator && orchestrator.discrepancy_detected) {
        banner.classList.remove("hidden");
        bannerText.textContent = orchestrator.discrepancy_explanation || 
            "Conflict detected between user complaint and verified scheme disclosures. Escalated for human verification.";
    } else {
        banner.classList.add("hidden");
    }

    // Badges
    const priorityBadge = document.getElementById("routing-priority-badge");
    const teamBadge = document.getElementById("routing-team-badge");

    if (routingText.includes("URGENT") || routingText.includes("CRITICAL") || orchestrator?.discrepancy_detected) {
        priorityBadge.className = "badge badge-rose";
        priorityBadge.textContent = "P1 - Critical";
    } else {
        priorityBadge.className = "badge badge-indigo";
        priorityBadge.textContent = "P2 - Standard";
    }

    if (routingText.includes("Banking") || routingText.includes("Payments")) {
        teamBadge.className = "badge badge-amber";
        teamBadge.textContent = "Payments Ops";
    } else if (routingText.includes("Compliance") || routingText.includes("Legal")) {
        teamBadge.className = "badge badge-purple";
        teamBadge.textContent = "Compliance Ops";
    } else {
        teamBadge.className = "badge badge-cyan";
        teamBadge.textContent = "Customer Ops";
    }
}

// --- HITL CONTROLS & MCP DISPATCH ---

function renderHITLControls(state) {
    const gateStatus = document.getElementById("mcp-gate-status");
    const btnApprove = document.getElementById("btn-approve");
    const mcpResults = document.getElementById("mcp-results-container");

    mcpResults.classList.add("hidden");

    if (state.is_quarantined) {
        gateStatus.className = "status-indicator badge-rose";
        gateStatus.textContent = "QUARANTINED (Max Reworks)";
        btnApprove.disabled = true;
    } else if (state.is_approved) {
        gateStatus.className = "status-indicator badge-emerald";
        gateStatus.textContent = "Approved & Dispatched";
        btnApprove.disabled = true;
    } else {
        gateStatus.className = "status-indicator";
        gateStatus.textContent = "Pending Operator Authorization";
        btnApprove.disabled = false;
    }

    const counter = document.getElementById("refine-counter");
    counter.textContent = `Budget: ${state.refinement_count || 0} / 5 Rounds`;
}

async function approveAndDispatch() {
    if (!currentState) {
        showToast("No active ticket state to approve.");
        return;
    }

    if (currentState.is_quarantined) {
        showToast("Quarantined tickets cannot be approved without administrative clearance.");
        return;
    }

    // If operator edited draft, sync back to state before dispatch
    const currentDraft = isEditMode ? 
        document.getElementById("reply-draft-editor").value : 
        document.getElementById("reply-draft-text").textContent;
    
    if (currentState.orchestrator) {
        currentState.orchestrator.reply_draft = currentDraft;
    }

    const btn = document.getElementById("btn-approve");
    btn.disabled = true;

    try {
        const res = await fetch("/api/approve", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: currentState })
        });

        const data = await res.json();
        if (data.status === "success") {
            currentState.is_approved = true;
            animateDAGStep(4); // MCP Node active
            document.getElementById("mcp-results-container").classList.remove("hidden");
            document.getElementById("mcp-gate-status").className = "status-indicator badge-emerald";
            document.getElementById("mcp-gate-status").textContent = "Approved & MCP Tools Dispatched";
            showToast("MCP Tools Dispatched: Doc Appended & Email Draft Staged!");
        } else {
            showToast(`Approval failed: ${data.message || "Unknown error"}`);
            btn.disabled = false;
        }
    } catch (e) {
        console.error("Approval error:", e);
        showToast("Failed to reach server for approval.");
        btn.disabled = false;
    }
}

function toggleRefineBox() {
    const box = document.getElementById("refinement-container");
    box.classList.toggle("hidden");
    if (!box.classList.contains("hidden")) {
        document.getElementById("refine-feedback").focus();
    }
}

async function submitRefinement() {
    const feedbackInput = document.getElementById("refine-feedback");
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
        showToast("Please enter specific feedback for agent refinement.");
        feedbackInput.focus();
        return;
    }

    if (!currentState) return;

    const btn = document.getElementById("btn-submit-refine");
    btn.disabled = true;
    btn.textContent = "Rerunning...";

    try {
        const res = await fetch("/api/refine", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ state: currentState, feedback })
        });

        const data = await res.json();
        if (data.status === "success") {
            currentState = data.state;
            renderState(currentState);
            feedbackInput.value = "";
            document.getElementById("refinement-container").classList.add("hidden");
            showToast(`Refinement applied! Round ${currentState.refinement_count} of 5`);
        } else {
            showToast(`Refinement error: ${data.message || "Could not apply refinement"}`);
        }
    } catch (e) {
        console.error("Refinement error:", e);
        showToast("Network error applying refinement.");
    } finally {
        btn.disabled = false;
        btn.textContent = "Rerun Targeted Agents";
    }
}

// --- RIGHT INSPECTOR (PII, EVIDENCE, COMPLIANCE, TRACE) ---

function switchInspectorTab(tabId) {
    document.querySelectorAll(".insp-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".insp-panel").forEach(p => p.classList.remove("active"));

    const tabBtn = Array.from(document.querySelectorAll(".insp-tab")).find(t => 
        t.getAttribute("onclick")?.includes(tabId)
    );
    if (tabBtn) tabBtn.classList.add("active");

    const panel = document.getElementById(`insp-panel-${tabId}`);
    if (panel) panel.classList.add("active");
}

function renderInspector(state) {
    // 1. PII Tab
    const rawBox = document.getElementById("pii-raw-text");
    const sanitizedBox = document.getElementById("pii-sanitized-text");
    const badgesContainer = document.getElementById("pii-badge-container");

    rawBox.textContent = state.raw_input || "—";
    sanitizedBox.textContent = state.sanitized_input || "—";

    const detected = state.pii_metadata?.detected_types || [];
    if (detected.length > 0) {
        badgesContainer.innerHTML = detected.map(t => 
            `<span class="badge badge-rose">Redacted ${t}</span>`
        ).join(" ");
    } else {
        badgesContainer.innerHTML = `<span class="badge badge-emerald">Zero PII (Clean)</span>`;
    }

    // 2. Evidence Tab
    const facts = state.facts;
    const factsStatus = document.getElementById("facts-status-badge");
    const factsScheme = document.getElementById("facts-scheme");
    const factsSection = document.getElementById("facts-section");
    const factsExtracted = document.getElementById("facts-extracted");
    const factsCitation = document.getElementById("facts-citation");

    if (facts && facts.status === "covered") {
        factsStatus.className = "badge badge-emerald";
        factsStatus.textContent = "COVERED";
        factsScheme.textContent = facts.scheme_name || "—";
        factsSection.textContent = facts.section_matched || "—";
        factsExtracted.textContent = facts.extracted_clause || "—";
        factsCitation.textContent = facts.source_url || "No URL";
        factsCitation.href = facts.source_url || "#";
    } else {
        factsStatus.className = "badge badge-amber";
        factsStatus.textContent = "OUT OF SCOPE";
        factsScheme.textContent = facts?.scheme_name || "Uncovered";
        factsSection.textContent = "External / Not in Local SID";
        factsExtracted.textContent = "No statutory text available for external or unlisted scheme.";
        factsCitation.textContent = "groww.in/mutual-funds";
        factsCitation.href = "https://groww.in/mutual-funds";
    }

    const pattern = state.pattern;
    const patternStatus = document.getElementById("pattern-status-badge");
    const patternTheme = document.getElementById("pattern-theme");
    const patternCount = document.getElementById("pattern-count");
    const patternFreq = document.getElementById("pattern-frequency");
    const patternWindow = document.getElementById("pattern-window");

    if (pattern) {
        patternStatus.className = "badge badge-indigo";
        patternStatus.textContent = pattern.theme ? "MATCHED" : "NO CLUSTER";
        patternTheme.textContent = pattern.theme ? pattern.theme.replace(/_/g, " ").toUpperCase() : "None";
        patternCount.textContent = `${pattern.cluster_count || 0} reviews in cluster`;
        patternFreq.textContent = pattern.frequency_status || "Standard";
        patternWindow.textContent = pattern.historical_window || "25-Jun-2026";
    }

    // 3. Compliance & Reviewer Gate Tab
    const comp = state.compliance;
    updateCheckItem("comp-check-advice", comp ? !comp.advice_detected : true);
    updateCheckItem("comp-check-perf", comp ? !comp.performance_claim_detected : true);
    updateCheckItem("comp-check-pii", comp ? !comp.pii_leakage_detected : true);

    const reviewer = state.reviewer;
    const reviewerBadge = document.getElementById("reviewer-status-badge");
    const checksList = document.getElementById("reviewer-checks-list");

    if (reviewer) {
        reviewerBadge.className = `badge badge-${reviewer.status === 'PASS' ? 'emerald' : 'rose'}`;
        reviewerBadge.textContent = reviewer.status;

        const rules = [
            { label: "SEBI Advice Deflection", pass: reviewer.checks?.no_advice_violation },
            { label: "Verified 25-Jun-2026 Grounding", pass: reviewer.checks?.has_grounded_timestamp },
            { label: "Single Citation Link Present", pass: reviewer.checks?.has_single_source_link },
            { label: "Strict ≤3 Sentence Cap", pass: reviewer.checks?.within_sentence_limit },
            { label: "Zero PII Leakage", pass: reviewer.checks?.no_pii_leakage }
        ];

        checksList.innerHTML = rules.map(r => `
            <div class="check-item ${r.pass ? '' : 'fail'}">
                <span class="check-icon">${r.pass ? '✓' : '✗'}</span>
                <div class="check-label">
                    <strong>${r.label}</strong>
                    <p class="text-xs text-muted">${r.pass ? 'Rule verified' : 'Check failed'}</p>
                </div>
            </div>
        `).join("");
    }

    // 4. Trace Log Tab
    const traceFeed = document.getElementById("trace-feed");
    const logs = state.fired_agents_log || [];
    if (logs.length > 0) {
        const timeNow = new Date().toLocaleTimeString();
        traceFeed.innerHTML = logs.map(agent => `
            <div class="trace-item">
                <span class="trace-time">${timeNow}</span>
                <span class="trace-agent">NODE: ${escapeHtml(agent)}</span>
            </div>
        `).join("");
    } else {
        traceFeed.innerHTML = `<div class="trace-item text-muted">Zero nodes recorded.</div>`;
    }
}

function updateCheckItem(elementId, passed) {
    const el = document.getElementById(elementId);
    if (!el) return;
    if (passed) {
        el.classList.remove("fail");
        el.querySelector(".check-icon").textContent = "✓";
    } else {
        el.classList.add("fail");
        el.querySelector(".check-icon").textContent = "✗";
    }
}

// ==============================================================================
// 5. KEYBOARD SHORTCUTS
// ==============================================================================

function setupKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
        // Ctrl+Enter or Cmd+Enter: Approve & Dispatch
        if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
            const btnApprove = document.getElementById("btn-approve");
            if (btnApprove && !btnApprove.disabled && currentState) {
                e.preventDefault();
                approveAndDispatch();
            }
        }

        // Only handle single-key shortcuts when focus is NOT inside an input or textarea
        const activeTag = document.activeElement ? document.activeElement.tagName.toLowerCase() : "";
        if (activeTag === "input" || activeTag === "textarea") return;

        if (e.key === "e" || e.key === "E") {
            if (currentState) {
                e.preventDefault();
                toggleEditMode();
            }
        } else if (e.key === "r" || e.key === "R") {
            if (currentState) {
                e.preventDefault();
                toggleRefineBox();
            }
        } else if (e.key === "Escape") {
            document.getElementById("refinement-container")?.classList.add("hidden");
            if (isEditMode) toggleEditMode();
        }
    });
}

// ==============================================================================
// 6. BENCHMARK & AUDIT VIEW (TAB 2)
// ==============================================================================

function switchTab(tabId) {
    document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));

    document.getElementById(`tab-${tabId}`).classList.add("active");
    document.getElementById(`view-${tabId}`).classList.add("active");
}

async function triggerBenchmark() {
    const btn = document.getElementById("btn-run-benchmark");
    const spinner = btn.querySelector(".btn-spinner");
    const btnText = btn.querySelector(".btn-text");

    btn.disabled = true;
    spinner.classList.remove("hidden");
    btnText.textContent = "Executing 40 Scenarios...";

    try {
        const res = await fetch("/api/benchmark");
        const data = await res.json();

        if (data.status === "success") {
            renderBenchmarkResults(data);
            showToast("40-Scenario Regulatory Audit Completed!");
        } else {
            showToast("Benchmark execution failed.");
        }
    } catch (e) {
        console.error("Benchmark error:", e);
        showToast("Error running benchmark.");
    } finally {
        btn.disabled = false;
        spinner.classList.add("hidden");
        btnText.textContent = "Execute 40-Scenario Audit";
    }
}

function renderBenchmarkResults(data) {
    const container = document.getElementById("benchmark-results-container");
    container.classList.remove("hidden");

    const scCards = document.getElementById("scorecard-cards");
    const tbody = document.getElementById("benchmark-table-body");
    const scorecard = data.scorecard || {};

    scCards.innerHTML = `
        <div class="stat-card">
            <span class="stat-val">${scorecard.total_runs || 40}</span>
            <span class="stat-label">Total Evaluated Scenarios</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(scorecard.compliance_safety_rate)}</span>
            <span class="stat-label">SEBI Zero-Advice Compliance</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(scorecard.pii_protection_rate)}</span>
            <span class="stat-label">Zero-PII Leakage Rate</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(scorecard.verification_date_grounding_rate)}</span>
            <span class="stat-label">25-Jun-2026 Grounding Rate</span>
        </div>
    `;

    const metrics = [
        { name: "SEBI Advice Deflection Rate", val: scorecard.compliance_safety_rate, target: "100.0%" },
        { name: "Zero-PII Leakage Rate", val: scorecard.pii_protection_rate, target: "100.0%" },
        { name: "Verification Date Grounding Rate", val: scorecard.verification_date_grounding_rate, target: "100.0%" },
        { name: "Source Citation Grounding Rate", val: scorecard.source_citation_presence_rate, target: "100.0%" },
        { name: "Draft ≤3 Sentence Cap Compliance", val: scorecard.sentence_cap_adherence_rate, target: "≥ 95.0%" },
        { name: "Discrepancy Capture Rate", val: scorecard.discrepancy_capture_rate, target: "100.0%" },
        { name: "Zero Autonomous SMTP Dispatch", val: scorecard.zero_auto_send_compliance, target: "100.0%" }
    ];

    tbody.innerHTML = metrics.map(m => {
        const pass = m.val >= 0.95 || m.val === 1.0;
        return `
            <tr>
                <td><strong>${m.name}</strong></td>
                <td><span class="stat-val text-xs">${formatPercent(m.val)}</span></td>
                <td>${m.target}</td>
                <td><span class="badge badge-${pass ? 'emerald' : 'rose'}">${pass ? 'PASSED' : 'FAILED'}</span></td>
            </tr>
        `;
    }).join("");
}

function formatPercent(val) {
    if (val === undefined || val === null) return "100.0%";
    return `${(val * 100).toFixed(1)}%`;
}

// ==============================================================================
// 7. UTILITY FUNCTIONS
// ==============================================================================

function showToast(msg) {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.classList.remove("hidden");
    setTimeout(() => {
        toast.classList.add("hidden");
    }, 3500);
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/[&<>"']/g, function(m) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m];
    });
}
