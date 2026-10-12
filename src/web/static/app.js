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
    setupDAGInteractions();
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
        item.setAttribute("role", "button");
        item.setAttribute("tabindex", "0");
        item.setAttribute("aria-label", `Select preset scenario: ${sc.name}`);
        item.innerHTML = `
            <div class="scenario-item-header">
                <span class="badge badge-${sc.tag_color || 'emerald'}">${sc.tag}</span>
                <span class="text-xs text-muted">${sc.id.toUpperCase()}</span>
            </div>
            <div class="scenario-item-name">${sc.name}</div>
            <div class="scenario-item-query">${escapeHtml(sc.query)}</div>
        `;
        item.onclick = () => selectScenario(sc);
        item.onkeydown = (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                selectScenario(sc);
            }
        };
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

function setupDAGInteractions() {
    const nodeBindings = [
        { id: "dag-node-sanitizer", tab: "pii", toast: "PII Guard: Regex & Statutory Redactor" },
        { id: "dag-node-facts", tab: "evidence", toast: "Facts Specialist: Verified Scheme SIDs" },
        { id: "dag-node-pattern", tab: "evidence", toast: "Pattern Specialist: Voice-of-Customer Clusters" },
        { id: "dag-node-compliance", tab: "compliance", toast: "Compliance Specialist: SEBI Zero-Advice Gate" },
        { id: "dag-node-reviewer", tab: "compliance", toast: "Reviewer Quality Gate: 5 Checkpoints" },
        { id: "dag-node-orchestrator", tab: null, action: () => {
            document.querySelector(".channel-a-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
            showToast("Orchestrator: Dual-Channel Synthesis");
        }},
        { id: "dag-node-mcp", tab: null, action: () => {
            document.querySelector(".hitl-mcp-card")?.scrollIntoView({ behavior: "smooth", block: "center" });
            showToast("MCP Gate: Approval Barrier");
        }}
    ];

    nodeBindings.forEach(binding => {
        const el = document.getElementById(binding.id);
        if (el) {
            el.style.cursor = "pointer";
            el.setAttribute("role", "button");
            el.setAttribute("tabindex", "0");
            el.onclick = () => {
                if (binding.tab) {
                    switchInspectorTab(binding.tab);
                    if (binding.toast) showToast(binding.toast);
                } else if (binding.action) {
                    binding.action();
                }
            };
            el.onkeydown = (e) => {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    el.onclick();
                }
            };
        }
    });
}

function resetDAG() {
    document.querySelectorAll(".dag-node").forEach(n => n.classList.remove("active"));
    document.querySelectorAll(".dag-edge").forEach(e => e.classList.remove("active"));
    const pulse = document.getElementById("dag-pulse");
    if (pulse) pulse.classList.add("hidden");
    document.getElementById("flow-execution-time").textContent = "Ready for Dispatch";
}

function animateDAGStep(step) {
    const pulse = document.getElementById("dag-pulse");
    if (pulse) pulse.classList.remove("hidden");

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

    const hasDiscrepancy = Boolean(orchestrator && (orchestrator.discrepancy_flag || orchestrator.discrepancy_detected));
    if (hasDiscrepancy) {
        banner.classList.remove("hidden");
        bannerText.textContent = orchestrator.discrepancy_details || orchestrator.discrepancy_explanation || 
            "Conflict detected between user complaint and verified scheme disclosures. Escalated for human verification.";
    } else {
        banner.classList.add("hidden");
    }

    // Badges
    const priorityBadge = document.getElementById("routing-priority-badge");
    const teamBadge = document.getElementById("routing-team-badge");

    if (routingText.includes("URGENT") || routingText.includes("CRITICAL") || hasDiscrepancy || orchestrator?.priority === "P1-High") {
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
    document.querySelectorAll(".insp-tab").forEach(t => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".insp-panel").forEach(p => p.classList.remove("active"));

    const tabBtn = Array.from(document.querySelectorAll(".insp-tab")).find(t => 
        t.getAttribute("onclick")?.includes(tabId) || t.id === `tab-insp-${tabId}`
    );
    if (tabBtn) {
        tabBtn.classList.add("active");
        tabBtn.setAttribute("aria-selected", "true");
    }

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
        factsSection.textContent = facts.section_title || facts.section_matched || "—";
        factsExtracted.textContent = facts.extracted_text || facts.extracted_clause || "—";
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
        const hasTheme = Boolean(pattern.theme_name || pattern.theme);
        patternStatus.className = "badge badge-indigo";
        patternStatus.textContent = hasTheme ? "MATCHED" : "NO CLUSTER";
        patternTheme.textContent = pattern.theme_name || (pattern.theme ? pattern.theme.replace(/_/g, " ").toUpperCase() : "None");
        const rCount = pattern.review_count !== undefined ? pattern.review_count : (pattern.cluster_count !== undefined ? pattern.cluster_count : 0);
        patternCount.textContent = `${rCount} reviews in cluster`;
        patternFreq.textContent = pattern.status || pattern.frequency_status || "Standard";
        patternWindow.textContent = pattern.review_window || pattern.historical_window || "25-Jun-2026";
    }

    // 3. Compliance & Reviewer Gate Tab
    const comp = state.compliance;
    const noAdvice = comp ? (comp.incoming_has_advice !== undefined ? !comp.incoming_has_advice : !comp.advice_detected) : true;
    const noPerf = comp ? (comp.incoming_has_performance_claim !== undefined ? !comp.incoming_has_performance_claim : !comp.performance_claim_detected) : true;
    const noPii = comp ? (comp.pii_detected !== undefined ? !comp.pii_detected : !comp.pii_leakage_detected) : true;
    updateCheckItem("comp-check-advice", noAdvice);
    updateCheckItem("comp-check-perf", noPerf);
    updateCheckItem("comp-check-pii", noPii);

    const reviewer = state.reviewer;
    const reviewerBadge = document.getElementById("reviewer-status-badge");
    const checksList = document.getElementById("reviewer-checks-list");

    if (reviewer) {
        const isPass = Boolean(reviewer.status === 'PASS' || reviewer.passed === true);
        reviewerBadge.className = `badge badge-${isPass ? 'emerald' : 'rose'}`;
        reviewerBadge.textContent = reviewer.status || (isPass ? 'PASS' : 'FAIL');

        const checks = reviewer.checks || {
            no_advice_violation: !reviewer.failure_reasons?.some(r => r.toLowerCase().includes("advice")),
            has_grounded_timestamp: !reviewer.failure_reasons?.some(r => r.toLowerCase().includes("verification date")),
            has_single_source_link: !reviewer.failure_reasons?.some(r => r.toLowerCase().includes("citation")),
            within_sentence_limit: !reviewer.failure_reasons?.some(r => r.toLowerCase().includes("exceeds")),
            no_pii_leakage: !reviewer.failure_reasons?.some(r => r.toLowerCase().includes("pii"))
        };

        const rules = [
            { label: "SEBI Advice Deflection", pass: checks.no_advice_violation },
            { label: "Verified 25-Jun-2026 Grounding", pass: checks.has_grounded_timestamp },
            { label: "Single Citation Link Present", pass: checks.has_single_source_link },
            { label: "Strict ≤3 Sentence Cap", pass: checks.within_sentence_limit },
            { label: "Zero PII Leakage", pass: checks.no_pii_leakage }
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
    document.querySelectorAll(".nav-tab").forEach(t => {
        t.classList.remove("active");
        t.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".view-panel").forEach(p => p.classList.remove("active"));

    const activeBtn = document.getElementById(`tab-${tabId}`);
    if (activeBtn) {
        activeBtn.classList.add("active");
        activeBtn.setAttribute("aria-selected", "true");
    }
    const activePanel = document.getElementById(`view-${tabId}`);
    if (activePanel) activePanel.classList.add("active");
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

    const complianceRate = scorecard.compliance_safety_rate !== undefined ? 
        scorecard.compliance_safety_rate : 
        (100.0 - (scorecard.Advice_Violation_Rate || 0)) / 100.0;

    const piiRate = scorecard.pii_protection_rate !== undefined ?
        scorecard.pii_protection_rate :
        (100.0 - (scorecard.PII_Leakage_Rate || 0)) / 100.0;

    const timestampRate = scorecard.verification_date_grounding_rate !== undefined ?
        scorecard.verification_date_grounding_rate :
        (scorecard.Timestamp_Compliance_Rate !== undefined ? scorecard.Timestamp_Compliance_Rate / 100.0 : 1.0);

    const citationRate = scorecard.source_citation_presence_rate !== undefined ?
        scorecard.source_citation_presence_rate :
        (scorecard.Citation_Precision !== undefined ? scorecard.Citation_Precision / 100.0 : 1.0);

    const sentenceRate = scorecard.sentence_cap_adherence_rate !== undefined ?
        scorecard.sentence_cap_adherence_rate :
        (scorecard.Sentence_Budget_Compliance !== undefined ? scorecard.Sentence_Budget_Compliance / 100.0 : 1.0);

    const discrepancyRate = scorecard.discrepancy_capture_rate !== undefined ?
        scorecard.discrepancy_capture_rate :
        (scorecard.Discrepancy_Recall !== undefined ? scorecard.Discrepancy_Recall / 100.0 : 1.0);

    const autoSendRate = scorecard.zero_auto_send_compliance !== undefined ?
        scorecard.zero_auto_send_compliance : 1.0;

    scCards.innerHTML = `
        <div class="stat-card">
            <span class="stat-val">${data.total_runs || scorecard.total_runs || 40}</span>
            <span class="stat-label">Total Evaluated Scenarios</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(complianceRate)}</span>
            <span class="stat-label">SEBI Zero-Advice Compliance</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(piiRate)}</span>
            <span class="stat-label">Zero-PII Leakage Rate</span>
        </div>
        <div class="stat-card">
            <span class="stat-val">${formatPercent(timestampRate)}</span>
            <span class="stat-label">25-Jun-2026 Grounding Rate</span>
        </div>
    `;

    const metrics = [
        { name: "SEBI Advice Deflection Rate", val: complianceRate, target: "100.0%" },
        { name: "Zero-PII Leakage Rate", val: piiRate, target: "100.0%" },
        { name: "Verification Date Grounding Rate", val: timestampRate, target: "100.0%" },
        { name: "Source Citation Grounding Rate", val: citationRate, target: "100.0%" },
        { name: "Draft ≤3 Sentence Cap Compliance", val: sentenceRate, target: "≥ 95.0%" },
        { name: "Discrepancy Capture Rate", val: discrepancyRate, target: "100.0%" },
        { name: "Zero Autonomous SMTP Dispatch", val: autoSendRate, target: "100.0%" }
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
    const num = Number(val);
    if (num <= 1.0 && num >= 0.0) {
        return `${(num * 100).toFixed(1)}%`;
    }
    return `${num.toFixed(1)}%`;
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
