"""Test UI static asset serving and Labs 1-14 views in the index HTML."""

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ui_index_html_serves_all_14_labs():
    """Verify navigation, view containers, and accurate Lab 9-12 scope descriptions."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Verify navigation tabs
    for i in range(1, 15):
        assert f'id="nav-tab-lab{i}"' in html, f"Missing nav-tab-lab{i} in index.html"
        assert f'id="lab{i}-view"' in html, f"Missing lab{i}-view in index.html"

    for notice in (
        "Deep Research Agent",
        "AI topic briefing, evidence table",
        "Failed deployment: diagnose &amp; fix",
        "Requirement → tested implementation",
        "Risk, approval, eval, rollback plan",
        "Local cloud-operations simulation",
        "changes only the simulator’s in-memory state",
        "it does not generate code from requirements",
        "SQLite-backed governance demo",
    ):
        assert notice in html
    assert "Not implemented" not in html
    assert "(Partial)" not in html
    for lab_id, title in (
        (9, "Deep Research Agent"),
        (10, "Cloud Operations Agent"),
        (11, "Agentic SDLC Factory"),
        (12, "Safety &amp; Governance"),
    ):
        assert f'title="Lab {lab_id}: {title}' in html
    assert 'id="btn-lab13-run"' in html
    assert 'id="btn-capstone-run"' in html
    assert 'id="btn-capstone-approve"' in html

    # Verify specific feature containers across Labs 3-8
    assert 'id="lab3-skills-catalog-grid"' in html
    assert 'id="lab3-sandbox-select"' in html
    assert 'id="lab2-course-select"' in html
    assert 'id="lab2-assignment-select"' in html
    assert 'id="lab3-sandbox-params" class="form-textarea font-mono" rows="4"></textarea>' in html
    assert 'id="admin-portal-section"' in html
    assert 'class="admin-overview-stats"' in html
    assert 'id="admin-assignment-details"' in html
    assert "Open assignment" in html
    assert "Administrator access cannot submit for a student." in html
    assert 'id="lab4-session-id-input"' in html
    assert 'id="lab4-session-id-input" class="form-input font-mono" value=""' in html
    assert 'id="lab4-rag-results-container"' in html
    assert 'id="lab5-source-select"' in html
    assert 'id="lab5-audit-table-container"' in html
    assert 'id="lab6-budget-steps"' in html
    assert 'id="btn-lab6-crash"' in html
    assert 'id="btn-lab6-resume"' in html
    assert 'id="lab7-graph-nodes-grid"' in html
    assert 'id="lab7-gate-banner"' in html
    assert 'id="btn-lab8-launch-swarm"' in html
    assert 'id="lab8-workers-grid"' in html


def test_ui_static_assets_serve_successfully():
    """Verify that all local frontend assets are served with status 200."""
    index = client.get("/")
    assert index.status_code == 200
    assert 'src="/static/app.js?v=1.1.4"' in index.text

    res_css = client.get("/static/style.css")
    assert res_css.status_code == 200
    assert "lab-switcher" in res_css.text
    assert ".admin-assignment-row" in res_css.text
    assert 'href="/static/style.css?v=1.1.3"' in index.text

    res_js = client.get("/static/app.js")
    assert res_js.status_code == 200
    assert "switchLab" in res_js.text

    res_icon = client.get("/static/favicon.svg")
    assert res_icon.status_code == 200
    assert "<svg" in res_icon.text


def test_ui_submissions_and_javascript_syntax_validity():
    """Verify that Submissions portal elements exist and app.js has zero JavaScript syntax errors."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert 'id="nav-tab-submissions"' in html
    assert 'id="submissions-view"' in html
    assert 'id="sub-github-url-input"' in html
    assert 'id="faculty-review-modal"' in html
    for control in (
        'id="btn-lab9-verify"',
        'id="btn-lab10-diagnose"',
        'id="btn-lab10-repair"',
        'id="btn-lab10-rollback"',
        'id="lab10-repair-approval"',
        'id="btn-lab10-validate"',
        'id="btn-lab10-simulate-repair"',
        'id="lab10-repair-index"',
        'id="lab10-inject-repair-failure"',
        'id="btn-lab11-run"',
        'id="btn-lab11-spec-build"',
        'id="btn-lab13-run"',
        'id="btn-capstone-run"',
        'id="btn-capstone-approve"',
        'id="btn-capstone-rollback"',
        'id="btn-lab12-propose"',
    ):
        assert control in html

    js = client.get("/static/app.js").text
    assert "session-demo-01" not in js
    assert "for (let i = 1; i <= 14; i++)" in js
    assert "async function createLab4Session()" in js
    assert "Number.isFinite(activeRun.steps_executed)" in js
    assert "runState === 'WAITING_APPROVAL'" in js
    assert "currentLab7State?.node_states?.[node.id]" in js
    assert "nodeState === 'WAITING_APPROVAL'" in js
    assert "/api/lab10/cloud-ops/diagnosis" in js
    assert "/api/lab10/cloud-ops/repair" in js
    assert "/api/lab10/cloud-ops/rollback" in js
    assert "apply_simulated_repair: true" in js
    for old_title in (
        "Deep Research Agent (Partial)",
        "Cloud Operations Agent (Not Implemented)",
        "Agentic SDLC Factory (Partial)",
        "Safety & Governance (Partial)",
    ):
        assert old_title not in js

    import shutil
    import subprocess
    node_exe = shutil.which("node")
    if node_exe:
        result = subprocess.run([node_exe, "--check", "app/static/app.js"], capture_output=True, text=True)
        assert result.returncode == 0, f"JavaScript syntax error in app.js: {result.stderr}"
