"""
EvalGuard-Style Process Extraction Evaluation Schemas (Pydantic v2).
Integrates the EvalGuard evaluation concept through an adapter specifically tailored to SOP process extraction.
"""

from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field, ConfigDict


class DocumentExtractionEvalResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    document_filename: str
    process_name: str
    category: str = Field(default="Enterprise SOP")

    # Core process extraction metrics requested in Section 8
    activity_precision: float = Field(..., ge=0.0, le=100.0)
    activity_recall: float = Field(..., ge=0.0, le=100.0)
    activity_f1: float = Field(..., ge=0.0, le=100.0)
    actor_accuracy: float = Field(..., ge=0.0, le=100.0)
    dependency_accuracy: float = Field(..., ge=0.0, le=100.0)
    decision_condition_accuracy: float = Field(..., ge=0.0, le=100.0)
    schema_validation_passed: bool
    source_citation_correctness: float = Field(..., ge=0.0, le=100.0)

    # EvalGuard adapter compatibility metrics
    evalguard_faithfulness: float = Field(..., ge=0.0, le=100.0)
    evalguard_hallucination_rate: float = Field(..., ge=0.0, le=100.0)
    evalguard_overall_score: float = Field(..., ge=0.0, le=100.0)

    expected_activity_count: int
    extracted_activity_count: int
    matched_activity_count: int
    ambiguity_detection_passed: bool = True
    notes: List[str] = Field(default_factory=list)


class EvalGuardSuiteReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_name: str = Field(default="EvalGuard ProcessMind Extraction Adapter v1.0")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_cases: int
    mean_activity_precision: float
    mean_activity_recall: float
    mean_activity_f1: float
    mean_actor_accuracy: float
    mean_dependency_accuracy: float
    mean_decision_condition_accuracy: float
    schema_validation_pass_rate: float
    mean_source_citation_correctness: float
    mean_evalguard_faithfulness: float
    mean_evalguard_hallucination_rate: float
    mean_evalguard_overall_score: float
    edge_case_pass_rate: float
    results: List[DocumentExtractionEvalResult]
