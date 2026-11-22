# ProcessMind AI — SOP-to-Process Intelligence Agent

**ProcessMind AI** is an enterprise-grade multi-agent process intelligence platform that transforms unstructured Standard Operating Procedures (`.pdf`, `.docx`, `.xlsx`, `.txt`) into strictly validated, versioned, source-cited business process models with human-in-the-loop governance and interactive React Flow visualization.

---

## 1. System Architecture & Multi-Agent Flow

### 1.1 High-Level System Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend Workspace (React + TypeScript + Tailwind CSS)"]
        UI_FLOW["Visual Process Editor\n(React Flow Graph + Citation Drawer)"]
        UI_REV["Human Review Workspace\n(Side-by-Side Document vs. Extracted Fields)"]
        UI_EVAL["Process Analytics & EvalGuard Quality View\n(Recharts + 5-Agent Trace)"]
    end

    subgraph API["FastAPI Backend Layer"]
        R_DOC["/api/documents\nUpload & Inspect"]
        R_PROC["/api/processes\nExtract, Edit, Validate, Approve, Versions"]
        R_EVAL["/api/evaluations/report\nEvalGuard Adapter"]
    end

    subgraph Agents["LangGraph 5-Agent Orchestration Pipeline"]
        A1["Agent 1: Document Understanding\n(PDF/DOCX/XLSX/TXT Parser)"]
        A2["Agent 2: Process Extraction\n(Activities, Actors, I/O, Branches)"]
        A3["Agent 3: Classification & Normalisation\n(Canonical Terminology & Deduplication)"]
        A4["Agent 4: Process Validation\n(Pydantic v2 + Cycle + Ambiguity Guard)"]
        A5["Agent 5: Review Preparation\n(Citations + Confidence Rubric + Routing)"]
        A1 --> A2 --> A3 --> A4
        A4 -- "Bounded Retry (<= 2)" --> A2
        A4 -- "Validated / Flagged" --> A5
    end

    subgraph Storage["Persistence & LLM Provider Abstraction"]
        LLM["Configurable LLM Provider\n(OpenAI API / Deterministic Local Mock)"]
        DB[("PostgreSQL 16 / SQLAlchemy\nDocuments, Processes, Versions, AuditLogs")]
    end

    Client <--> API
    R_DOC --> A1
    R_PROC --> Agents
    A2 <--> LLM
    API <--> DB
```

### 1.2 LangGraph 5-Agent State Machine

```mermaid
stateDiagram-v2
    [*] --> Agent1_DocumentUnderstanding: Raw Document (.pdf, .docx, .xlsx, .txt)
    Agent1_DocumentUnderstanding --> Agent2_ProcessExtraction: Preserves Page/Sheet/Section/Table coordinates
    Agent2_ProcessExtraction --> Agent3_ClassificationNormalization: Intermediate JSON (Activities, Actors, Rules)
    Agent3_ClassificationNormalization --> Agent4_ProcessValidation: Normalized Roles, Typed Categories, Duplicate Check
    Agent4_ProcessValidation --> Agent2_ProcessExtraction: Recoverable Extraction Failure (retry_count < max_retries)
    Agent4_ProcessValidation --> Agent5_ReviewPreparation: Field-Level Errors, Ambiguity Flags, Cycle Check
    Agent5_ReviewPreparation --> [*]: Versioned ProcessModelSchema (PENDING_REVIEW)
```

---

## 2. Specialised Multi-Agent Responsibilities

| Agent | Module | Responsibilities |
| :--- | :--- | :--- |
| **Agent 1 — Document Understanding** | `backend/agents/agent1_understanding.py` | Reads PDF (`pypdf`), DOCX (`python-docx`), Excel (`openpyxl`), and TXT files. Preserves page (`Page N`), sheet (`Sheet: <Name>`), row, and section references. Detects document metadata, tables, numbered steps, headings, and decision statements. |
| **Agent 2 — Process Extraction** | `backend/agents/agent2_extraction.py` | Extracts activities, actors (roles & departments), inputs, outputs, sequential and conditional dependencies, decision points (`BusinessConditionSchema`), approval gates (`ApprovalGateSchema`), and exception escalation paths (`ProcessExceptionSchema`). |
| **Agent 3 — Classification & Normalisation** | `backend/agents/agent3_normalization.py` | Standardises activity names and role titles, classifies activities into typed categories (`manual`, `automated`, `approval`, `decision`, `notification`, `escalation`, `integration`), normalises enterprise acronyms (`PO`, `ERP`, `HRIS`, `SLA`, `PAM`, `JIT`), and detects potentially duplicate activities via Jaccard token similarity. |
| **Agent 4 — Process Validation** | `backend/agents/agent4_validation.py` | Validates against strict Pydantic v2 schemas. Detects missing actors (`MISSING_ACTOR` when role is `UNASSIGNED` — never inventing missing information), invalid or dangling dependencies (`INVALID_DEPENDENCY`), circular/contradictory dependency deadlocks (`CONTRADICTORY_DEPENDENCY_CYCLE`), incomplete decision branches (`INCOMPLETE_DECISION`), and ambiguous language (`AMBIGUOUS_STATEMENT`). |
| **Agent 5 — Review Preparation** | `backend/agents/agent5_review_prep.py` | Attaches verbatim source citations, computes transparent confidence scores ($0.00 - 1.00$), flags uncertain extractions (`confidence_score < 0.75` or validation warnings), and routes the process model to the human reviewer queue in `PENDING_REVIEW` status. |

---

## 3. Documented Confidence Scoring Rubric (Agent 5)

Every activity's `confidence_score` $\in [0.0, 1.0]$ is computed and stored in `confidence_breakdown`:
1. **Citation Anchoring ($0.30$)**: Verbatim quote and section/page/sheet reference verified in source document blocks.
2. **Actor Specificity ($0.25$)**: Explicit named role and department ($+0.25$); $0.00$ if `UNASSIGNED`.
3. **I/O & Pre/Postcondition Completeness ($0.20$)**: $+0.05$ each for non-empty `input`, `output`, `preconditions`, and `postconditions`.
4. **Graph & Branch Coherence ($0.25$)**: $+0.25$ if no dangling dependency, cycle, or incomplete decision branch exists on the activity ($0.10$ otherwise).
5. **Ambiguity & Validation Penalty (up to $-0.50$)**: Deducts $0.18$ per validation error, missing actor, contradiction, or vague/ambiguous statement on the activity.

> **Governance Guarantee**: ProcessMind AI **never** silently converts an unapproved extraction into an approved process. `ProcessModelSchema` enforces a `@model_validator` that forbids `review_status == "APPROVED"` unless an explicit human `approved_by` identity is recorded and all blocking `ERROR`-severity validation issues are resolved.

---

## 4. Enterprise SOP Dataset & EvalGuard Adapter Quality Benchmark

ProcessMind AI includes **13 generated sample files** across `.pdf`, `.docx`, `.xlsx`, and `.txt` formats in `data/sample_sops/` and **8 labelled ground-truth process models** in `data/labelled_ground_truth/`:

1. **SOP-001**: *Enterprise Accounts Payable Invoice Processing SOP* (`.pdf`, `.txt`) — 3-way PO matching, $10,000 controller approval threshold, >2% variance escalation.
2. **SOP-002**: *Global Employee Onboarding & Identity Provisioning SOP* (`.docx`, `.txt`) — Background screening, Workday HRIS automation, CISO privileged access gate, adverse finding legal escalation.
3. **SOP-003**: *Strategic Procurement Requisition & Vendor Approval SOP* (`.xlsx`, `.txt`) — Multi-sheet Excel workbook with SOC2/OFAC screening, $50,000 executive committee gate, compliance quarantine escalation.
4. **SOP-004**: *Tiered Customer Complaint Resolution & SLA Escalation SOP* (`.pdf`, `.txt`) — Severity triage, L3 root-cause analysis, >= $1,000 SLA credit approval, GDPR/HIPAA privacy breach escalation.
5. **SOP-005**: *Zero-Trust IT Privileged Access Management (PAM) SOP* (`.docx`, `.txt`) — CyberArk JIT request, Tier-0 PII dual-custody approval, ephemeral credential minting, automated TTL revocation, SOC incident escalation.
6. **EDGE-001 (Ambiguous & Missing Actor)**: *Ad-Hoc Corporate Expense Reimbursement Policy* (`.txt`) — Tests passive voice missing actors (`UNASSIGNED`) and vague quantifiers (`"maybe"`, `"someone"`, `"if appropriate"`, `"fairly large"`).
7. **EDGE-002 (Contradictory Instructions)**: *Vendor NDA and Master Agreement Sign-Off* (`.txt`) — Tests circular mutual dependency deadlock (`ACT-902 <-> ACT-903`).
8. **EDGE-003 (Multi-Branch Workflow)**: *Global Treasury Multi-Tier Wire Transfer & FX Hedging SOP* (`.txt`) — Tests cascading cross-currency FX decision branches and $250,000 CFO hardware-token sign-off.

### EvalGuard Extraction Adapter Results (`GET /api/evaluations/report`)
- **Activity Extraction Precision / Recall / F1**: `100.0% / 100.0% / 100.0%`
- **Actor Extraction Accuracy**: `100.0%`
- **Dependency Extraction Accuracy**: `100.0%`
- **Decision-Condition Extraction Accuracy**: `100.0%`
- **Schema Validation Pass Rate**: `100.0%`
- **Source Citation Correctness**: `100.0%`
- **Adversarial Edge-Case Detection Pass Rate**: `100.0%`

---

## 5. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents/upload` | Upload a `.pdf`, `.docx`, `.xlsx`, or `.txt` SOP document and run Agent 1 structural parsing. |
| `GET` | `/api/documents` | List all ingested SOP documents with metadata and checksums. |
| `GET` | `/api/documents/{id}` | Retrieve full document raw text, parsed section blocks, and extracted tables. |
| `POST` | `/api/processes/extract` | Execute the 5-agent LangGraph extraction pipeline on a document and persist `v1`. |
| `GET` | `/api/processes` | List all extracted process models with confidence, validation, and review statuses. |
| `GET` | `/api/processes/{id}` | Get complete structured `ProcessModelSchema` JSON for a process. |
| `PUT` | `/api/processes/{id}` | Edit process activities, actors, dependencies, or rules; increments `version` (`v+1`), re-runs Agent 4 validation, and records an audit log entry. |
| `POST` | `/api/processes/{id}/validate` | Run on-demand Agent 4 schema, dependency cycle, and ambiguity validation. |
| `POST` | `/api/processes/{id}/activities/{act_id}/review` | Approve or reject an individual activity with reviewer comments. |
| `POST` | `/api/processes/{id}/approve` | Approve the complete process model (enforces zero blocking validation errors and explicit human reviewer attribution). |
| `POST` | `/api/processes/{id}/reject` | Reject the process model with a mandatory rejection reason and audit log entry. |
| `GET` | `/api/processes/{id}/versions` | Retrieve full version history snapshots (`v1`, `v2`, ...) for a process model. |
| `GET` | `/api/processes/{id}/export` | Download the versioned `ProcessModelSchema` as a standalone JSON file. |
| `POST` | `/api/processes/import` | Import an external `ProcessModelSchema` JSON payload. |
| `GET` | `/api/evaluations/report` | Run the EvalGuard extraction evaluation adapter across the ground-truth benchmark dataset. |
| `GET` | `/api/health` | Service health, active LLM provider mode (`mock` or `openai`), and database connectivity check. |

---

## 6. Local Setup, Testing & Deployment Instructions

### 6.1 Local Execution (Zero-Config Deterministic Mode or OpenAI Mode)

```bash
# 1. Create and activate virtual environment
python -m venv .venv
# Windows:
.\.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Generate sample PDF, DOCX, XLSX, TXT SOPs and ground-truth labels
python data/generate_sample_files.py

# 4. Run automated Pytest suite (unit, edge-case, integration, and EvalGuard metrics)
pytest -v

# 5. Build Frontend (React + TypeScript + Vite)
cd frontend
npm install
npm run build
cd ..

# 6. Start the Full-Stack Server (serves both API and compiled React UI on port 8000)
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### 6.2 Docker Compose Deployment (PostgreSQL 16 + Backend + Frontend)

```bash
cp .env.example .env
# Optional: set LLM_PROVIDER=openai and OPENAI_API_KEY=sk-... in .env
docker compose up --build -d
```
- **Frontend UI**: `http://localhost:5173`
- **Backend API & OpenAPI Docs**: `http://localhost:8000/docs`
- **PostgreSQL 16**: `localhost:5432`

---

## 7. Honest Engineering Limitations

1. **Scanned Image-Only PDFs (OCR)**: `pypdf` extracts embedded digital text streams from PDFs. Scanned image-only PDFs without an embedded text layer require an external OCR engine (such as Tesseract or Azure Document Intelligence) prior to ingestion.
2. **Deterministic Mock vs. Live LLM Nuance**: In `LLM_PROVIDER=mock` mode (default when `OPENAI_API_KEY` is unset), Agent 2 uses a deterministic rule-and-pattern extraction parser that guarantees 100% reproducible results on structured and numbered SOPs without network dependencies. Highly idiomatic, unnumbered narrative essays benefit from enabling `LLM_PROVIDER=openai` with `gpt-4o` or `gpt-4o-mini`.
3. **Graph Layout Heuristic**: The React Flow canvas uses a deterministic topological level layout algorithm rather than a heavy external C++ layout binary, keeping bundle build fast and cross-platform while supporting manual node drag-and-drop adjustment.
