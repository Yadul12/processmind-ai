"""
Generates realistic enterprise SOP documents across PDF, DOCX, XLSX, and TXT formats,
along with labelled expected ground-truth process models for automated evaluation.
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import docx
import openpyxl


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BASE_DIR / "data" / "sample_sops"
GROUND_TRUTH_DIR = BASE_DIR / "data" / "labelled_ground_truth"


def _escape_pdf_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
        .replace("—", "-")
        .replace("–", "-")
        .replace("≥", ">=")
        .replace("≤", "<=")
    )


def create_multi_page_pdf(filepath: Path, pages: List[List[str]]) -> None:
    """
    Generates a standard, spec-compliant multi-page PDF file readable by pypdf.PdfReader.
    Each page is a list of text lines.
    """
    objects: List[bytes] = []

    def add_obj(content: bytes) -> int:
        objects.append(content)
        return len(objects)

    # Object 1: Catalog (placeholder updated later)
    add_obj(b"")
    # Object 2: Pages root (placeholder updated later)
    add_obj(b"")
    # Object 3: Helvetica Font
    font_obj_id = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_obj_ids: List[int] = []

    for page_lines in pages:
        stream_lines = ["BT", "/F1 10 Tf", "45 750 Td", "13 TL"]
        for line in page_lines:
            escaped = _escape_pdf_text(line)
            stream_lines.append(f"({escaped}) Tj T*")
        stream_lines.append("ET")
        stream_bytes = "\n".join(stream_lines).encode("latin-1", errors="replace")

        content_obj_id = add_obj(
            f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
            + stream_bytes
            + b"\nendstream"
        )
        page_dict = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 {font_obj_id} 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        ).encode("ascii")
        page_id = add_obj(page_dict)
        page_obj_ids.append(page_id)

    kids_str = " ".join(f"{pid} 0 R" for pid in page_obj_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids_str}] /Count {len(page_obj_ids)} >>".encode("ascii")

    out = bytearray(b"%PDF-1.4\n")
    offsets: List[int] = [0]
    for idx, obj_bytes in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{idx} 0 obj\n".encode("ascii"))
        out.extend(obj_bytes)
        out.extend(b"\nendobj\n")

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    out.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
    )
    filepath.write_bytes(bytes(out))


SOP_SPECS: List[Dict[str, Any]] = [
    {
        "case_id": "SOP-001",
        "title": "Enterprise Accounts Payable Invoice Processing SOP",
        "document_code": "SOP-FIN-001",
        "department": "Finance & Accounts Payable",
        "effective_date": "2026-01-15",
        "owner_role": "VP of Finance Operations",
        "base_filename": "sop_01_invoice_processing",
        "formats": ["pdf", "txt"],
        "category": "Invoice Processing",
        "sections": [
            {
                "section": "Section 1.0 - Purpose and Scope",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-FIN-001 | DEPARTMENT: Finance & Accounts Payable",
                    "TITLE: Enterprise Accounts Payable Invoice Processing SOP",
                    "OWNER: VP of Finance Operations | EFFECTIVE DATE: 2026-01-15",
                    "1.0 Purpose: Standardize receipt, OCR extraction, 3-way PO matching, approval routing, and ERP payment posting for vendor invoices.",
                ],
            },
            {
                "section": "Section 2.0 - Process Activities and Execution Rules",
                "page": 1,
                "lines": [
                    "Step 1 [ACT-001] Receive and Digitize Vendor Invoice | Role: AP Intake Specialist (Finance & Accounts Payable) | Type: manual",
                    "Description: Receive vendor PDF or paper invoice via AP portal and register invoice batch metadata.",
                    "Input: Raw Vendor Invoice, Delivery Receipt | Output: Registered Invoice Record",
                    "Preconditions: Vendor is active in Master Vendor Registry | Postconditions: Invoice assigned unique tracking ID",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-002] Execute Automated OCR and Three-Way PO Match | Role: ERP Matching Engine (Finance Systems) | Type: automated",
                    "Description: Extract line items via OCR and perform automated 3-way match against Purchase Order and Goods Receipt Note within 2% tolerance.",
                    "Input: Registered Invoice Record, Purchase Order, Goods Receipt Note | Output: Three-Way Match Report",
                    "Preconditions: Invoice tracking ID exists and PO reference is present | Postconditions: Match variance percentage calculated",
                    "Dependencies: ACT-001",
                    "",
                    "Step 3 [ACT-003] Evaluate Match Discrepancy and Variance Threshold | Role: AP Senior Analyst (Finance & Accounts Payable) | Type: decision",
                    "Description: Decision gate evaluating if 3-way match variance is within 2% tolerance and whether invoice amount exceeds $10,000 approval threshold.",
                    "Input: Three-Way Match Report | Output: Routing Decision Signal",
                    "Preconditions: Three-Way Match Report generated | Postconditions: Invoice routed to approval gate, auto-posting, or discrepancy escalation",
                    "Dependencies: ACT-002",
                    "DECISION RULE [COND-001]: IF match_variance <= 2% AND invoice_amount >= $10,000 THEN route to ACT-004 ELSE IF match_variance <= 2% AND invoice_amount < $10,000 THEN route to ACT-005.",
                    "EXCEPTION RULE [EXC-001]: IF match_variance > 2% OR missing Goods Receipt Note THEN escalate to Procurement Dispute Specialist within 24 hours (Target: ACT-006). Remediation: Issue Vendor Debit Memo or PO Amendment.",
                ],
            },
            {
                "section": "Section 3.0 - Approvals, Exception Handling, and Settlement",
                "page": 2,
                "lines": [
                    "Step 4 [ACT-004] Approve High-Value Invoice Settlement | Role: Finance Controller (Executive Finance) | Type: approval",
                    "Description: Review supporting audit package and approve invoices valued at $10,000 or above.",
                    "Input: Routing Decision Signal, Three-Way Match Report | Output: Signed Payment Authorization",
                    "Preconditions: Invoice amount >= $10,000 and 3-way match verified | Postconditions: Payment authorization token recorded in ERP",
                    "Dependencies: ACT-003",
                    "APPROVAL GATE [APR-001]: Approver: Finance Controller | Criteria: Budget availability and valid 3-way match for invoices >= $10,000 | SLA: 16 hours | Rejection Target: ACT-006.",
                    "",
                    "Step 5 [ACT-005] Post General Ledger Entry and Schedule ACH Payment | Role: ERP Treasury Scheduler (Finance Systems) | Type: automated",
                    "Description: Post balanced liability journal to General Ledger and schedule Net-30 ACH payment run.",
                    "Input: Signed Payment Authorization, Registered Invoice Record | Output: GL Journal Voucher, ACH Payment Instruction",
                    "Preconditions: Either Finance Controller approval obtained or auto-approved (< $10,000) | Postconditions: Payment scheduled and vendor notified",
                    "Dependencies: ACT-003, ACT-004",
                    "",
                    "Step 6 [ACT-006] Resolve PO Discrepancy with Vendor and Procurement | Role: Procurement Dispute Specialist (Procurement) | Type: escalation",
                    "Description: Investigate quantity or price variance > 2% with buyer and supplier, issuing credit note request or invoice rejection.",
                    "Input: Three-Way Match Report, Discrepancy Alert | Output: Discrepancy Resolution Memo",
                    "Preconditions: Match variance > 2% or controller rejection | Postconditions: Invoice placed on hold or credit memo received",
                    "Dependencies: ACT-003",
                ],
            },
        ],
    },
    {
        "case_id": "SOP-002",
        "title": "Global Employee Onboarding and Identity Provisioning SOP",
        "document_code": "SOP-HR-002",
        "department": "Human Resources & People Operations",
        "effective_date": "2026-02-01",
        "owner_role": "Director of People Operations",
        "base_filename": "sop_02_employee_onboarding",
        "formats": ["docx", "txt"],
        "category": "Employee Onboarding",
        "sections": [
            {
                "section": "Section 1.0 - Policy Overview",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-HR-002 | DEPARTMENT: Human Resources & People Operations",
                    "TITLE: Global Employee Onboarding and Identity Provisioning SOP",
                    "OWNER: Director of People Operations | EFFECTIVE DATE: 2026-02-01",
                    "1.0 Overview: Governs end-to-end pre-boarding verification, HRIS record creation, IT equipment & SSO provisioning, and mandatory security compliance.",
                ],
            },
            {
                "section": "Section 2.0 - Pre-Boarding and Identity Setup",
                "page": 1,
                "lines": [
                    "Step 1 [ACT-101] Verify Signed Offer and Background Check Clearance | Role: HR Onboarding Coordinator (Human Resources) | Type: manual",
                    "Description: Validate countersigned employment contract, I-9/right-to-work documents, and background screening clearance report.",
                    "Input: Signed Offer Letter, Background Screening Report | Output: Verified Pre-Boarding Dossier",
                    "Preconditions: Candidate accepted offer in ATS | Postconditions: Background check marked PASSED",
                    "Dependencies: None",
                    "EXCEPTION RULE [EXC-101]: IF background check reveals unverified employment or adverse criminal finding THEN escalate to Employee Relations Legal Counsel within 8 hours (Target: ACT-106). Remediation: Hold start date and initiate adverse action review.",
                    "",
                    "Step 2 [ACT-102] Create Master Employee Profile in Workday HRIS | Role: HRIS Automation Bot (People Systems) | Type: automated",
                    "Description: Generate canonical Employee ID, cost-center assignment, and organizational reporting hierarchy in Workday.",
                    "Input: Verified Pre-Boarding Dossier | Output: Active HRIS Employee Record",
                    "Preconditions: Background check clearance verified | Postconditions: Employee ID broadcast to IAM provisioning queue",
                    "Dependencies: ACT-101",
                    "",
                    "Step 3 [ACT-103] Evaluate Role Security Tier and Production Access Need | Role: IT Security Analyst (Information Security) | Type: decision",
                    "Description: Determine if new hire requires Tier-1 Privileged Engineering access or Standard Corporate role access.",
                    "Input: Active HRIS Employee Record, Job Role Matrix | Output: Access Tier Classification",
                    "Preconditions: HRIS Employee Record active | Postconditions: Access tier selected for provisioning",
                    "Dependencies: ACT-102",
                    "DECISION RULE [COND-101]: IF role_security_tier == 'Privileged_Engineering' THEN route to ACT-104 ELSE route to ACT-105.",
                ],
            },
            {
                "section": "Section 3.0 - Approvals, IT Provisioning, and Escalation",
                "page": 2,
                "lines": [
                    "Step 4 [ACT-104] Approve Privileged Engineering Workstation and Cloud Roles | Role: CISO Delegate (Information Security) | Type: approval",
                    "Description: Approve elevated developer laptop profile, SSH bastion keys, and cloud staging access.",
                    "Input: Access Tier Classification | Output: Signed Security Clearance Approval",
                    "Preconditions: Hire assigned to Privileged_Engineering tier | Postconditions: Elevated IAM grant authorized",
                    "Dependencies: ACT-103",
                    "APPROVAL GATE [APR-101]: Approver: CISO Delegate | Criteria: Verified security training pledge and engineering manager justification | SLA: 12 hours | Rejection Target: ACT-105.",
                    "",
                    "Step 5 [ACT-105] Provision SSO Identity, Hardware Asset, and Welcome Notification | Role: IT Endpoint Provisioning Service (IT Operations) | Type: notification",
                    "Description: Provision Okta SSO account, MDM-enrolled laptop shipment, and send Day-1 onboarding schedule notification to hiring manager and employee.",
                    "Input: Active HRIS Employee Record, Access Tier Classification | Output: Provisioned SSO Credentials, Onboarding Welcome Package",
                    "Preconditions: HRIS record active and security tier evaluated | Postconditions: Employee ready for Day-1 orientation",
                    "Dependencies: ACT-103, ACT-104",
                    "",
                    "Step 6 [ACT-106] Conduct Adverse Background Finding Legal Review | Role: Employee Relations Legal Counsel (Legal & Compliance) | Type: escalation",
                    "Description: Review background check discrepancy with candidate and issue compliance determination.",
                    "Input: Background Screening Report | Output: Legal Eligibility Determination",
                    "Preconditions: Background screening flag triggered | Postconditions: Offer rescinded or exception waiver granted",
                    "Dependencies: ACT-101",
                ],
            },
        ],
    },
    {
        "case_id": "SOP-003",
        "title": "Strategic Procurement Requisition and Vendor Approval SOP",
        "document_code": "SOP-PROC-003",
        "department": "Global Strategic Sourcing & Procurement",
        "effective_date": "2026-01-20",
        "owner_role": "Chief Procurement Officer",
        "base_filename": "sop_03_procurement_approvals",
        "formats": ["xlsx", "txt"],
        "category": "Procurement Approvals",
        "sections": [
            {
                "section": "Section 1.0 - Governance & Thresholds",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-PROC-003 | DEPARTMENT: Global Strategic Sourcing & Procurement",
                    "TITLE: Strategic Procurement Requisition and Vendor Approval SOP",
                    "OWNER: Chief Procurement Officer | EFFECTIVE DATE: 2026-01-20",
                    "1.0 Scope: Defines purchase requisition intake, vendor risk compliance, budget threshold routing, and Purchase Order issuance.",
                ],
            },
            {
                "section": "Section 2.0 - Requisition Workflow Steps",
                "page": 1,
                "lines": [
                    "Step 1 [ACT-201] Submit Purchase Requisition and Statement of Work | Role: Department Cost-Center Manager (Business Operations) | Type: manual",
                    "Description: Draft purchase requisition specifying technical scope, estimated contract value, and vendor quotes.",
                    "Input: Project Scope Document, Vendor Quotation | Output: Draft Purchase Requisition",
                    "Preconditions: Annual department budget allocated | Postconditions: Requisition submitted in Coupa Procurement",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-202] Perform Vendor Cyber Risk and Sanctions Screening | Role: Third-Party Risk Analyst (Risk & Compliance) | Type: manual",
                    "Description: Verify vendor SOC2 attestation, OFAC sanctions status, and GDPR data processing addendum.",
                    "Input: Draft Purchase Requisition, Vendor Compliance Packet | Output: Vendor Risk Assessment Score",
                    "Preconditions: Requisition submitted with vendor details | Postconditions: Risk score classified as Low, Medium, or Critical",
                    "Dependencies: ACT-201",
                    "EXCEPTION RULE [EXC-201]: IF vendor fails OFAC sanctions check OR lacks mandatory SOC2 certification THEN escalate to Chief Compliance Officer within 4 hours (Target: ACT-206). Remediation: Block vendor onboarding and require alternative supplier.",
                    "",
                    "Step 3 [ACT-203] Evaluate Requisition Contract Value and Competitive Bidding | Role: Strategic Sourcing Lead (Procurement) | Type: decision",
                    "Description: Evaluate whether total contract value exceeds $50,000 executive threshold or qualifies for standard PO issuance.",
                    "Input: Draft Purchase Requisition, Vendor Risk Assessment Score | Output: Procurement Tier Decision",
                    "Preconditions: Vendor passed risk screening | Postconditions: Routed to Procurement Committee approval or direct PO generation",
                    "Dependencies: ACT-202",
                    "DECISION RULE [COND-201]: IF total_contract_value >= $50,000 THEN route to ACT-204 ELSE route to ACT-205.",
                ],
            },
            {
                "section": "Section 3.0 - Executive Approval & Purchase Order Dispatch",
                "page": 2,
                "lines": [
                    "Step 4 [ACT-204] Approve High-Value Strategic Procurement Contract | Role: VP of Finance & Procurement Committee (Executive Finance) | Type: approval",
                    "Description: Review competitive RFP scoring matrix and approve requisitions >= $50,000.",
                    "Input: Procurement Tier Decision, RFP Scoring Matrix | Output: Executive Contract Approval",
                    "Preconditions: Contract value >= $50,000 and minimum 3 vendor bids evaluated | Postconditions: Requisition marked APPROVED for PO creation",
                    "Dependencies: ACT-203",
                    "APPROVAL GATE [APR-201]: Approver: VP of Finance & Procurement Committee | Criteria: 3 competitive bids and positive ROI business case for spend >= $50,000 | SLA: 24 hours | Rejection Target: ACT-201.",
                    "",
                    "Step 5 [ACT-205] Generate and Dispatch Binding Purchase Order | Role: Coupa PO Dispatch Engine (Procurement Systems) | Type: automated",
                    "Description: Issue binding Purchase Order PDF, commit encumbrance in ERP budget ledger, and transmit PO to supplier.",
                    "Input: Executive Contract Approval, Draft Purchase Requisition | Output: Issued Purchase Order",
                    "Preconditions: Requisition approved and vendor active | Postconditions: Purchase Order dispatched to vendor via EDI/email",
                    "Dependencies: ACT-203, ACT-204",
                    "",
                    "Step 6 [ACT-206] Execute Vendor Compliance Quarantine and Disqualification | Role: Chief Compliance Officer (Risk & Compliance) | Type: escalation",
                    "Description: Formally quarantine non-compliant vendor record and notify requester to select approved supplier.",
                    "Input: Vendor Risk Assessment Score | Output: Vendor Disqualification Notice",
                    "Preconditions: Critical compliance or sanctions violation detected | Postconditions: Requisition cancelled and vendor blocked",
                    "Dependencies: ACT-202",
                ],
            },
        ],
    },
    {
        "case_id": "SOP-004",
        "title": "Tiered Customer Complaint Resolution and SLA Escalation SOP",
        "document_code": "SOP-CX-004",
        "department": "Customer Experience & Quality Assurance",
        "effective_date": "2026-02-10",
        "owner_role": "VP of Customer Success",
        "base_filename": "sop_04_customer_complaint_resolution",
        "formats": ["pdf", "txt"],
        "category": "Customer Complaint Resolution",
        "sections": [
            {
                "section": "Section 1.0 - Service Level Objectives",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-CX-004 | DEPARTMENT: Customer Experience & Quality Assurance",
                    "TITLE: Tiered Customer Complaint Resolution and SLA Escalation SOP",
                    "OWNER: VP of Customer Success | EFFECTIVE DATE: 2026-02-10",
                    "1.0 Objective: Ensure structured intake, severity triage, root-cause investigation, goodwill credit approval, and regulatory escalation for enterprise customer complaints.",
                ],
            },
            {
                "section": "Section 2.0 - Intake, Triage, and Investigation",
                "page": 1,
                "lines": [
                    "Step 1 [ACT-301] Log Customer Complaint and Acknowledge Receipt | Role: Customer Support Specialist (Customer Experience) | Type: manual",
                    "Description: Record customer complaint in Salesforce Service Cloud, attach evidence logs, and send automated 15-minute SLA acknowledgement.",
                    "Input: Customer Complaint Submission, Account Telemetry Logs | Output: Logged Case Ticket",
                    "Preconditions: Customer holds active service agreement | Postconditions: Case ID created and SLA timer started",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-302] Triage Complaint Severity and Regulatory Impact | Role: Quality Assurance Team Lead (Quality Assurance) | Type: decision",
                    "Description: Classify complaint into Severity-1 (Regulatory/Data Privacy Breach), Severity-2 (Service Outage with SLA Credit), or Severity-3 (Standard Defect).",
                    "Input: Logged Case Ticket | Output: Severity Triage Classification",
                    "Preconditions: Case ticket logged with initial facts | Postconditions: Severity tier assigned",
                    "Dependencies: ACT-301",
                    "DECISION RULE [COND-301]: IF credit_requested >= $1,000 THEN route to ACT-304 ELSE route to ACT-303.",
                    "EXCEPTION RULE [EXC-301]: IF complaint involves GDPR/HIPAA privacy breach OR regulatory threat THEN escalate to Data Privacy & Legal Response Team within 2 hours (Target: ACT-306). Remediation: Freeze affected tenant logs and initiate statutory incident response.",
                    "",
                    "Step 3 [ACT-303] Execute Technical Root Cause Analysis and Service Remediation | Role: L3 Incident Resolution Engineer (Engineering Operations) | Type: manual",
                    "Description: Reproduce reported issue, deploy configuration hotfix or data correction, and document 5-Whys Root Cause Analysis.",
                    "Input: Severity Triage Classification, Account Telemetry Logs | Output: Root Cause & Remediation Report",
                    "Preconditions: Complaint triaged as technical/operational issue | Postconditions: Technical fix verified in customer environment",
                    "Dependencies: ACT-302",
                ],
            },
            {
                "section": "Section 3.0 - Financial Credit Approval and Closure",
                "page": 2,
                "lines": [
                    "Step 4 [ACT-304] Approve Customer SLA Service Credit or Refund | Role: Director of Customer Operations (Customer Experience) | Type: approval",
                    "Description: Review SLA downtime calculation and approve billing credit or refund >= $1,000.",
                    "Input: Root Cause & Remediation Report, SLA Credit Calculation | Output: Approved Credit Authorization",
                    "Preconditions: Customer claim >= $1,000 validated against contract SLA | Postconditions: Credit memo authorized for billing",
                    "Dependencies: ACT-302, ACT-303",
                    "APPROVAL GATE [APR-301]: Approver: Director of Customer Operations | Criteria: Verified SLA breach duration and contract penalty clause for credits >= $1,000 | SLA: 8 hours | Rejection Target: ACT-305.",
                    "",
                    "Step 5 [ACT-305] Dispatch Final Resolution Report and Close Case | Role: Customer Success Manager (Customer Experience) | Type: notification",
                    "Description: Deliver formal RCA summary and credit confirmation to customer executive sponsor and mark ticket RESOLVED.",
                    "Input: Root Cause & Remediation Report, Approved Credit Authorization | Output: Customer Resolution Closure Notice",
                    "Preconditions: Technical remediation complete and credit decision finalized | Postconditions: Case closed and CSAT survey triggered",
                    "Dependencies: ACT-303, ACT-304",
                    "",
                    "Step 6 [ACT-306] Manage Regulatory Compliance and Privacy Breach Escalation | Role: Data Privacy & Legal Response Team (Legal & Compliance) | Type: escalation",
                    "Description: Conduct forensic privacy assessment, draft regulatory notification if required, and coordinate legal communication.",
                    "Input: Logged Case Ticket, Severity Triage Classification | Output: Regulatory Incident Disposition",
                    "Preconditions: Severity-1 regulatory or privacy trigger identified | Postconditions: Legal hold and regulatory compliance protocol executed",
                    "Dependencies: ACT-302",
                ],
            },
        ],
    },
    {
        "case_id": "SOP-005",
        "title": "Zero-Trust IT Privileged Access Management (PAM) SOP",
        "document_code": "SOP-SEC-005",
        "department": "Cybersecurity & Identity Governance",
        "effective_date": "2026-02-15",
        "owner_role": "Chief Information Security Officer (CISO)",
        "base_filename": "sop_05_it_access_management",
        "formats": ["docx", "txt"],
        "category": "IT Access Management",
        "sections": [
            {
                "section": "Section 1.0 - Zero-Trust Access Policy",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-SEC-005 | DEPARTMENT: Cybersecurity & Identity Governance",
                    "TITLE: Zero-Trust IT Privileged Access Management (PAM) SOP",
                    "OWNER: Chief Information Security Officer (CISO) | EFFECTIVE DATE: 2026-02-15",
                    "1.0 Policy: Enforces just-in-time (JIT) privileged access requests, least-privilege risk evaluation, dual approval for production databases, and automated time-bound revocation.",
                ],
            },
            {
                "section": "Section 2.0 - Request Intake and Risk Evaluation",
                "page": 1,
                "lines": [
                    "Step 1 [ACT-401] Submit Just-In-Time Privileged Access Request | Role: Cloud Platform Engineer (Engineering) | Type: manual",
                    "Description: Submit JIT access ticket in CyberArk PAM specifying target production resource, business ticket ID, and requested duration (max 8 hours).",
                    "Input: Incident or Change Ticket ID, Target Resource ARN | Output: PAM Access Request Record",
                    "Preconditions: Requester holds valid MFA hardware token and active security certification | Postconditions: PAM request queued for automated policy evaluation",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-402] Evaluate Entitlement Risk and Environment Classification | Role: IAM Policy Decision Engine (Cybersecurity Systems) | Type: decision",
                    "Description: Calculate entitlement risk score and verify whether target system is a Tier-0 Production Database containing PII/PCI data.",
                    "Input: PAM Access Request Record, Asset Sensitivity Catalog | Output: Entitlement Risk Decision",
                    "Preconditions: PAM request contains valid change ticket | Postconditions: Routed to Data Owner approval or direct JIT token issuance",
                    "Dependencies: ACT-401",
                    "DECISION RULE [COND-401]: IF target_tier == 'Tier0_Production_PII' OR duration_hours > 4 THEN route to ACT-403 ELSE route to ACT-404.",
                    "EXCEPTION RULE [EXC-401]: IF request originates from unmanaged endpoint OR triggers SoD (Segregation of Duties) conflict THEN escalate to SOC Incident Commander within 1 hour (Target: ACT-406). Remediation: Deny request immediately and lock session for SOC review.",
                ],
            },
            {
                "section": "Section 3.0 - Dual Approval, JIT Provisioning, and Revocation",
                "page": 2,
                "lines": [
                    "Step 3 [ACT-403] Approve Tier-0 Production Database Privileged Access | Role: Production Data Owner & Security Lead (Cybersecurity & Governance) | Type: approval",
                    "Description: Review change window justification and grant dual-custody approval for Tier-0 PII/PCI production access.",
                    "Input: Entitlement Risk Decision, PAM Access Request Record | Output: Dual-Custody Access Grant",
                    "Preconditions: Target asset is Tier-0 Production PII or duration > 4 hours | Postconditions: Cryptographic approval token signed",
                    "Dependencies: ACT-402",
                    "APPROVAL GATE [APR-401]: Approver: Production Data Owner & Security Lead | Criteria: Verified P1/P2 change window and zero SoD conflict for Tier-0 Production access | SLA: 2 hours | Rejection Target: ACT-406.",
                    "",
                    "Step 4 [ACT-404] Issue Ephemeral Short-Lived Credentials and Record Session | Role: CyberArk JIT Vault Service (Cybersecurity Systems) | Type: automated",
                    "Description: Mint ephemeral 4-hour IAM role session with full keystroke and query audit recording enabled.",
                    "Input: Dual-Custody Access Grant, PAM Access Request Record | Output: Ephemeral Session Token, Session Audit Stream",
                    "Preconditions: Risk check passed and required approval granted | Postconditions: Engineer granted time-bound session",
                    "Dependencies: ACT-402, ACT-403",
                    "",
                    "Step 5 [ACT-405] Execute Automated TTL Lease Expiry and Access Revocation | Role: IAM Lease Revocation Daemon (Cybersecurity Systems) | Type: automated",
                    "Description: Automatically revoke ephemeral credentials upon TTL expiration, rotate vault secrets, and dispatch audit log digest.",
                    "Input: Ephemeral Session Token, Session Audit Stream | Output: Revocation Confirmation & Audit Digest",
                    "Preconditions: Session TTL expired or change ticket closed | Postconditions: Zero standing privileges confirmed",
                    "Dependencies: ACT-404",
                    "",
                    "Step 6 [ACT-406] Investigate Segregation of Duties Breach or Unauthorized Request | Role: SOC Incident Commander (Security Operations Center) | Type: escalation",
                    "Description: Investigate policy violation or unmanaged device attempt and file security incident report.",
                    "Input: PAM Access Request Record, Entitlement Risk Decision | Output: SOC Security Incident Report",
                    "Preconditions: SoD violation, unmanaged device, or rejected Tier-0 request | Postconditions: User account audited and incident logged",
                    "Dependencies: ACT-402",
                ],
            },
        ],
    },
    # EDGE CASE 1: Ambiguous Wording & Missing Information (Missing Actor, Vague Thresholds)
    {
        "case_id": "EDGE-001",
        "title": "Ad-Hoc Corporate Expense Reimbursement Policy (Ambiguous Draft)",
        "document_code": "SOP-EXP-EDGE1",
        "department": "General Administration",
        "effective_date": "2026-03-01",
        "owner_role": "Office Administrator",
        "base_filename": "edge_01_ambiguous_missing_actor",
        "formats": ["txt"],
        "category": "Edge Case - Ambiguous & Missing Actor",
        "is_edge_case": True,
        "sections": [
            {
                "section": "Section 1.0 - Informal Expense Instructions",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-EXP-EDGE1 | DEPARTMENT: General Administration",
                    "TITLE: Ad-Hoc Corporate Expense Reimbursement Policy (Ambiguous Draft)",
                    "OWNER: Office Administrator | EFFECTIVE DATE: 2026-03-01",
                    "",
                    "Step 1 [ACT-801] Upload Travel Receipt Scan | Role: Employee Submitter (General Operations) | Type: manual",
                    "Description: Upload meal or hotel receipt image into the shared expense folder.",
                    "Input: Receipt Image | Output: Uploaded Receipt File",
                    "Preconditions: Travel completed | Postconditions: File saved in folder",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-802] Verify Expense Receipt Completeness | Role: UNASSIGNED (General Administration) | Type: manual",
                    "Description: The receipt should be checked if appropriate to make sure the numbers look reasonable, maybe by someone in the back office.",
                    "Input: Uploaded Receipt File | Output: Checked Receipt Note",
                    "Preconditions: Receipt uploaded | Postconditions: Someone looked at it",
                    "Dependencies: ACT-801",
                    "",
                    "Step 3 [ACT-803] Evaluate If Expense Amount Is Large | Role: UNASSIGNED (General Administration) | Type: decision",
                    "Description: If the amount seems fairly large or unusual, someone should probably approve it as needed before paying.",
                    "Input: Checked Receipt Note | Output: Informal Decision",
                    "Preconditions: Receipt checked | Postconditions: Routed somewhere",
                    "Dependencies: ACT-802",
                    "DECISION RULE [COND-801]: IF amount is large or unusual THEN route to ACT-804.",
                    "",
                    "Step 4 [ACT-804] Reimburse Employee Bank Account | Role: Payroll Clerk (Finance) | Type: manual",
                    "Description: Send reimbursement transfer to the employee bank account whenever convenient.",
                    "Input: Informal Decision | Output: Bank Transfer Confirmation",
                    "Preconditions: Decision completed | Postconditions: Employee paid",
                    "Dependencies: ACT-803",
                ],
            }
        ],
    },
    # EDGE CASE 2: Contradictory Instructions & Cyclic Dependencies
    {
        "case_id": "EDGE-002",
        "title": "Vendor NDA and Master Agreement Sign-Off (Contradictory Draft)",
        "document_code": "SOP-LEG-EDGE2",
        "department": "Legal & Finance",
        "effective_date": "2026-03-05",
        "owner_role": "General Counsel",
        "base_filename": "edge_02_contradictory_instructions",
        "formats": ["txt"],
        "category": "Edge Case - Contradictory Rules",
        "is_edge_case": True,
        "sections": [
            {
                "section": "Section 1.0 - Conflicting Sign-Off Rules",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-LEG-EDGE2 | DEPARTMENT: Legal & Finance",
                    "TITLE: Vendor NDA and Master Agreement Sign-Off (Contradictory Draft)",
                    "OWNER: General Counsel | EFFECTIVE DATE: 2026-03-05",
                    "",
                    "Step 1 [ACT-901] Draft Master Services Agreement | Role: Commercial Contracts Manager (Legal) | Type: manual",
                    "Description: Prepare initial MSA draft from enterprise template.",
                    "Input: Deal Term Sheet | Output: Draft MSA Document",
                    "Preconditions: Deal term sheet received | Postconditions: MSA ready for review",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-902] Legal Counsel Final Sign-Off | Role: Senior Legal Counsel (Legal) | Type: approval",
                    "Description: MANDATORY RULE: Legal Counsel must never sign off until Finance Director approval (ACT-903) is 100% completed first.",
                    "Input: Draft MSA Document | Output: Legal Sign-Off Stamp",
                    "Preconditions: Finance Director approval ACT-903 must be completed prior to Legal sign-off | Postconditions: Legal stamp applied",
                    "Dependencies: ACT-901, ACT-903",
                    "APPROVAL GATE [APR-901]: Approver: Senior Legal Counsel | Criteria: Requires prior Finance Director sign-off ACT-903 | SLA: 24 hours | Rejection Target: ACT-901.",
                    "",
                    "Step 3 [ACT-903] Finance Director Commercial Approval | Role: Finance Director (Finance) | Type: approval",
                    "Description: CONTRADICTORY RULE: Finance Director must strictly wait until Legal Counsel Final Sign-Off (ACT-902) is completed before reviewing.",
                    "Input: Legal Sign-Off Stamp | Output: Finance Approval Stamp",
                    "Preconditions: Legal Counsel sign-off ACT-902 must be completed before Finance review | Postconditions: Finance stamp applied",
                    "Dependencies: ACT-902",
                    "APPROVAL GATE [APR-902]: Approver: Finance Director | Criteria: Requires prior Legal Counsel sign-off ACT-902 | SLA: 24 hours | Rejection Target: ACT-901.",
                ],
            }
        ],
    },
    # EDGE CASE 3: Multi-Branch Workflow
    {
        "case_id": "EDGE-003",
        "title": "Global Treasury Multi-Tier Wire Transfer & FX Hedging SOP",
        "document_code": "SOP-TRS-EDGE3",
        "department": "Global Treasury",
        "effective_date": "2026-03-10",
        "owner_role": "Group Treasurer",
        "base_filename": "edge_03_complex_multibranch",
        "formats": ["txt"],
        "category": "Edge Case - Multi-Branch Workflow",
        "is_edge_case": True,
        "sections": [
            {
                "section": "Section 1.0 - Multi-Branch Treasury Execution",
                "page": 1,
                "lines": [
                    "DOCUMENT CODE: SOP-TRS-EDGE3 | DEPARTMENT: Global Treasury",
                    "TITLE: Global Treasury Multi-Tier Wire Transfer & FX Hedging SOP",
                    "OWNER: Group Treasurer | EFFECTIVE DATE: 2026-03-10",
                    "",
                    "Step 1 [ACT-701] Initiate International Wire Request | Role: Treasury Analyst (Global Treasury) | Type: manual",
                    "Description: Enter beneficiary SWIFT BIC, currency pair, and wire amount in Treasury Management System.",
                    "Input: Approved Settlement Instruction | Output: Wire Transfer Ticket",
                    "Preconditions: Beneficiary IBAN verified | Postconditions: Wire ticket created",
                    "Dependencies: None",
                    "",
                    "Step 2 [ACT-702] Evaluate Currency Exposure and FX Hedge Requirement | Role: FX Desk Manager (Global Treasury) | Type: decision",
                    "Description: Check if wire is cross-currency (non-USD) requiring forward FX contract execution.",
                    "Input: Wire Transfer Ticket | Output: Currency Routing Signal",
                    "Preconditions: Wire ticket created | Postconditions: Routed to FX spot/forward execution or direct liquidity check",
                    "Dependencies: ACT-701",
                    "DECISION RULE [COND-701]: IF currency != 'USD' THEN route to ACT-703 ELSE route to ACT-704.",
                    "",
                    "Step 3 [ACT-703] Execute Spot or Forward FX Conversion | Role: FX Trading Desk Bot (Treasury Systems) | Type: automated",
                    "Description: Lock real-time FX conversion rate via institutional liquidity provider.",
                    "Input: Currency Routing Signal | Output: FX Trade Confirmation",
                    "Preconditions: Non-USD wire confirmed | Postconditions: Settlement amount locked",
                    "Dependencies: ACT-702",
                    "",
                    "Step 4 [ACT-704] Evaluate Wire Notional Tier for Dual Treasury Sign-Off | Role: Treasury Operations Lead (Global Treasury) | Type: decision",
                    "Description: Determine whether USD-equivalent notional value exceeds $250,000 board threshold.",
                    "Input: Wire Transfer Ticket, FX Trade Confirmation | Output: Authorization Tier Signal",
                    "Preconditions: Currency conversion finalized | Postconditions: Routed to CFO dual sign-off or automated SWIFT release",
                    "Dependencies: ACT-702, ACT-703",
                    "DECISION RULE [COND-702]: IF notional_usd >= $250,000 THEN route to ACT-705 ELSE route to ACT-706.",
                    "",
                    "Step 5 [ACT-705] Approve High-Value Institutional Wire Release | Role: Chief Financial Officer (Executive Finance) | Type: approval",
                    "Description: Hardware-token sign-off for treasury wires >= $250,000.",
                    "Input: Authorization Tier Signal | Output: Hardware Token Signature",
                    "Preconditions: Wire value >= $250,000 | Postconditions: Dual signature recorded on SWIFT message",
                    "Dependencies: ACT-704",
                    "APPROVAL GATE [APR-701]: Approver: Chief Financial Officer | Criteria: Liquidity reserve check and dual token verification for wires >= $250,000 | SLA: 4 hours | Rejection Target: ACT-701.",
                    "",
                    "Step 6 [ACT-706] Transmit SWIFT MT103 Payment and Reconcile Nostro Account | Role: SWIFT Gateway Service (Treasury Systems) | Type: automated",
                    "Description: Broadcast SWIFT MT103 message and reconcile settlement confirmation against Nostro account statement.",
                    "Input: Wire Transfer Ticket, Hardware Token Signature | Output: SWIFT UETR Settlement Receipt",
                    "Preconditions: All required approvals and FX locks complete | Postconditions: Wire settled and ledger reconciled",
                    "Dependencies: ACT-704, ACT-705",
                ],
            }
        ],
    },
]


def write_txt_sop(filepath: Path, spec: Dict[str, Any]) -> None:
    lines: List[str] = []
    for sec in spec["sections"]:
        lines.append(f"=== {sec['section']} (Page {sec['page']}) ===")
        lines.extend(sec["lines"])
        lines.append("")
    filepath.write_text("\n".join(lines), encoding="utf-8")


def write_pdf_sop(filepath: Path, spec: Dict[str, Any]) -> None:
    pages_map: Dict[int, List[str]] = {}
    for sec in spec["sections"]:
        p = int(sec["page"])
        pages_map.setdefault(p, [])
        pages_map[p].append(f"=== {sec['section']} ===")
        pages_map[p].extend(sec["lines"])
        pages_map[p].append("")
    ordered_pages = [pages_map[k] for k in sorted(pages_map.keys())]
    create_multi_page_pdf(filepath, ordered_pages)


def write_docx_sop(filepath: Path, spec: Dict[str, Any]) -> None:
    doc = docx.Document()
    doc.add_heading(spec["title"], level=0)
    meta_p = doc.add_paragraph(
        f"DOCUMENT CODE: {spec['document_code']} | DEPARTMENT: {spec['department']} | "
        f"OWNER: {spec['owner_role']} | EFFECTIVE DATE: {spec['effective_date']}"
    )
    for sec in spec["sections"]:
        doc.add_heading(sec["section"], level=1)
        for line in sec["lines"]:
            if line.strip():
                doc.add_paragraph(line)

    # Also add a summary RACI / Step Table in the DOCX to verify table extraction
    table = doc.add_table(rows=1, cols=4)
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Activity ID"
    hdr_cells[1].text = "Activity Name"
    hdr_cells[2].text = "Responsible Role"
    hdr_cells[3].text = "Activity Type"

    for sec in spec["sections"]:
        for line in sec["lines"]:
            if line.startswith("Step ") and "[" in line and "|" in line:
                parts = [p.strip() for p in line.split("|")]
                act_id = line.split("[")[1].split("]")[0]
                act_name = parts[0].split("]", 1)[1].strip()
                role = parts[1].replace("Role:", "").strip() if len(parts) > 1 else ""
                atype = parts[2].replace("Type:", "").strip() if len(parts) > 2 else "manual"
                row_cells = table.add_row().cells
                row_cells[0].text = act_id
                row_cells[1].text = act_name
                row_cells[2].text = role
                row_cells[3].text = atype

    doc.save(str(filepath))


def write_xlsx_sop(filepath: Path, spec: Dict[str, Any]) -> None:
    wb = openpyxl.Workbook()
    ws_meta = wb.active
    ws_meta.title = "SOP_Overview"
    ws_meta.append(["Field", "Value"])
    ws_meta.append(["DOCUMENT CODE", spec["document_code"]])
    ws_meta.append(["TITLE", spec["title"]])
    ws_meta.append(["DEPARTMENT", spec["department"]])
    ws_meta.append(["OWNER", spec["owner_role"]])
    ws_meta.append(["EFFECTIVE DATE", spec["effective_date"]])

    ws_steps = wb.create_sheet(title="Process_Activities")
    ws_steps.append([
        "Section",
        "Instruction_Line",
    ])
    for sec in spec["sections"]:
        for line in sec["lines"]:
            if line.strip():
                ws_steps.append([sec["section"], line])

    wb.save(str(filepath))


def build_ground_truth_for_spec(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Builds the ground-truth expected model for precision/recall/F1 and accuracy benchmarking."""
    expected_activities = []
    expected_actors = set()
    expected_dependencies = []
    expected_conditions = []
    expected_approvals = []
    expected_exceptions = []

    current_act: Dict[str, Any] = {}
    for sec in spec["sections"]:
        sec_name = sec["section"]
        for line in sec["lines"]:
            line_s = line.strip()
            if line_s.startswith("Step ") and "[" in line_s and "]" in line_s:
                if current_act:
                    expected_activities.append(current_act)
                parts = [p.strip() for p in line_s.split("|")]
                act_id = line_s.split("[")[1].split("]")[0].strip()
                act_name = parts[0].split("]", 1)[1].strip()
                role_raw = parts[1].replace("Role:", "").strip() if len(parts) > 1 else "UNASSIGNED"
                role_name = role_raw.split("(")[0].strip()
                dept = role_raw.split("(")[1].replace(")", "").strip() if "(" in role_raw else spec["department"]
                atype = parts[2].replace("Type:", "").strip().lower() if len(parts) > 2 else "manual"
                current_act = {
                    "activity_id": act_id,
                    "activity_name": act_name,
                    "responsible_role": role_name,
                    "department": dept,
                    "activity_type": atype,
                    "section": sec_name,
                    "dependencies": [],
                }
                if role_name != "UNASSIGNED":
                    expected_actors.add(role_name)
            elif line_s.startswith("Dependencies:") and current_act:
                dep_raw = line_s.replace("Dependencies:", "").strip()
                if dep_raw and dep_raw.lower() != "none":
                    deps = [d.strip() for d in dep_raw.split(",") if d.strip()]
                    current_act["dependencies"] = deps
                    for d in deps:
                        expected_dependencies.append({"source": d, "target": current_act["activity_id"]})
            elif line_s.startswith("DECISION RULE ["):
                cid = line_s.split("[")[1].split("]")[0]
                rule_text = line_s.split(":", 1)[1].strip()
                expected_conditions.append({
                    "condition_id": cid,
                    "decision_activity_id": current_act.get("activity_id", ""),
                    "rule_expression": rule_text,
                })
            elif line_s.startswith("APPROVAL GATE ["):
                aid = line_s.split("[")[1].split("]")[0]
                expected_approvals.append({
                    "approval_id": aid,
                    "activity_id": current_act.get("activity_id", ""),
                })
            elif line_s.startswith("EXCEPTION RULE ["):
                eid = line_s.split("[")[1].split("]")[0]
                expected_exceptions.append({
                    "exception_id": eid,
                    "source_activity_id": current_act.get("activity_id", ""),
                })

    if current_act:
        expected_activities.append(current_act)

    return {
        "case_id": spec["case_id"],
        "title": spec["title"],
        "document_code": spec["document_code"],
        "category": spec["category"],
        "base_filename": spec["base_filename"],
        "primary_format": spec["formats"][0],
        "is_edge_case": spec.get("is_edge_case", False),
        "expected_activities": expected_activities,
        "expected_actors": sorted(list(expected_actors)),
        "expected_dependencies": expected_dependencies,
        "expected_conditions": expected_conditions,
        "expected_approvals": expected_approvals,
        "expected_exceptions": expected_exceptions,
    }


def generate_all_samples() -> List[Dict[str, Any]]:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)
    generated_manifest: List[Dict[str, Any]] = []

    for spec in SOP_SPECS:
        base = spec["base_filename"]
        for fmt in spec["formats"]:
            out_path = SAMPLE_DIR / f"{base}.{fmt}"
            if fmt == "txt":
                write_txt_sop(out_path, spec)
            elif fmt == "pdf":
                write_pdf_sop(out_path, spec)
            elif fmt == "docx":
                write_docx_sop(out_path, spec)
            elif fmt == "xlsx":
                write_xlsx_sop(out_path, spec)
            generated_manifest.append({"case_id": spec["case_id"], "file": out_path.name, "format": fmt})

        gt = build_ground_truth_for_spec(spec)
        gt_path = GROUND_TRUTH_DIR / f"{base}_ground_truth.json"
        gt_path.write_text(json.dumps(gt, indent=2), encoding="utf-8")

    return generated_manifest


if __name__ == "__main__":
    manifest = generate_all_samples()
    print(f"Generated {len(manifest)} sample SOP files and ground-truth labels.")
