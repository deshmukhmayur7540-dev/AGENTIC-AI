/**
 * CourseAgentAI — Frontend Client Logic & Micro-Interactions
 * Strictly API-driven: connects directly to FastAPI endpoints with zero duplicated backend business logic.
 * Phase 3: Enhanced with Apple-grade micro-interactions, keyboard accessibility, and focus management.
 */

document.addEventListener('DOMContentLoaded', () => {
  let authenticatedUser = null;
  // Application State
  const state = {
    originalPrompt: '',
    requestId: '',
    courseCodeHint: '26ECAC401',
    clarificationQuestions: [],
    currentPlan: null,
    planHistory: null,
    latestRevision: null,
    scenarios: [],
    actionTrace: [], // Auditable action timeline records
  };
  const courseMaterialsState = {
    categories: [],
    folders: [],
    activeCategoryId: null,
    activeFolderId: null,
    selectedFolderId: null,
    pendingReplacementId: null,
  };

  // DOM Elements Cache
  const el = {
    // Screens
    screenRequest: document.getElementById('screen-request'),
    screenClarification: document.getElementById('screen-clarification'),
    screenPlan: document.getElementById('screen-plan'),

    // Stepper Nodes
    stepNode1: document.getElementById('step-node-1'),
    stepNode2: document.getElementById('step-node-2'),
    stepNode3: document.getElementById('step-node-3'),
    stepNode4: document.getElementById('step-node-4'),

    // Inputs & Buttons
    promptInput: document.getElementById('prompt-input'),
    btnAnalyzeRequest: document.getElementById('btn-analyze-request'),
    spinnerAnalyze: document.getElementById('spinner-analyze'),
    scenariosChips: document.getElementById('scenarios-chips'),

    questionsList: document.getElementById('questions-list'),
    questionsCountBadge: document.getElementById('questions-count-badge'),
    btnGeneratePlan: document.getElementById('btn-generate-plan'),
    spinnerGenerate: document.getElementById('spinner-generate'),
    btnBackToRequest: document.getElementById('btn-back-to-request'),

    // Plan Elements
    planCourseCode: document.getElementById('plan-course-code'),
    planCourseName: document.getElementById('plan-course-name'),
    versionPillsList: document.getElementById('version-pills-list'),
    statDuration: document.getElementById('stat-duration'),
    statAssignmentsCount: document.getElementById('stat-assignments-count'),
    statTaHours: document.getElementById('stat-ta-hours'),
    statGradeBalance: document.getElementById('stat-grade-balance'),

    planDescription: document.getElementById('plan-description'),
    planAudience: document.getElementById('plan-audience'),
    planPrereqsList: document.getElementById('plan-prereqs-list'),
    planMilestonesList: document.getElementById('plan-milestones-list'),

    materialsContainer: document.getElementById('materials-container'),
    tabMaterialsCount: document.getElementById('tab-materials-count'),

    assignmentsContainer: document.getElementById('assignments-container'),
    tabAssignmentsCount: document.getElementById('tab-assignments-count'),

    gradesContainer: document.getElementById('grades-container'),
    gradeTotalBadge: document.getElementById('grade-total-badge'),

    diffsList: document.getElementById('diffs-list'),
    diffsBadgeCount: document.getElementById('diffs-badge-count'),
    diffPrevVer: document.getElementById('diff-prev-ver'),
    diffCurrVer: document.getElementById('diff-curr-ver'),
    changelogSummaryText: document.getElementById('changelog-summary-text'),
    tabBtnDiffs: document.getElementById('tab-btn-diffs'),

    // Version History Tab
    versionHistoryTimeline: document.getElementById('version-history-timeline'),
    versionsCountBadge: document.getElementById('versions-count-badge'),

    // Action Trace Tab
    actionTraceList: document.getElementById('action-trace-list'),
    actionTraceCount: document.getElementById('action-trace-count'),

    // Revision Box
    revisionPromptInput: document.getElementById('revision-prompt-input'),
    btnSubmitRevision: document.getElementById('btn-submit-revision'),
    spinnerRevise: document.getElementById('spinner-revise'),
    nextVersionPreview: document.getElementById('next-version-preview'),

    // Global Alert & Audit
    globalAlert: document.getElementById('global-alert'),
    alertMessage: document.getElementById('alert-message'),
    btnCloseAlert: document.getElementById('btn-close-alert'),
    btnReset: document.getElementById('btn-reset'),
    btnAuditDrawer: document.getElementById('btn-audit-drawer'),
    auditDrawer: document.getElementById('audit-drawer'),
    btnCloseDrawer: document.getElementById('btn-close-drawer'),
    auditTimeline: document.getElementById('audit-timeline'),
    systemStatusText: document.getElementById('system-status-text'),
    authLoginScreen: document.getElementById('auth-login-screen'),
    authLoginForm: document.getElementById('auth-login-form'),
    authEmail: document.getElementById('auth-email'),
    authPassword: document.getElementById('auth-password'),
    authLoginError: document.getElementById('auth-login-error'),
    authLoginSubmit: document.getElementById('auth-login-submit'),
    authUserLabel: document.getElementById('auth-user-label'),
    btnAuthLogout: document.getElementById('btn-auth-logout'),

    // Top Lab Navigation
    navTabs: {
      dashboard: document.getElementById('nav-tab-dashboard'),
      notifications: document.getElementById('nav-tab-notifications'),
      knowledge: document.getElementById('nav-tab-knowledge'),
      lab1: document.getElementById('nav-tab-lab1'),
      lab2: document.getElementById('nav-tab-lab2'),
      lab3: document.getElementById('nav-tab-lab3'),
      lab4: document.getElementById('nav-tab-lab4'),
      lab5: document.getElementById('nav-tab-lab5'),
      lab6: document.getElementById('nav-tab-lab6'),
      lab7: document.getElementById('nav-tab-lab7'),
      lab8: document.getElementById('nav-tab-lab8'),
      lab9: document.getElementById('nav-tab-lab9'),
      lab10: document.getElementById('nav-tab-lab10'),
      lab11: document.getElementById('nav-tab-lab11'),
      lab12: document.getElementById('nav-tab-lab12'),
      lab13: document.getElementById('nav-tab-lab13'),
      lab14: document.getElementById('nav-tab-lab14'),
      submissions: document.getElementById('nav-tab-submissions'),
      faculty: document.getElementById('nav-tab-faculty'),
      history: document.getElementById('nav-tab-history'),
      about: document.getElementById('nav-tab-about'),
    },
    views: {
      dashboard: document.getElementById('dashboard-view'),
      notifications: document.getElementById('notifications-view'),
      knowledge: document.getElementById('knowledge-view'),
      lab1: document.getElementById('lab1-view'),
      lab2: document.getElementById('lab2-view'),
      lab3: document.getElementById('lab3-view'),
      lab4: document.getElementById('lab4-view'),
      lab5: document.getElementById('lab5-view'),
      lab6: document.getElementById('lab6-view'),
      lab7: document.getElementById('lab7-view'),
      lab8: document.getElementById('lab8-view'),
      lab9: document.getElementById('lab9-view'),
      lab10: document.getElementById('lab10-view'),
      lab11: document.getElementById('lab11-view'),
      lab12: document.getElementById('lab12-view'),
      lab13: document.getElementById('lab13-view'),
      lab14: document.getElementById('lab14-view'),
      submissions: document.getElementById('submissions-view'),
      history: document.getElementById('history-view'),
      about: document.getElementById('about-view'),
    },
    activeLabTag: document.getElementById('active-lab-tag'),
    navTabLab1: document.getElementById('nav-tab-lab1'),
    navTabLab2: document.getElementById('nav-tab-lab2'),
    lab1View: document.getElementById('lab1-view'),
    lab2View: document.getElementById('lab2-view'),

    // Submissions Elements
    btnPortalStudent: document.getElementById('btn-portal-student'),
    btnPortalFaculty: document.getElementById('btn-portal-faculty'),
    portalRoleSwitcher: document.getElementById('portal-role-switcher'),
    studentPortalSection: document.getElementById('student-portal-section'),
    facultyPortalSection: document.getElementById('faculty-portal-section'),
    adminPortalSection: document.getElementById('admin-portal-section'),
    adminAssignmentCount: document.getElementById('admin-assignment-count'),
    adminCourseLabel: document.getElementById('admin-course-label'),
    adminAssignmentList: document.getElementById('admin-assignment-list'),
    adminAssignmentDetails: document.getElementById('admin-assignment-details'),
    adminAssignmentDetailTitle: document.getElementById('admin-assignment-detail-title'),
    adminAssignmentDetailStatus: document.getElementById('admin-assignment-detail-status'),
    adminAssignmentDetailPoints: document.getElementById('admin-assignment-detail-points'),
    adminAssignmentDetailDue: document.getElementById('admin-assignment-detail-due'),
    adminAssignmentDetailDescription: document.getElementById('admin-assignment-detail-description'),
    adminAssignmentDetailRules: document.getElementById('admin-assignment-detail-rules'),
    btnAdminCloseAssignmentDetails: document.getElementById('btn-admin-close-assignment-details'),
    subStudentSelect: document.getElementById('sub-student-select'),
    subAssignmentSelect: document.getElementById('sub-assignment-select'),
    subGithubUrlInput: document.getElementById('sub-github-url-input'),
    subNotesInput: document.getElementById('sub-notes-input'),
    subUrlFeedback: document.getElementById('sub-url-feedback'),
    btnSubmitGithub: document.getElementById('btn-submit-github'),
    spinnerSubmitGithub: document.getElementById('spinner-submit-github'),
    subReceiptCard: document.getElementById('sub-receipt-card'),
    receiptStatusBadge: document.getElementById('receipt-status-badge'),
    receiptAttemptPill: document.getElementById('receipt-attempt-pill'),
    receiptTitle: document.getElementById('receipt-title'),
    receiptTimestamp: document.getElementById('receipt-timestamp'),
    receiptRepoLink: document.getElementById('receipt-repo-link'),
    receiptDetails: document.getElementById('receipt-details'),
    asgnDetailTitle: document.getElementById('asgn-detail-title'),
    asgnDetailDesc: document.getElementById('asgn-detail-desc'),
    asgnStatPoints: document.getElementById('asgn-stat-points'),
    asgnStatWeight: document.getElementById('asgn-stat-weight'),
    asgnStatWeek: document.getElementById('asgn-stat-week'),
    asgnStatStatus: document.getElementById('asgn-stat-status'),
    asgnDueDate: document.getElementById('asgn-due-date'),
    asgnLatePolicy: document.getElementById('asgn-late-policy'),
    asgnSubmissionRules: document.getElementById('asgn-submission-rules'),
    studentHistoryTbody: document.getElementById('student-history-tbody'),
    btnRefreshStudentHistory: document.getElementById('btn-refresh-student-history'),
    facultyAsgnFilter: document.getElementById('faculty-asgn-filter'),
    facultyStatusFilter: document.getElementById('faculty-status-filter'),
    btnRefreshFacultySubs: document.getElementById('btn-refresh-faculty-subs'),
    facultySubmissionsTbody: document.getElementById('faculty-submissions-tbody'),
    facultyReviewModal: document.getElementById('faculty-review-modal'),
    btnCloseReviewModal: document.getElementById('btn-close-review-modal'),
    modalReviewStudent: document.getElementById('modal-review-student'),
    modalReviewAssignment: document.getElementById('modal-review-assignment'),
    modalReviewRepo: document.getElementById('modal-review-repo'),
    modalReviewTimestamp: document.getElementById('modal-review-timestamp'),
    modalReviewSubId: document.getElementById('modal-review-sub-id'),
    modalReviewStatus: document.getElementById('modal-review-status'),
    modalReviewStateNote: document.getElementById('modal-review-state-note'),
    modalReviewScore: document.getElementById('modal-review-score'),
    modalReviewFeedback: document.getElementById('modal-review-feedback'),
    btnSaveFacultyReview: document.getElementById('btn-save-faculty-review'),
    spinnerSaveReview: document.getElementById('spinner-save-review'),
    btnApproveFacultyGrade: document.getElementById('btn-approve-faculty-grade'),
    btnPublishFacultyGrade: document.getElementById('btn-publish-faculty-grade'),

    // Lab 2 Elements
    lab2QueryInput: document.getElementById('lab2-query-input'),
    lab2ScenariosChips: document.getElementById('lab2-scenarios-chips'),
    lab2CourseSelect: document.getElementById('lab2-course-select'),
    lab2AssignmentSelect: document.getElementById('lab2-assignment-select'),
    btnLab2RunQuery: document.getElementById('btn-lab2-run-query'),
    spinnerLab2Run: document.getElementById('spinner-lab2-run'),
    lab2ResultsContainer: document.getElementById('lab2-results-container'),
    lab2StatStatus: document.getElementById('lab2-stat-status'),
    lab2StatToolsCount: document.getElementById('lab2-stat-tools-count'),
    lab2StatFactsCount: document.getElementById('lab2-stat-facts-count'),
    lab2StatDuration: document.getElementById('lab2-stat-duration'),
    lab2StepsBadge: document.getElementById('lab2-steps-badge'),
    lab2TraceStepsList: document.getElementById('lab2-trace-steps-list'),
    lab2FinalConclusion: document.getElementById('lab2-final-conclusion'),
    lab2VerifiedFactsList: document.getElementById('lab2-verified-facts-list'),

    // Lab 2 Tools & Sandbox
    btnLab2ViewTools: document.getElementById('btn-lab2-view-tools'),
    lab2ToolsModal: document.getElementById('lab2-tools-modal'),
    btnCloseToolsModal: document.getElementById('btn-close-tools-modal'),
    lab2ToolsListContainer: document.getElementById('lab2-tools-list-container'),

    btnLab2OpenSandbox: document.getElementById('btn-lab2-open-sandbox'),
    lab2SandboxModal: document.getElementById('lab2-sandbox-modal'),
    btnCloseSandboxModal: document.getElementById('btn-close-sandbox-modal'),
    sandboxToolSelect: document.getElementById('sandbox-tool-select'),
    sandboxParamsInput: document.getElementById('sandbox-params-input'),
    btnRunSandbox: document.getElementById('btn-run-sandbox'),
    spinnerSandbox: document.getElementById('spinner-sandbox'),
    sandboxResultPre: document.getElementById('sandbox-result-pre'),

    // Lab 3 Elements
    lab3QueryInput: document.getElementById('lab3-query-input'),
    lab3ScenariosChips: document.getElementById('lab3-scenarios-chips'),
    btnLab3RunAgent: document.getElementById('btn-lab3-run-agent'),
    spinnerLab3Run: document.getElementById('spinner-lab3-run'),
    lab3SkillsCatalogGrid: document.getElementById('lab3-skills-catalog-grid'),
    btnLab3RefreshSkills: document.getElementById('btn-lab3-refresh-skills'),
    lab3SandboxSelect: document.getElementById('lab3-sandbox-select'),
    lab3SandboxParams: document.getElementById('lab3-sandbox-params'),
    btnLab3RunSandbox: document.getElementById('btn-lab3-run-sandbox'),
    spinnerLab3Sandbox: document.getElementById('spinner-lab3-sandbox'),
    lab3SandboxResultPre: document.getElementById('lab3-sandbox-result-pre'),
    lab3ResultsContainer: document.getElementById('lab3-results-container'),
    lab3StatStatus: document.getElementById('lab3-stat-status'),
    lab3StatSkillsCount: document.getElementById('lab3-stat-skills-count'),
    lab3StatDuration: document.getElementById('lab3-stat-duration'),
    lab3SkillStepsList: document.getElementById('lab3-skill-steps-list'),
    lab3FinalFormattedOutput: document.getElementById('lab3-final-formatted-output'),

    // Lab 4 Elements
    lab4AgentQueryInput: document.getElementById('lab4-agent-query-input'),
    btnLab4RunAgent: document.getElementById('btn-lab4-run-agent'),
    spinnerLab4Agent: document.getElementById('spinner-lab4-agent'),
    lab4SessionIdInput: document.getElementById('lab4-session-id-input'),
    btnLab4NewSession: document.getElementById('btn-lab4-new-session'),
    lab4TurnRole: document.getElementById('lab4-turn-role'),
    lab4TurnContent: document.getElementById('lab4-turn-content'),
    btnLab4AddTurn: document.getElementById('btn-lab4-add-turn'),
    lab4ScratchKey: document.getElementById('lab4-scratch-key'),
    lab4ScratchVal: document.getElementById('lab4-scratch-val'),
    btnLab4SetScratch: document.getElementById('btn-lab4-set-scratch'),
    btnLab4RefreshSession: document.getElementById('btn-lab4-refresh-session'),
    lab4SessionViewPre: document.getElementById('lab4-session-view-pre'),
    lab4RagChapterSelect: document.getElementById('lab4-rag-chapter-select'),
    lab4RagQueryInput: document.getElementById('lab4-rag-query-input'),
    btnLab4SearchRag: document.getElementById('btn-lab4-search-rag'),
    spinnerLab4Rag: document.getElementById('spinner-lab4-rag'),
    lab4RagResultsContainer: document.getElementById('lab4-rag-results-container'),
    lab4AgentResponseBox: document.getElementById('lab4-agent-response-box'),
    lab4AgentResponseContent: document.getElementById('lab4-agent-response-content'),

    // Lab 5 Elements
    lab5ScenariosChips: document.getElementById('lab5-scenarios-chips'),
    lab5SourceSelect: document.getElementById('lab5-source-select'),
    lab5OpSelect: document.getElementById('lab5-op-select'),
    lab5RoleSelect: document.getElementById('lab5-role-select'),
    lab5ResourceInput: document.getElementById('lab5-resource-input'),
    lab5ParamsInput: document.getElementById('lab5-params-input'),
    btnLab5Dispatch: document.getElementById('btn-lab5-dispatch'),
    spinnerLab5Dispatch: document.getElementById('spinner-lab5-dispatch'),
    lab5ResultPre: document.getElementById('lab5-result-pre'),
    btnLab5RefreshAudit: document.getElementById('btn-lab5-refresh-audit'),
    lab5AuditTableContainer: document.getElementById('lab5-audit-table-container'),

    // Lab 6 Elements
    lab6TaskInput: document.getElementById('lab6-task-input'),
    lab6BudgetSteps: document.getElementById('lab6-budget-steps'),
    lab6ActiveRunPill: document.getElementById('lab6-active-run-pill'),
    btnLab6StartRun: document.getElementById('btn-lab6-start-run'),
    spinnerLab6Start: document.getElementById('spinner-lab6-start'),
    lab6RunControllerCard: document.getElementById('lab6-run-controller-card'),
    lab6RunTitle: document.getElementById('lab6-run-title'),
    lab6RunStatusBadge: document.getElementById('lab6-run-status-badge'),
    btnLab6Step: document.getElementById('btn-lab6-step'),
    btnLab6Crash: document.getElementById('btn-lab6-crash'),
    btnLab6Resume: document.getElementById('btn-lab6-resume'),
    lab6StatSteps: document.getElementById('lab6-stat-steps'),
    lab6StatGate: document.getElementById('lab6-stat-gate'),
    lab6StatCheckpoints: document.getElementById('lab6-stat-checkpoints'),
    lab6ApprovalGateBanner: document.getElementById('lab6-approval-gate-banner'),
    lab6ApprovalPromptText: document.getElementById('lab6-approval-prompt-text'),
    btnLab6Approve: document.getElementById('btn-lab6-approve'),
    btnLab6Reject: document.getElementById('btn-lab6-reject'),
    lab6StepsTimeline: document.getElementById('lab6-steps-timeline'),
    lab6CheckpointPre: document.getElementById('lab6-checkpoint-pre'),

    // Lab 7 Elements
    lab7TaskInput: document.getElementById('lab7-task-input'),
    lab7StatusTag: document.getElementById('lab7-status-tag'),
    btnLab7StepGraph: document.getElementById('btn-lab7-step-graph'),
    btnLab7RunAll: document.getElementById('btn-lab7-run-all'),
    spinnerLab7Run: document.getElementById('spinner-lab7-run'),
    lab7GateBanner: document.getElementById('lab7-gate-banner'),
    btnLab7Approve: document.getElementById('btn-lab7-approve'),
    btnLab7Reject: document.getElementById('btn-lab7-reject'),
    lab7RetryBadge: document.getElementById('lab7-retry-badge'),
    lab7GraphNodesGrid: document.getElementById('lab7-graph-nodes-grid'),
    lab7OutputContainer: document.getElementById('lab7-output-container'),
    lab7OutputContent: document.getElementById('lab7-output-content'),

    // Lab 8 Elements
    lab8CourseGoalInput: document.getElementById('lab8-course-goal-input'),
    lab8FailSimCheckbox: document.getElementById('lab8-fail-sim-checkbox'),
    btnLab8LaunchSwarm: document.getElementById('btn-lab8-launch-swarm'),
    spinnerLab8Run: document.getElementById('spinner-lab8-run'),
    lab8StatsContainer: document.getElementById('lab8-stats-container'),
    lab8StatStatus: document.getElementById('lab8-stat-status'),
    lab8StatWorkers: document.getElementById('lab8-stat-workers'),
    lab8StatParallelTime: document.getElementById('lab8-stat-parallel-time'),
    lab8StatSeqTime: document.getElementById('lab8-stat-seq-time'),
    lab8StatSpeedup: document.getElementById('lab8-stat-speedup'),
    lab8WorkersGrid: document.getElementById('lab8-workers-grid'),
    lab8MergedContainer: document.getElementById('lab8-merged-container'),
    lab8ResilienceBadge: document.getElementById('lab8-resilience-badge'),
    lab8MergedContent: document.getElementById('lab8-merged-content'),
  };

  // =========================================================================
  // Auditable Action Trace Logger (No Private CoT)
  // =========================================================================

  function recordActionTrace(stepName, detail, status = 'SUCCESS') {
    const record = {
      stepName,
      detail,
      status,
      timestamp: new Date().toLocaleTimeString(),
    };
    state.actionTrace.push(record);
    renderActionTrace();
  }

  function renderActionTrace() {
    if (!el.actionTraceList) return;
    el.actionTraceList.innerHTML = '';
    el.actionTraceCount.textContent = state.actionTrace.length;

    state.actionTrace.forEach((trace) => {
      const stepEl = document.createElement('div');
      stepEl.className = 'action-trace-step completed';
      stepEl.innerHTML = `
        <div class="action-step-header">
          <span class="action-step-title">${escapeHtml(trace.stepName)}</span>
          <span class="action-step-time">${trace.timestamp}</span>
        </div>
        <div class="action-step-detail">${escapeHtml(trace.detail)}</div>
      `;
      el.actionTraceList.appendChild(stepEl);
    });
  }

  // =========================================================================
  // API Client Helper
  // =========================================================================

  function csrfRequestHeaders() {
    const cookie = document.cookie
      .split('; ')
      .find(item => item.startsWith('courseagent_csrf='));
    if (!cookie) return {};
    return { 'X-CSRF-Token': decodeURIComponent(cookie.slice('courseagent_csrf='.length)) };
  }

  async function apiCall(endpoint, method = 'GET', body = null, extraHeaders = {}) {
    hideAlert();
    try {
      const options = {
        method,
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json', ...csrfRequestHeaders(), ...extraHeaders },
      };
      if (body) {
        options.body = JSON.stringify(body);
      }

      const response = await fetch(endpoint, options);
      const contentType = response.headers.get('content-type') || '';
      if (!contentType.includes('application/json')) {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: Request failed`);
        }
        return response;
      }
      const envelope = await response.json();

      if (!response.ok || !envelope.success) {
        let errorMsg = envelope.error?.message;
        if (!errorMsg && envelope.detail) {
          if (Array.isArray(envelope.detail)) {
            errorMsg = envelope.detail.map(d => `${d.loc ? d.loc.join('.') + ': ' : ''}${d.msg}`).join(', ');
          } else {
            errorMsg = String(envelope.detail);
          }
        }
        if (!errorMsg) {
          errorMsg = `HTTP ${response.status}: Request failed`;
        }
        throw new Error(errorMsg);
      }

      return envelope.data;
    } catch (err) {
      showAlert(err.message || 'Network communication failure');
      throw err;
    }
  }

  function showAlert(message) {
    const toast = document.getElementById('app-toast');
    const toastMsg = document.getElementById('toast-message');
    if (toast && toastMsg) {
      toastMsg.textContent = message;
      toast.classList.remove('hidden');
    }
    if (el.alertMessage) el.alertMessage.textContent = message;
    el.globalAlert.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function hideAlert() {
    if (el.globalAlert) el.globalAlert.classList.add('hidden');
    const toast = document.getElementById('app-toast');
    if (toast) toast.classList.add('hidden');
  }

  function setButtonLoading(btn, spinner, isLoading) {
    if (!btn) return;
    btn.disabled = !!isLoading;
    if (spinner) {
      if (isLoading) {
        spinner.classList.remove('hidden');
      } else {
        spinner.classList.add('hidden');
      }
    }
  }

  // =========================================================================
  // Screen & Stepper Navigation
  // =========================================================================

  function setStep(stepNum) {
    [el.stepNode1, el.stepNode2, el.stepNode3, el.stepNode4].forEach((node, idx) => {
      node.classList.remove('active', 'completed');
      if (idx + 1 < stepNum) {
        node.classList.add('completed');
      } else if (idx + 1 === stepNum) {
        node.classList.add('active');
      }
    });
  }

  function showScreen(screen) {
    [el.screenRequest, el.screenClarification, el.screenPlan].forEach(s => s.classList.add('hidden'));
    screen.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // =========================================================================
  // SCREEN 1: Request Analysis & Clarification Question Fetching
  // =========================================================================

  async function handleAnalyzeRequest() {
    const prompt = el.promptInput.value.trim();
    if (!prompt) {
      showAlert('Please enter a course request description before analyzing.');
      el.promptInput.focus();
      return;
    }

    if (prompt.length < 5) {
      showAlert('Course request must be at least 5 characters long.');
      el.promptInput.focus();
      return;
    }

    state.originalPrompt = prompt;
    el.btnAnalyzeRequest.disabled = true;
    el.spinnerAnalyze.classList.remove('hidden');

    recordActionTrace('Request received', `Faculty submitted prompt: "${prompt.slice(0, 70)}..."`);

    try {
      const data = await apiCall('/api/lab1/clarify', 'POST', {
        raw_prompt: prompt,
        course_title_hint: state.courseCodeHint,
      });

      state.clarificationQuestions = data.questions || [];
      state.requestId = `req-${Date.now()}`;

      recordActionTrace('Missing information detected', `Identified gaps across ${data.questions_count} dimensions.`);
      recordActionTrace('Clarification generated', `Generated ${data.questions_count} targeted questions.`);

      renderClarificationQuestions(data.questions);
      setStep(2);
      showScreen(el.screenClarification);
    } catch (err) {
      showAlert(`Could not analyze the course request: ${err.message}`);
    } finally {
      el.btnAnalyzeRequest.disabled = false;
      el.spinnerAnalyze.classList.add('hidden');
    }
  }

  function renderClarificationQuestions(questions) {
    el.questionsList.innerHTML = '';
    el.questionsCountBadge.textContent = `${questions.length} Questions`;

    questions.forEach((q, idx) => {
      const qCard = document.createElement('div');
      qCard.className = 'question-card';
      qCard.id = `q-card-${q.question_id}`;

      let optionsHtml = '';
      (q.suggested_options || []).forEach((opt, optIdx) => {
        const checked = optIdx === 0 ? 'checked' : '';
        optionsHtml += `
          <label class="option-item">
            <input type="radio" name="opt-${q.question_id}" value="${escapeHtml(opt)}" ${checked}>
            <span class="option-label">${escapeHtml(opt)}</span>
          </label>
        `;
      });

      qCard.innerHTML = `
        <div class="question-header">
          <span class="badge badge-accent">${formatCategory(q.category)}</span>
          <span class="badge badge-neutral">Question ${idx + 1} of ${questions.length}</span>
        </div>
        <div class="question-text">${escapeHtml(q.question_text)}</div>
        <div class="question-rationale">
          <strong>Why this matters:</strong> ${escapeHtml(q.rationale)}
        </div>
        <div class="options-group">
          ${optionsHtml}
          <div class="form-group" style="margin-top: 0.5rem; margin-bottom: 0;">
            <input 
              type="text" 
              class="form-input custom-input" 
              data-qid="${q.question_id}" 
              placeholder="Or type custom specification for ${formatCategory(q.category)}..."
              aria-label="Custom specification for ${formatCategory(q.category)}"
            >
          </div>
        </div>
      `;

      el.questionsList.appendChild(qCard);
    });
  }

  // =========================================================================
  // SCREEN 2: Plan Generation v1.0
  // =========================================================================

  async function handleGeneratePlan() {
    el.btnGeneratePlan.disabled = true;
    el.spinnerGenerate.classList.remove('hidden');

    try {
      // Gather answers from real user selections
      const answeredQuestions = state.clarificationQuestions.map(q => {
        const selectedRadio = document.querySelector(`input[name="opt-${q.question_id}"]:checked`);
        const customInput = document.querySelector(`input.custom-input[data-qid="${q.question_id}"]`);

        const chosenOption = selectedRadio ? selectedRadio.value : (q.suggested_options[0] || '');
        const customText = customInput && customInput.value.trim() ? customInput.value.trim() : null;

        return {
          question_id: q.question_id,
          category: q.category,
          question_text: q.question_text,
          rationale: q.rationale,
          suggested_options: q.suggested_options,
          selected_option: chosenOption,
          custom_response: customText,
        };
      });

      recordActionTrace('Answers received', `Captured responses for ${answeredQuestions.length} questions.`);

      const planData = await apiCall('/api/lab1/generate', 'POST', {
        request_id: state.requestId,
        original_prompt: state.originalPrompt,
        course_code_hint: state.courseCodeHint,
        answers: answeredQuestions,
      });

      state.currentPlan = planData;
      recordActionTrace('Plan generated', `Plan v${planData.version} (${planData.course_code}) synthesized with 3 core pillars.`);

      await refreshPlanHistory(planData.plan_id);
      renderPlan(planData);

      setStep(3);
      showScreen(el.screenPlan);
    } catch (err) {
      showAlert(`Could not generate the course plan: ${err.message}`);
    } finally {
      el.btnGeneratePlan.disabled = false;
      el.spinnerGenerate.classList.add('hidden');
    }
  }

  // =========================================================================
  // SCREEN 3: Structured Plan Viewer
  // =========================================================================

  function renderPlan(plan) {
    if (!plan) return;

    // Header & Stats
    el.planCourseCode.textContent = plan.course_code || '26ECAC401';
    el.planCourseName.textContent = plan.course_name || 'Agentic AI';
    el.statDuration.textContent = plan.duration_weeks ? `${plan.duration_weeks} Weeks` : (plan.organization_type === 'SOURCE_BASED' ? 'Source-based' : 'Not specified');
    el.statAssignmentsCount.textContent = plan.assignments && plan.assignments.length > 0 ? `${plan.assignments.length} Deliverables` : 'Not specified';
    el.statTaHours.textContent = plan.ta_allocation_hours !== null && plan.ta_allocation_hours !== undefined ? `${plan.ta_allocation_hours} hrs/wk` : 'Not specified';

    // Overview Tab
    el.planDescription.textContent = plan.description || 'Not specified in supplied course material.';
    el.planAudience.textContent = plan.target_audience || 'Not specified in supplied course material.';

    el.planPrereqsList.innerHTML = '';
    if (!plan.prerequisites || plan.prerequisites.length === 0) {
      const li = document.createElement('li');
      li.className = 'text-muted';
      li.textContent = 'Not specified in supplied course material.';
      el.planPrereqsList.appendChild(li);
    } else {
      (plan.prerequisites || []).forEach(p => {
        const li = document.createElement('li');
        li.textContent = p;
        el.planPrereqsList.appendChild(li);
      });
    }

    el.planMilestonesList.innerHTML = '';
    if (!plan.milestones || plan.milestones.length === 0) {
      const div = document.createElement('div');
      div.className = 'milestone-item text-muted';
      div.textContent = 'Not specified in supplied course material.';
      el.planMilestonesList.appendChild(div);
    } else {
      (plan.milestones || []).forEach(m => {
        const div = document.createElement('div');
        div.className = 'milestone-item';
        div.textContent = m;
        el.planMilestonesList.appendChild(div);
      });
    }

    // Pillar 1: Notes & Materials
    el.tabMaterialsCount.textContent = plan.materials_and_notes.length;
    el.materialsContainer.innerHTML = '';
    plan.materials_and_notes.forEach(mat => {
      const card = document.createElement('div');
      card.className = 'material-card';

      const topicsHtml = (mat.topics || []).map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('');
      const readingsHtml = (mat.reading_materials || []).map(r => `<div>📖 ${escapeHtml(r)}</div>`).join('');
      const badgeLabel = mat.week !== null && mat.week !== undefined ? `WEEK ${mat.week}` : (mat.section_label || 'SECTION');

      card.innerHTML = `
        <span class="material-week-badge">${escapeHtml(badgeLabel)}</span>
        <h4 class="material-title">${escapeHtml(mat.title)}</h4>
        <div class="topics-list">${topicsHtml}</div>
        <div class="readings-box">${readingsHtml}</div>
        <div class="notes-summary">
          <strong>Lecture Core Notes:</strong> ${escapeHtml(mat.lecture_notes_summary)}
        </div>
      `;
      el.materialsContainer.appendChild(card);
    });

    // Pillar 2: Assignments & Rubrics
    el.tabAssignmentsCount.textContent = plan.assignments.length;
    el.assignmentsContainer.innerHTML = '';
    if (!plan.assignments || plan.assignments.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.className = 'text-muted';
      emptyDiv.style.padding = '2rem 1rem';
      emptyDiv.style.textAlign = 'center';
      emptyDiv.style.color = 'var(--text-muted)';
      emptyDiv.textContent = 'No assignments or practical deliverables established in supplied course notes (unestablished).';
      el.assignmentsContainer.appendChild(emptyDiv);
    } else {
      plan.assignments.forEach(asgn => {
        const card = document.createElement('div');
        card.className = 'assignment-card';

        const delivHtml = (asgn.deliverables || []).map(d => `<li>${escapeHtml(d)}</li>`).join('');

        card.innerHTML = `
          <div class="asgn-header">
            <span class="asgn-id">${escapeHtml(asgn.assignment_id)}</span>
            <span class="asgn-due">${asgn.due_week ? 'Due Week ' + asgn.due_week : 'Unscheduled'}</span>
          </div>
          <h4 class="asgn-title">${escapeHtml(asgn.title)}</h4>
          <p class="asgn-desc">${escapeHtml(asgn.description)}</p>
          <div class="deliv-title">Required Deliverables:</div>
          <ul class="deliverables-list">${delivHtml}</ul>
          <div class="asgn-footer">
            <span>Max Points: <strong>${asgn.max_points} pts</strong></span>
            <span>Grade Weight: <strong>${asgn.weight_percentage !== null && asgn.weight_percentage !== undefined ? asgn.weight_percentage + '%' : 'N/A'}</strong></span>
          </div>
        `;
        el.assignmentsContainer.appendChild(card);
      });
    }

    // Pillar 3: Grades Breakdown & Policies
    el.gradesContainer.innerHTML = '';
    if (!plan.grade_breakdown || plan.grade_breakdown.length === 0) {
      const emptyDiv = document.createElement('div');
      emptyDiv.className = 'text-muted';
      emptyDiv.style.padding = '1.5rem 1rem';
      emptyDiv.style.color = 'var(--text-muted)';
      emptyDiv.textContent = 'Official university grading policy and weight breakdown are not established in the supplied course notes.';
      el.gradesContainer.appendChild(emptyDiv);

      el.gradeTotalBadge.textContent = 'Not established';
      el.gradeTotalBadge.className = 'badge badge-neutral';
      el.statGradeBalance.textContent = 'Not established';
    } else {
      let totalGrade = 0;
      (plan.grade_breakdown || []).forEach(item => {
        totalGrade += item.weight_percentage;
        const row = document.createElement('div');
        row.className = 'grade-row';
        row.innerHTML = `
          <div class="grade-row-top">
            <span class="grade-cat-name">${escapeHtml(item.category)}</span>
            <span class="grade-weight-val">${item.weight_percentage.toFixed(1)}%</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${Math.min(100, item.weight_percentage)}%"></div>
          </div>
          <div class="grade-desc">${escapeHtml(item.description)}</div>
        `;
        el.gradesContainer.appendChild(row);
      });

      el.gradeTotalBadge.textContent = `Total: ${totalGrade.toFixed(1)}%`;
      el.statGradeBalance.textContent = `${totalGrade.toFixed(1)}%`;
      if (Math.abs(totalGrade - 100.0) < 0.05) {
        el.gradeTotalBadge.className = 'badge badge-success';
      } else {
        el.gradeTotalBadge.className = 'badge badge-danger';
      }
    }

    // Preview next version number in revision box
    const currentVer = plan.version || '1.0';
    el.nextVersionPreview.textContent = incrementVersionStr(currentVer);
  }

  // =========================================================================
  // SCREEN 4: Natural Language Revision Engine
  // =========================================================================

  async function handleRevision() {
    const prompt = el.revisionPromptInput.value.trim();
    if (!prompt) {
      showAlert('Please enter feedback describing desired changes to the plan.');
      el.revisionPromptInput.focus();
      return;
    }

    if (!state.currentPlan || !state.currentPlan.plan_id) {
      showAlert('No active plan found to revise.');
      return;
    }

    el.btnSubmitRevision.disabled = true;
    el.spinnerRevise.classList.remove('hidden');

    recordActionTrace('Revision requested', `Submitted feedback: "${prompt.slice(0, 70)}..."`);

    try {
      const revisionData = await apiCall('/api/lab1/revise', 'POST', {
        plan_id: state.currentPlan.plan_id,
        revision_prompt: prompt,
      });

      recordActionTrace('Plan validated', 'Curriculum constraints and 100% grade balance verified.');
      recordActionTrace('New version created', `Created v${revisionData.current_version} with ${revisionData.structured_diffs.length} structured diffs.`);

      state.latestRevision = revisionData;
      state.currentPlan = revisionData.revised_plan;

      // Update plan history and dropdown
      await refreshPlanHistory(state.currentPlan.plan_id);

      // Re-render plan with updated v1.1
      renderPlan(state.currentPlan);
      renderDiffs(revisionData);

      // Switch to Diffs tab to showcase exact changes
      switchPlanTab('tab-diffs');
      setStep(4);

      // Clear revision prompt
      el.revisionPromptInput.value = '';
    } catch (err) {
      showAlert(`Could not revise the course plan: ${err.message}`);
    } finally {
      el.btnSubmitRevision.disabled = false;
      el.spinnerRevise.classList.add('hidden');
    }
  }

  // =========================================================================
  // SCREEN 6: Structured Diff Renderer
  // =========================================================================

  function renderDiffs(revisionData) {
    if (!revisionData) return;
    const diffs = revisionData.structured_diffs || [];
    el.diffsBadgeCount.textContent = diffs.length;
    el.diffPrevVer.textContent = revisionData.previous_version;
    el.diffCurrVer.textContent = revisionData.current_version;
    el.changelogSummaryText.textContent = revisionData.changelog_summary || 'Changes applied successfully.';

    el.diffsList.innerHTML = '';
    diffs.forEach(d => {
      const card = document.createElement('div');
      card.className = 'diff-card';

      let actionBadge = 'badge-accent';
      if (d.action === 'ADDED') actionBadge = 'badge-success';
      if (d.action === 'REMOVED') actionBadge = 'badge-danger';
      if (d.action === 'MODIFIED') actionBadge = 'badge-warning';

      const oldValFormatted = d.old_value !== null && d.old_value !== undefined ? (typeof d.old_value === 'object' ? JSON.stringify(d.old_value) : String(d.old_value)) : 'None';
      const newValFormatted = d.new_value !== null && d.new_value !== undefined ? (typeof d.new_value === 'object' ? JSON.stringify(d.new_value) : String(d.new_value)) : 'None';

      card.innerHTML = `
        <div class="diff-header">
          <span class="badge ${actionBadge}">${escapeHtml(d.action)}</span>
          <span class="badge badge-neutral">Section: ${escapeHtml(d.section)}</span>
          <span class="diff-path">Path: ${escapeHtml(d.path)}</span>
        </div>
        <div class="diff-desc">${escapeHtml(d.change_description)}</div>
        <div class="diff-compare-box">
          <div class="diff-old"><strong>Before:</strong> ${escapeHtml(oldValFormatted)}</div>
          <div class="diff-new"><strong>After:</strong> ${escapeHtml(newValFormatted)}</div>
        </div>
      `;
      el.diffsList.appendChild(card);
    });
  }

  // =========================================================================
  // SCREEN 5: Version History & Switching
  // =========================================================================

  async function refreshPlanHistory(planId) {
    try {
      const history = await apiCall(`/api/lab1/history/${planId}`);
      state.planHistory = history;

      const versions = (history.versions || []).map(p => p.version);
      renderVersionPills(versions, history.current_version);
      renderVersionHistoryTab(history);
    } catch (err) {
      console.error('History refresh error:', err);
    }
  }

  function renderVersionPills(versions, activeVersion) {
    el.versionPillsList.innerHTML = '';
    versions.forEach(v => {
      const btn = document.createElement('button');
      btn.className = `version-pill-btn ${v === activeVersion ? 'active' : ''}`;
      btn.textContent = `v${v}${v === '1.0' ? ' (Initial)' : ''}`;
      btn.setAttribute('aria-label', `Switch to Plan Version ${v}`);
      btn.addEventListener('click', () => switchVersion(v));
      el.versionPillsList.appendChild(btn);
    });
  }

  async function switchVersion(selectedVersion) {
    if (!state.currentPlan) return;
    try {
      const plan = await apiCall(`/api/lab1/plan/${state.currentPlan.plan_id}?version=${selectedVersion}`);
      state.currentPlan = plan;
      renderPlan(plan);
      
      const versions = (state.planHistory?.versions || []).map(p => p.version);
      renderVersionPills(versions, selectedVersion);
      renderVersionHistoryTab(state.planHistory, selectedVersion);
    } catch (err) {
      console.error('Version switch error:', err);
    }
  }

  function renderVersionHistoryTab(history, activeVersion = null) {
    if (!el.versionHistoryTimeline || !history) return;
    const currentVer = activeVersion || history.current_version;
    const versions = history.versions || [];
    el.versionsCountBadge.textContent = `${versions.length} Version${versions.length > 1 ? 's' : ''}`;

    el.versionHistoryTimeline.innerHTML = '';
    versions.forEach(verPlan => {
      const isCurrent = verPlan.version === currentVer;
      const card = document.createElement('div');
      card.className = `history-item-card ${isCurrent ? 'active-version' : ''}`;

      const matchedRev = (history.revisions || []).find(r => r.current_version === verPlan.version);
      const summaryText = matchedRev ? matchedRev.changelog_summary : (verPlan.version === '1.0' ? 'Initial baseline synthesized from clarification answers.' : 'Revised version.');

      card.innerHTML = `
        <div class="history-item-top">
          <div style="display: flex; align-items: center; gap: 0.6rem;">
            <span class="badge ${isCurrent ? 'badge-accent' : 'badge-neutral'} history-ver-badge">v${verPlan.version}</span>
            <span style="font-weight: 600; font-size: 0.95rem; color: var(--text-primary);">${escapeHtml(verPlan.course_name)}</span>
            ${isCurrent ? '<span class="badge badge-success">Active View</span>' : ''}
          </div>
          <button class="btn btn-secondary btn-sm btn-load-ver" data-ver="${verPlan.version}" aria-label="Inspect Plan Version ${verPlan.version}">
            ${isCurrent ? 'Viewing' : 'Inspect v' + verPlan.version}
          </button>
        </div>
        <div class="history-summary">${escapeHtml(summaryText)}</div>
        <div style="font-size: 0.78rem; color: var(--text-muted);">
          Duration: ${verPlan.duration_weeks ? verPlan.duration_weeks + ' Weeks' : 'Source-based'} &bull; Deliverables: ${verPlan.assignments && verPlan.assignments.length > 0 ? verPlan.assignments.length : 'Not specified'} &bull; TA Staffing: ${verPlan.ta_allocation_hours !== null && verPlan.ta_allocation_hours !== undefined ? verPlan.ta_allocation_hours + ' hrs/wk' : 'Not specified'}
        </div>
      `;

      card.querySelector('.btn-load-ver').addEventListener('click', () => switchVersion(verPlan.version));
      el.versionHistoryTimeline.appendChild(card);
    });
  }

  // =========================================================================
  // System Execution Audit Trail Drawer & Modals
  // =========================================================================

  function openModal(modalEl, openerBtn) {
    if (!modalEl) return;
    modalEl.classList.remove('hidden');
    if (openerBtn) openerBtn.setAttribute('aria-expanded', 'true');
    // Focus first interactive element or close button for accessibility
    const focusTarget = modalEl.querySelector('.btn-close') || modalEl.querySelector('input, select, textarea, button');
    if (focusTarget) focusTarget.focus();
  }

  function closeModal(modalEl, openerBtn) {
    if (!modalEl) return;
    modalEl.classList.add('hidden');
    if (openerBtn) {
      openerBtn.setAttribute('aria-expanded', 'false');
      openerBtn.focus();
    }
  }

  async function openAuditDrawer() {
    openModal(el.auditDrawer, el.btnAuditDrawer);
    el.auditTimeline.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">Loading audit trail...</div>';

    try {
      const logs = await apiCall('/api/system/audit');
      renderAuditTimeline(logs);
    } catch (err) {
      el.auditTimeline.innerHTML = '<div style="color: var(--danger-text);">Failed to load audit logs.</div>';
    }
  }

  function renderAuditTimeline(logs) {
    el.auditTimeline.innerHTML = '';
    if (!logs || logs.length === 0) {
      el.auditTimeline.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem;">No actions logged in this session yet.</div>';
      return;
    }

    logs.slice().reverse().forEach(log => {
      const item = document.createElement('div');
      item.className = 'audit-item';
      item.innerHTML = `
        <div class="audit-item-top">
          <span class="audit-action">${escapeHtml(log.lab_id)}:${escapeHtml(log.action)}</span>
          <span class="audit-dur">${typeof log.duration_ms === 'number' ? log.duration_ms.toFixed(1) + 'ms' : ''}</span>
        </div>
        <div style="font-size: 0.75rem; color: var(--text-muted); font-family: var(--font-mono);">
          Trace ID: ${escapeHtml(log.trace_id)} &bull; Status: ${escapeHtml(log.status)}
        </div>
      `;
      el.auditTimeline.appendChild(item);
    });
  }

  // =========================================================================
  // Tab Switching
  // =========================================================================

  function switchPlanTab(tabId) {
    document.querySelectorAll('.plan-tab-btn').forEach(btn => {
      const isActive = btn.getAttribute('data-tab') === tabId;
      btn.classList.toggle('active', isActive);
      btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    document.querySelectorAll('.tab-pane').forEach(pane => {
      const isTarget = pane.id === tabId;
      pane.classList.toggle('active', isTarget);
      pane.classList.toggle('hidden', !isTarget);
    });
    if (tabId === 'tab-actiontrace') renderActionTrace();
    if (tabId === 'tab-history' && state.currentPlan) renderHistoryUI(state.planHistory || [state.currentPlan]);
  }

  // =========================================================================
  // Helpers & Reset
  // =========================================================================

  function formatCategory(cat) {
    const map = {
      schedule_pacing: 'Schedule & Pacing',
      materials_prerequisites: 'Materials & Prerequisites',
      assignments_labs: 'Assignments & Labs',
      grading_weights: 'Grading Weights',
      ta_support: 'TA Support',
    };
    return map[cat] || cat.replace(/_/g, ' ').toUpperCase();
  }

  function incrementVersionStr(vStr) {
    const parts = vStr.split('.');
    if (parts.length === 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
      return `${parts[0]}.${parseInt(parts[1]) + 1}`;
    }
    return `${vStr}.1`;
  }

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function resetSession() {
    state.originalPrompt = '';
    state.requestId = '';
    state.clarificationQuestions = [];
    state.currentPlan = null;
    state.planHistory = null;
    state.latestRevision = null;
    state.actionTrace = [];

    el.promptInput.value = '';
    el.revisionPromptInput.value = '';
    if (el.questionsList) el.questionsList.innerHTML = '';
    if (el.materialsContainer) el.materialsContainer.innerHTML = '';
    if (el.assignmentsContainer) el.assignmentsContainer.innerHTML = '';
    if (el.gradesContainer) el.gradesContainer.innerHTML = '';
    if (el.versionPillsList) el.versionPillsList.innerHTML = '';
    if (el.versionHistoryTimeline) el.versionHistoryTimeline.innerHTML = '';
    if (el.diffsList) el.diffsList.innerHTML = '';
    if (el.changelogSummaryText) el.changelogSummaryText.textContent = '';
    hideAlert();
    renderActionTrace();
    setStep(1);
    showScreen(el.screenRequest);
    el.promptInput.focus();
  }

  // =========================================================================
  // Lab 2 Logic: Tool-Using Agent & Trace Auditor
  // =========================================================================

  let lab2ToolsList = [];

  const labTitles = {
    lab1: 'Workspace Planner',
    lab2: 'Tool & Agent Auditor',
    lab3: 'Reusable Skills Center',
    lab4: 'Memory & Grounded RAG',
    lab5: 'Governed Academic Sources',
    lab6: 'Controlled Runtime & Gates',
    lab7: 'Agentic Node Graph',
    lab8: 'Parallel Swarm',
    lab9: 'Deep Research Agent',
    lab10: 'Cloud Operations Agent',
    lab11: 'Agentic SDLC Factory',
    lab12: 'Safety & Governance',
    lab13: 'Course-Type Specialists',
    lab14: 'Integrated Course Capstone',
    submissions: 'GitHub Submissions',
    dashboard: 'Dashboard',
    notifications: 'Notifications',
    knowledge: 'Knowledge & Notes',
    faculty: 'Faculty Review',
    history: 'History',
    about: 'About',
  };

  function switchLab(labId) {
    const activeViewKey = labId === 'faculty' ? 'submissions' : labId;
    Object.keys(el.navTabs).forEach((id) => {
      const tab = el.navTabs[id];
      if (!tab) return;
      const isActive = id === labId;
      tab.classList.toggle('active', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });
    Object.keys(el.views).forEach((id) => {
      const view = el.views[id];
      if (!view) return;
      if (id === activeViewKey) {
        view.classList.remove('hidden');
      } else {
        view.classList.add('hidden');
      }
    });
    el.activeLabTag.textContent = labTitles[labId] || 'Workspace Planner';

    if (labId === 'lab2') loadLab2Scenarios();
    if (labId === 'lab3') loadLab3Data();
    if (labId === 'lab4') loadLab4Data();
    if (labId === 'lab5') loadLab5Data();
    if (labId === 'lab6') loadLab6Data();
    if (labId === 'lab7') loadLab7Topology();
    if (labId === 'lab8') loadLab8Data();
    if (labId === 'submissions' || labId === 'faculty') loadSubmissionsData();
    if (labId === 'faculty') switchPortalRole('FACULTY');
    if (labId === 'knowledge') {
      loadKnowledgeFiles();
      loadCourseMaterials();
    }
    if (labId === 'dashboard') loadDashboard();
    if (labId === 'notifications') loadInbox();
    if (labId === 'history') loadHistory();
  }

  async function loadLab2Scenarios() {
    await loadLab2Catalog();
    if (el.lab2ScenariosChips.children.length > 0) return;
    try {
      const scenarios = await apiCall('/api/lab2/scenarios');
      el.lab2ScenariosChips.innerHTML = '';
      scenarios.forEach(sc => {
        const btn = document.createElement('button');
        btn.className = 'chip-btn';
        btn.textContent = sc.title.replace('Scenario ', 'S');
        btn.title = sc.description;
        btn.addEventListener('click', async () => {
          el.lab2QueryInput.value = sc.prompt;
          if (sc.course_id && el.lab2CourseSelect) {
            el.lab2CourseSelect.value = sc.course_id;
            await loadLab2Assignments();
          }
          if (sc.assignment_id && el.lab2AssignmentSelect) {
            el.lab2AssignmentSelect.value = sc.assignment_id;
          }
          el.lab2QueryInput.focus();
        });
        el.lab2ScenariosChips.appendChild(btn);
      });
    } catch (err) {
      console.warn('Failed to load Lab 2 scenarios', err);
    }
  }

  async function loadLab2Catalog() {
    if (!el.lab2CourseSelect || !el.lab2AssignmentSelect) return;
    const scopedCourses = authenticatedUser?.course_scopes || [];
    const courseIds = authenticatedUser?.role === 'ADMIN'
      ? [state.courseCodeHint || '26ECAC401']
      : (scopedCourses.length > 0 ? scopedCourses : [state.courseCodeHint || '26ECAC401']);
    const selectedCourse = el.lab2CourseSelect.value;
    el.lab2CourseSelect.innerHTML = courseIds.map(courseId =>
      `<option value="${escapeHtml(courseId)}">${escapeHtml(courseId)}</option>`
    ).join('');
    if (courseIds.includes(selectedCourse)) el.lab2CourseSelect.value = selectedCourse;
    await loadLab2Assignments();
  }

  async function loadLab2Assignments() {
    if (!el.lab2CourseSelect || !el.lab2AssignmentSelect) return;
    const courseId = el.lab2CourseSelect.value;
    el.lab2AssignmentSelect.innerHTML = '<option value="">Select a course assignment</option>';
    if (!courseId) return;
    try {
      const assignments = await apiCall(`/api/assignments?course_id=${encodeURIComponent(courseId)}`);
      (assignments || []).forEach(assignment => {
        const option = document.createElement('option');
        option.value = assignment.id;
        option.textContent = `${assignment.title} (${assignment.id})`;
        el.lab2AssignmentSelect.appendChild(option);
      });
    } catch (err) {
      console.warn('Failed to load authorized Lab 2 assignment catalog', err);
    }
  }

  async function handleLab2Query() {
    const query = el.lab2QueryInput.value.trim();
    if (!query) {
      showAlert('Please enter a course query or select an evaluation scenario.');
      el.lab2QueryInput.focus();
      return;
    }
    if (/\b(rubric|assignment|deliverables|submission)\b/i.test(query) && !el.lab2AssignmentSelect?.value) {
      showAlert('Select an assignment from the authorized course catalog before asking about its specification or rubric.');
      el.lab2AssignmentSelect?.focus();
      return;
    }

    setButtonLoading(el.btnLab2RunQuery, el.spinnerLab2Run, true);
    hideAlert();

    try {
      const trace = await apiCall('/api/lab2/query', 'POST', {
        request: query,
        course_id: el.lab2CourseSelect?.value || state.courseCodeHint || '26ECAC401',
        assignment_id: el.lab2AssignmentSelect?.value || null,
      });
      renderLab2Trace(trace);
    } catch (err) {
      showAlert(`Tool Agent Execution Failed: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab2RunQuery, el.spinnerLab2Run, false);
    }
  }

  function renderLab2Trace(trace) {
    if (!trace) return;
    el.lab2ResultsContainer.classList.remove('hidden');

    // Quick Stats
    const stepCount = trace.steps ? trace.steps.length : 0;
    const factKeys = trace.verified_facts ? Object.keys(trace.verified_facts) : [];
    
    const topStatus = trace.status || (trace.steps && trace.steps.some(s => s.tool_call && s.tool_call.status !== 'SUCCESS') ? 'EXECUTION_ERROR' : 'SUCCESS');
    el.lab2StatStatus.textContent = topStatus;
    el.lab2StatStatus.className = topStatus === 'SUCCESS' ? 'stat-value text-success' : 'stat-value text-danger';
    
    el.lab2StatToolsCount.textContent = `${stepCount} Call${stepCount === 1 ? '' : 's'}`;
    el.lab2StatFactsCount.textContent = `${factKeys.length} Confirmed`;
    el.lab2StatDuration.textContent = `${(trace.total_duration_ms || 0).toFixed(2)} ms`;
    el.lab2StepsBadge.textContent = `${stepCount} Step${stepCount === 1 ? '' : 's'}`;

    // Trace Steps Timeline
    el.lab2TraceStepsList.innerHTML = '';
    (trace.steps || []).forEach(step => {
      const stepCard = document.createElement('div');
      stepCard.className = 'lab2-step-card';
      
      const tc = step.tool_call || {};
      const statusClass = tc.status === 'SUCCESS' ? 'badge-success' : 'badge-danger';
      const durationText = tc.execution_duration_ms ? `${tc.execution_duration_ms.toFixed(2)} ms` : '-- ms';

      stepCard.innerHTML = `
        <div class="step-card-header">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge badge-accent">Step ${step.step_number}</span>
            <span class="step-tool-badge">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
              </svg>
              ${escapeHtml(tc.tool_name || 'unknown')}
            </span>
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span class="badge ${statusClass}">${escapeHtml(tc.status || 'UNKNOWN')}</span>
            <span class="audit-dur">${durationText}</span>
          </div>
        </div>

        <div class="step-rationale">
          <strong>Action Rationale:</strong> ${escapeHtml(step.selected_action || '')}
        </div>

        <div class="step-summary-box">
          ${escapeHtml(step.intermediate_summary || '')}
        </div>

        <details class="step-details-toggle">
          <summary style="cursor: pointer; font-weight: 600; color: var(--accent-light);">
            View Validated Input & Output Payloads
          </summary>
          <div class="step-json-drawer">
            <div>
              <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">INPUT (Validated against schema):</span>
              <pre class="json-viewer">${escapeHtml(JSON.stringify(tc.validated_input || {}, null, 2))}</pre>
            </div>
            <div>
              <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">OUTPUT DATA (Verified):</span>
              <pre class="json-viewer">${escapeHtml(JSON.stringify(tc.output_data || { error: tc.error }, null, 2))}</pre>
            </div>
          </div>
        </details>

        <div class="step-provenance">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"></path>
          </svg>
          Source: ${escapeHtml(step.evidence_source || 'Course Repository')}
        </div>
      `;
      el.lab2TraceStepsList.appendChild(stepCard);
    });

    // Final Conclusion
    el.lab2FinalConclusion.textContent = trace.final_conclusion || 'No conclusion generated.';

    // Verified Facts
    el.lab2VerifiedFactsList.innerHTML = '';
    if (factKeys.length === 0) {
      el.lab2VerifiedFactsList.innerHTML = '<div style="font-size: 0.85rem; color: var(--text-muted); padding: 0.5rem;">No verified facts established (error or unknown entity).</div>';
    } else {
      factKeys.forEach(key => {
        const val = trace.verified_facts[key];
        const factCard = document.createElement('div');
        factCard.className = 'fact-item-card';
        const displayVal = typeof val === 'object' ? JSON.stringify(val) : String(val);
        factCard.innerHTML = `
          <span class="fact-item-key">${escapeHtml(key)}</span>
          <span class="fact-item-val">${escapeHtml(displayVal)}</span>
        `;
        el.lab2VerifiedFactsList.appendChild(factCard);
      });
    }

    el.lab2ResultsContainer.scrollIntoView({ behavior: 'smooth' });
  }

  // Tools Catalog Modal
  async function openLab2ToolsModal() {
    openModal(el.lab2ToolsModal, el.btnLab2ViewTools);
    if (lab2ToolsList.length === 0) {
      try {
        lab2ToolsList = await apiCall('/api/lab2/tools');
        renderLab2ToolsCatalog();
      } catch (err) {
        el.lab2ToolsListContainer.innerHTML = `<div style="color: var(--danger-text);">Failed to load tools: ${escapeHtml(err.message)}</div>`;
      }
    }
  }

  function renderLab2ToolsCatalog() {
    el.lab2ToolsListContainer.innerHTML = '';
    lab2ToolsList.forEach(tool => {
      const card = document.createElement('div');
      card.className = 'tool-def-card';
      card.innerHTML = `
        <div class="tool-def-header">
          <span class="tool-def-name">${escapeHtml(tool.name)}</span>
          <span class="badge badge-accent">${escapeHtml(tool.category || 'tool')}</span>
        </div>
        <p class="tool-def-desc">${escapeHtml(tool.description)}</p>
        <div class="tool-def-schemas">
          <div>
            <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">INPUT SCHEMA (Pydantic):</span>
            <pre class="json-viewer" style="max-height: 140px;">${escapeHtml(JSON.stringify(tool.input_schema || {}, null, 2))}</pre>
          </div>
          <div>
            <span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">OUTPUT SCHEMA (Pydantic):</span>
            <pre class="json-viewer" style="max-height: 140px;">${escapeHtml(JSON.stringify(tool.output_schema || {}, null, 2))}</pre>
          </div>
        </div>
      `;
      el.lab2ToolsListContainer.appendChild(card);
    });
  }

  // Direct Sandbox Modal
  async function openLab2Sandbox() {
    openModal(el.lab2SandboxModal, el.btnLab2OpenSandbox);
    if (lab2ToolsList.length === 0) {
      try {
        lab2ToolsList = await apiCall('/api/lab2/tools');
      } catch (err) {
        console.warn(err);
      }
    }
    el.sandboxToolSelect.innerHTML = '';
    lab2ToolsList.forEach(t => {
      const opt = document.createElement('option');
      opt.value = t.name;
      opt.textContent = `${t.name} (${t.category})`;
      el.sandboxToolSelect.appendChild(opt);
    });
  }

  async function handleRunSandbox() {
    const toolName = el.sandboxToolSelect.value;
    let params = {};
    try {
      params = JSON.parse(el.sandboxParamsInput.value.trim() || '{}');
    } catch (err) {
      showAlert('Invalid JSON in Sandbox input parameters.');
      el.sandboxParamsInput.focus();
      return;
    }

    setButtonLoading(el.btnRunSandbox, el.spinnerSandbox, true);
    try {
      const res = await apiCall('/api/lab2/tools/execute', 'POST', {
        tool_name: toolName,
        parameters: params,
      });
      el.sandboxResultPre.textContent = JSON.stringify(res, null, 2);
    } catch (err) {
      el.sandboxResultPre.textContent = `ERROR: ${err.message}`;
    } finally {
      setButtonLoading(el.btnRunSandbox, el.spinnerSandbox, false);
    }
  }

  // =========================================================================
  // Lab 3: Reusable Agent Skills (Planning, Research, Formatting)
  // =========================================================================
  async function loadLab3Data() {
    try {
      const [skills, scenarios] = await Promise.all([
        apiCall('/api/lab3/skills'),
        apiCall('/api/lab3/scenarios')
      ]);
      renderLab3Skills(skills);
      renderLab3Scenarios(scenarios);
    } catch (err) {
      console.warn('Failed to load Lab 3 data', err);
    }
  }

  function renderLab3Skills(skillsData) {
    if (!el.lab3SkillsCatalogGrid || !skillsData) return;
    const skills = Array.isArray(skillsData) ? skillsData : (skillsData.skills || []);
    el.lab3SkillsCatalogGrid.innerHTML = '';

    if (el.lab3SandboxSelect) {
      el.lab3SandboxSelect.innerHTML = '';
    }

    skills.forEach(skill => {
      const card = document.createElement('div');
      card.className = 'skill-card';
      card.innerHTML = `
        <div class="skill-card-header">
          <span class="skill-title">${escapeHtml(skill.title || skill.name)}</span>
          <span class="badge badge-accent">v${escapeHtml(skill.version || '1.0.0')}</span>
        </div>
        <div class="skill-desc">${escapeHtml(skill.description)}</div>
        <div style="display: flex; gap: 0.5rem; margin-top: auto;">
          <button class="btn btn-secondary btn-sm" onclick="prefillSkillSandbox('${escapeHtml(skill.name)}')">Use in Sandbox</button>
        </div>
      `;
      el.lab3SkillsCatalogGrid.appendChild(card);

      if (el.lab3SandboxSelect) {
        const opt = document.createElement('option');
        opt.value = skill.name;
        opt.textContent = `${skill.title || skill.name} (${skill.name})`;
        el.lab3SandboxSelect.appendChild(opt);
      }
    });

    if (skills.length > 0 && el.lab3SandboxParams && !el.lab3SandboxParams.value.trim()) {
      window.prefillSkillSandbox(skills[0].name);
    }
  }

  window.prefillSkillSandbox = function(skillName) {
    if (el.lab3SandboxSelect) el.lab3SandboxSelect.value = skillName;
    if (skillName === 'planning_skill' || skillName === 'course_planning_skill') {
      el.lab3SandboxParams.value = JSON.stringify({ course_code: '26ECAC401', target_weeks: 14, focus_chapters: [1, 2, 3, 4] }, null, 2);
    } else if (skillName === 'research_skill' || skillName === 'research_summary_skill') {
      el.lab3SandboxParams.value = JSON.stringify({ topic: 'autonomous agent loops', course_code: '26ECAC401', target_chapter: 1 }, null, 2);
    } else if (skillName === 'formatting_skill' || skillName === 'course_content_formatting_skill') {
      el.lab3SandboxParams.value = JSON.stringify({ title: 'Unit 1 Overview', course_code: '26ECAC401', target_format: 'markdown_handout', raw_content: 'Plan-Act-Observe-Revise autonomous loop architecture' }, null, 2);
    }
    el.lab3SandboxParams.focus();
  };

  function renderLab3Scenarios(scenarios) {
    if (!el.lab3ScenariosChips || !scenarios) return;
    el.lab3ScenariosChips.innerHTML = '';
    scenarios.forEach(sc => {
      const btn = document.createElement('button');
      btn.className = 'chip-btn';
      btn.textContent = sc.title.replace('Scenario: ', '');
      btn.title = sc.description;
      btn.addEventListener('click', () => {
        el.lab3QueryInput.value = sc.prompt;
        el.lab3QueryInput.focus();
      });
      el.lab3ScenariosChips.appendChild(btn);
    });
  }

  async function handleLab3Agent() {
    const query = el.lab3QueryInput.value.trim();
    if (!query) {
      showAlert('Please enter an agent task for Lab 3.');
      el.lab3QueryInput.focus();
      return;
    }
    setButtonLoading(el.btnLab3RunAgent, el.spinnerLab3Run, true);
    hideAlert();
    try {
      const res = await apiCall('/api/lab3/query', 'POST', {
        request: query,
        course_id: '26ECAC401'
      });
      el.lab3ResultsContainer.classList.remove('hidden');
      el.lab3StatStatus.textContent = res.status || 'UNKNOWN';
      el.lab3StatSkillsCount.textContent = `${res.skills_executed?.length || 0} Skills`;
      el.lab3StatDuration.textContent = `${Number(res.duration_ms || 0).toFixed(2)} ms`;

      el.lab3SkillStepsList.innerHTML = '';
      (res.skills_executed || []).forEach(step => {
        const div = document.createElement('div');
        div.className = 'step-record';
        div.innerHTML = `
          <div class="step-header">
            <strong>${escapeHtml(step.skill_name || 'Unknown skill')}</strong>
            <span class="badge ${step.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${escapeHtml(step.status || 'UNKNOWN')}</span>
          </div>
          <p class="step-rationale" style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(step.rationale || '')}</p>
          <pre class="code-block json-viewer" style="max-height: 140px;">${escapeHtml(JSON.stringify(step.output_data || {}, null, 2))}</pre>
        `;
        el.lab3SkillStepsList.appendChild(div);
      });

      el.lab3FinalFormattedOutput.innerHTML = `<pre style="white-space: pre-wrap; font-family: var(--font-sans);">${escapeHtml(res.formatted_output || JSON.stringify(res, null, 2))}</pre>`;
    } catch (err) {
      showAlert(`Lab 3 error: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab3RunAgent, el.spinnerLab3Run, false);
    }
  }

  async function handleLab3Sandbox() {
    const skillName = el.lab3SandboxSelect.value;
    let params = {};
    try {
      params = JSON.parse(el.lab3SandboxParams.value.trim() || '{}');
    } catch (err) {
      showAlert('Invalid JSON in Sandbox input parameters.');
      return;
    }
    setButtonLoading(el.btnLab3RunSandbox, el.spinnerLab3Sandbox, true);
    try {
      const res = await apiCall('/api/lab3/skills/execute', 'POST', {
        skill_name: skillName,
        parameters: params
      });
      el.lab3SandboxResultPre.textContent = JSON.stringify(res, null, 2);
    } catch (err) {
      el.lab3SandboxResultPre.textContent = `ERROR: ${err.message}`;
    } finally {
      setButtonLoading(el.btnLab3RunSandbox, el.spinnerLab3Sandbox, false);
    }
  }

  // =========================================================================
  // Lab 4: Memory & Retrieval
  // =========================================================================
  async function loadLab4Data() {
    await refreshLab4Session();
  }

  async function createLab4Session() {
    const session = await apiCall('/api/lab4/session/create', 'POST', {
      course_id: '26ECAC401'
    });
    if (typeof session?.session_id !== 'string' || !session.session_id) {
      throw new Error('The server did not return a session ID.');
    }
    el.lab4SessionIdInput.value = session.session_id;
    el.lab4SessionViewPre.textContent = JSON.stringify(session, null, 2);
    return session.session_id;
  }

  async function ensureLab4Session() {
    return el.lab4SessionIdInput.value.trim() || await createLab4Session();
  }

  async function refreshLab4Session() {
    const sid = el.lab4SessionIdInput.value.trim();
    try {
      if (!sid) {
        await createLab4Session();
        return;
      }
      const response = await fetch(`/api/lab4/sessions/${encodeURIComponent(sid)}`);
      const envelope = await response.json();
      if (response.status === 404) {
        await createLab4Session();
        return;
      }
      if (!response.ok || !envelope.success) {
        throw new Error(envelope.error?.message || `HTTP ${response.status}: Could not load session.`);
      }
      el.lab4SessionViewPre.textContent = JSON.stringify(envelope.data, null, 2);
    } catch (err) {
      el.lab4SessionViewPre.textContent = `Failed to load session '${sid}': ${err.message}`;
      showAlert(`Could not initialize Lab 4 session: ${err.message}`);
    }
  }

  async function handleLab4NewSession() {
    try {
      await createLab4Session();
    } catch (err) {
      el.lab4SessionViewPre.textContent = `Failed to create session: ${err.message}`;
    }
  }

  async function handleLab4AddTurn() {
    const role = el.lab4TurnRole.value;
    const content = el.lab4TurnContent.value.trim();
    if (!content) return;
    try {
      const sid = await ensureLab4Session();
      await apiCall(`/api/lab4/sessions/${encodeURIComponent(sid)}/turn`, 'POST', { role, content });
      el.lab4TurnContent.value = '';
      refreshLab4Session();
    } catch (err) {
      showAlert(`Failed to append turn: ${err.message}`);
    }
  }

  async function handleLab4SetScratch() {
    const key = el.lab4ScratchKey.value.trim();
    const value = el.lab4ScratchVal.value.trim();
    if (!key) return;
    try {
      const sid = await ensureLab4Session();
      await apiCall(`/api/lab4/sessions/${encodeURIComponent(sid)}/scratchpad`, 'POST', { key, value });
      el.lab4ScratchKey.value = '';
      el.lab4ScratchVal.value = '';
      refreshLab4Session();
    } catch (err) {
      showAlert(`Failed to set scratchpad: ${err.message}`);
    }
  }

  async function handleLab4SearchRag() {
    const query = el.lab4RagQueryInput.value.trim();
    if (!query) {
      showAlert('Please enter a search query for long-term knowledge.');
      return;
    }
    const chapterVal = el.lab4RagChapterSelect.value;
    const chapter = chapterVal ? parseInt(chapterVal, 10) : null;

    setButtonLoading(el.btnLab4SearchRag, el.spinnerLab4Rag, true);
    try {
      const res = await apiCall('/api/lab4/retrieval/search', 'POST', {
        query,
        course_id: '26ECAC401',
        chapter,
        top_k: 5
      });
      renderLab4RagResults(res);
    } catch (err) {
      showAlert(`Search failed: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab4SearchRag, el.spinnerLab4Rag, false);
    }
  }

  function renderLab4RagResults(res) {
    if (!el.lab4RagResultsContainer) return;
    el.lab4RagResultsContainer.innerHTML = '';
    const items = (res && (res.matches || res.results)) || [];
    if (items.length === 0) {
      el.lab4RagResultsContainer.innerHTML = `<div class="empty-state-hint">No matching knowledge chunks found (Anti-hallucination filter active).</div>`;
      return;
    }
    items.forEach(chunk => {
      const card = document.createElement('div');
      card.className = 'rag-chunk-card';
      const chunkText = chunk.matched_text || chunk.text || chunk.chunk_id;
      card.innerHTML = `
        <div class="rag-chunk-header">
          <span class="rag-chunk-source">${escapeHtml(chunk.source || chunk.source_document || 'Notes')}</span>
          <span class="badge badge-accent">Chapter ${chunk.chapter || 'All'}</span>
        </div>
        <p class="rag-chunk-text">${escapeHtml(chunkText)}</p>
        <div style="font-size: 0.72rem; color: var(--text-muted);">${(chunk.tags || []).map(t => `#${escapeHtml(t)}`).join(' ')}</div>
      `;
      el.lab4RagResultsContainer.appendChild(card);
    });
  }

  async function handleLab4Agent() {
    const query = el.lab4AgentQueryInput.value.trim();
    if (!query) {
      showAlert('Please enter a question for the memory agent.');
      return;
    }
    setButtonLoading(el.btnLab4RunAgent, el.spinnerLab4Agent, true);
    try {
      const sid = await ensureLab4Session();
      const res = await apiCall('/api/lab4/query', 'POST', {
        query: query,
        request: query,
        session_id: sid,
        course_id: '26ECAC401'
      });
      el.lab4AgentResponseBox.classList.remove('hidden');
      el.lab4AgentResponseContent.innerHTML = `
        <div style="margin-bottom: 0.8rem; font-size: 0.85rem; color: var(--text-muted);">
          Context Turns Used: <strong>${res.session_turns_used || res.short_term_turn_count || 0}</strong> &bull; Knowledge Chunks Cited: <strong>${(res.citations || res.retrieved_evidence || []).length}</strong>
        </div>
        <div style="white-space: pre-wrap; font-size: 0.92rem;">${escapeHtml(res.answer || res.response || res.grounded_answer || '')}</div>
      `;
      refreshLab4Session();
    } catch (err) {
      showAlert(`Memory agent error: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab4RunAgent, el.spinnerLab4Agent, false);
    }
  }

  // =========================================================================
  // Lab 5: MCP-Style Governed Connector & RBAC
  // =========================================================================
  async function loadLab5Data() {
    try {
      const [scenarios, audit] = await Promise.all([
        apiCall('/api/lab5/scenarios'),
        apiCall('/api/lab5/audit')
      ]);
      renderLab5Scenarios(scenarios);
      renderLab5Audit(audit);
    } catch (err) {
      console.warn('Failed to load Lab 5 data', err);
    }
  }

  function renderLab5Scenarios(scenarios) {
    if (!el.lab5ScenariosChips || !scenarios) return;
    el.lab5ScenariosChips.innerHTML = '';
    scenarios.forEach(sc => {
      const btn = document.createElement('button');
      btn.className = 'chip-btn';
      btn.textContent = sc.title.replace('Scenario: ', '');
      btn.title = sc.description;
      btn.addEventListener('click', () => {
        el.lab5SourceSelect.value = sc.source_id;
        el.lab5OpSelect.value = sc.operation;
        el.lab5RoleSelect.value = sc.role;
        el.lab5ResourceInput.value = sc.resource_path;
        el.lab5ParamsInput.value = JSON.stringify(sc.parameters || {}, null, 2);
      });
      el.lab5ScenariosChips.appendChild(btn);
    });
  }

  async function handleLab5Dispatch() {
    const source_id = el.lab5SourceSelect.value;
    const operation = el.lab5OpSelect.value;
    const client_role = el.lab5RoleSelect.value;
    const resource_path = el.lab5ResourceInput.value.trim();
    let parameters = {};
    try {
      parameters = JSON.parse(el.lab5ParamsInput.value.trim() || '{}');
    } catch (err) {
      showAlert('Invalid JSON in Parameters input.');
      return;
    }

    setButtonLoading(el.btnLab5Dispatch, el.spinnerLab5Dispatch, true);
    try {
      const res = await apiCall('/api/lab5/execute', 'POST', {
        source_id,
        operation,
        client_role,
        resource_path,
        parameters
      });
      el.lab5ResultPre.textContent = JSON.stringify(res, null, 2);
      await refreshLab5Audit();
    } catch (err) {
      el.lab5ResultPre.textContent = `ERROR: ${err.message}`;
    } finally {
      setButtonLoading(el.btnLab5Dispatch, el.spinnerLab5Dispatch, false);
    }
  }

  async function refreshLab5Audit() {
    try {
      const audit = await apiCall('/api/lab5/audit');
      renderLab5Audit(audit);
    } catch (err) {
      console.warn('Failed to refresh Lab 5 audit', err);
    }
  }

  function renderLab5Audit(auditLogs) {
    const logList = Array.isArray(auditLogs)
      ? auditLogs
      : (auditLogs && Array.isArray(auditLogs.logs) ? auditLogs.logs : []);

    if (!el.lab5AuditTableContainer) return;
    if (logList.length === 0) {
      el.lab5AuditTableContainer.innerHTML = `<div class="empty-state-hint" style="padding: 1rem;">No connector operations logged yet.</div>`;
      return;
    }
    let html = `
      <table class="audit-table">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Role</th>
            <th>Source</th>
            <th>Operation</th>
            <th>Resource</th>
            <th>Status</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
    `;
    logList.slice(0, 10).forEach(log => {
      const isSuccess = log.status === 'SUCCESS' || log.success === true;
      const statusBadge = isSuccess ? '<span class="badge badge-success">OK</span>' : '<span class="badge badge-danger">DENIED / ERR</span>';
      html += `
        <tr>
          <td>${escapeHtml(log.timestamp || '')}</td>
          <td><span class="badge badge-neutral">${escapeHtml(log.client_role || '')}</span></td>
          <td>${escapeHtml(log.source_id || '')}</td>
          <td>${escapeHtml(log.operation || '')}</td>
          <td>${escapeHtml(log.resource_path || '')}</td>
          <td>${statusBadge}</td>
          <td>${log.duration_ms || 0} ms</td>
        </tr>
      `;
    });
    html += `</tbody></table>`;
    el.lab5AuditTableContainer.innerHTML = html;
  }

  // =========================================================================
  // Lab 6: Controlled Agent Runtime & Gates
  // =========================================================================
  let currentLab6RunId = null;

  async function loadLab6Data() {
    // Ready for runtime
  }

  async function handleLab6Start() {
    const task = el.lab6TaskInput.value.trim() || 'Synthesize 14-week 26ECAC401 workspace plan';
    const max_steps = parseInt(el.lab6BudgetSteps.value, 10) || 6;

    setButtonLoading(el.btnLab6StartRun, el.spinnerLab6Start, true);
    try {
      const res = await apiCall('/api/lab6/start', 'POST', {
        task_description: task,
        course_id: '26ECAC401',
        budget: { max_steps, timeout_seconds: 60 }
      });
      currentLab6RunId = res.run_id;
      el.lab6RunControllerCard.classList.remove('hidden');
      el.lab6ActiveRunPill.textContent = `Run ID: ${res.run_id}`;
      el.lab6RunTitle.textContent = `Run: ${res.run_id}`;
      updateLab6RunUI(res);
    } catch (err) {
      showAlert(`Failed to start run: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab6StartRun, el.spinnerLab6Start, false);
    }
  }

  async function handleLab6Step() {
    if (!currentLab6RunId) return;
    try {
      const res = await apiCall('/api/lab6/step', 'POST', { run_id: currentLab6RunId });
      updateLab6RunUI(res);
    } catch (err) {
      showAlert(`Step execution failed: ${err.message}`);
    }
  }

  async function handleLab6Crash() {
    if (!currentLab6RunId) return;
    try {
      const res = await apiCall('/api/lab6/crash', 'POST', { run_id: currentLab6RunId });
      updateLab6RunUI(res);
      showAlert('Simulated Mid-Run Crash injected. State safely snapshotted in checkpoint!');
    } catch (err) {
      showAlert(`Crash simulation error: ${err.message}`);
    }
  }

  async function handleLab6Resume() {
    if (!currentLab6RunId) return;
    try {
      const res = await apiCall('/api/lab6/resume', 'POST', { run_id: currentLab6RunId });
      updateLab6RunUI(res);
      showAlert('Successfully resumed run from serialized state checkpoint!');
    } catch (err) {
      showAlert(`Resume error: ${err.message}`);
    }
  }

  async function handleLab6Decision(approved) {
    if (!currentLab6RunId) return;
    try {
      const res = await apiCall('/api/lab6/decision', 'POST', {
        run_id: currentLab6RunId,
        approved,
        comment: approved ? 'Approved by faculty review' : 'Rejected by faculty'
      });
      updateLab6RunUI(res);
    } catch (err) {
      showAlert(`Approval decision error: ${err.message}`);
    }
  }

  function updateLab6RunUI(run) {
    if (!run) return;
    const activeRun = (run && run.run) ? run.run : run;
    const runState = typeof activeRun.state === 'string' ? activeRun.state : (activeRun.state?.value || 'UNKNOWN');
    const executedSteps = Number.isFinite(activeRun.steps_executed)
      ? activeRun.steps_executed
      : (Array.isArray(activeRun.steps_executed) ? activeRun.steps_executed.length : 0);
    const auditEntries = Array.isArray(activeRun.audit_entries) ? activeRun.audit_entries : [];
    el.lab6RunStatusBadge.textContent = runState;
    el.lab6StatSteps.textContent = `${executedSteps} / ${activeRun.budget?.max_steps || 6}`;
    el.lab6StatCheckpoints.textContent = `${activeRun.checkpoints?.length || 0} Snapshots`;

    if (runState === 'WAITING_APPROVAL' || runState === 'PAUSED_FOR_APPROVAL') {
      el.lab6ApprovalGateBanner.classList.remove('hidden');
      el.lab6StatGate.textContent = 'Awaiting Signoff';
    } else {
      el.lab6ApprovalGateBanner.classList.add('hidden');
      el.lab6StatGate.textContent = runState === 'COMPLETED' ? 'Approved & Done' : 'None';
    }

    el.lab6StepsTimeline.innerHTML = '';
    auditEntries.forEach((step, idx) => {
      const div = document.createElement('div');
      div.className = 'step-record';
      div.innerHTML = `
        <div class="step-header">
          <strong>Event ${idx + 1}: ${escapeHtml(step.action)}</strong>
          <span class="badge ${step.status === 'SUCCESS' ? 'badge-success' : 'badge-danger'}">${escapeHtml(step.status)}</span>
        </div>
        <p style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(step.actor || '')}${step.error ? ` — ${escapeHtml(step.error)}` : ''}</p>
      `;
      el.lab6StepsTimeline.appendChild(div);
    });

    if (!auditEntries.length && executedSteps > 0) {
      el.lab6StepsTimeline.innerHTML = `<div class="empty-state-hint">${executedSteps} step(s) executed; detailed audit entries are unavailable in this response.</div>`;
    } else if (!auditEntries.length) {
      el.lab6StepsTimeline.innerHTML = '<div class="empty-state-hint">No runtime events recorded yet.</div>';
    }

    const lastCp = (activeRun.checkpoints && activeRun.checkpoints.length > 0) ? activeRun.checkpoints[activeRun.checkpoints.length - 1] : null;
    el.lab6CheckpointPre.textContent = lastCp ? JSON.stringify(lastCp, null, 2) : 'No checkpoints yet.';
  }

  // =========================================================================
  // Lab 7: Agentic Specialist Node Graph DAG
  // =========================================================================
  let currentLab7State = null;

  async function loadLab7Topology() {
    try {
      const topo = await apiCall('/api/lab7/topology');
      renderLab7Nodes(topo.nodes || []);
    } catch (err) {
      console.warn('Failed to load Lab 7 topology', err);
    }
  }

  function renderLab7Nodes(nodes) {
    if (!el.lab7GraphNodesGrid) return;
    el.lab7GraphNodesGrid.innerHTML = '';
    nodes.forEach((node, idx) => {
      const nodeState = currentLab7State?.node_states?.[node.id];
      const isCompleted = ['COMPLETED', 'SUCCESS', 'DONE'].includes(nodeState) || currentLab7State?.completed_nodes?.includes(node.id);
      const isWaiting = nodeState === 'WAITING_APPROVAL';
      const isActive = currentLab7State?.current_node === node.id && !isWaiting;
      const isFailed = ['ERROR', 'VALIDATION_FAILED'].includes(nodeState);
      const nodeTrace = [...(currentLab7State?.execution_history || [])].reverse().find(item => item.node_id === node.id);

      let stateClass = '';
      let badgeHtml = '<span class="badge badge-neutral node-status-badge">PENDING</span>';
      if (isCompleted) {
        stateClass = 'completed';
        badgeHtml = '<span class="badge badge-success node-status-badge">DONE</span>';
      } else if (isWaiting) {
        stateClass = 'waiting';
        badgeHtml = '<span class="badge badge-accent node-status-badge">GATE SIGN OFF</span>';
      } else if (isActive) {
        stateClass = 'active';
        badgeHtml = `<span class="badge badge-accent node-status-badge">${escapeHtml(nodeState || 'RUNNING')}</span>`;
      } else if (isFailed) {
        stateClass = 'failed';
        badgeHtml = `<span class="badge badge-danger node-status-badge">${escapeHtml(nodeState)}</span>`;
      } else if (nodeState && nodeState !== 'PENDING') {
        badgeHtml = `<span class="badge badge-neutral node-status-badge">${escapeHtml(nodeState)}</span>`;
      }

      const card = document.createElement('div');
      card.className = `graph-node-card ${stateClass}`;
      card.innerHTML = `
        <span class="node-num">Node ${idx + 1}</span>
        <div class="node-title">${escapeHtml(node.label || node.id)}</div>
        <p style="font-size: 0.75rem; color: var(--text-muted);">${escapeHtml(node.description || '')}</p>
        ${badgeHtml}
        ${nodeTrace ? `<details class="node-execution-details"><summary>Execution details</summary><p>Attempt ${Number(nodeTrace.attempt_number || 1)} &bull; ${Number(nodeTrace.duration_ms || 0).toFixed(2)} ms</p><p><strong>Input:</strong> ${escapeHtml(nodeTrace.input_summary || 'Not recorded')}</p><p><strong>Output:</strong> ${escapeHtml(nodeTrace.output_summary || 'Not recorded')}</p>${nodeTrace.error ? `<p class="text-danger"><strong>Error:</strong> ${escapeHtml(nodeTrace.error)}</p>` : ''}</details>` : ''}
      `;
      el.lab7GraphNodesGrid.appendChild(card);
    });
  }

  async function handleLab7Run(singleStep = false) {
    const task = el.lab7TaskInput.value.trim() || 'Synthesize 26ECAC401 workspace plan';
    setButtonLoading(el.btnLab7RunAll, el.spinnerLab7Run, true);
    try {
      const endpoint = singleStep ? '/api/lab7/step' : '/api/lab7/run';
      const body = currentLab7State?.run_id ? { run_id: currentLab7State.run_id } : { user_request: task, course_id: '26ECAC401' };
      const res = await apiCall(endpoint, 'POST', body);
      currentLab7State = res;
      updateLab7UI(res);
    } catch (err) {
      showAlert(`Lab 7 graph error: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab7RunAll, el.spinnerLab7Run, false);
    }
  }

  async function handleLab7Approve(approved) {
    if (!currentLab7State?.run_id) return;
    try {
      const res = await apiCall('/api/lab7/approve', 'POST', {
        run_id: currentLab7State.run_id,
        approved
      });
      currentLab7State = res;
      updateLab7UI(res);
    } catch (err) {
      showAlert(`Faculty approval error: ${err.message}`);
    }
  }

  function updateLab7UI(state) {
    if (!state) return;
    el.lab7StatusTag.textContent = state.status;
    el.lab7RetryBadge.textContent = `Retries: ${state.retry_count || 0} / 3`;

    if (state.status === 'WAITING_APPROVAL') {
      el.lab7GateBanner.classList.remove('hidden');
    } else {
      el.lab7GateBanner.classList.add('hidden');
    }

    loadLab7Topology();

    if (state.status === 'COMPLETED' || state.published_workspace) {
      el.lab7OutputContainer.classList.remove('hidden');
      el.lab7OutputContent.innerHTML = `
        <h3>Published Workspace Artifact:</h3>
        <p><strong>Course:</strong> ${escapeHtml(state.course_id)} &bull; <strong>Status:</strong> ${escapeHtml(state.status)}</p>
        <pre class="code-block json-viewer">${escapeHtml(JSON.stringify(state.published_workspace || state, null, 2))}</pre>
      `;
    }
  }

  // =========================================================================
  // Lab 8: Parallel Swarm & Dynamic Fan-Out
  // =========================================================================
  const defaultWorkers = [
    { worker_id: 'worker-unit-1', name: 'Unit 1 Specialist: Foundations & ReAct', status: 'IDLE', summary: 'Not dispatched.' },
    { worker_id: 'worker-unit-2', name: 'Unit 2 Specialist: Tools, Memory & MCP', status: 'IDLE', summary: 'Not dispatched.' },
    { worker_id: 'worker-unit-3', name: 'Unit 3 Specialist: Multi-Agent & Swarms', status: 'IDLE', summary: 'Not dispatched.' },
    { worker_id: 'worker-unit-4', name: 'Unit 4 Specialist: Safety & Governance', status: 'IDLE', summary: 'Not dispatched.' }
  ];

  async function loadLab8Data() {
    renderLab8Workers(defaultWorkers);
  }

  function renderLab8Workers(workers) {
    if (!el.lab8WorkersGrid) return;
    el.lab8WorkersGrid.innerHTML = '';
    workers.forEach(w => {
      const isFailed = w.status === 'FAILED';
      const isDone = w.status === 'COMPLETED';
      const card = document.createElement('div');
      card.className = `swarm-worker-card ${isFailed ? 'failed' : ''}`;
      card.innerHTML = `
        <div class="worker-header">
          <span class="worker-title">${escapeHtml(w.name || w.worker_id)}</span>
          <span class="badge ${isDone ? 'badge-success' : (isFailed ? 'badge-danger' : 'badge-neutral')}">${escapeHtml(w.status)}</span>
        </div>
        <div class="worker-meta">Worker ID: ${escapeHtml(w.worker_id)} &bull; Duration: ${w.duration_ms != null ? w.duration_ms + ' ms' : 'Not dispatched'}</div>
        <p style="font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.4rem;">${escapeHtml(w.summary || 'No worker result is available.')}</p>
      `;
      el.lab8WorkersGrid.appendChild(card);
    });
  }

  async function handleLab8Dispatch() {
    const goal = el.lab8CourseGoalInput.value.trim() || 'Complete 26ECAC401 Agentic AI 14-Week Curriculum';
    const simulate_failure = el.lab8FailSimCheckbox.checked;

    setButtonLoading(el.btnLab8LaunchSwarm, el.spinnerLab8Run, true);
    hideAlert();

    try {
      const res = await apiCall('/api/lab8/dispatch', 'POST', {
        course_id: '26ECAC401',
        target_chapters: [1, 2, 3, 4],
        simulate_worker_failure: simulate_failure ? 3 : null,
      });

      el.lab8StatsContainer.classList.remove('hidden');
      el.lab8StatStatus.textContent = res.status || 'MERGED';
      el.lab8StatWorkers.textContent = `${res.total_workers || res.workers?.length || 4} Concurrent`;
      el.lab8StatParallelTime.textContent = `${(res.parallel_duration_ms || 0).toFixed(1)} ms`;
      el.lab8StatSeqTime.textContent = `${(res.sequential_estimated_ms || 0).toFixed(1)} ms`;
      el.lab8StatSpeedup.textContent = `${(res.speedup_ratio || 1).toFixed(2)}x Faster`;

      // Map backend worker records to UI format
      const workers = (res.workers || []).map(w => ({
        worker_id: w.worker_id,
        name: w.role || w.worker_id,
        status: w.status === 'SUCCESS' ? 'COMPLETED' : w.status,
        duration_ms: w.duration_ms,
        summary: w.output_data?.summary || (w.status === 'SUCCESS' ? `Chapter ${w.unit_chapter} compiled successfully.` : w.error || ''),
      }));
      renderLab8Workers(workers.length > 0 ? workers : defaultWorkers);

      el.lab8MergedContainer.classList.remove('hidden');
      el.lab8ResilienceBadge.textContent = simulate_failure ? 'Partial Recovery (Worker 3 Handled)' : 'Full 4-Unit Convergence';
      const mergedContent = res.merged_workspace
        ? JSON.stringify(res.merged_workspace, null, 2)
        : JSON.stringify(res, null, 2);
      el.lab8MergedContent.innerHTML = `<pre style="white-space: pre-wrap; font-family: var(--font-sans);">${escapeHtml(mergedContent)}</pre>`;
    } catch (err) {
      showAlert(`Swarm dispatch failed: ${err.message}`);
    } finally {
      setButtonLoading(el.btnLab8LaunchSwarm, el.spinnerLab8Run, false);
    }
  }

  // =========================================================================
  // GitHub Assignment Submissions & Faculty Review Portal
  // =========================================================================
  let submissionsState = {
    assignments: [],
    students: [],
    activeStudentId: '',
    activeRole: 'STUDENT', // 'STUDENT' or 'FACULTY'
    selectedAssignment: null,
  };

  async function loadSubmissionsData() {
    try {
      const [assignments, students] = await Promise.all([
        apiCall('/api/assignments'),
        apiCall('/api/students')
      ]);

      submissionsState.assignments = assignments || [];
      submissionsState.students = students || [];

      // The server returns only the account's own student profile to students.
      if (el.subStudentSelect && submissionsState.students.length > 0) {
        el.subStudentSelect.innerHTML = submissionsState.students.map(s => `
          <option value="${s.id}">${s.name} (${s.id}) &bull; ${s.email}</option>
        `).join('');
        submissionsState.activeStudentId = authenticatedUser?.student_id || submissionsState.students[0].id;
        el.subStudentSelect.value = submissionsState.activeStudentId;
        el.subStudentSelect.disabled = authenticatedUser?.role === 'STUDENT';
      }
      if (el.studentPortalSection) el.studentPortalSection.classList.toggle('hidden', authenticatedUser?.role !== 'STUDENT');
      if (el.facultyPortalSection) el.facultyPortalSection.classList.toggle('hidden', authenticatedUser?.role !== 'FACULTY');
      if (el.adminPortalSection) el.adminPortalSection.classList.toggle('hidden', authenticatedUser?.role !== 'ADMIN');
      if (el.portalRoleSwitcher) el.portalRoleSwitcher.classList.toggle('hidden', authenticatedUser?.role === 'ADMIN');
      if (el.btnPortalStudent) el.btnPortalStudent.classList.toggle('hidden', authenticatedUser?.role !== 'STUDENT');
      if (el.btnPortalFaculty) el.btnPortalFaculty.classList.toggle('hidden', authenticatedUser?.role !== 'FACULTY');

      if (authenticatedUser?.role === 'ADMIN' && el.adminAssignmentList) {
        el.adminAssignmentCount.textContent = String(submissionsState.assignments.length);
        const courses = [...new Set(submissionsState.assignments.map(a => a.course_id).filter(Boolean))];
        el.adminCourseLabel.textContent = courses.join(', ') || 'No configured course';
        el.adminAssignmentList.innerHTML = submissionsState.assignments.map(assignment => `
          <div class="admin-assignment-row">
            <strong class="admin-assignment-title">${escapeHtml(assignment.title)}</strong>
            <span class="admin-assignment-meta">
              <span class="admin-assignment-id">${escapeHtml(assignment.id)}</span>
              <span class="badge ${assignment.status === 'OPEN' ? 'badge-success' : 'badge-neutral'}">${escapeHtml(assignment.status)}</span>
              <span>${Number(assignment.max_points)} points</span>
              <button class="btn btn-secondary btn-sm admin-open-assignment" type="button" data-assignment-id="${escapeHtml(assignment.id)}">Open assignment</button>
            </span>
          </div>
        `).join('') || '<p class="empty-state-hint">No assignments are configured for this account.</p>';
        el.adminAssignmentList.querySelectorAll('.admin-open-assignment').forEach(button => {
          button.addEventListener('click', () => showAdminAssignmentDetails(button.dataset.assignmentId));
        });
      }

      // Populate assignment selector and faculty filter
      if (el.subAssignmentSelect && submissionsState.assignments.length > 0) {
        el.subAssignmentSelect.innerHTML = submissionsState.assignments.map(a => `
          <option value="${a.id}">${a.title} (Week ${a.due_week}) &bull; ${a.max_points} pts</option>
        `).join('');

        if (el.facultyAsgnFilter) {
          el.facultyAsgnFilter.innerHTML = '<option value="">All Assignments</option>' + submissionsState.assignments.map(a => `
            <option value="${a.id}">${a.title}</option>
          `).join('');
        }

        updateSelectedAssignmentDetails();
      }

      // Load history for active student
      if (authenticatedUser?.role === 'STUDENT') await loadStudentSubmissionsHistory();

      // If faculty portal active, load faculty submissions
      if (authenticatedUser?.role === 'FACULTY' && submissionsState.activeRole === 'FACULTY') {
        await loadFacultySubmissions();
      }
    } catch (err) {
      showAlert(`Failed to load assignment submissions data: ${err.message}`);
    }
  }

  function updateSelectedAssignmentDetails() {
    const asgnId = el.subAssignmentSelect?.value;
    const asgn = submissionsState.assignments.find(a => a.id === asgnId);
    submissionsState.selectedAssignment = asgn;
    if (!asgn) return;

    if (el.asgnDetailTitle) el.asgnDetailTitle.textContent = asgn.title;
    if (el.asgnDetailDesc) el.asgnDetailDesc.textContent = asgn.description || 'No description established.';
    if (el.asgnStatPoints) el.asgnStatPoints.textContent = `${asgn.max_points} pts`;
    if (el.asgnStatWeight) el.asgnStatWeight.textContent = `${asgn.weight_percentage}%`;
    if (el.asgnStatWeek) el.asgnStatWeek.textContent = `Week ${asgn.due_week}`;
    if (el.asgnStatStatus) {
      el.asgnStatStatus.textContent = asgn.status;
      el.asgnStatStatus.className = asgn.status === 'OPEN' ? 'stat-value text-success' : 'stat-value text-danger';
    }
    if (el.asgnDueDate) el.asgnDueDate.textContent = asgn.due_date ? formatIsoDate(asgn.due_date) : 'Unestablished (Open pacing)';
    if (el.asgnLatePolicy) el.asgnLatePolicy.textContent = asgn.late_policy || 'Unestablished';
    if (el.asgnSubmissionRules) el.asgnSubmissionRules.textContent = asgn.submission_rules || 'HTTPS GitHub repository link with solution code.';
  }

  function showAdminAssignmentDetails(assignmentId) {
    const assignment = submissionsState.assignments.find(item => item.id === assignmentId);
    if (!assignment || !el.adminAssignmentDetails) return;
    el.adminAssignmentDetailTitle.textContent = assignment.title;
    el.adminAssignmentDetailStatus.textContent = assignment.status;
    el.adminAssignmentDetailPoints.textContent = `${Number(assignment.max_points)} points`;
    el.adminAssignmentDetailDue.textContent = assignment.due_date
      ? formatIsoDate(assignment.due_date)
      : 'Not configured';
    el.adminAssignmentDetailDescription.textContent = assignment.description || 'No assignment description is recorded.';
    el.adminAssignmentDetailRules.textContent = `Submission requirements: ${assignment.submission_rules || 'No submission requirements are recorded.'}`;
    el.adminAssignmentDetails.classList.remove('hidden');
    el.adminAssignmentDetails.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function handleUrlInputValidation() {
    const val = el.subGithubUrlInput.value.trim();
    if (!val) {
      el.subUrlFeedback.textContent = '';
      el.subUrlFeedback.style.color = 'var(--text-secondary)';
      return;
    }

    const githubRegex = /^https:\/\/(?:www\.)?github\.com\/[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}\/[a-zA-Z0-9._-]+\/?$/;

    try {
      const parsed = new URL(val);
      if (parsed.protocol !== 'https:') {
        el.subUrlFeedback.textContent = '❌ Insecure HTTP scheme. Only secure HTTPS (https://) is accepted.';
        el.subUrlFeedback.style.color = 'var(--danger-text)';
        return;
      }
      if (parsed.hostname !== 'github.com' && parsed.hostname !== 'www.github.com') {
        el.subUrlFeedback.textContent = `❌ Domain '${parsed.hostname}' is not permitted. Only 'github.com' repository URLs are accepted.`;
        el.subUrlFeedback.style.color = 'var(--danger-text)';
        return;
      }
      if (parsed.username || parsed.password) {
        el.subUrlFeedback.textContent = '❌ URLs with embedded credentials are not permitted.';
        el.subUrlFeedback.style.color = 'var(--danger-text)';
        return;
      }
      if (githubRegex.test(val)) {
        el.subUrlFeedback.textContent = '✓ Valid GitHub repository URL format.';
        el.subUrlFeedback.style.color = '#34c759';
      } else {
        el.subUrlFeedback.textContent = '⚠️ Root repository required (format: https://github.com/<owner>/<repo>). No subpaths.';
        el.subUrlFeedback.style.color = 'var(--warning-text)';
      }
    } catch {
      el.subUrlFeedback.textContent = '⚠️ Invalid URL structure. Format: https://github.com/<owner>/<repo>';
      el.subUrlFeedback.style.color = 'var(--warning-text)';
    }
  }

  async function handleSubmitGithubAssignment() {
    const studentId = authenticatedUser?.student_id;
    const assignmentId = el.subAssignmentSelect?.value;
    const repoUrl = el.subGithubUrlInput?.value.trim();
    const notes = el.subNotesInput?.value.trim();

    if (!repoUrl) {
      showAlert('Please enter a valid GitHub repository URL.');
      el.subGithubUrlInput.focus();
      return;
    }

    setButtonLoading(el.btnSubmitGithub, el.spinnerSubmitGithub, true);
    try {
      const res = await apiCall('/api/submissions', 'POST', {
        assignment_id: assignmentId,
        student_id: studentId,
        repository_url: repoUrl,
        notes: notes || null
      });

      // Display Receipt Card
      if (el.subReceiptCard) {
        el.subReceiptCard.classList.remove('hidden');
        el.receiptStatusBadge.textContent = res.status;
        el.receiptStatusBadge.className = res.status === 'LATE' ? 'badge badge-warning' : 'badge badge-success';
        el.receiptAttemptPill.textContent = `Attempt #${res.attempt_number}`;
        el.receiptTitle.textContent = `Submission ${res.id} Confirmed`;
        el.receiptTimestamp.textContent = `Submitted: ${formatIsoDate(res.submission_timestamp)}`;
        
        el.receiptRepoLink.href = res.normalized_url;
        el.receiptRepoLink.textContent = res.normalized_url;

        let detailsHtml = `<div><strong>Validation:</strong> ${res.validation_status}</div>`;
        if (res.validation_details?.remote_check) {
          const rc = res.validation_details.remote_check;
          if (rc.reachable === true) {
            detailsHtml += `<div style="color: #34c759;">✓ Remote GitHub verified (Default branch: ${rc.default_branch || 'main'})</div>`;
          } else if (rc.note) {
            detailsHtml += `<div style="color: var(--warning-text);">ℹ ${rc.note}</div>`;
          }
        }
        if (res.status === 'LATE') {
          detailsHtml += `<div style="color: var(--danger-text); margin-top: 4px;">⚠️ Marked LATE against deadline: ${formatIsoDate(res.validation_details?.deadline)}</div>`;
        }
        el.receiptDetails.innerHTML = detailsHtml;
      }

      // Refresh student history
      await loadStudentSubmissionsHistory();
      showAlert('Assignment submitted successfully! Submission ID recorded in persistent database.');
    } catch (err) {
      showAlert(`Submission failed: ${err.message}`);
    } finally {
      setButtonLoading(el.btnSubmitGithub, el.spinnerSubmitGithub, false);
    }
  }

  async function loadStudentSubmissionsHistory() {
    const studentId = authenticatedUser?.student_id;
    if (!studentId || !el.studentHistoryTbody) return;

    try {
      const list = await apiCall(`/api/submissions/student/${encodeURIComponent(studentId)}`);

      if (!list || list.length === 0) {
        el.studentHistoryTbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align: center; padding: 1.5rem; color: var(--text-secondary);">
              No submissions recorded yet for this student. Submit a repository URL above!
            </td>
          </tr>
        `;
        return;
      }

      el.studentHistoryTbody.innerHTML = list.map(item => {
        const asgn = submissionsState.assignments.find(a => a.id === item.assignment_id);
        const asgnTitle = asgn ? asgn.title : item.assignment_id;
        const reviewStatus = displayReviewStatus(item);
        const statusBadgeClass = reviewStatus === 'PUBLISHED' ? 'badge-success' : (reviewStatus === 'LATE' ? 'badge-warning' : 'badge-neutral');
        const isPublished = reviewStatus === 'PUBLISHED' && Boolean(item.published_at);
        const scoreDisplay = isPublished && item.review_score !== null && item.review_score !== undefined ? `${item.review_score} / 100` : '<span style="color: var(--text-secondary);">Not published</span>';
        const feedbackDisplay = isPublished && item.review_feedback ? escapeHtml(item.review_feedback) : '<span style="color: var(--text-secondary);">Not published</span>';

        return `
          <tr style="border-bottom: 1px solid var(--border-card);">
            <td style="padding: 0.6rem; font-weight: 600;">#${item.attempt_number} ${item.is_latest ? '<span class="badge badge-accent" style="font-size: 0.7rem; padding: 2px 6px;">Latest</span>' : ''}</td>
            <td style="padding: 0.6rem;">${asgnTitle}</td>
            <td style="padding: 0.6rem; font-size: 0.82rem; color: var(--text-secondary);">${formatIsoDate(item.submission_timestamp)}</td>
            <td style="padding: 0.6rem;"><a href="${escapeHtml(item.normalized_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent); text-decoration: underline;">${escapeHtml(item.repo_owner)}/${escapeHtml(item.repo_name)}</a></td>
            <td style="padding: 0.6rem;"><span class="badge ${statusBadgeClass}">${reviewStatus}</span></td>
            <td style="padding: 0.6rem; font-weight: 600;">${scoreDisplay}</td>
            <td style="padding: 0.6rem; font-size: 0.85rem;">${feedbackDisplay}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      el.studentHistoryTbody.innerHTML = `<tr><td colspan="7" style="color: var(--danger-text); padding: 1rem;">Failed to load history: ${err.message}</td></tr>`;
    }
  }

  async function loadFacultySubmissions() {
    if (!el.facultySubmissionsTbody) return;
    const asgnFilter = el.facultyAsgnFilter?.value || '';
    const statusFilter = el.facultyStatusFilter?.value || 'ALL';

    let endpoint = '/api/submissions/faculty?only_latest=false';
    if (asgnFilter) endpoint += `&assignment_id=${encodeURIComponent(asgnFilter)}`;
    if (statusFilter && statusFilter !== 'ALL') endpoint += `&status=${encodeURIComponent(statusFilter)}`;

    try {
      const list = await apiCall(endpoint);

      if (!list || list.length === 0) {
        el.facultySubmissionsTbody.innerHTML = `
          <tr>
            <td colspan="9" style="text-align: center; padding: 1.5rem; color: var(--text-secondary);">
              No submissions match the current filter criteria.
            </td>
          </tr>
        `;
        return;
      }

      el.facultySubmissionsTbody.innerHTML = list.map(item => {
        const student = submissionsState.students.find(s => s.id === item.student_id);
        const studentDisplay = student ? `${student.name} (${student.id})` : item.student_id;
        const asgn = submissionsState.assignments.find(a => a.id === item.assignment_id);
        const asgnTitle = asgn ? asgn.title : item.assignment_id;
        const reviewStatus = displayReviewStatus(item);
        const statusBadgeClass = ['PUBLISHED', 'APPROVED'].includes(reviewStatus) ? 'badge-success' : (reviewStatus === 'LATE' ? 'badge-warning' : (['UNDER_REVIEW', 'DRAFT_GRADED'].includes(reviewStatus) ? 'badge-accent' : 'badge-neutral'));
        const scoreText = item.review_score !== null && item.review_score !== undefined
          ? `${reviewStatus === 'PUBLISHED' ? 'Published' : reviewStatus === 'APPROVED' ? 'Approved' : 'Draft'}: ${item.review_score}`
          : '--';

        return `
          <tr style="border-bottom: 1px solid var(--border-card);">
            <td style="padding: 0.6rem; font-family: var(--font-mono); font-size: 0.82rem;">${item.id}</td>
            <td style="padding: 0.6rem;">${escapeHtml(studentDisplay)}</td>
            <td style="padding: 0.6rem;">${escapeHtml(asgnTitle)}</td>
            <td style="padding: 0.6rem; text-align: center;">#${item.attempt_number}</td>
            <td style="padding: 0.6rem; font-size: 0.82rem; color: var(--text-secondary);">${formatIsoDate(item.submission_timestamp)}</td>
            <td style="padding: 0.6rem;"><span class="badge ${statusBadgeClass}">${reviewStatus}</span></td>
            <td style="padding: 0.6rem;"><a href="${escapeHtml(item.normalized_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--accent); text-decoration: underline;">GitHub &nearr;</a></td>
            <td style="padding: 0.6rem; font-weight: 600;">${scoreText}</td>
            <td style="padding: 0.6rem;">
              <button class="btn btn-secondary btn-sm btn-review-sub" data-sub-id="${item.id}">Review / Grade</button>
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      el.facultySubmissionsTbody.innerHTML = `<tr><td colspan="9" style="color: var(--danger-text); padding: 1rem;">Failed to load faculty submissions: ${err.message}</td></tr>`;
    }
  }

  function switchPortalRole(role) {
    if (authenticatedUser?.role === 'STUDENT' && role !== 'STUDENT') return;
    if (authenticatedUser?.role === 'ADMIN') return;
    if (authenticatedUser && authenticatedUser.role !== 'STUDENT' && role !== 'FACULTY') return;
    submissionsState.activeRole = role;
    if (role === 'STUDENT') {
      el.btnPortalStudent.className = 'btn btn-sm btn-primary';
      el.btnPortalFaculty.className = 'btn btn-sm btn-secondary';
      el.studentPortalSection.classList.remove('hidden');
      el.facultyPortalSection.classList.add('hidden');
      loadStudentSubmissionsHistory();
    } else {
      el.btnPortalStudent.className = 'btn btn-sm btn-secondary';
      el.btnPortalFaculty.className = 'btn btn-sm btn-primary';
      el.studentPortalSection.classList.add('hidden');
      el.facultyPortalSection.classList.remove('hidden');
      loadFacultySubmissions();
    }
  }

  async function openReviewModal(subId) {
    try {
      const record = await apiCall(`/api/submissions/detail/${encodeURIComponent(subId)}`);
      if (!record) return;

      const student = submissionsState.students.find(s => s.id === record.student_id);
      const asgn = submissionsState.assignments.find(a => a.id === record.assignment_id);

      el.modalReviewSubId.value = record.id;
      el.modalReviewStudent.textContent = student ? `${student.name} (${student.id})` : record.student_id;
      el.modalReviewAssignment.textContent = asgn ? asgn.title : record.assignment_id;
      el.modalReviewRepo.href = record.normalized_url;
      el.modalReviewRepo.textContent = record.normalized_url;
      el.modalReviewTimestamp.textContent = formatIsoDate(record.submission_timestamp);
      const currentStatus = displayReviewStatus(record);
      el.modalReviewStatus.value = ['UNDER_REVIEW', 'DRAFT_GRADED', 'RETURNED_FOR_REVISION'].includes(currentStatus)
        ? currentStatus
        : 'UNDER_REVIEW';
      el.modalReviewScore.value = record.review_score !== null && record.review_score !== undefined ? record.review_score : '';
      el.modalReviewFeedback.value = record.review_feedback || '';
      el.modalReviewStatus.disabled = ['APPROVED', 'PUBLISHED'].includes(currentStatus);
      el.modalReviewScore.disabled = currentStatus === 'PUBLISHED';
      el.modalReviewFeedback.disabled = currentStatus === 'PUBLISHED';
      el.modalReviewStateNote.textContent = `Persisted state: ${currentStatus}. Draft grades and feedback remain private until approved and published.`;
      el.btnSaveFacultyReview.disabled = ['APPROVED', 'PUBLISHED'].includes(currentStatus);
      el.btnApproveFacultyGrade.disabled = !['DRAFT_GRADED'].includes(currentStatus) || record.review_score === null || !record.review_feedback;
      el.btnPublishFacultyGrade.disabled = currentStatus !== 'APPROVED';

      el.facultyReviewModal.classList.remove('hidden');
      el.modalReviewScore.focus();
    } catch (err) {
      showAlert(`Cannot open review: ${err.message}`);
    }
  }

  async function handleSaveFacultyReview() {
    const subId = el.modalReviewSubId?.value;
    const review_status = el.modalReviewStatus?.value || 'UNDER_REVIEW';
    const rawScore = el.modalReviewScore?.value;
    const review_score = rawScore !== '' && !isNaN(parseFloat(rawScore)) ? parseFloat(rawScore) : null;
    const review_feedback = el.modalReviewFeedback?.value.trim() || null;

    if (review_score !== null && (review_score < 0 || review_score > 100)) {
      showAlert('Score must be between 0.0 and 100.0.');
      el.modalReviewScore.focus();
      return;
    }

    setButtonLoading(el.btnSaveFacultyReview, el.spinnerSaveReview, true);
    try {
      await apiCall(`/api/submissions/${encodeURIComponent(subId)}/review`, 'POST', {
        review_status,
        review_score,
        review_feedback
      });

      closeModal(el.facultyReviewModal, null);
      await loadFacultySubmissions();
      showAlert('Review draft saved. It is not visible to the student until approved and published.');
    } catch (err) {
      showAlert(`Failed to save review: ${err.message}`);
    } finally {
      setButtonLoading(el.btnSaveFacultyReview, el.spinnerSaveReview, false);
    }
  }

  async function handleApproveFacultyGrade() {
    const subId = el.modalReviewSubId?.value;
    if (!subId) return;
    try {
      await apiCall(`/api/submissions/${encodeURIComponent(subId)}/approve`, 'POST', {});
      closeModal(el.facultyReviewModal, null);
      await loadFacultySubmissions();
      showAlert('Grade approved. Publish it explicitly when ready.');
    } catch (err) {
      showAlert(`Failed to approve grade: ${err.message}`);
    }
  }

  async function handlePublishFacultyGrade() {
    const subId = el.modalReviewSubId?.value;
    if (!subId) return;
    try {
      await apiCall(`/api/submissions/${encodeURIComponent(subId)}/publish`, 'POST', {});
      closeModal(el.facultyReviewModal, null);
      await loadFacultySubmissions();
      showAlert('Approved grade and feedback published to the student.');
    } catch (err) {
      showAlert(`Failed to publish grade: ${err.message}`);
    }
  }

  function displayReviewStatus(item) {
    const reviewStatus = item.review_status || 'PENDING';
    if (reviewStatus === 'REVIEWED') return 'DRAFT_GRADED';
    if (reviewStatus === 'RESUBMISSION_REQUESTED') return 'RETURNED_FOR_REVISION';
    if (reviewStatus !== 'PENDING') return reviewStatus;
    return item.status === 'LATE' ? 'LATE' : 'SUBMITTED';
  }

  function formatIsoDate(isoStr) {
    if (!isoStr) return '--';
    try {
      const d = new Date(isoStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch {
      return isoStr;
    }
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // =========================================================================
  // Initial Setup & Event Listeners
  // =========================================================================

  async function init() {
    document.body.classList.add('auth-locked');
    el.authLoginScreen?.classList.remove('hidden');
    try {
      const sessionResponse = await fetch('/api/auth/me', { credentials: 'same-origin' });
      if (!sessionResponse.ok) {
        if (sessionResponse.status !== 401) throw new Error('Unable to verify your sign-in session.');
        return;
      }
      authenticatedUser = await sessionResponse.json();
      document.body.classList.remove('auth-locked');
      el.authLoginScreen?.classList.add('hidden');
      if (el.authUserLabel) {
        el.authUserLabel.textContent = `${authenticatedUser.display_name} · ${authenticatedUser.role}`;
      }
      const isStudent = authenticatedUser.role === 'STUDENT';
      const isAdmin = authenticatedUser.role === 'ADMIN';
      el.navTabs.faculty?.classList.toggle('hidden', isStudent);
      el.navTabs.lab12?.classList.toggle('hidden', !isAdmin);
      el.navTabs.history?.classList.toggle('hidden', !isAdmin);
      el.btnAuditDrawer?.classList.toggle('hidden', !isAdmin);
      if (el.btnPortalStudent) el.btnPortalStudent.classList.toggle('hidden', !isStudent);
      if (el.btnPortalFaculty) el.btnPortalFaculty.classList.toggle('hidden', isStudent);
      if (el.studentPortalSection) el.studentPortalSection.classList.toggle('hidden', !isStudent);
      if (el.facultyPortalSection) el.facultyPortalSection.classList.toggle('hidden', isStudent);
      submissionsState.activeRole = isStudent ? 'STUDENT' : 'FACULTY';

      const healthRes = await fetch('/api/health');
      if (healthRes.ok) {
        el.systemStatusText.textContent = 'Backend connected';
      } else {
        el.systemStatusText.textContent = 'Backend error';
      }
      const status = await apiCall('/api/system/status');
      el.systemStatusText.textContent = `${status.app_name} (v${status.version})`;

      const scenarios = await apiCall('/api/system/scenarios');
      state.scenarios = scenarios;
      renderLab1Scenarios(scenarios);
      await loadDashboard();
      await refreshUnreadCount();
      window.setInterval(refreshUnreadCount, 60000);
    } catch (err) {
      if (authenticatedUser) {
        document.body.classList.remove('auth-locked');
        el.authLoginScreen?.classList.add('hidden');
        el.systemStatusText.textContent = 'Backend Offline';
      } else if (el.authLoginError) {
        el.authLoginError.textContent = err.message;
      }
    }
  }

  function formatBytes(n) {
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / (1024 * 1024)).toFixed(1) + ' MB';
  }

  async function loadDashboard() {
    try {
      const health = await fetch('/api/health').then(r => r.json());
      const stats = await apiCall('/api/knowledge/stats');
      const h = document.getElementById('dash-health-status');
      const f = document.getElementById('dash-file-count');
      const c = document.getElementById('dash-chunk-count');
      const d = document.getElementById('dash-db-status');
      if (h) h.textContent = health.status || 'ok';
      if (f) f.textContent = String(stats.downloadable_files);
      if (c) c.textContent = String(stats.indexed_chunks);
      if (d) d.textContent = health.database_exists ? 'SQLite ready' : 'missing';
    } catch (err) {
      const h = document.getElementById('dash-health-status');
      if (h) h.textContent = 'unavailable';
    }
  }

  function updateUnreadBadge(count) {
    const badge = document.getElementById('notifications-unread-badge');
    const summary = document.getElementById('notifications-unread-summary');
    const unreadCount = Number(count) || 0;
    if (badge) {
      badge.textContent = unreadCount > 99 ? '99+' : String(unreadCount);
      badge.classList.toggle('hidden', unreadCount === 0);
      badge.setAttribute('aria-label', `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'}`);
    }
    if (summary) {
      summary.textContent = `${unreadCount} unread notification${unreadCount === 1 ? '' : 's'}`;
    }
  }

  function createInboxItem(item, { announcement = false } = {}) {
    const article = document.createElement('article');
    article.className = `inbox-item${item.is_read ? ' is-read' : ''}`;

    const heading = document.createElement('h3');
    heading.className = 'card-title';
    heading.textContent = item.title || 'Update';
    article.appendChild(heading);

    const message = document.createElement('p');
    message.className = 'inbox-message';
    message.textContent = announcement ? (item.content || '') : (item.message || '');
    article.appendChild(message);

    const metadata = document.createElement('p');
    metadata.className = 'inbox-metadata';
    metadata.textContent = announcement
      ? `${item.priority || 'NORMAL'} · ${item.posted_by || 'Course staff'} · ${item.created_at || ''}`
      : `${item.category || 'UPDATE'} · ${item.created_at || ''}`;
    article.appendChild(metadata);

    if (!announcement && item.link) {
      try {
        const safeUrl = new URL(item.link, window.location.origin);
        if (item.link.startsWith('/') && safeUrl.origin === window.location.origin) {
          const link = document.createElement('a');
          link.className = 'btn btn-ghost btn-sm inbox-link';
          link.href = safeUrl.href;
          link.textContent = 'Open';
          article.appendChild(link);
        }
      } catch {
        // Ignore malformed stored links; notification text remains available.
      }
    }

    if (!announcement && !item.is_read) {
      const button = document.createElement('button');
      button.className = 'btn btn-secondary btn-sm';
      button.type = 'button';
      button.textContent = 'Mark as read';
      button.addEventListener('click', async () => {
        button.disabled = true;
        try {
          await apiCall(`/api/notifications/${encodeURIComponent(item.id)}/read`, 'POST', {});
          await loadInbox();
        } catch (err) {
          button.disabled = false;
          const error = document.getElementById('notifications-error');
          if (error) {
            error.textContent = err.message || 'Could not mark notification as read.';
            error.classList.remove('hidden');
          }
        }
      });
      article.appendChild(button);
    }
    return article;
  }

  async function refreshUnreadCount() {
    if (!authenticatedUser) return;
    try {
      const result = await apiCall('/api/notifications/unread-count');
      updateUnreadBadge(result.count);
    } catch {
      // Keep the last known badge while the backend is unavailable.
    }
  }

  async function loadInbox() {
    const notificationsList = document.getElementById('notifications-list');
    const announcementsList = document.getElementById('announcements-list');
    const error = document.getElementById('notifications-error');
    if (error) error.classList.add('hidden');
    try {
      const [notifications, unread] = await Promise.all([
        apiCall('/api/notifications'),
        apiCall('/api/notifications/unread-count'),
      ]);
      updateUnreadBadge(unread.count);
      if (notificationsList) {
        notificationsList.replaceChildren();
        if (!notifications.length) {
          const empty = document.createElement('p');
          empty.className = 'empty-state-hint';
          empty.textContent = 'No notifications yet.';
          notificationsList.appendChild(empty);
        } else {
          notifications.forEach(item => notificationsList.appendChild(createInboxItem(item)));
        }
      }
      if (announcementsList) {
        announcementsList.replaceChildren();
        try {
          const announcements = await apiCall('/api/announcements');
          if (!announcements.length) {
            const empty = document.createElement('p');
            empty.className = 'empty-state-hint';
            empty.textContent = 'No course announcements are available.';
            announcementsList.appendChild(empty);
          } else {
            announcements.forEach(item => announcementsList.appendChild(createInboxItem(item, { announcement: true })));
          }
        } catch (err) {
          const empty = document.createElement('p');
          empty.className = 'empty-state-hint';
          empty.textContent = `Announcements unavailable: ${err.message || 'course access is not authorized.'}`;
          announcementsList.appendChild(empty);
        }
      }
    } catch (err) {
      if (error) {
        error.textContent = err.message || 'Could not load your inbox.';
        error.classList.remove('hidden');
      }
    }
  }

  async function loadKnowledgeFiles() {
    const tbody = document.getElementById('knowledge-files-tbody');
    const countLabel = document.getElementById('knowledge-count-label');
    const empty = document.getElementById('knowledge-empty');
    const errBox = document.getElementById('knowledge-error');
    const q = (document.getElementById('knowledge-search-input') || {}).value || '';
    if (errBox) errBox.classList.add('hidden');
    try {
      const url = q ? `/api/knowledge/files?q=${encodeURIComponent(q)}` : '/api/knowledge/files';
      const data = await apiCall(url);
      const files = data.files || [];
      if (countLabel) countLabel.textContent = `${files.length} file(s) under knowledge/`;
      if (empty) empty.classList.toggle('hidden', files.length > 0);
      if (!tbody) return;
      tbody.innerHTML = files.map((file) => `
        <tr>
          <td>${escapeHtml(file.chapter ? ('Chapter ' + file.chapter) : file.folder)}</td>
          <td>${escapeHtml(file.filename)}</td>
          <td class="font-mono">${escapeHtml(file.relative_path)}</td>
          <td>${escapeHtml(file.format)}</td>
          <td>${formatBytes(file.size_bytes)}</td>
          <td>${escapeHtml((file.last_modified || '').slice(0, 19))}</td>
          <td>${file.indexed ? 'indexed' : 'download only'}</td>
          <td><button class="btn btn-secondary btn-sm btn-download-note" data-file-id="${file.file_id}" data-filename="${escapeHtml(file.filename)}">Download</button></td>
        </tr>
      `).join('');
    } catch (err) {
      if (errBox) {
        errBox.textContent = err.message || 'Could not list knowledge files.';
        errBox.classList.remove('hidden');
      }
    }
  }

  function showCourseMaterialsError(message) {
    const box = document.getElementById('cm-library-error');
    if (!box) return;
    box.textContent = message;
    box.classList.remove('hidden');
  }

  async function courseMaterialsRequest(url, method = 'GET', body = null, multipart = false) {
    const options = {
      method,
      credentials: 'same-origin',
      headers: { ...csrfRequestHeaders() },
    };
    if (body && multipart) {
      options.body = body;
    } else if (body) {
      options.headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.success === false) {
      throw new Error(payload.detail || payload.error?.message || `Request failed (${response.status}).`);
    }
    return payload.data;
  }

  function flattenMaterialFolders(nodes, parentId = null, depth = 0, prefix = '') {
    const result = [];
    (nodes || []).forEach((folder) => {
      const path = prefix ? `${prefix} / ${folder.name}` : folder.name;
      result.push({ ...folder, parent_id: parentId, depth, path });
      result.push(...flattenMaterialFolders(folder.children, folder.folder_id, depth + 1, path));
    });
    return result;
  }

  function activeMaterialCategory() {
    return courseMaterialsState.categories.find(item => item.category_id === courseMaterialsState.activeCategoryId);
  }

  async function loadCourseMaterials() {
    const errorBox = document.getElementById('cm-library-error');
    const loading = document.getElementById('cm-library-loading');
    if (errorBox) errorBox.classList.add('hidden');
    if (loading) loading.classList.remove('hidden');
    try {
      courseMaterialsState.categories = await courseMaterialsRequest('/api/course-materials/categories');
      if (!courseMaterialsState.activeCategoryId ||
          !courseMaterialsState.categories.some(item => item.category_id === courseMaterialsState.activeCategoryId)) {
        courseMaterialsState.activeCategoryId = courseMaterialsState.categories[0]?.category_id || null;
      }
      const categoryGrid = document.getElementById('cm-category-grid');
      if (categoryGrid) {
        categoryGrid.innerHTML = courseMaterialsState.categories.map(category => `
          <button type="button" class="cm-category-card ${category.category_id === courseMaterialsState.activeCategoryId ? 'is-active' : ''}"
                  data-cm-category="${escapeHtml(category.category_id)}">
            <strong>${escapeHtml(category.name)}</strong>
            <span>${Number(category.material_count) || 0} material(s)</span>
          </button>
        `).join('');
      }
      const uploadPanel = document.getElementById('cm-upload-panel');
      const createFolderForm = document.getElementById('cm-create-folder-form');
      const canManage = authenticatedUser?.role === 'FACULTY';
      if (uploadPanel) uploadPanel.classList.toggle('hidden', !canManage);
      if (createFolderForm) createFolderForm.classList.toggle('hidden', !canManage);
      const uploadCategory = document.getElementById('cm-upload-category');
      if (uploadCategory) {
        uploadCategory.innerHTML = courseMaterialsState.categories.map(category =>
          `<option value="${escapeHtml(category.category_id)}">${escapeHtml(category.name)}</option>`
        ).join('');
        uploadCategory.value = courseMaterialsState.activeCategoryId || '';
      }
      if (courseMaterialsState.activeCategoryId) await loadCourseMaterialCategory();
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not load the course material library.');
    } finally {
      if (loading) loading.classList.add('hidden');
    }
  }

  async function loadCourseMaterialCategory() {
    const categoryId = courseMaterialsState.activeCategoryId;
    if (!categoryId) return;
    const query = new URLSearchParams({ category_id: categoryId });
    const tree = await courseMaterialsRequest(`/api/course-materials/folders?${query}`);
    courseMaterialsState.folders = tree.folders || [];
    const allFolders = flattenMaterialFolders(courseMaterialsState.folders);
    if (courseMaterialsState.activeFolderId &&
        !allFolders.some(folder => folder.folder_id === courseMaterialsState.activeFolderId)) {
      courseMaterialsState.activeFolderId = null;
    }
    const title = document.getElementById('cm-current-category');
    if (title) title.textContent = tree.category_name;
    renderCourseMaterialFolders(allFolders);
    await loadCourseMaterialItems();
  }

  function renderCourseMaterialFolders(allFolders) {
    const treeBox = document.getElementById('cm-folder-tree');
    const breadcrumbs = document.getElementById('cm-breadcrumbs');
    const folderManagement = document.getElementById('cm-folder-management');
    const uploadFolder = document.getElementById('cm-upload-folder');
    const moveTarget = document.getElementById('cm-folder-move-target');
    const categoryId = courseMaterialsState.activeCategoryId;
    if (treeBox) {
      const draw = (nodes, depth = 0) => (nodes || []).map(folder => `
        <div class="cm-folder-node" style="--folder-depth:${depth}">
          <button type="button" class="cm-folder-open ${folder.folder_id === courseMaterialsState.activeFolderId ? 'is-active' : ''}"
                  data-cm-folder-open="${escapeHtml(folder.folder_id)}">
            ${escapeHtml(folder.name)} <span class="cm-material-meta">(${Number(folder.material_count) || 0})</span>
          </button>
          ${authenticatedUser?.role === 'FACULTY' ? `
            <button type="button" class="cm-folder-action" data-cm-folder-rename="${escapeHtml(folder.folder_id)}" aria-label="Rename ${escapeHtml(folder.name)}">Rename</button>
            <button type="button" class="cm-folder-action" data-cm-folder-select="${escapeHtml(folder.folder_id)}">Select</button>
            <button type="button" class="cm-folder-action" data-cm-folder-delete="${escapeHtml(folder.folder_id)}" aria-label="Delete ${escapeHtml(folder.name)}">Delete</button>
          ` : ''}
        </div>${draw(folder.children, depth + 1)}
      `).join('');
      treeBox.innerHTML = `<button type="button" class="cm-folder-open ${courseMaterialsState.activeFolderId ? '' : 'is-active'}" data-cm-folder-open="">All ${escapeHtml(activeMaterialCategory()?.name || 'materials')}</button>${draw(courseMaterialsState.folders)}`;
    }
    if (folderManagement) {
      folderManagement.classList.toggle('hidden', authenticatedUser?.role !== 'FACULTY' || !courseMaterialsState.selectedFolderId);
    }
    const options = `<option value="">Category root</option>${allFolders.map(folder =>
      `<option value="${escapeHtml(folder.folder_id)}">${'&nbsp;'.repeat(folder.depth * 2)}${escapeHtml(folder.path)}</option>`
    ).join('')}`;
    if (uploadFolder) {
      uploadFolder.innerHTML = options;
      uploadFolder.value = courseMaterialsState.activeFolderId || '';
    }
    if (moveTarget) {
      moveTarget.innerHTML = options;
      moveTarget.value = '';
    }
    if (breadcrumbs) {
      const current = allFolders.find(folder => folder.folder_id === courseMaterialsState.activeFolderId);
      const crumbs = current
        ? current.path.split(' / ').reduce((list, name) => {
          list.push({ name, path: list.length ? `${list[list.length - 1].path} / ${name}` : name });
          return list;
        }, [])
        : [];
      breadcrumbs.innerHTML = `<button type="button" class="btn btn-secondary btn-sm" data-cm-crumb="">${escapeHtml(activeMaterialCategory()?.name || 'Category root')}</button>` +
        crumbs.map(crumb => `<button type="button" class="btn btn-secondary btn-sm" data-cm-crumb="${escapeHtml(crumb.path)}">${escapeHtml(crumb.name)}</button>`).join('');
    }
  }

  async function loadCourseMaterialItems() {
    const category = activeMaterialCategory();
    const container = document.getElementById('cm-materials-list');
    const countLabel = document.getElementById('cm-results-count');
    if (!category || !container) return;
    container.innerHTML = '<div class="empty-state-hint">Loading course materials…</div>';
    const params = new URLSearchParams({
      category_id: category.category_id,
      root_only: courseMaterialsState.activeFolderId ? 'false' : 'true',
      recursive: 'false',
    });
    if (courseMaterialsState.activeFolderId) params.set('folder_id', courseMaterialsState.activeFolderId);
    const query = (document.getElementById('cm-search') || {}).value?.trim();
    const chapter = (document.getElementById('cm-chapter-filter') || {}).value;
    const lab = (document.getElementById('cm-lab-filter') || {}).value;
    const fileType = (document.getElementById('cm-type-filter') || {}).value;
    if (query) params.set('query', query);
    if (chapter) params.set('chapter', chapter);
    if (lab) params.set('lab', lab);
    if (fileType) params.set('file_type', fileType);
    let result;
    try {
      result = await courseMaterialsRequest(`/api/course-materials/materials?${params}`);
    } catch (err) {
      container.innerHTML = '<div class="empty-state-hint">Could not load this folder. Use Refresh to try again.</div>';
      throw err;
    }
    if (countLabel) countLabel.textContent = `${result.count} material(s) in this folder`;
    const items = result.items || [];
    if (!items.length) {
      container.innerHTML = '<div class="empty-state-hint">No uploaded materials match this location and filter.</div>';
      return;
    }
    const canManage = authenticatedUser?.role === 'FACULTY';
    const allFolders = flattenMaterialFolders(courseMaterialsState.folders);
    const folderOptions = `<option value="">Category root</option>${allFolders.map(folder =>
      `<option value="${escapeHtml(folder.folder_id)}">${escapeHtml(folder.path)}</option>`
    ).join('')}`;
    container.innerHTML = items.map(material => `
      <article class="cm-material-card">
        <span class="cm-file-badge">${escapeHtml(material.extension)}</span>
        <h4>${escapeHtml(material.title)}</h4>
        <p>${escapeHtml(material.description || 'No description provided.')}</p>
        <div class="cm-material-meta">
          ${escapeHtml(material.folder_path || category.name)} · ${formatBytes(material.size_bytes)} ·
          Uploaded ${escapeHtml((material.uploaded_at || '').slice(0, 10))}
          ${material.uploader_name ? `by ${escapeHtml(material.uploader_name)}` : ''}
          ${material.chapter ? ` · Chapter ${Number(material.chapter)}` : ''}
          ${material.lab ? ` · Lab ${Number(material.lab)}` : ''}
        </div>
        <div class="cm-material-actions">
          <button type="button" class="btn btn-secondary btn-sm" data-cm-preview="${escapeHtml(material.material_id)}">Preview</button>
          <button type="button" class="btn btn-secondary btn-sm" data-cm-download="${escapeHtml(material.material_id)}">Download</button>
          ${canManage ? `
            <button type="button" class="btn btn-secondary btn-sm" data-cm-edit="${escapeHtml(material.material_id)}">Edit details</button>
            <label class="form-group cm-move-select">
              <span class="sr-only">Move ${escapeHtml(material.title)} to folder</span>
              <select class="form-input" data-cm-move-target="${escapeHtml(material.material_id)}">${folderOptions}</select>
            </label>
            <button type="button" class="btn btn-secondary btn-sm" data-cm-move="${escapeHtml(material.material_id)}">Move</button>
            <button type="button" class="btn btn-secondary btn-sm" data-cm-replace="${escapeHtml(material.material_id)}">Replace file</button>
            <button type="button" class="btn btn-danger btn-sm" data-cm-delete="${escapeHtml(material.material_id)}">Delete</button>
          ` : ''}
        </div>
      </article>
    `).join('');
  }

  async function previewCourseMaterial(materialId) {
    const preview = document.getElementById('cm-material-preview');
    const body = document.getElementById('cm-preview-body');
    const title = document.getElementById('cm-preview-title');
    try {
      const [material, data] = await Promise.all([
        courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}`),
        courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}/preview`),
      ]);
      if (title) title.textContent = material.title;
      if (!body) return;
      if (data.kind === 'text') {
        const pre = document.createElement('pre');
        pre.className = 'cm-preview-text';
        pre.textContent = data.text;
        body.replaceChildren(pre);
      } else if (data.kind === 'inline') {
        const element = document.createElement(material.extension === 'pdf' ? 'iframe' : 'img');
        element.className = material.extension === 'pdf' ? 'cm-preview-frame' : 'cm-preview-image';
        element.src = data.url;
        element.setAttribute('title', `Preview of ${material.title}`);
        body.replaceChildren(element);
      } else {
        const message = document.createElement('p');
        message.textContent = data.text;
        const download = document.createElement('button');
        download.type = 'button';
        download.className = 'btn btn-secondary';
        download.textContent = 'Download original';
        download.addEventListener('click', () => downloadCourseMaterial(materialId, material.original_filename));
        body.replaceChildren(message, download);
      }
      preview?.classList.remove('hidden');
      preview?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not preview this course material.');
    }
  }

  async function downloadCourseMaterial(materialId, filename) {
    try {
      const response = await fetch(`/api/course-materials/materials/${encodeURIComponent(materialId)}/content?download=true`, {
        credentials: 'same-origin',
      });
      if (!response.ok) throw new Error(`Download failed (${response.status}).`);
      const url = URL.createObjectURL(await response.blob());
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename || 'course-material';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not download this course material.');
    }
  }

  async function chooseReplacement(materialId) {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.pdf,.docx,.pptx,.xlsx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp';
    input.addEventListener('change', async () => {
      if (!input.files?.[0]) return;
      const form = new FormData();
      form.append('file', input.files[0]);
      try {
        await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}/file`, 'PUT', form, true);
        await loadCourseMaterials();
        window.alert('Course material file replaced.');
      } catch (err) {
        showCourseMaterialsError(err.message || 'Could not replace the course material.');
      }
    }, { once: true });
    input.click();
  }

  async function handleCourseMaterialAction(event) {
    const target = event.target.closest('[data-cm-category], [data-cm-folder-open], [data-cm-folder-rename], [data-cm-folder-select], [data-cm-folder-delete], [data-cm-crumb], [data-cm-preview], [data-cm-download], [data-cm-edit], [data-cm-move], [data-cm-replace], [data-cm-delete]');
    if (!target) return;
    try {
      if (target.hasAttribute('data-cm-category')) {
        courseMaterialsState.activeCategoryId = target.getAttribute('data-cm-category');
        courseMaterialsState.activeFolderId = null;
        courseMaterialsState.selectedFolderId = null;
        await loadCourseMaterialCategory();
        await loadCourseMaterials();
      } else if (target.hasAttribute('data-cm-folder-open')) {
        courseMaterialsState.activeFolderId = target.getAttribute('data-cm-folder-open') || null;
        courseMaterialsState.selectedFolderId = target.getAttribute('data-cm-folder-open') || null;
        renderCourseMaterialFolders(flattenMaterialFolders(courseMaterialsState.folders));
        await loadCourseMaterialItems();
      } else if (target.hasAttribute('data-cm-folder-select')) {
        courseMaterialsState.selectedFolderId = target.getAttribute('data-cm-folder-select');
        document.getElementById('cm-folder-management')?.classList.remove('hidden');
      } else if (target.hasAttribute('data-cm-crumb')) {
        const path = target.getAttribute('data-cm-crumb');
        const folder = flattenMaterialFolders(courseMaterialsState.folders).find(item => item.path === path);
        courseMaterialsState.activeFolderId = folder?.folder_id || null;
        await loadCourseMaterialCategory();
      } else if (target.hasAttribute('data-cm-folder-rename')) {
        const folderId = target.getAttribute('data-cm-folder-rename');
        const folder = flattenMaterialFolders(courseMaterialsState.folders).find(item => item.folder_id === folderId);
        const name = window.prompt('New folder name', folder?.name || '');
        if (name === null) return;
        await courseMaterialsRequest(`/api/course-materials/folders/${encodeURIComponent(folderId)}`, 'PATCH', { name });
        await loadCourseMaterialCategory();
      } else if (target.hasAttribute('data-cm-folder-delete')) {
        const folderId = target.getAttribute('data-cm-folder-delete');
        if (!window.confirm('Delete this empty folder?')) return;
        await courseMaterialsRequest(`/api/course-materials/folders/${encodeURIComponent(folderId)}`, 'DELETE');
        courseMaterialsState.selectedFolderId = null;
        await loadCourseMaterialCategory();
      } else if (target.hasAttribute('data-cm-preview')) {
        await previewCourseMaterial(target.getAttribute('data-cm-preview'));
      } else if (target.hasAttribute('data-cm-download')) {
        const material = await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(target.getAttribute('data-cm-download'))}`);
        await downloadCourseMaterial(material.material_id, material.original_filename);
      } else if (target.hasAttribute('data-cm-edit')) {
        const materialId = target.getAttribute('data-cm-edit');
        const material = await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}`);
        const title = window.prompt('Material title', material.title);
        if (title === null) return;
        const description = window.prompt('Description', material.description || '');
        if (description === null) return;
        await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}`, 'PATCH', { title, description });
        await loadCourseMaterialCategory();
      } else if (target.hasAttribute('data-cm-move')) {
        const materialId = target.getAttribute('data-cm-move');
        const select = document.querySelector(`[data-cm-move-target="${CSS.escape(materialId)}"]`);
        await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}`, 'PATCH', { folder_id: select?.value || null });
        await loadCourseMaterialCategory();
      } else if (target.hasAttribute('data-cm-replace')) {
        chooseReplacement(target.getAttribute('data-cm-replace'));
      } else if (target.hasAttribute('data-cm-delete')) {
        const materialId = target.getAttribute('data-cm-delete');
        if (!window.confirm('Delete this material and its stored file?')) return;
        await courseMaterialsRequest(`/api/course-materials/materials/${encodeURIComponent(materialId)}`, 'DELETE');
        document.getElementById('cm-material-preview')?.classList.add('hidden');
        await loadCourseMaterialCategory();
      }
    } catch (err) {
      showCourseMaterialsError(err.message || 'The course material action could not be completed.');
    }
  }

  async function downloadKnowledgeFile(fileId, filename) {
    try {
      const response = await fetch(`/api/knowledge/files/${encodeURIComponent(fileId)}/download`);
      if (!response.ok) {
        let msg = `Download failed (${response.status})`;
        try {
          const body = await response.json();
          msg = body.detail || body.error?.message || msg;
        } catch (_e) { /* not JSON */ }
        throw new Error(msg);
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'note';
      document.body.appendChild(a);
      a.click();
      a.remove();
      // Let the browser begin consuming the Blob before releasing its object URL.
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      showAlert(`Download started: ${filename || 'note'}`);
    } catch (err) {
      showAlert(err.message || 'Download failed');
    }
  }

  async function searchIndexedKnowledge() {
    const input = document.getElementById('knowledge-query-input');
    const box = document.getElementById('knowledge-search-results');
    const query = (input && input.value || '').trim();
    if (!query) {
      showAlert('Enter a question to search indexed notes.');
      return;
    }
    try {
      const data = await apiCall('/api/knowledge/search', 'POST', { query, course_id: '26ECAC401', top_k: 5 });
      if (!box) return;
      if (!data.match_count) {
        box.innerHTML = `<div class="empty-state-hint">${escapeHtml(data.notice || 'The available sources do not establish the answer.')}</div>`;
        return;
      }
      box.innerHTML = data.matches.map((m) => `
        <div class="card" style="margin-bottom:0.6rem;">
          <strong>${escapeHtml(m.topic)}</strong>
          <div class="card-subtitle">${escapeHtml(m.source)} — ${escapeHtml(m.source_document)}</div>
          <p>${escapeHtml((m.matched_text || '').slice(0, 500))}</p>
        </div>
      `).join('');
    } catch (err) {
      showAlert(err.message || 'Search failed');
    }
  }

  async function loadHistory() {
    const list = document.getElementById('history-list');
    try {
      const logs = await apiCall('/api/system/audit');
      if (!list) return;
      if (!logs || !logs.length) {
        list.innerHTML = '<div class="empty-state-hint">No coordinator events yet. Run a lab to create history.</div>';
        return;
      }
      list.innerHTML = logs.slice().reverse().slice(0, 50).map((row) => `
        <div class="audit-item">
          <strong>${escapeHtml(row.lab_id || row.event_type || 'event')}</strong>
          <div>${escapeHtml(row.payload_summary || row.action || JSON.stringify(row))}</div>
        </div>
      `).join('');
    } catch (err) {
      if (list) list.innerHTML = `<div class="empty-state-hint">${escapeHtml(err.message)}</div>`;
    }
  }

  function renderLab1Scenarios(scenarios) {
    if (!el.scenariosChips || !scenarios || scenarios.length === 0) return;
    el.scenariosChips.innerHTML = '';
    scenarios.forEach(sc => {
      const btn = document.createElement('button');
      btn.className = 'chip-btn';
      btn.setAttribute('data-scenario', sc.scenario_id);
      btn.textContent = sc.title.replace('Agentic AI Course Curriculum: ', '').replace('Autonomous Multi-Agent System ', '');
      btn.title = sc.description;
      el.scenariosChips.appendChild(btn);
    });
  }

  // Event Listeners
  el.btnAnalyzeRequest.addEventListener('click', handleAnalyzeRequest);
  el.btnBackToRequest.addEventListener('click', () => {
    setStep(1);
    showScreen(el.screenRequest);
    el.promptInput.focus();
  });
  el.btnGeneratePlan.addEventListener('click', handleGeneratePlan);
  el.btnSubmitRevision.addEventListener('click', handleRevision);
  el.btnCloseAlert.addEventListener('click', hideAlert);
  el.btnReset.addEventListener('click', resetSession);
  
  // Audit Drawer Open / Close
  el.btnAuditDrawer.addEventListener('click', openAuditDrawer);
  el.btnCloseDrawer.addEventListener('click', () => closeModal(el.auditDrawer, el.btnAuditDrawer));

  // Lab Navigation Switching
  for (let i = 1; i <= 14; i++) {
    const labId = `lab${i}`;
    const btn = el.navTabs[labId];
    if (btn) {
      btn.addEventListener('click', () => switchLab(labId));
    }
  }

  // Lab 2 Actions
  el.btnLab2RunQuery.addEventListener('click', handleLab2Query);
  el.lab2CourseSelect?.addEventListener('change', loadLab2Assignments);
  el.btnLab2ViewTools.addEventListener('click', openLab2ToolsModal);
  el.btnCloseToolsModal.addEventListener('click', () => closeModal(el.lab2ToolsModal, el.btnLab2ViewTools));
  el.btnLab2OpenSandbox.addEventListener('click', openLab2Sandbox);
  el.btnCloseSandboxModal.addEventListener('click', () => closeModal(el.lab2SandboxModal, el.btnLab2OpenSandbox));
  el.btnRunSandbox.addEventListener('click', handleRunSandbox);

  // Lab 3 Actions
  if (el.btnLab3RunAgent) el.btnLab3RunAgent.addEventListener('click', handleLab3Agent);
  if (el.btnLab3RunSandbox) el.btnLab3RunSandbox.addEventListener('click', handleLab3Sandbox);
  if (el.btnLab3RefreshSkills) el.btnLab3RefreshSkills.addEventListener('click', loadLab3Data);

  // Lab 4 Actions
  if (el.btnLab4RunAgent) el.btnLab4RunAgent.addEventListener('click', handleLab4Agent);
  if (el.btnLab4NewSession) el.btnLab4NewSession.addEventListener('click', handleLab4NewSession);
  if (el.btnLab4AddTurn) el.btnLab4AddTurn.addEventListener('click', handleLab4AddTurn);
  if (el.btnLab4SetScratch) el.btnLab4SetScratch.addEventListener('click', handleLab4SetScratch);
  if (el.btnLab4RefreshSession) el.btnLab4RefreshSession.addEventListener('click', refreshLab4Session);
  if (el.btnLab4SearchRag) el.btnLab4SearchRag.addEventListener('click', handleLab4SearchRag);

  // Lab 5 Actions
  if (el.btnLab5Dispatch) el.btnLab5Dispatch.addEventListener('click', handleLab5Dispatch);
  if (el.btnLab5RefreshAudit) el.btnLab5RefreshAudit.addEventListener('click', refreshLab5Audit);

  // Lab 6 Actions
  if (el.btnLab6StartRun) el.btnLab6StartRun.addEventListener('click', handleLab6Start);
  if (el.btnLab6Step) el.btnLab6Step.addEventListener('click', handleLab6Step);
  if (el.btnLab6Crash) el.btnLab6Crash.addEventListener('click', handleLab6Crash);
  if (el.btnLab6Resume) el.btnLab6Resume.addEventListener('click', handleLab6Resume);
  if (el.btnLab6Approve) el.btnLab6Approve.addEventListener('click', () => handleLab6Decision(true));
  if (el.btnLab6Reject) el.btnLab6Reject.addEventListener('click', () => handleLab6Decision(false));

  // Lab 7 Actions
  if (el.btnLab7RunAll) el.btnLab7RunAll.addEventListener('click', () => handleLab7Run(false));
  if (el.btnLab7StepGraph) el.btnLab7StepGraph.addEventListener('click', () => handleLab7Run(true));
  if (el.btnLab7Approve) el.btnLab7Approve.addEventListener('click', () => handleLab7Approve(true));
  if (el.btnLab7Reject) el.btnLab7Reject.addEventListener('click', () => handleLab7Approve(false));

  // Lab 8 Actions
  if (el.btnLab8LaunchSwarm) el.btnLab8LaunchSwarm.addEventListener('click', handleLab8Dispatch);

  // Keyboard Escape Handler (Micro-Interaction)
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (el.lab2ToolsModal && !el.lab2ToolsModal.classList.contains('hidden')) {
        closeModal(el.lab2ToolsModal, el.btnLab2ViewTools);
      } else if (el.lab2SandboxModal && !el.lab2SandboxModal.classList.contains('hidden')) {
        closeModal(el.lab2SandboxModal, el.btnLab2OpenSandbox);
      } else if (el.auditDrawer && !el.auditDrawer.classList.contains('hidden')) {
        closeModal(el.auditDrawer, el.btnAuditDrawer);
      } else if (el.globalAlert && !el.globalAlert.classList.contains('hidden')) {
        hideAlert();
      }
    }
  });

  // Backdrop Click to Close Modals / Drawer (Micro-Interaction)
  [el.lab2ToolsModal, el.lab2SandboxModal, el.auditDrawer, el.facultyReviewModal].forEach(overlay => {
    if (overlay) {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
          if (overlay === el.lab2ToolsModal) closeModal(el.lab2ToolsModal, el.btnLab2ViewTools);
          if (overlay === el.lab2SandboxModal) closeModal(el.lab2SandboxModal, el.btnLab2OpenSandbox);
          if (overlay === el.auditDrawer) closeModal(el.auditDrawer, el.btnAuditDrawer);
          if (overlay === el.facultyReviewModal) closeModal(el.facultyReviewModal, null);
        }
      });
    }
  });

  // Tab buttons
  document.querySelectorAll('.plan-tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.getAttribute('data-tab');
      switchPlanTab(tabId);
    });
  });

  // Scenario chips (Lab 1)
  el.scenariosChips.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip-btn');
    if (!chip) return;
    const scenarioId = chip.getAttribute('data-scenario');
    const matched = state.scenarios.find(s => s.scenario_id === scenarioId);
    if (matched) {
      el.promptInput.value = matched.raw_prompt;
      state.courseCodeHint = matched.course_name.split(':')[0] || '26ECAC401';
      el.promptInput.focus();
    }
  });

  // Revision chips
  document.querySelectorAll('.chip-rev').forEach(btn => {
    btn.addEventListener('click', () => {
      const promptText = btn.getAttribute('data-prompt');
      if (promptText) {
        el.revisionPromptInput.value = promptText;
        el.revisionPromptInput.focus();
      }
    });
  });

  // Submissions Event Listeners
  if (el.navTabs.submissions) {
    el.navTabs.submissions.addEventListener('click', () => switchLab('submissions'));
  }
  if (el.btnPortalStudent) {
    el.btnPortalStudent.addEventListener('click', () => switchPortalRole('STUDENT'));
  }
  if (el.btnPortalFaculty) {
    el.btnPortalFaculty.addEventListener('click', () => switchPortalRole('FACULTY'));
  }
  if (el.btnAdminCloseAssignmentDetails) {
    el.btnAdminCloseAssignmentDetails.addEventListener('click', () => {
      el.adminAssignmentDetails?.classList.add('hidden');
    });
  }
  if (el.subAssignmentSelect) {
    el.subAssignmentSelect.addEventListener('change', updateSelectedAssignmentDetails);
  }
  if (el.subStudentSelect) {
    el.subStudentSelect.addEventListener('change', () => {
      submissionsState.activeStudentId = el.subStudentSelect.value;
      loadStudentSubmissionsHistory();
    });
  }
  if (el.subGithubUrlInput) {
    el.subGithubUrlInput.addEventListener('input', handleUrlInputValidation);
  }
  if (el.btnSubmitGithub) {
    el.btnSubmitGithub.addEventListener('click', handleSubmitGithubAssignment);
  }
  if (el.btnRefreshStudentHistory) {
    el.btnRefreshStudentHistory.addEventListener('click', loadStudentSubmissionsHistory);
  }
  if (el.facultyAsgnFilter) {
    el.facultyAsgnFilter.addEventListener('change', loadFacultySubmissions);
  }
  if (el.facultyStatusFilter) {
    el.facultyStatusFilter.addEventListener('change', loadFacultySubmissions);
  }
  if (el.btnRefreshFacultySubs) {
    el.btnRefreshFacultySubs.addEventListener('click', loadFacultySubmissions);
  }
  if (el.btnCloseReviewModal) {
    el.btnCloseReviewModal.addEventListener('click', () => closeModal(el.facultyReviewModal, null));
  }
  if (el.btnSaveFacultyReview) {
    el.btnSaveFacultyReview.addEventListener('click', handleSaveFacultyReview);
  }
  if (el.btnApproveFacultyGrade) {
    el.btnApproveFacultyGrade.addEventListener('click', handleApproveFacultyGrade);
  }
  if (el.btnPublishFacultyGrade) {
    el.btnPublishFacultyGrade.addEventListener('click', handlePublishFacultyGrade);
  }
  if (el.facultySubmissionsTbody) {
    el.facultySubmissionsTbody.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-review-sub');
      if (btn) {
        const subId = btn.getAttribute('data-sub-id');
        openReviewModal(subId);
      }
    });
  }

  ['dashboard', 'notifications', 'knowledge', 'faculty', 'history', 'about'].forEach((id) => {
    const btn = el.navTabs[id];
    if (btn) btn.addEventListener('click', () => switchLab(id));
  });
  const refreshNotifications = document.getElementById('btn-refresh-notifications');
  if (refreshNotifications) refreshNotifications.addEventListener('click', loadInbox);
  const closeToast = document.getElementById('btn-close-toast');
  if (closeToast) closeToast.addEventListener('click', hideAlert);
  const themeBtn = document.getElementById('btn-theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      document.body.classList.toggle('light-theme');
      document.body.classList.toggle('dark-theme');
    });
  }
  document.querySelectorAll('.dash-lab-card').forEach((btn) => {
    btn.addEventListener('click', () => switchLab(btn.getAttribute('data-goto')));
  });
  const refreshKnowledge = document.getElementById('btn-refresh-knowledge');
  if (refreshKnowledge) refreshKnowledge.addEventListener('click', loadKnowledgeFiles);
  const knowledgeSearchInput = document.getElementById('knowledge-search-input');
  if (knowledgeSearchInput) {
    knowledgeSearchInput.addEventListener('input', () => loadKnowledgeFiles());
  }
  const knowledgeTbody = document.getElementById('knowledge-files-tbody');
  if (knowledgeTbody) {
    knowledgeTbody.addEventListener('click', (e) => {
      const btn = e.target.closest('.btn-download-note');
      if (btn) downloadKnowledgeFile(btn.getAttribute('data-file-id'), btn.getAttribute('data-filename'));
    });
  }
  const knowledgeSearchBtn = document.getElementById('btn-knowledge-search');
  if (knowledgeSearchBtn) knowledgeSearchBtn.addEventListener('click', searchIndexedKnowledge);
  ['cm-category-grid', 'cm-folder-tree', 'cm-breadcrumbs', 'cm-materials-list'].forEach((id) => {
    const container = document.getElementById(id);
    if (container) container.addEventListener('click', handleCourseMaterialAction);
  });
  const cmRefresh = document.getElementById('cm-refresh');
  if (cmRefresh) cmRefresh.addEventListener('click', loadCourseMaterials);
  const cmFilters = ['cm-chapter-filter', 'cm-lab-filter', 'cm-type-filter'];
  cmFilters.forEach((id) => {
    document.getElementById(id)?.addEventListener('change', () => {
      loadCourseMaterialItems().catch(err => showCourseMaterialsError(err.message));
    });
  });
  let materialSearchTimer = null;
  document.getElementById('cm-search')?.addEventListener('input', () => {
    window.clearTimeout(materialSearchTimer);
    materialSearchTimer = window.setTimeout(() => {
      loadCourseMaterialItems().catch(err => showCourseMaterialsError(err.message));
    }, 250);
  });
  document.getElementById('cm-create-folder-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const name = document.getElementById('cm-folder-name')?.value.trim();
    if (!name || !courseMaterialsState.activeCategoryId) return;
    try {
      await courseMaterialsRequest('/api/course-materials/folders', 'POST', {
        course_id: '26ECAC401',
        category_id: courseMaterialsState.activeCategoryId,
        parent_folder_id: courseMaterialsState.activeFolderId,
        name,
      });
      event.target.reset();
      await loadCourseMaterialCategory();
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not create the folder.');
    }
  });
  document.getElementById('cm-folder-move')?.addEventListener('click', async () => {
    const folderId = courseMaterialsState.selectedFolderId;
    if (!folderId) return;
    const target = document.getElementById('cm-folder-move-target')?.value || null;
    try {
      await courseMaterialsRequest(`/api/course-materials/folders/${encodeURIComponent(folderId)}`, 'PATCH', {
        parent_folder_id: target,
      });
      courseMaterialsState.selectedFolderId = null;
      await loadCourseMaterialCategory();
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not move the folder.');
    }
  });
  document.getElementById('cm-upload-category')?.addEventListener('change', async (event) => {
    try {
      const response = await courseMaterialsRequest(`/api/course-materials/folders?category_id=${encodeURIComponent(event.target.value)}`);
      const folders = flattenMaterialFolders(response.folders || []);
      const select = document.getElementById('cm-upload-folder');
      if (select) {
        select.innerHTML = `<option value="">Category root</option>${folders.map(folder =>
          `<option value="${escapeHtml(folder.folder_id)}">${'&nbsp;'.repeat(folder.depth * 2)}${escapeHtml(folder.path)}</option>`
        ).join('')}`;
      }
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not load the destination folders.');
    }
  });
  document.getElementById('cm-upload-form')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const files = document.getElementById('cm-upload-files')?.files || [];
    if (!files.length) return showCourseMaterialsError('Choose at least one file to upload.');
    const form = new FormData();
    form.append('course_id', '26ECAC401');
    form.append('category_id', document.getElementById('cm-upload-category')?.value || courseMaterialsState.activeCategoryId);
    const destinationFolder = document.getElementById('cm-upload-folder')?.value;
    const materialTitle = document.getElementById('cm-upload-title')?.value.trim();
    if (destinationFolder) form.append('folder_id', destinationFolder);
    if (materialTitle) form.append('title', materialTitle);
    form.append('description', document.getElementById('cm-upload-description')?.value || '');
    const chapter = document.getElementById('cm-upload-chapter')?.value;
    const lab = document.getElementById('cm-upload-lab')?.value;
    if (chapter) form.append('chapter', chapter);
    if (lab) form.append('lab', lab);
    Array.from(files).forEach(file => form.append('files', file));
    const submit = document.getElementById('cm-upload-submit');
    if (submit) submit.disabled = true;
    try {
      courseMaterialsState.activeCategoryId = document.getElementById('cm-upload-category')?.value || courseMaterialsState.activeCategoryId;
      courseMaterialsState.activeFolderId = destinationFolder || null;
      const data = await courseMaterialsRequest('/api/course-materials/materials', 'POST', form, true);
      event.target.reset();
      await loadCourseMaterials();
      showAlert(`${data.count} course material(s) uploaded.`);
    } catch (err) {
      showCourseMaterialsError(err.message || 'Could not upload the selected files.');
    } finally {
      if (submit) submit.disabled = false;
    }
  });
  document.getElementById('cm-preview-close')?.addEventListener('click', () => {
    document.getElementById('cm-material-preview')?.classList.add('hidden');
    document.getElementById('cm-preview-body')?.replaceChildren();
  });
  const lab9Verify = document.getElementById('btn-lab9-verify');
  if (lab9Verify) lab9Verify.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab9-result');
    const claims = document.getElementById('lab9-claims-input').value.split(/\r?\n/).map(value => value.trim()).filter(Boolean);
    if (!claims.length) return showAlert('Enter at least one claim to inspect.');
    lab9Verify.disabled = true;
    try {
      const chapter = document.getElementById('lab9-chapter-select').value;
      const data = await apiCall('/api/lab9/grounding/verify', 'POST', { claims, chapter: chapter ? Number(chapter) : null });
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Evidence lookup failed: ${err.message}`;
    } finally {
      lab9Verify.disabled = false;
    }
  });
  const lab10Validate = document.getElementById('btn-lab10-validate');
  const lab10Result = document.getElementById('lab10-result');
  if (lab10Validate) lab10Validate.addEventListener('click', async () => {
    try {
      const weights = JSON.parse(document.getElementById('lab10-weights-input').value);
      const data = await apiCall('/api/lab10/validation/repair', 'POST', { weights });
      lab10Result.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      lab10Result.textContent = `Validation failed: ${err.message}`;
    }
  });
  const lab10SimulateRepair = document.getElementById('btn-lab10-simulate-repair');
  if (lab10SimulateRepair) lab10SimulateRepair.addEventListener('click', async () => {
    try {
      const weights = JSON.parse(document.getElementById('lab10-weights-input').value);
      const repairIndex = Number(document.getElementById('lab10-repair-index').value);
      const injectFailure = document.getElementById('lab10-inject-repair-failure').checked;
      const data = await apiCall('/api/lab10/validation/repair', 'POST', {
        weights,
        apply_simulated_repair: true,
        repair_index: repairIndex,
        max_attempts: 3,
        inject_repair_failure: injectFailure
      });
      lab10Result.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      lab10Result.textContent = `Bounded repair simulation failed: ${err.message}`;
    }
  });
  let lab10RemediationId = null;
  const lab10CloudResult = document.getElementById('lab10-cloud-result');
  const lab10Diagnose = document.getElementById('btn-lab10-diagnose');
  if (lab10Diagnose) lab10Diagnose.addEventListener('click', async () => {
    lab10Diagnose.disabled = true;
    try {
      const data = await apiCall('/api/lab10/cloud-ops/diagnosis');
      lab10CloudResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      lab10CloudResult.textContent = `Simulation diagnosis failed: ${err.message}`;
    } finally {
      lab10Diagnose.disabled = false;
    }
  });
  const lab10Repair = document.getElementById('btn-lab10-repair');
  const lab10Rollback = document.getElementById('btn-lab10-rollback');
  if (lab10Repair) lab10Repair.addEventListener('click', async () => {
    if (!document.getElementById('lab10-repair-approval').checked) {
      lab10CloudResult.textContent = 'Check the approval box before applying this simulation-only repair.';
      return;
    }
    lab10Repair.disabled = true;
    try {
      const data = await apiCall('/api/lab10/cloud-ops/repair', 'POST', { approved: true });
      lab10RemediationId = data.proposal.remediation_id;
      lab10Rollback.disabled = !data.rollback_available;
      lab10CloudResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      lab10CloudResult.textContent = `Simulated repair failed: ${err.message}`;
    } finally {
      lab10Repair.disabled = false;
    }
  });
  if (lab10Rollback) lab10Rollback.addEventListener('click', async () => {
    if (!lab10RemediationId) return;
    lab10Rollback.disabled = true;
    try {
      const data = await apiCall('/api/lab10/cloud-ops/rollback', 'POST', { remediation_id: lab10RemediationId });
      lab10CloudResult.textContent = JSON.stringify(data, null, 2);
      lab10RemediationId = null;
      document.getElementById('lab10-repair-approval').checked = false;
    } catch (err) {
      lab10CloudResult.textContent = `Simulated rollback failed: ${err.message}`;
      lab10Rollback.disabled = false;
    }
  });
  const lab11Run = document.getElementById('btn-lab11-run');
  if (lab11Run) lab11Run.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab11-result');
    lab11Run.disabled = true;
    try {
      const data = await apiCall('/api/lab11/benchmarks/run', 'POST');
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Benchmark failed: ${err.message}`;
    } finally {
      lab11Run.disabled = false;
    }
  });
  const lab11SpecBuild = document.getElementById('btn-lab11-spec-build');
  if (lab11SpecBuild) lab11SpecBuild.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab11-spec-result');
    const requirement = document.getElementById('lab11-spec-requirement').value.trim();
    if (!requirement) return showAlert('Enter a course requirement first.');
    const chapterValue = document.getElementById('lab11-spec-chapter').value;
    try {
      const data = await apiCall('/api/lab11/spec-build', 'POST', {
        course_id: '26ECAC401',
        specialist_type: document.getElementById('lab11-spec-type').value,
        requirement,
        chapter: chapterValue ? Number(chapterValue) : null,
      });
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Structured artifact build failed: ${err.message}`;
    }
  });
  const lab13Run = document.getElementById('btn-lab13-run');
  if (lab13Run) lab13Run.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab13-result');
    const workItem = document.getElementById('lab13-work-item').value.trim();
    if (!workItem) return showAlert('Enter a theory topic, lab task, or project deliverable.');
    const chapterValue = document.getElementById('lab13-chapter').value;
    try {
      const data = await apiCall('/api/lab13/specialists/run', 'POST', {
        course_id: '26ECAC401',
        specialist_type: document.getElementById('lab13-specialist-type').value,
        work_item: workItem,
        chapter: chapterValue ? Number(chapterValue) : null,
      });
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Specialist request failed: ${err.message}`;
    }
  });
  let capstoneRunId = null;
  let capstoneReleaseId = null;
  const capstoneResult = document.getElementById('capstone-result');
  const capstoneRun = document.getElementById('btn-capstone-run');
  if (capstoneRun) capstoneRun.addEventListener('click', async () => {
    capstoneRun.disabled = true;
    try {
      const data = await apiCall('/api/capstone/runs', 'POST', {
        course_id: document.getElementById('capstone-course-id').value.trim(),
        assignment_id: document.getElementById('capstone-assignment-id').value.trim(),
        request: document.getElementById('capstone-request').value.trim(),
      });
      capstoneRunId = data.run_id;
      capstoneResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      capstoneResult.textContent = `Capstone preparation failed: ${err.message}`;
    } finally {
      capstoneRun.disabled = false;
    }
  });
  const capstoneDecision = async (approved) => {
    if (!capstoneRunId) return showAlert('Prepare a capstone run before submitting a faculty decision.');
    try {
      const data = await apiCall(
        `/api/capstone/runs/${encodeURIComponent(capstoneRunId)}/decision`,
        'POST',
        { approved, comment: approved ? 'Faculty-approved workspace release.' : 'Returned for faculty revision.' },
      );
      if (approved && data.release_id) capstoneReleaseId = data.release_id;
      capstoneResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      capstoneResult.textContent = `Faculty decision was not applied: ${err.message}`;
    }
  };
  const capstoneApprove = document.getElementById('btn-capstone-approve');
  const capstoneReject = document.getElementById('btn-capstone-reject');
  if (capstoneApprove) capstoneApprove.addEventListener('click', () => capstoneDecision(true));
  if (capstoneReject) capstoneReject.addEventListener('click', () => capstoneDecision(false));
  const capstoneCurrent = document.getElementById('btn-capstone-current');
  if (capstoneCurrent) capstoneCurrent.addEventListener('click', async () => {
    const courseId = encodeURIComponent(document.getElementById('capstone-course-id').value.trim());
    try {
      const data = await apiCall(`/api/capstone/releases/current?course_id=${courseId}`);
      capstoneReleaseId = data.release_id;
      capstoneResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      capstoneResult.textContent = `Published release unavailable: ${err.message}`;
    }
  });
  const capstoneRollback = document.getElementById('btn-capstone-rollback');
  if (capstoneRollback) capstoneRollback.addEventListener('click', async () => {
    if (!capstoneReleaseId) return showAlert('Load or publish a current release before rollback.');
    try {
      const data = await apiCall(`/api/capstone/releases/${encodeURIComponent(capstoneReleaseId)}/rollback`, 'POST', {});
      capstoneReleaseId = data ? data.release_id : null;
      capstoneResult.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      capstoneResult.textContent = `Release rollback failed: ${err.message}`;
    }
  });
  const lab12Propose = document.getElementById('btn-lab12-propose');
  if (lab12Propose) lab12Propose.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab12-result');
    try {
      const current_value = JSON.parse(document.getElementById('lab12-current-input').value);
      const proposed_value = JSON.parse(document.getElementById('lab12-proposed-input').value);
      const data = await apiCall('/api/lab12/proposals', 'POST', {
        resource_id: document.getElementById('lab12-resource-input').value.trim(),
        summary: document.getElementById('lab12-summary-input').value.trim(),
        current_value,
        proposed_value
      });
      document.getElementById('lab12-proposal-id').value = data.proposal_id;
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Could not stage proposal: ${err.message}`;
    }
  });
  const lab12Decision = async (approved) => {
    const resultBox = document.getElementById('lab12-result');
    const proposalId = document.getElementById('lab12-proposal-id').value.trim();
    if (!proposalId) return showAlert('Create a governance proposal before deciding.');
    try {
      const data = await apiCall(`/api/lab12/proposals/${encodeURIComponent(proposalId)}/decision`, 'POST', {
        approved,
        comment: document.getElementById('lab12-decision-comment').value.trim() || null
      });
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Decision failed: ${err.message}`;
    }
  };
  const lab12Approve = document.getElementById('btn-lab12-approve');
  const lab12Reject = document.getElementById('btn-lab12-reject');
  if (lab12Approve) lab12Approve.addEventListener('click', () => lab12Decision(true));
  if (lab12Reject) lab12Reject.addEventListener('click', () => lab12Decision(false));
  const lab12Rollback = document.getElementById('btn-lab12-rollback');
  if (lab12Rollback) lab12Rollback.addEventListener('click', async () => {
    const resultBox = document.getElementById('lab12-result');
    const proposalId = document.getElementById('lab12-proposal-id').value.trim();
    if (!proposalId) return showAlert('Create and approve a proposal before rollback.');
    try {
      const data = await apiCall(`/api/lab12/proposals/${encodeURIComponent(proposalId)}/rollback`, 'POST', {});
      resultBox.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultBox.textContent = `Rollback failed: ${err.message}`;
    }
  });
  const refreshHistory = document.getElementById('btn-refresh-history');
  if (refreshHistory) refreshHistory.addEventListener('click', loadHistory);

  if (el.authLoginForm) {
    el.authLoginForm.addEventListener('submit', async event => {
      event.preventDefault();
      el.authLoginError.textContent = '';
      el.authLoginSubmit.disabled = true;
      try {
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: el.authEmail.value.trim(),
            password: el.authPassword.value,
          }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Sign-in failed.');
        el.authPassword.value = '';
        await init();
      } catch (err) {
        el.authLoginError.textContent = err.message || 'Sign-in failed.';
      } finally {
        el.authLoginSubmit.disabled = false;
      }
    });
  }
  if (el.btnAuthLogout) {
    el.btnAuthLogout.addEventListener('click', async () => {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: csrfRequestHeaders(),
      });
      window.location.reload();
    });
  }

  init();
});
