"""
EvalGuard ProcessMind Extraction Evaluation Adapter.
Bridges EvalGuard's precision, recall, F1, faithfulness, and hallucination scoring engine
with ProcessMind AI's structured business process extraction metrics:
- Activity extraction precision, recall, and F1
- Actor extraction accuracy
- Dependency extraction accuracy
- Decision-condition extraction accuracy
- Schema validation pass rate
- Source citation correctness
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from backend.agents.agent1_understanding import agent1_understanding
from backend.agents.orchestrator import process_orchestrator
from backend.config import settings
from backend.schemas.document import DocumentFileTypeEnum, ParsedDocumentStructure
from backend.schemas.evaluation import DocumentExtractionEvalResult, EvalGuardSuiteReport
from backend.schemas.process import ProcessModelSchema
from backend.services.document_parsers import document_parser


def _normalize_token_str(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _activity_matches(extracted_act: Dict[str, Any], expected_act: Dict[str, Any]) -> bool:
    if extracted_act.get("activity_id") == expected_act.get("activity_id"):
        return True
    ext_tokens = set(_normalize_token_str(extracted_act.get("activity_name", "")).split())
    exp_tokens = set(_normalize_token_str(expected_act.get("activity_name", "")).split())
    if not ext_tokens or not exp_tokens:
        return False
    overlap = len(ext_tokens & exp_tokens) / max(1, len(ext_tokens | exp_tokens))
    return overlap >= 0.60


class EvalGuardExtractionAdapter:
    """Evaluates extracted ProcessModelSchema objects against labelled ground-truth expectations."""

    def evaluate_single_process(
        self,
        extracted: ProcessModelSchema,
        ground_truth: Dict[str, Any],
        raw_document_text: str,
    ) -> DocumentExtractionEvalResult:
        exp_activities: List[Dict[str, Any]] = ground_truth.get("expected_activities", [])
        ext_activities = [a.model_dump(mode="json") for a in extracted.activities]

        matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any]]] = []
        used_expected: Set[int] = set()

        for ext_a in ext_activities:
            for idx, exp_a in enumerate(exp_activities):
                if idx in used_expected:
                    continue
                if _activity_matches(ext_a, exp_a):
                    matched_pairs.append((ext_a, exp_a))
                    used_expected.add(idx)
                    break

        matched_count = len(matched_pairs)
        precision = (matched_count / len(ext_activities) * 100.0) if ext_activities else 0.0
        recall = (matched_count / len(exp_activities) * 100.0) if exp_activities else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

        # 2. Actor extraction accuracy (on matched activities + expected actor set)
        actor_matches = 0
        for ext_a, exp_a in matched_pairs:
            ext_role = _normalize_token_str(ext_a.get("responsible_role", ""))
            exp_role = _normalize_token_str(exp_a.get("responsible_role", ""))
            if ext_role == exp_role or (ext_role and exp_role and (ext_role in exp_role or exp_role in ext_role)):
                actor_matches += 1
        actor_accuracy = (actor_matches / len(matched_pairs) * 100.0) if matched_pairs else 0.0

        # 3. Dependency extraction accuracy
        exp_deps: Set[Tuple[str, str]] = {
            (d["source"], d["target"]) for d in ground_truth.get("expected_dependencies", [])
        }
        ext_deps: Set[Tuple[str, str]] = {
            (d.source_activity_id, d.target_activity_id) for d in extracted.dependencies
        }
        if not exp_deps and not ext_deps:
            dependency_accuracy = 100.0
        elif not exp_deps or not ext_deps:
            dependency_accuracy = 0.0
        else:
            dep_inter = len(exp_deps & ext_deps)
            dep_union = len(exp_deps | ext_deps)
            dependency_accuracy = (dep_inter / dep_union) * 100.0

        # 4. Decision-condition extraction accuracy
        exp_conds = ground_truth.get("expected_conditions", [])
        ext_conds = extracted.conditions
        if not exp_conds and not ext_conds:
            decision_accuracy = 100.0
        elif not exp_conds:
            decision_accuracy = 100.0
        else:
            exp_dec_ids = {c["decision_activity_id"] for c in exp_conds}
            ext_dec_ids = {c.decision_activity_id for c in ext_conds}
            cond_matches = len(exp_dec_ids & ext_dec_ids)
            decision_accuracy = min(100.0, (cond_matches / max(1, len(exp_dec_ids))) * 100.0)

        # 5. Schema validation pass check (strict Pydantic v2 validation succeeded)
        schema_valid = True
        try:
            ProcessModelSchema.model_validate(extracted.model_dump(mode="json"))
        except Exception:
            schema_valid = False

        # 6. Source citation correctness (verify extracted quote tokens appear in raw document text)
        raw_norm = _normalize_token_str(raw_document_text)
        raw_tokens = set(raw_norm.split())
        verified_citations = 0
        for act in extracted.activities:
            quote_norm = _normalize_token_str(act.source_reference.exact_quote)
            quote_tokens = quote_norm.split()
            if not quote_tokens:
                continue
            token_hits = sum(1 for t in quote_tokens if t in raw_tokens)
            if (token_hits / len(quote_tokens)) >= 0.80 and act.source_reference.section:
                verified_citations += 1
        citation_correctness = (
            (verified_citations / len(extracted.activities)) * 100.0 if extracted.activities else 0.0
        )

        # 7. EvalGuard compatibility scores (faithfulness, hallucination_rate, overall_score)
        evalguard_faithfulness = round(citation_correctness * 0.65 + actor_accuracy * 0.35, 1)
        evalguard_hallucination_rate = round(max(0.0, 100.0 - evalguard_faithfulness), 1)
        evalguard_overall_score = round(
            f1 * 0.30
            + actor_accuracy * 0.20
            + dependency_accuracy * 0.20
            + decision_accuracy * 0.15
            + citation_correctness * 0.15,
            1,
        )

        # 8. Edge-case validation verification
        case_id = ground_truth.get("case_id", "SOP")
        error_codes = {e.error_code for e in extracted.validation_errors}
        notes: List[str] = []
        edge_passed = True

        if case_id == "EDGE-001":
            has_missing_actor = "MISSING_ACTOR" in error_codes
            has_ambig = "AMBIGUOUS_STATEMENT" in error_codes
            has_inc_dec = "INCOMPLETE_DECISION" in error_codes
            edge_passed = bool(has_missing_actor and has_ambig)
            notes.append(
                f"Edge-001 checks: MISSING_ACTOR={has_missing_actor}, AMBIGUOUS_STATEMENT={has_ambig}, INCOMPLETE_DECISION={has_inc_dec}"
            )
        elif case_id == "EDGE-002":
            has_cycle = "CONTRADICTORY_DEPENDENCY_CYCLE" in error_codes
            edge_passed = has_cycle
            notes.append(f"Edge-002 contradictory cycle detection: CONTRADICTORY_DEPENDENCY_CYCLE={has_cycle}")
        elif case_id == "EDGE-003":
            edge_passed = len(extracted.conditions) >= 2 and len(extracted.approvals) >= 1
            notes.append(
                f"Edge-003 multi-branch workflow: {len(extracted.conditions)} decision branches and {len(extracted.approvals)} approval gates extracted"
            )
        else:
            notes.append(f"Standard SOP validated with status {extracted.validation_status.value}")

        return DocumentExtractionEvalResult(
            case_id=case_id,
            document_filename=f"{ground_truth.get('base_filename')}.{ground_truth.get('primary_format', 'txt')}",
            process_name=extracted.process_name,
            category=ground_truth.get("category", "Enterprise SOP"),
            activity_precision=round(precision, 1),
            activity_recall=round(recall, 1),
            activity_f1=round(f1, 1),
            actor_accuracy=round(actor_accuracy, 1),
            dependency_accuracy=round(dependency_accuracy, 1),
            decision_condition_accuracy=round(decision_accuracy, 1),
            schema_validation_passed=schema_valid,
            source_citation_correctness=round(citation_correctness, 1),
            evalguard_faithfulness=evalguard_faithfulness,
            evalguard_hallucination_rate=evalguard_hallucination_rate,
            evalguard_overall_score=evalguard_overall_score,
            expected_activity_count=len(exp_activities),
            extracted_activity_count=len(ext_activities),
            matched_activity_count=matched_count,
            ambiguity_detection_passed=edge_passed,
            notes=notes,
        )

    def run_full_evaluation_suite(self) -> EvalGuardSuiteReport:
        gt_dir = Path(settings.ground_truth_dir)
        sample_dir = Path(settings.sample_data_dir)

        if not list(gt_dir.glob("*_ground_truth.json")):
            from data.generate_sample_files import generate_all_samples

            generate_all_samples()

        results: List[DocumentExtractionEvalResult] = []
        for gt_file in sorted(gt_dir.glob("*_ground_truth.json")):
            gt_data = json.loads(gt_file.read_text(encoding="utf-8"))
            base_name = gt_data["base_filename"]
            fmt = gt_data.get("primary_format", "txt")
            doc_path = sample_dir / f"{base_name}.{fmt}"
            if not doc_path.exists():
                doc_path = sample_dir / f"{base_name}.txt"

            content_bytes = doc_path.read_bytes()
            doc_id = f"EVAL-{gt_data['case_id']}"
            ftype, raw_text, blocks, tables, page_count = document_parser.parse_bytes(
                content_bytes, doc_path.name, doc_id
            )
            meta = agent1_understanding.extract_metadata(doc_path.name, blocks, len(tables), page_count)
            parsed_doc = ParsedDocumentStructure(
                document_id=doc_id,
                filename=doc_path.name,
                file_type=DocumentFileTypeEnum(ftype.value),
                metadata=meta,
                headings=[b.text for b in blocks if b.block_type == "heading"],
                blocks=blocks,
                tables=tables,
                numbered_steps=[b.text for b in blocks if b.block_type == "numbered_step"],
                decision_statements=[b.text for b in blocks if b.is_decision_statement],
            )
            extracted_model = process_orchestrator.execute_pipeline(
                document_id=doc_id,
                filename=doc_path.name,
                file_type=ftype.value,
                checksum_sha256="eval-checksum",
                raw_text=raw_text,
                parsed_document=parsed_doc,
            )
            res = self.evaluate_single_process(extracted_model, gt_data, raw_text)
            results.append(res)

        n = max(1, len(results))
        return EvalGuardSuiteReport(
            total_cases=len(results),
            mean_activity_precision=round(sum(r.activity_precision for r in results) / n, 1),
            mean_activity_recall=round(sum(r.activity_recall for r in results) / n, 1),
            mean_activity_f1=round(sum(r.activity_f1 for r in results) / n, 1),
            mean_actor_accuracy=round(sum(r.actor_accuracy for r in results) / n, 1),
            mean_dependency_accuracy=round(sum(r.dependency_accuracy for r in results) / n, 1),
            mean_decision_condition_accuracy=round(sum(r.decision_condition_accuracy for r in results) / n, 1),
            schema_validation_pass_rate=round(
                sum(100.0 if r.schema_validation_passed else 0.0 for r in results) / n, 1
            ),
            mean_source_citation_correctness=round(sum(r.source_citation_correctness for r in results) / n, 1),
            mean_evalguard_faithfulness=round(sum(r.evalguard_faithfulness for r in results) / n, 1),
            mean_evalguard_hallucination_rate=round(sum(r.evalguard_hallucination_rate for r in results) / n, 1),
            mean_evalguard_overall_score=round(sum(r.evalguard_overall_score for r in results) / n, 1),
            edge_case_pass_rate=round(
                sum(100.0 if r.ambiguity_detection_passed else 0.0 for r in results) / n, 1
            ),
            results=results,
        )


evalguard_adapter = EvalGuardExtractionAdapter()
