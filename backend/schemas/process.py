"""
Strict, Versioned Pydantic v2 Schemas for ProcessMind AI Structured Process Models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class ActivityTypeEnum(str, Enum):
    MANUAL = "manual"
    AUTOMATED = "automated"
    APPROVAL = "approval"
    DECISION = "decision"
    NOTIFICATION = "notification"
    ESCALATION = "escalation"
    INTEGRATION = "integration"


class ValidationStatusEnum(str, Enum):
    VALID = "VALID"
    VALID_WITH_WARNINGS = "VALID_WITH_WARNINGS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    INVALID = "INVALID"


class ReviewStatusEnum(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ActivityReviewDecisionEnum(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


class DependencyTypeEnum(str, Enum):
    SEQUENTIAL = "sequential"
    CONDITIONAL_TRUE = "conditional_true"
    CONDITIONAL_FALSE = "conditional_false"
    APPROVAL_GATED = "approval_gated"
    EXCEPTION_ESCALATION = "exception_escalation"
    PARALLEL_JOIN = "parallel_join"


class ValidationSeverityEnum(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    AMBIGUITY = "AMBIGUITY"


class SourceReferenceSchema(BaseModel):
    """Granular source citation linking an extracted element to its exact document location."""
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., min_length=1)
    section: str = Field(..., min_length=1, description="Section identifier, e.g. 'Section 4.1'")
    page_or_sheet: str = Field(..., min_length=1, description="Page number or Excel sheet name")
    line_or_row: str = Field(default="Line 1", description="Line number or table row reference")
    exact_quote: str = Field(..., min_length=1, description="Verbatim excerpt from source document")
    block_id: Optional[str] = Field(default=None, description="Reference to DocumentSectionBlock ID")


class FieldLevelValidationError(BaseModel):
    """Structured field-level validation or ambiguity error returned by Agent 4."""
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(..., description="e.g. MISSING_ACTOR, INVALID_DEPENDENCY, INCOMPLETE_DECISION, AMBIGUOUS_STATEMENT, CONTRADICTORY_RULE")
    severity: ValidationSeverityEnum
    field_path: str = Field(..., description="JSON path to offending field, e.g. 'activities[2].responsible_role'")
    activity_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    suggested_remediation: Optional[str] = None
    source_quote: Optional[str] = None


class ConfidenceBreakdownSchema(BaseModel):
    """Documented scoring rule components computed by Agent 5."""
    model_config = ConfigDict(extra="forbid")

    citation_anchoring_score: float = Field(default=0.30, ge=0.0, le=0.30)
    actor_specificity_score: float = Field(default=0.25, ge=0.0, le=0.25)
    io_completeness_score: float = Field(default=0.20, ge=0.0, le=0.20)
    graph_coherence_score: float = Field(default=0.25, ge=0.0, le=0.25)
    ambiguity_penalty: float = Field(default=0.0, ge=0.0, le=0.50)
    final_score: float = Field(..., ge=0.0, le=1.0)
    scoring_rationale: str = Field(..., min_length=1)


class ProcessActivitySchema(BaseModel):
    """
    Strict schema for every extracted process activity.
    Contains all 12 mandatory fields plus governance, field-level citations, and review metadata.
    """
    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(..., min_length=1, pattern=r"^[A-Za-z0-9_-]+$")
    activity_name: str = Field(..., min_length=2)
    description: str = Field(..., min_length=3)
    activity_type: ActivityTypeEnum
    responsible_role: str = Field(..., min_length=1)
    department: str = Field(default="General Operations")
    input: List[str] = Field(default_factory=list)
    output: List[str] = Field(default_factory=list)
    preconditions: List[str] = Field(default_factory=list)
    postconditions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of upstream activity_ids that must complete before this activity",
    )
    source_reference: SourceReferenceSchema
    confidence_score: float = Field(..., ge=0.0, le=1.0)

    # Field-level citation mapping & human review state
    field_citations: Dict[str, str] = Field(
        default_factory=dict,
        description="Field-specific verbatim snippets, e.g. {'responsible_role': '...', 'preconditions': '...'}",
    )
    confidence_breakdown: Optional[ConfidenceBreakdownSchema] = None
    is_uncertain: bool = Field(default=False)
    uncertainty_reason: Optional[str] = None
    potential_duplicate_of: Optional[str] = None
    review_decision: ActivityReviewDecisionEnum = Field(default=ActivityReviewDecisionEnum.PENDING)
    reviewer_note: Optional[str] = None

    @field_validator("confidence_score")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(float(v), 3)


class ProcessActorSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actor_id: str = Field(..., min_length=1)
    role_name: str = Field(..., min_length=1)
    department: str = Field(default="Operations")
    is_approver: bool = Field(default=False)
    assigned_activity_ids: List[str] = Field(default_factory=list)
    source_reference: Optional[SourceReferenceSchema] = None


class BusinessConditionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    condition_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    rule_expression: str = Field(..., min_length=1, description="Logical or threshold rule, e.g. 'invoice_amount >= 5000'")
    decision_activity_id: str = Field(..., min_length=1)
    branch_when_true: Optional[str] = Field(default=None, description="Target activity_id when condition holds")
    branch_when_false: Optional[str] = Field(default=None, description="Target activity_id when condition is false")
    source_reference: SourceReferenceSchema
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)


class ActivityDependencySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dependency_id: str = Field(..., min_length=1)
    source_activity_id: str = Field(..., min_length=1)
    target_activity_id: str = Field(..., min_length=1)
    dependency_type: DependencyTypeEnum = Field(default=DependencyTypeEnum.SEQUENTIAL)
    condition_label: Optional[str] = None
    source_reference: Optional[SourceReferenceSchema] = None


class ProcessIOSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    io_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    io_type: str = Field(..., description="input | output")
    artifact_format: str = Field(default="Document / Record")
    associated_activity_id: str = Field(..., min_length=1)
    source_reference: Optional[SourceReferenceSchema] = None


class ProcessExceptionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_id: str = Field(..., min_length=1)
    exception_name: str = Field(..., min_length=1)
    trigger_condition: str = Field(..., min_length=1)
    source_activity_id: str = Field(..., min_length=1)
    escalation_role: str = Field(..., min_length=1)
    target_recovery_activity_id: Optional[str] = None
    remediation_action: str = Field(..., min_length=1)
    sla_hours: Optional[int] = None
    source_reference: SourceReferenceSchema
    confidence_score: float = Field(default=0.88, ge=0.0, le=1.0)


class ApprovalGateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_id: str = Field(..., min_length=1)
    activity_id: str = Field(..., min_length=1)
    approver_role: str = Field(..., min_length=1)
    department: str = Field(default="Management")
    approval_criteria: str = Field(..., min_length=1)
    threshold_rule: Optional[str] = None
    rejection_target_activity_id: Optional[str] = None
    sla_hours: Optional[int] = None
    source_reference: SourceReferenceSchema
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)


class DocumentSourceRefSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., min_length=1)
    filename: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1)
    checksum_sha256: str = Field(default="")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AgentExecutionStepSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_name: str
    status: str = Field(default="COMPLETED")
    duration_ms: float = Field(default=0.0)
    summary: str
    items_processed: int = Field(default=0)
    warnings_count: int = Field(default=0)
    retry_iteration: int = Field(default=0)


class ReviewerCommentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment_id: str
    author: str
    role: str = Field(default="Process Reviewer")
    activity_id: Optional[str] = None
    comment: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogEntrySchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    log_id: str
    version: int
    action: str
    actor: str
    details: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessModelSchema(BaseModel):
    """
    Strict, versioned Process Model schema containing all 13 mandatory top-level attributes
    plus human review governance, field-level validation issues, and LangGraph agent trace.
    """
    model_config = ConfigDict(extra="forbid")

    process_id: str = Field(..., min_length=1)
    process_name: str = Field(..., min_length=2)
    document_source: DocumentSourceRefSchema
    version: int = Field(default=1, ge=1)
    activities: List[ProcessActivitySchema] = Field(..., min_length=1)
    actors: List[ProcessActorSchema] = Field(default_factory=list)
    conditions: List[BusinessConditionSchema] = Field(default_factory=list)
    dependencies: List[ActivityDependencySchema] = Field(default_factory=list)
    inputs: List[ProcessIOSchema] = Field(default_factory=list)
    outputs: List[ProcessIOSchema] = Field(default_factory=list)
    exceptions: List[ProcessExceptionSchema] = Field(default_factory=list)
    approvals: List[ApprovalGateSchema] = Field(default_factory=list)
    validation_status: ValidationStatusEnum = Field(default=ValidationStatusEnum.NEEDS_REVIEW)

    # Human Review Governance & Traceability
    schema_version: str = Field(default="2.0.0")
    review_status: ReviewStatusEnum = Field(default=ReviewStatusEnum.PENDING_REVIEW)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    needs_human_review: bool = Field(default=True)
    review_routing_reasons: List[str] = Field(default_factory=list)
    validation_errors: List[FieldLevelValidationError] = Field(default_factory=list)
    agent_trace: List[AgentExecutionStepSchema] = Field(default_factory=list)
    reviewer_comments: List[ReviewerCommentSchema] = Field(default_factory=list)
    audit_logs: List[AuditLogEntrySchema] = Field(default_factory=list)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def verify_non_silent_approval(self) -> "ProcessModelSchema":
        """Enforce rule: Never silently convert an unapproved extraction into an approved process."""
        if self.review_status == ReviewStatusEnum.APPROVED and not self.approved_by:
            raise ValueError("Process cannot be in APPROVED state without an explicit human approved_by actor.")
        return self
