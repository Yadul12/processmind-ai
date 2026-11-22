"""
Automated Evaluation Benchmark Tests via EvalGuard Extraction Adapter.
Evaluates:
- Activity extraction precision, recall, and F1
- Actor extraction accuracy
- Dependency extraction accuracy
- Decision-condition extraction accuracy
- Schema validation pass rate
- Source citation correctness
"""

from fastapi.testclient import TestClient
from backend.services.evalguard_adapter import evalguard_adapter


def test_evalguard_extraction_quality_metrics(client: TestClient) -> None:
    report = evalguard_adapter.run_full_evaluation_suite()

    assert report.total_cases == 8
    assert report.mean_activity_precision >= 95.0
    assert report.mean_activity_recall >= 95.0
    assert report.mean_activity_f1 >= 95.0
    assert report.mean_actor_accuracy >= 95.0
    assert report.mean_dependency_accuracy >= 95.0
    assert report.mean_decision_condition_accuracy >= 95.0
    assert report.schema_validation_pass_rate == 100.0
    assert report.mean_source_citation_correctness >= 95.0
    assert report.edge_case_pass_rate == 100.0

    # Also verify REST endpoint GET /api/evaluations/report
    resp = client.get("/api/evaluations/report")
    assert resp.status_code == 200
    api_report = resp.json()
    assert api_report["total_cases"] == 8
    assert api_report["schema_validation_pass_rate"] == 100.0
