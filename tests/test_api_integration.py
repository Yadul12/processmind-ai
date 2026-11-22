"""
End-to-End REST API Integration Tests covering Document Upload, Extraction,
Validation, Individual Activity Review, Editing/Versioning, Approval Guards,
Rejection, and JSON Import/Export.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from backend.config import settings


def test_health_endpoint(client: TestClient) -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database_connected"] is True
    assert data["sample_documents_loaded"] >= 5

    # Verify compiled React frontend bundle is served at root
    ui_resp = client.get("/")
    assert ui_resp.status_code == 200
    assert "ProcessMind AI" in ui_resp.text


def test_document_upload_and_process_extraction_lifecycle(client: TestClient) -> None:
    sample_pdf = Path(settings.sample_data_dir) / "sop_01_invoice_processing.pdf"
    with sample_pdf.open("rb") as f:
        up_resp = client.post(
            "/api/documents/upload",
            files={"file": ("uploaded_invoice_sop.pdf", f, "application/pdf")},
        )
    assert up_resp.status_code == 201
    doc_data = up_resp.json()
    doc_id = doc_data["id"]
    assert doc_data["file_type"] == "pdf"
    assert len(doc_data["parsed_structure"]["blocks"]) >= 10

    # List documents & get single document
    list_resp = client.get("/api/documents")
    assert list_resp.status_code == 200
    assert any(d["id"] == doc_id for d in list_resp.json())

    get_doc_resp = client.get(f"/api/documents/{doc_id}")
    assert get_doc_resp.status_code == 200

    # Extract process model
    ext_resp = client.post(
        "/api/processes/extract",
        json={
            "document_id": doc_id,
            "custom_process_name": "AP Invoice Processing v1 Test",
            "force_reextract": True,
        },
    )
    assert ext_resp.status_code == 201
    proc = ext_resp.json()
    proc_id = proc["process_id"]
    assert proc["version"] == 1
    assert proc["review_status"] == "PENDING_REVIEW"
    assert len(proc["activities"]) == 6

    # Validate process endpoint
    val_resp = client.post(f"/api/processes/{proc_id}/validate")
    assert val_resp.status_code == 200
    assert val_resp.json()["is_schema_valid"] is True

    # Review single activity
    act_rev_resp = client.post(
        f"/api/processes/{proc_id}/activities/ACT-001/review",
        json={
            "decision": "APPROVED",
            "reviewer_name": "Clara Vance (Lead Process Architect)",
            "reviewer_note": "Verified intake step against Section 2.0 Page 1.",
        },
    )
    assert act_rev_resp.status_code == 200
    assert act_rev_resp.json()["review_status"] == "IN_REVIEW"

    # Update process via PUT (increments version to v2)
    activities_updated = act_rev_resp.json()["activities"]
    activities_updated[0]["description"] = "Receive vendor invoice via AP portal and validate vendor tax ID."
    put_resp = client.put(
        f"/api/processes/{proc_id}",
        json={
            "process_name": "AP Invoice Processing (Reviewed v2)",
            "activities": activities_updated,
            "reviewer_name": "Clara Vance (Lead Process Architect)",
            "change_summary": "Clarified vendor tax ID check in ACT-001",
            "comment": "Updated ACT-001 description for audit clarity.",
        },
    )
    assert put_resp.status_code == 200
    updated_proc = put_resp.json()
    assert updated_proc["version"] == 2

    # Check version history endpoint
    ver_resp = client.get(f"/api/processes/{proc_id}/versions")
    assert ver_resp.status_code == 200
    ver_data = ver_resp.json()
    assert ver_data["current_version"] == 2
    assert len(ver_data["versions"]) == 2

    # Approve complete process model
    apr_resp = client.post(
        f"/api/processes/{proc_id}/approve",
        json={
            "reviewer_name": "Clara Vance (Lead Process Architect)",
            "comment": "All 6 activities and 3-way match rules verified.",
            "approve_all_pending_activities": True,
        },
    )
    assert apr_resp.status_code == 200
    approved_proc = apr_resp.json()
    assert approved_proc["review_status"] == "APPROVED"
    assert approved_proc["approved_by"] == "Clara Vance (Lead Process Architect)"
    assert approved_proc["needs_human_review"] is False

    # Export and Import JSON
    export_resp = client.get(f"/api/processes/{proc_id}/export")
    assert export_resp.status_code == 200
    exported_json = export_resp.json()

    import_resp = client.post(
        "/api/processes/import",
        json={
            "process_model": exported_json,
            "imported_by": "Integration Test Runner",
        },
    )
    assert import_resp.status_code == 201


def test_blocking_errors_prevent_process_approval_until_remediated_by_reviewer(client: TestClient) -> None:
    edge_file = Path(settings.sample_data_dir) / "edge_01_ambiguous_missing_actor.txt"
    with edge_file.open("rb") as f:
        up_resp = client.post(
            "/api/documents/upload",
            files={"file": ("edge_01_ambiguous_missing_actor.txt", f, "text/plain")},
        )
    doc_id = up_resp.json()["id"]

    ext_resp = client.post(
        "/api/processes/extract",
        json={"document_id": doc_id, "force_reextract": True},
    )
    proc = ext_resp.json()
    proc_id = proc["process_id"]
    assert proc["validation_status"] == "NEEDS_REVIEW"

    # Attempt to approve while MISSING_ACTOR errors exist -> must fail with HTTP 400
    bad_apr = client.post(
        f"/api/processes/{proc_id}/approve",
        json={"reviewer_name": "Auditor", "comment": "Try approving unfixed model"},
    )
    assert bad_apr.status_code == 400
    assert "MISSING_ACTOR" in bad_apr.json()["detail"]

    # Now remediate missing actors via PUT /api/processes/{id}
    fixed_activities = proc["activities"]
    for act in fixed_activities:
        if act["responsible_role"] == "UNASSIGNED":
            act["responsible_role"] = "Expense Audit Specialist"

    put_resp = client.put(
        f"/api/processes/{proc_id}",
        json={
            "activities": fixed_activities,
            "reviewer_name": "Senior Process Reviewer",
            "change_summary": "Assigned Expense Audit Specialist to ACT-802 and ACT-803",
        },
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["validation_status"] == "VALID_WITH_WARNINGS"

    # Now approval succeeds!
    good_apr = client.post(
        f"/api/processes/{proc_id}/approve",
        json={
            "reviewer_name": "Senior Process Reviewer",
            "comment": "Assigned missing roles and approved.",
            "approve_all_pending_activities": True,
        },
    )
    assert good_apr.status_code == 200
    assert good_apr.json()["review_status"] == "APPROVED"

    # Also test process rejection flow
    rej_resp = client.post(
        f"/api/processes/{proc_id}/reject",
        json={
            "reviewer_name": "Chief Compliance Officer",
            "reason": "Policy requires quantitative threshold instead of 'large amount'.",
        },
    )
    assert rej_resp.status_code == 200
    assert rej_resp.json()["review_status"] == "REJECTED"
