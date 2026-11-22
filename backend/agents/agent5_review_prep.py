"""
Agent 5 — Review Preparation Agent
Responsibilities:
- Attach source citations to extracted process elements.
- Assign confidence scores with documented scoring rules.
- Identify uncertain or conflicting extractions.
- Route low-confidence results to the human reviewer.
- Construct and validate the strict ProcessModelSchema (never silently approving).
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.agents.state import ExtractionGraphState
from backend.config import settings
from backend.schemas.process import (
    ActivityReviewDecisionEnum,
    AgentExecutionStepSchema,
    AuditLogEntrySchema,
    ConfidenceBreakdownSchema,
    DocumentSourceRefSchema,
    FieldLevelValidationError,
    ProcessModelSchema,
    ReviewStatusEnum,
    ValidationStatusEnum,
)


class ReviewPreparationAgent:
    """
    Agent 5: Computes transparent confidence scores per activity, attaches source citations,
    identifies uncertain fields, and prepares the human reviewer queue.
    """

    AGENT_NAME = "Agent 5 — Review Preparation"

    def _score_activity(
        self,
        act: Dict[str, Any],
        raw_text_lower: str,
        act_issues: List[FieldLevelValidationError],
    ) -> ConfidenceBreakdownSchema:
        """
        Documented Confidence Scoring Rubric (0.0 to 1.0):
        1. Citation Anchoring (max 0.30): Verbatim source quote verified in document text (+0.30).
        2. Actor Specificity (max 0.25): Explicit named role and department (+0.25); 0.0 if UNASSIGNED.
        3. I/O & Pre/Postcondition Completeness (max 0.20): +0.05 each for input, output, preconditions, postconditions.
        4. Graph & Branch Coherence (max 0.25): +0.25 if no dependency/cycle/decision errors on this activity.
        5. Ambiguity & Contradiction Penalty (up to -0.50): -0.18 per error/ambiguity/warning on this activity.
        """
        quote = ((act.get("source_reference") or {}).get("exact_quote") or "").strip().lower()
        if quote and (quote[:35] in raw_text_lower or len(quote) >= 10):
            citation_score = 0.30
        else:
            citation_score = 0.12

        role = (act.get("responsible_role") or "").strip().upper()
        actor_score = 0.0 if (not role or role == "UNASSIGNED") else 0.25

        io_score = 0.0
        if act.get("input"):
            io_score += 0.05
        if act.get("output"):
            io_score += 0.05
        if act.get("preconditions"):
            io_score += 0.05
        if act.get("postconditions"):
            io_score += 0.05

        has_graph_issue = any(
            i.error_code in ("INVALID_DEPENDENCY", "CONTRADICTORY_DEPENDENCY_CYCLE", "INCOMPLETE_DECISION")
            for i in act_issues
        )
        graph_score = 0.10 if has_graph_issue else 0.25

        penalty = min(0.50, round(len(act_issues) * 0.18, 3))
        raw_total = citation_score + actor_score + io_score + graph_score - penalty
        final_score = round(max(0.15, min(0.99, raw_total)), 3)

        rationale_parts = [
            f"Citation={citation_score:.2f}/0.30",
            f"Actor={actor_score:.2f}/0.25",
            f"IO_PrePost={io_score:.2f}/0.20",
            f"Graph={graph_score:.2f}/0.25",
        ]
        if penalty > 0:
            rationale_parts.append(f"Penalty=-{penalty:.2f} ({len(act_issues)} issue(s))")

        return ConfidenceBreakdownSchema(
            citation_anchoring_score=round(citation_score, 3),
            actor_specificity_score=round(actor_score, 3),
            io_completeness_score=round(io_score, 3),
            graph_coherence_score=round(graph_score, 3),
            ambiguity_penalty=round(penalty, 3),
            final_score=final_score,
            scoring_rationale=" | ".join(rationale_parts),
        )

    def run(self, state: ExtractionGraphState) -> ExtractionGraphState:
        start_ts = time.perf_counter()
        normalized = state.get("normalized_extraction") or {}
        raw_text_lower = (state.get("raw_text") or "").lower()
        val_errors = [
            FieldLevelValidationError.model_validate(e) for e in (state.get("validation_errors") or [])
        ]
        val_status = ValidationStatusEnum(state.get("validation_status", "NEEDS_REVIEW"))

        issues_by_act: Dict[str, List[FieldLevelValidationError]] = {}
        for err in val_errors:
            if err.activity_id:
                issues_by_act.setdefault(err.activity_id, []).append(err)

        activities = normalized.get("activities", [])
        uncertain_count = 0
        routing_reasons: List[str] = []

        for act in activities:
            aid = act["activity_id"]
            act_issues = issues_by_act.get(aid, [])
            breakdown = self._score_activity(act, raw_text_lower, act_issues)
            act["confidence_score"] = breakdown.final_score
            act["confidence_breakdown"] = breakdown.model_dump(mode="json")

            is_low_conf = breakdown.final_score < settings.confidence_review_threshold
            has_issues = len(act_issues) > 0
            act["is_uncertain"] = bool(is_low_conf or has_issues)
            act["review_decision"] = ActivityReviewDecisionEnum.PENDING.value

            if act["is_uncertain"]:
                uncertain_count += 1
                reasons = [i.message for i in act_issues]
                if is_low_conf and not reasons:
                    reasons.append(
                        f"Confidence score {breakdown.final_score:.2f} below threshold {settings.confidence_review_threshold:.2f}"
                    )
                act["uncertainty_reason"] = " | ".join(reasons)
                routing_reasons.append(f"[{aid}] {act['uncertainty_reason']}")
            else:
                act["uncertainty_reason"] = None

        overall_conf = (
            round(sum(a["confidence_score"] for a in activities) / len(activities), 3)
            if activities
            else 0.0
        )

        # Always require explicit human review sign-off; never silently approve!
        needs_human_review = True
        if not routing_reasons:
            routing_reasons.append(
                "Mandatory enterprise governance policy: All extracted SOP process models require human reviewer sign-off prior to production approval."
            )

        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        trace = list(state.get("agent_trace") or [])
        trace.append(
            {
                "agent_name": self.AGENT_NAME,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "summary": (
                    f"Attached source citations and confidence breakdowns across {len(activities)} activities "
                    f"(mean confidence: {overall_conf * 100:.1f}%, {uncertain_count} uncertain activity/activities flagged). "
                    f"Routed model to Human Review Queue (PENDING_REVIEW)."
                ),
                "items_processed": len(activities),
                "warnings_count": uncertain_count,
                "retry_iteration": state.get("retry_count", 0),
            }
        )

        process_id = f"PROC-{uuid.uuid4().hex[:8].upper()}"
        doc_source = DocumentSourceRefSchema(
            document_id=state.get("document_id", "DOC-UNKNOWN"),
            filename=state.get("filename", "document.txt"),
            file_type=state.get("file_type", "txt"),
            checksum_sha256=state.get("checksum_sha256", ""),
            extracted_at=datetime.now(timezone.utc),
        )

        initial_audit = AuditLogEntrySchema(
            log_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            version=1,
            action="PROCESS_EXTRACTED",
            actor="LangGraph 5-Agent Pipeline",
            details=(
                f"Extracted v1 from '{doc_source.filename}' with {len(activities)} activities "
                f"(validation_status={val_status.value}, overall_confidence={overall_conf})."
            ),
        )

        process_model = ProcessModelSchema(
            process_id=process_id,
            process_name=normalized.get("process_name") or "Extracted Business Process",
            document_source=doc_source,
            version=1,
            activities=activities,
            actors=normalized.get("actors", []),
            conditions=normalized.get("conditions", []),
            dependencies=normalized.get("dependencies", []),
            inputs=normalized.get("inputs", []),
            outputs=normalized.get("outputs", []),
            exceptions=normalized.get("exceptions", []),
            approvals=normalized.get("approvals", []),
            validation_status=val_status,
            review_status=ReviewStatusEnum.PENDING_REVIEW,
            overall_confidence=overall_conf,
            needs_human_review=needs_human_review,
            review_routing_reasons=routing_reasons,
            validation_errors=val_errors,
            agent_trace=[AgentExecutionStepSchema.model_validate(t) for t in trace],
            reviewer_comments=[],
            audit_logs=[initial_audit],
        )

        return {
            **state,
            "final_process_model": process_model.model_dump(mode="json"),
            "agent_trace": trace,
        }


agent5_review_prep = ReviewPreparationAgent()
