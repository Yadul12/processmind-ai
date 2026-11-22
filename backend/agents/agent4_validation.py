"""
Agent 4 — Process Validation Agent
Responsibilities:
- Validate every output against strict Pydantic schemas.
- Detect missing actors, invalid dependencies, and incomplete decision conditions.
- Flag ambiguous statements rather than inventing missing information.
- Detect contradictory instructions / circular dependency deadlocks.
- Return field-level validation errors.
"""

import re
import time
from typing import Any, Dict, List, Set, Tuple

from backend.agents.state import ExtractionGraphState
from backend.schemas.process import (
    FieldLevelValidationError,
    ValidationSeverityEnum,
    ValidationStatusEnum,
)


class ProcessValidationAgent:
    """Agent 4: Executes schema, graph topology, completeness, contradiction, and ambiguity checks."""

    AGENT_NAME = "Agent 4 — Process Validation"

    AMBIGUOUS_PATTERNS = [
        (r"\bmaybe\b", "Vague certainty qualifier 'maybe'"),
        (r"\bprobably\b", "Non-deterministic qualifier 'probably'"),
        (r"\bsomeone\b", "Unspecified actor pronoun 'someone'"),
        (r"\bif appropriate\b", "Undefined conditional criterion 'if appropriate'"),
        (r"\bas needed\b", "Undefined trigger criterion 'as needed'"),
        (r"\bfairly large\b", "Unquantified numerical threshold 'fairly large'"),
        (r"\bunusual\b", "Subjective criterion 'unusual' without metric threshold"),
        (r"\bwhenever convenient\b", "Undefined SLA timing 'whenever convenient'"),
    ]

    def _find_cycles(self, activity_ids: Set[str], adj: Dict[str, List[str]]) -> List[List[str]]:
        visited: Set[str] = set()
        on_stack: Set[str] = set()
        path: List[str] = []
        cycles: List[List[str]] = []

        def dfs(node: str) -> None:
            visited.add(node)
            on_stack.add(node)
            path.append(node)
            for nbr in adj.get(node, []):
                if nbr not in activity_ids:
                    continue
                if nbr not in visited:
                    dfs(nbr)
                elif nbr in on_stack:
                    idx = path.index(nbr)
                    cycle_nodes = path[idx:] + [nbr]
                    cycles.append(cycle_nodes)
            path.pop()
            on_stack.remove(node)

        for aid in sorted(activity_ids):
            if aid not in visited:
                dfs(aid)
        return cycles

    def validate_extraction_dict(
        self,
        normalized: Dict[str, Any],
    ) -> Tuple[List[FieldLevelValidationError], ValidationStatusEnum]:
        errors: List[FieldLevelValidationError] = []
        activities: List[Dict[str, Any]] = normalized.get("activities", [])
        conditions: List[Dict[str, Any]] = normalized.get("conditions", [])
        exceptions: List[Dict[str, Any]] = normalized.get("exceptions", [])
        approvals: List[Dict[str, Any]] = normalized.get("approvals", [])

        activity_ids: Set[str] = {a.get("activity_id", "") for a in activities if a.get("activity_id")}
        cond_by_act: Dict[str, List[Dict[str, Any]]] = {}
        for c in conditions:
            cond_by_act.setdefault(c.get("decision_activity_id", ""), []).append(c)
        exc_by_act: Dict[str, List[Dict[str, Any]]] = {}
        for e in exceptions:
            exc_by_act.setdefault(e.get("source_activity_id", ""), []).append(e)
        apr_by_act: Dict[str, List[Dict[str, Any]]] = {}
        for ap in approvals:
            apr_by_act.setdefault(ap.get("activity_id", ""), []).append(ap)

        adj: Dict[str, List[str]] = {aid: [] for aid in activity_ids}

        for idx, act in enumerate(activities):
            aid = act.get("activity_id", f"INDEX_{idx}")
            role = (act.get("responsible_role") or "").strip()
            desc = act.get("description") or ""
            atype = act.get("activity_type") or "manual"
            src_quote = (act.get("source_reference") or {}).get("exact_quote", "")

            # 1. Missing Actor check
            if not role or role.upper() in ("UNASSIGNED", "UNKNOWN", "TBD", "SOMEONE"):
                errors.append(
                    FieldLevelValidationError(
                        error_code="MISSING_ACTOR",
                        severity=ValidationSeverityEnum.ERROR,
                        field_path=f"activities[{idx}].responsible_role",
                        activity_id=aid,
                        message=(
                            f"Activity '{aid}' ({act.get('activity_name')}) lacks an assigned responsible role "
                            f"(found '{role or 'EMPTY'}'). Do not invent an actor; route to human review."
                        ),
                        suggested_remediation="Assign a specific organizational role and department during Human Review.",
                        source_quote=src_quote,
                    )
                )

            # 2. Invalid Dependency checks (dangling or self-loop)
            for d_idx, dep_id in enumerate(act.get("dependencies", [])):
                if dep_id == aid:
                    errors.append(
                        FieldLevelValidationError(
                            error_code="INVALID_DEPENDENCY",
                            severity=ValidationSeverityEnum.ERROR,
                            field_path=f"activities[{idx}].dependencies[{d_idx}]",
                            activity_id=aid,
                            message=f"Activity '{aid}' contains a self-referential dependency on '{dep_id}'.",
                            suggested_remediation="Remove self-dependency.",
                            source_quote=src_quote,
                        )
                    )
                elif dep_id not in activity_ids:
                    errors.append(
                        FieldLevelValidationError(
                            error_code="INVALID_DEPENDENCY",
                            severity=ValidationSeverityEnum.ERROR,
                            field_path=f"activities[{idx}].dependencies[{d_idx}]",
                            activity_id=aid,
                            message=f"Activity '{aid}' references non-existent upstream dependency '{dep_id}'.",
                            suggested_remediation=f"Link '{aid}' to a valid existing activity_id in {sorted(activity_ids)}.",
                            source_quote=src_quote,
                        )
                    )
                else:
                    adj.setdefault(dep_id, []).append(aid)

            # 3. Incomplete Decision Condition checks
            if atype == "decision":
                act_conds = cond_by_act.get(aid, [])
                if not act_conds:
                    errors.append(
                        FieldLevelValidationError(
                            error_code="INCOMPLETE_DECISION",
                            severity=ValidationSeverityEnum.WARNING,
                            field_path=f"activities[{idx}].activity_type",
                            activity_id=aid,
                            message=f"Decision activity '{aid}' has no explicit branching condition rule extracted.",
                            suggested_remediation="Specify a BusinessCondition with IF/ELSE target branches.",
                            source_quote=src_quote,
                        )
                    )
                else:
                    for c_obj in act_conds:
                        has_true = bool(c_obj.get("branch_when_true"))
                        has_false = bool(c_obj.get("branch_when_false")) or bool(exc_by_act.get(aid))
                        if not (has_true and has_false):
                            errors.append(
                                FieldLevelValidationError(
                                    error_code="INCOMPLETE_DECISION",
                                    severity=ValidationSeverityEnum.WARNING,
                                    field_path=f"activities[{idx}].conditions",
                                    activity_id=aid,
                                    message=(
                                        f"Decision condition '{c_obj.get('condition_id')}' on '{aid}' is incomplete: "
                                        f"missing explicit ELSE/alternative branch target."
                                    ),
                                    suggested_remediation="Define both True and False branch target activity IDs.",
                                    source_quote=c_obj.get("rule_expression", src_quote),
                                )
                            )

            # 4. Approval Gate completeness
            if atype == "approval" and not apr_by_act.get(aid):
                errors.append(
                    FieldLevelValidationError(
                        error_code="MISSING_APPROVAL_CRITERIA",
                        severity=ValidationSeverityEnum.WARNING,
                        field_path=f"activities[{idx}].approvals",
                        activity_id=aid,
                        message=f"Approval activity '{aid}' has no formal ApprovalGate criteria record attached.",
                        suggested_remediation="Attach approval threshold, SLA, and rejection target.",
                        source_quote=src_quote,
                    )
                )

            # 5. Ambiguous Statement detection (never invent missing thresholds/actors)
            combined_text = " ".join(
                [desc] + act.get("preconditions", []) + act.get("postconditions", [])
            )
            found_ambiguities: List[str] = []
            for pattern, explanation in self.AMBIGUOUS_PATTERNS:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    found_ambiguities.append(explanation)

            if found_ambiguities:
                errors.append(
                    FieldLevelValidationError(
                        error_code="AMBIGUOUS_STATEMENT",
                        severity=ValidationSeverityEnum.AMBIGUITY,
                        field_path=f"activities[{idx}].description",
                        activity_id=aid,
                        message=(
                            f"Ambiguous wording detected in '{aid}': {'; '.join(found_ambiguities)}. "
                            f"Flagged for human clarification rather than hallucinating specificity."
                        ),
                        suggested_remediation="Clarify quantitative thresholds, SLAs, and role ownership with policy owner.",
                        source_quote=desc,
                    )
                )

            # 6. Duplicate warning propagation
            if act.get("potential_duplicate_of"):
                errors.append(
                    FieldLevelValidationError(
                        error_code="POTENTIAL_DUPLICATE_ACTIVITY",
                        severity=ValidationSeverityEnum.WARNING,
                        field_path=f"activities[{idx}].activity_name",
                        activity_id=aid,
                        message=f"Activity '{aid}' appears semantically similar to '{act['potential_duplicate_of']}'.",
                        suggested_remediation="Merge or differentiate duplicate process activities.",
                        source_quote=src_quote,
                    )
                )

        # 7. Contradictory Instructions / Circular Dependency Cycle check
        cycles = self._find_cycles(activity_ids, adj)
        for cyc in cycles:
            cycle_str = " -> ".join(cyc)
            errors.append(
                FieldLevelValidationError(
                    error_code="CONTRADICTORY_DEPENDENCY_CYCLE",
                    severity=ValidationSeverityEnum.ERROR,
                    field_path="dependencies",
                    activity_id=cyc[0],
                    message=(
                        f"Contradictory circular dependency deadlock detected ({cycle_str}). "
                        f"Activities mutually require each other to complete first."
                    ),
                    suggested_remediation="Break the dependency cycle by establishing a strict sequential sign-off order.",
                    source_quote=cycle_str,
                )
            )

        # Determine overall ValidationStatusEnum
        has_error = any(e.severity == ValidationSeverityEnum.ERROR for e in errors)
        has_warn_or_ambig = any(
            e.severity in (ValidationSeverityEnum.WARNING, ValidationSeverityEnum.AMBIGUITY) for e in errors
        )

        if has_error:
            status = ValidationStatusEnum.NEEDS_REVIEW
        elif has_warn_or_ambig:
            status = ValidationStatusEnum.VALID_WITH_WARNINGS
        else:
            status = ValidationStatusEnum.VALID

        return errors, status

    def run(self, state: ExtractionGraphState) -> ExtractionGraphState:
        start_ts = time.perf_counter()
        normalized = state.get("normalized_extraction") or {}
        errors, val_status = self.validate_extraction_dict(normalized)

        retry_count = int(state.get("retry_count", 0))
        max_retries = int(state.get("max_retries", 2))

        # Check if there is a recoverable extraction issue (e.g., empty activities) and retries remain
        needs_retry = False
        retry_feedback: List[str] = []
        if not normalized.get("activities") and retry_count < max_retries:
            needs_retry = True
            retry_feedback.append("No activities were extracted; re-run extraction with fallback step segmentation.")

        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        trace = list(state.get("agent_trace") or [])
        trace.append(
            {
                "agent_name": self.AGENT_NAME,
                "status": "RETRY_REQUESTED" if needs_retry else "COMPLETED",
                "duration_ms": duration_ms,
                "summary": (
                    f"Validation status: {val_status.value} ({len(errors)} field-level issue(s) found: "
                    f"{sum(1 for e in errors if e.severity == ValidationSeverityEnum.ERROR)} error(s), "
                    f"{sum(1 for e in errors if e.severity == ValidationSeverityEnum.WARNING)} warning(s), "
                    f"{sum(1 for e in errors if e.severity == ValidationSeverityEnum.AMBIGUITY)} ambiguity flag(s))."
                ),
                "items_processed": len(normalized.get("activities", [])),
                "warnings_count": len(errors),
                "retry_iteration": retry_count,
            }
        )

        return {
            **state,
            "validation_errors": [e.model_dump(mode="json") for e in errors],
            "validation_status": val_status.value,
            "needs_retry": needs_retry,
            "retry_count": retry_count + (1 if needs_retry else 0),
            "retry_feedback": retry_feedback,
            "agent_trace": trace,
        }


agent4_validation = ProcessValidationAgent()
