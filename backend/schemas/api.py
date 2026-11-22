"""
REST API Request and Response Schemas (Pydantic v2).
"""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.schemas.document import DocumentFileTypeEnum, DocumentMetadataSchema, ParsedDocumentStructure
from backend.schemas.process import (
    ActivityReviewDecisionEnum,
    FieldLevelValidationError,
    ProcessActivitySchema,
    ProcessActorSchema,
    BusinessConditionSchema,
    ActivityDependencySchema,
    ProcessIOSchema,
    ProcessExceptionSchema,
    ApprovalGateSchema,
    ProcessModelSchema,
    ReviewStatusEnum,
    ValidationStatusEnum,
)


class HealthResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = "healthy"
    service: str
    version: str
    llm_provider: str
    database_connected: bool
    sample_documents_loaded: int
    timestamp: datetime


class DocumentSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    file_type: DocumentFileTypeEnum
    file_size_bytes: int
    checksum_sha256: str
    metadata: DocumentMetadataSchema
    created_at: datetime


class DocumentDetailResponse(DocumentSummaryResponse):
    model_config = ConfigDict(extra="forbid")

    raw_text: str
    parsed_structure: ParsedDocumentStructure


class ProcessExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., min_length=1, description="Uploaded document ID to extract process model from")
    custom_process_name: Optional[str] = Field(default=None, description="Optional override for process title")
    force_reextract: bool = Field(default=False, description="Force fresh multi-agent run even if process exists")


class ProcessSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: str
    process_name: str
    document_id: str
    document_filename: str
    version: int
    activity_count: int
    actor_count: int
    condition_count: int
    approval_count: int
    exception_count: int
    validation_status: ValidationStatusEnum
    review_status: ReviewStatusEnum
    overall_confidence: float
    needs_human_review: bool
    validation_error_count: int
    created_at: datetime
    updated_at: datetime


class ProcessUpdateRequest(BaseModel):
    """PUT /api/processes/{id} payload to edit activities, actors, dependencies, conditions, and comments."""
    model_config = ConfigDict(extra="forbid")

    process_name: Optional[str] = None
    activities: Optional[List[ProcessActivitySchema]] = None
    actors: Optional[List[ProcessActorSchema]] = None
    conditions: Optional[List[BusinessConditionSchema]] = None
    dependencies: Optional[List[ActivityDependencySchema]] = None
    inputs: Optional[List[ProcessIOSchema]] = None
    outputs: Optional[List[ProcessIOSchema]] = None
    exceptions: Optional[List[ProcessExceptionSchema]] = None
    approvals: Optional[List[ApprovalGateSchema]] = None
    reviewer_name: str = Field(default="Senior Process Analyst")
    change_summary: str = Field(default="Updated process model elements via Reviewer Workspace")
    comment: Optional[str] = None


class ActivityReviewRequest(BaseModel):
    """Approve or reject an individual activity within a process model."""
    model_config = ConfigDict(extra="forbid")

    decision: ActivityReviewDecisionEnum
    reviewer_name: str = Field(default="Senior Process Analyst", min_length=1)
    reviewer_note: Optional[str] = None


class ProcessValidationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: str
    version: int
    validation_status: ValidationStatusEnum
    is_schema_valid: bool
    error_count: int
    warning_count: int
    ambiguity_count: int
    validation_errors: List[FieldLevelValidationError]


class ProcessApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_name: str = Field(..., min_length=2, description="Human reviewer approving the process model")
    comment: str = Field(default="Verified all activities, citations, and branching rules against source SOP.")
    approve_all_pending_activities: bool = Field(
        default=True,
        description="Explicitly mark remaining pending activities as approved by this reviewer during sign-off",
    )


class ProcessRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviewer_name: str = Field(..., min_length=2, description="Human reviewer rejecting the process model")
    reason: str = Field(..., min_length=5, description="Mandatory explanation for rejecting the extracted model")


class ProcessVersionItemSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int
    validation_status: ValidationStatusEnum
    review_status: ReviewStatusEnum
    overall_confidence: float
    change_summary: str
    changed_by: str
    created_at: datetime
    process_model: ProcessModelSchema


class ProcessVersionHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_id: str
    current_version: int
    versions: List[ProcessVersionItemSchema]


class ProcessImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    process_model: ProcessModelSchema
    imported_by: str = Field(default="Process Architect")
