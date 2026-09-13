"""Offline tests for the Gate 19.12 localhost visual demonstration."""

from opslens.demo.visual import (
    DemoVisualProjection,
    VisualFact,
    render_visual_projection,
)
from opslens.demo.web import (
    LOCAL_DEMO_HOST,
    LOCAL_DEMO_PORT,
    build_visual_catalog,
    route_visual_request,
)


def test_visual_catalog_reuses_exact_three_deterministic_scenario_results() -> None:
    """The visual adapter must expose exactly the three retained Gate 19.11 outcomes."""
    catalog = build_visual_catalog()

    assert tuple(item.scenario_id for item in catalog) == (
        "material-vulnerability",
        "controlled-benign",
        "fail-closed-incomplete-evidence",
    )
    assert tuple(item.state for item in catalog) == (
        "MATERIAL_FINDING",
        "NO_MATERIAL_FINDING",
        "REJECTED_INCOMPLETE_EVIDENCE",
    )
    assert catalog[0].risk_summary.startswith("P0 · 90/100")
    assert "not a claim that a live repository is safe" in catalog[1].notices[0]
    assert catalog[2].risk_summary == "No risk result and no benign conclusion were produced."


def test_localhost_contract_has_no_external_bind_surface() -> None:
    """The V1 visual server default must remain bound to loopback only."""
    assert LOCAL_DEMO_HOST == "127.0.0.1"
    assert LOCAL_DEMO_PORT == 8765


def test_index_and_each_allowlisted_scenario_render_without_provider_input() -> None:
    """Reviewer routes must render from admitted offline scenarios only."""
    index = route_visual_request("/")
    assert index.status == 200
    index_html = index.body.decode("utf-8")
    assert "Software risk, with the authority boundary visible." in index_html

    for scenario_id in (
        "material-vulnerability",
        "controlled-benign",
        "fail-closed-incomplete-evidence",
    ):
        response = route_visual_request(f"/scenario/{scenario_id}")
        assert response.status == 200
        html = response.body.decode("utf-8")
        assert scenario_id in html
        assert "AI explanation" in html
        assert "Disabled in the V1 offline demo." in html
        assert "visual projection != business authority" in html


def test_unknown_route_scenario_and_query_fail_closed() -> None:
    """Browser-controlled path text must not become arbitrary scenario or provider authority."""
    assert route_visual_request("/scenario/not-admitted").status == 404
    assert route_visual_request("/arbitrary").status == 404
    assert route_visual_request("/?repository=https://example.com/evil").status == 400
    assert route_visual_request("/").status == 200


def test_health_projection_is_provider_and_model_free() -> None:
    """The local health route must declare the offline execution boundary."""
    response = route_visual_request("/health")
    assert response.status == 200
    body = response.body.decode("utf-8")
    assert '"host":"127.0.0.1"' in body
    assert '"model_execution":false' in body
    assert '"provider_execution":false' in body


def test_dynamic_visual_values_are_html_escaped() -> None:
    """Presentation values must never become executable browser markup."""
    projection = DemoVisualProjection(
        scenario_id='<script>alert("scenario")</script>',
        title="escape-test",
        state="REJECTED",
        tone="blocked",
        repository="<b>repo</b>",
        commit_sha="1" * 40,
        dependency="pkg<unsafe>==1",
        finding_summary="<img src=x onerror=alert(1)>",
        risk_summary="no risk",
        evidence_summary="escaped",
        result_id="result<unsafe>",
        provenance=(VisualFact("source", "<script>alert(2)</script>"),),
        notices=("<em>notice</em>",),
        canonical_json='{"payload":"</pre><script>alert(3)</script>"}',
    )

    rendered = render_visual_projection(projection)

    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "<b>repo</b>" not in rendered
    assert "&lt;script&gt;alert" in rendered
    assert "&lt;img src=x onerror=alert(1)&gt;" in rendered
    assert "&lt;b&gt;repo&lt;/b&gt;" in rendered
