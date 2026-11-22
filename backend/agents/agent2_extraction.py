"""
Agent 2 — Process Extraction Agent
Responsibilities:
- Identify activities, actors, inputs, and outputs.
- Extract process sequences and dependencies.
- Identify decision points and approval gates.
- Identify exception conditions and alternate paths.
- Produce structured intermediate JSON.
"""

import re
import time
from typing import Any, Dict, List, Optional

from backend.agents.state import ExtractionGraphState
from backend.schemas.document import DocumentSectionBlock, ParsedDocumentStructure
from backend.services.llm_provider import llm_provider


class ProcessExtractionAgent:
    """Agent 2: Extracts intermediate structured process elements from Agent 1's parsed document blocks."""

    AGENT_NAME = "Agent 2 — Process Extraction"

    STEP_HEADER_RE = re.compile(
        r"^Step\s+(?P<num>\d+)\s*(?:\[(?P<id>ACT-[A-Za-z0-9_-]+)\])?\s*(?P<rest>.+)$",
        re.IGNORECASE,
    )
    FREEFORM_STEP_RE = re.compile(
        r"^(?:Step\s+)?(?P<num>\d+)[\.\)\:]\s+(?P<rest>.+)$",
        re.IGNORECASE,
    )
    DECISION_RULE_RE = re.compile(
        r"^DECISION\s+RULE\s*(?:\[(?P<id>COND-[A-Za-z0-9_-]+)\])?\s*:\s*(?P<rule>.+)$",
        re.IGNORECASE,
    )
    APPROVAL_GATE_RE = re.compile(
        r"^APPROVAL\s+GATE\s*(?:\[(?P<id>APR-[A-Za-z0-9_-]+)\])?\s*:\s*(?P<rule>.+)$",
        re.IGNORECASE,
    )
    EXCEPTION_RULE_RE = re.compile(
        r"^EXCEPTION\s+RULE\s*(?:\[(?P<id>EXC-[A-Za-z0-9_-]+)\])?\s*:\s*(?P<rule>.+)$",
        re.IGNORECASE,
    )

    def _deterministic_extract(self, parsed: ParsedDocumentStructure) -> Dict[str, Any]:
        activities: List[Dict[str, Any]] = []
        actors_map: Dict[str, Dict[str, Any]] = {}
        conditions: List[Dict[str, Any]] = []
        dependencies: List[Dict[str, Any]] = []
        inputs_list: List[Dict[str, Any]] = []
        outputs_list: List[Dict[str, Any]] = []
        exceptions: List[Dict[str, Any]] = []
        approvals: List[Dict[str, Any]] = []

        current_act: Optional[Dict[str, Any]] = None
        default_dept = parsed.metadata.department or "Enterprise Operations"

        def flush_current() -> None:
            nonlocal current_act
            if current_act is not None:
                activities.append(current_act)
                current_act = None

        for blk in parsed.blocks:
            line = blk.text.strip()
            if not line or blk.block_type == "heading":
                continue

            # 1. Check structured Step header: Step N [ACT-XXX] Name | Role: ... | Type: ...
            m_step = self.STEP_HEADER_RE.match(line)
            if m_step:
                flush_current()
                step_num = int(m_step.group("num"))
                act_id = m_step.group("id") or f"ACT-{step_num:03d}"
                rest = m_step.group("rest")
                parts = [p.strip() for p in rest.split("|")]
                act_name = parts[0]
                role_raw = "UNASSIGNED"
                act_type = "manual"
                dept = default_dept

                for part in parts[1:]:
                    if part.lower().startswith("role:"):
                        r_val = part.split(":", 1)[1].strip()
                        if "(" in r_val and ")" in r_val:
                            role_raw = r_val.split("(", 1)[0].strip()
                            dept = r_val.split("(", 1)[1].split(")")[0].strip()
                        else:
                            role_raw = r_val
                    elif part.lower().startswith("type:"):
                        act_type = part.split(":", 1)[1].strip().lower()

                current_act = {
                    "activity_id": act_id,
                    "activity_name": act_name,
                    "description": act_name,
                    "activity_type": act_type,
                    "responsible_role": role_raw or "UNASSIGNED",
                    "department": dept,
                    "input": [],
                    "output": [],
                    "preconditions": [],
                    "postconditions": [],
                    "dependencies": [],
                    "source_reference": {
                        "document_id": parsed.document_id,
                        "section": blk.section_ref,
                        "page_or_sheet": blk.page_or_sheet,
                        "line_or_row": blk.line_or_row,
                        "exact_quote": line,
                        "block_id": blk.block_id,
                    },
                    "field_citations": {
                        "activity_name": line,
                        "responsible_role": line,
                    },
                }
                continue

            # 2. Check structured sub-attributes of current activity
            if current_act is not None:
                if line.lower().startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    current_act["description"] = desc
                    current_act["field_citations"]["description"] = line
                    continue

                if line.lower().startswith("input:"):
                    parts = [p.strip() for p in line.split("|")]
                    for p in parts:
                        if p.lower().startswith("input:"):
                            raw_in = p.split(":", 1)[1].strip()
                            in_items = [x.strip() for x in raw_in.split(",") if x.strip() and x.strip().lower() != "none"]
                            current_act["input"] = in_items
                            current_act["field_citations"]["input"] = p
                        elif p.lower().startswith("output:"):
                            raw_out = p.split(":", 1)[1].strip()
                            out_items = [x.strip() for x in raw_out.split(",") if x.strip() and x.strip().lower() != "none"]
                            current_act["output"] = out_items
                            current_act["field_citations"]["output"] = p
                    continue

                if line.lower().startswith("preconditions:"):
                    parts = [p.strip() for p in line.split("|")]
                    for p in parts:
                        if p.lower().startswith("preconditions:"):
                            raw_pre = p.split(":", 1)[1].strip()
                            current_act["preconditions"] = [raw_pre] if raw_pre and raw_pre.lower() != "none" else []
                            current_act["field_citations"]["preconditions"] = p
                        elif p.lower().startswith("postconditions:"):
                            raw_post = p.split(":", 1)[1].strip()
                            current_act["postconditions"] = [raw_post] if raw_post and raw_post.lower() != "none" else []
                            current_act["field_citations"]["postconditions"] = p
                    continue

                if line.lower().startswith("dependencies:"):
                    dep_str = line.split(":", 1)[1].strip()
                    if dep_str and dep_str.lower() != "none":
                        deps = [d.strip() for d in dep_str.split(",") if d.strip()]
                        current_act["dependencies"] = deps
                        current_act["field_citations"]["dependencies"] = line
                    continue

            # 3. Check DECISION RULE
            m_dec = self.DECISION_RULE_RE.match(line)
            if m_dec:
                cid = m_dec.group("id") or f"COND-{len(conditions) + 1:03d}"
                rule_txt = m_dec.group("rule").strip()
                dec_act_id = current_act["activity_id"] if current_act else (activities[-1]["activity_id"] if activities else "ACT-001")
                targets = re.findall(r"\b(ACT-[A-Za-z0-9_-]+)\b", rule_txt)
                branch_true = targets[0] if len(targets) >= 1 else None
                branch_false = targets[1] if len(targets) >= 2 else None
                conditions.append(
                    {
                        "condition_id": cid,
                        "name": f"Decision Branch for {dec_act_id}",
                        "rule_expression": rule_txt,
                        "decision_activity_id": dec_act_id,
                        "branch_when_true": branch_true,
                        "branch_when_false": branch_false,
                        "source_reference": {
                            "document_id": parsed.document_id,
                            "section": blk.section_ref,
                            "page_or_sheet": blk.page_or_sheet,
                            "line_or_row": blk.line_or_row,
                            "exact_quote": line,
                            "block_id": blk.block_id,
                        },
                    }
                )
                continue

            # 4. Check APPROVAL GATE
            m_apr = self.APPROVAL_GATE_RE.match(line)
            if m_apr:
                aid = m_apr.group("id") or f"APR-{len(approvals) + 1:03d}"
                rule_txt = m_apr.group("rule").strip()
                act_id = current_act["activity_id"] if current_act else (activities[-1]["activity_id"] if activities else "ACT-001")
                approver_role = current_act["responsible_role"] if current_act else "Department Approver"
                criteria = rule_txt
                sla_hours: Optional[int] = None
                rej_target: Optional[str] = None

                for seg in [s.strip() for s in rule_txt.split("|")]:
                    if seg.lower().startswith("approver:"):
                        approver_role = seg.split(":", 1)[1].strip()
                    elif seg.lower().startswith("criteria:"):
                        criteria = seg.split(":", 1)[1].strip()
                    elif seg.lower().startswith("sla:"):
                        m_hr = re.search(r"(\d+)", seg)
                        if m_hr:
                            sla_hours = int(m_hr.group(1))
                    elif seg.lower().startswith("rejection target:"):
                        m_rt = re.search(r"(ACT-[A-Za-z0-9_-]+)", seg)
                        if m_rt:
                            rej_target = m_rt.group(1)

                thresh_m = re.search(r"([><=]+\s*\$?[\d,]+(?:\s*\w+)?)", criteria)
                approvals.append(
                    {
                        "approval_id": aid,
                        "activity_id": act_id,
                        "approver_role": approver_role,
                        "department": current_act["department"] if current_act else default_dept,
                        "approval_criteria": criteria,
                        "threshold_rule": thresh_m.group(1) if thresh_m else None,
                        "rejection_target_activity_id": rej_target,
                        "sla_hours": sla_hours,
                        "source_reference": {
                            "document_id": parsed.document_id,
                            "section": blk.section_ref,
                            "page_or_sheet": blk.page_or_sheet,
                            "line_or_row": blk.line_or_row,
                            "exact_quote": line,
                            "block_id": blk.block_id,
                        },
                    }
                )
                continue

            # 5. Check EXCEPTION RULE
            m_exc = self.EXCEPTION_RULE_RE.match(line)
            if m_exc:
                eid = m_exc.group("id") or f"EXC-{len(exceptions) + 1:03d}"
                rule_txt = m_exc.group("rule").strip()
                src_act_id = current_act["activity_id"] if current_act else (activities[-1]["activity_id"] if activities else "ACT-001")

                esc_role = "Escalation Review Board"
                m_role = re.search(r"escalate\s+to\s+([A-Za-z0-9\s&-]+?)(?:\s+within|\s*\(|$|\.)", rule_txt, re.IGNORECASE)
                if m_role:
                    esc_role = m_role.group(1).strip()

                sla_hours_exc = None
                m_sla = re.search(r"within\s+(\d+)\s+hour", rule_txt, re.IGNORECASE)
                if m_sla:
                    sla_hours_exc = int(m_sla.group(1))

                target_act = None
                m_tgt = re.search(r"Target:\s*(ACT-[A-Za-z0-9_-]+)", rule_txt, re.IGNORECASE)
                if m_tgt:
                    target_act = m_tgt.group(1)

                remediation = "Escalate and hold process execution pending manual investigation."
                if "Remediation:" in rule_txt:
                    remediation = rule_txt.split("Remediation:", 1)[1].strip()

                trigger_cond = rule_txt.split("THEN")[0].replace("IF", "").strip() if "THEN" in rule_txt else rule_txt

                exceptions.append(
                    {
                        "exception_id": eid,
                        "exception_name": f"Exception on {src_act_id}",
                        "trigger_condition": trigger_cond,
                        "source_activity_id": src_act_id,
                        "escalation_role": esc_role,
                        "target_recovery_activity_id": target_act,
                        "remediation_action": remediation,
                        "sla_hours": sla_hours_exc,
                        "source_reference": {
                            "document_id": parsed.document_id,
                            "section": blk.section_ref,
                            "page_or_sheet": blk.page_or_sheet,
                            "line_or_row": blk.line_or_row,
                            "exact_quote": line,
                            "block_id": blk.block_id,
                        },
                    }
                )
                continue

        flush_current()

        # Fallback for completely free-form unstructured documents without "Step N [ACT-XXX]" markers
        if not activities:
            step_idx = 1
            prev_act_id: Optional[str] = None
            for blk in parsed.blocks:
                line = blk.text.strip()
                if not line or blk.block_type == "heading":
                    continue
                if any(
                    line.upper().startswith(prefix)
                    for prefix in ("DOCUMENT CODE:", "TITLE:", "OWNER:", "DEPARTMENT:", "EFFECTIVE DATE:", "1.0 ")
                ):
                    continue
                m_free = self.FREEFORM_STEP_RE.match(line)
                if m_free or len(line.split()) >= 5:
                    act_id = f"ACT-{step_idx:03d}"
                    body = m_free.group("rest") if m_free else line
                    role_guess = "UNASSIGNED"
                    role_match = re.search(
                        r"\b(Manager|Analyst|Specialist|Controller|Director|Engineer|Officer|Coordinator|Counsel|Clerk|Admin)\b",
                        body,
                        re.IGNORECASE,
                    )
                    if role_match:
                        role_guess = f"{role_match.group(1).title()}"
                    atype = "manual"
                    if blk.is_decision_statement:
                        atype = "decision"
                    elif blk.is_approval_statement:
                        atype = "approval"
                    elif blk.is_exception_statement:
                        atype = "escalation"

                    activities.append(
                        {
                            "activity_id": act_id,
                            "activity_name": body[:68].strip(" .,:;"),
                            "description": body,
                            "activity_type": atype,
                            "responsible_role": role_guess,
                            "department": default_dept,
                            "input": ["Upstream Process Context"] if prev_act_id else ["Initial Request"],
                            "output": [f"{act_id} Completion Record"],
                            "preconditions": [f"{prev_act_id} completed"] if prev_act_id else ["Process triggered"],
                            "postconditions": [f"{act_id} verified"],
                            "dependencies": [prev_act_id] if prev_act_id else [],
                            "source_reference": {
                                "document_id": parsed.document_id,
                                "section": blk.section_ref,
                                "page_or_sheet": blk.page_or_sheet,
                                "line_or_row": blk.line_or_row,
                                "exact_quote": line,
                                "block_id": blk.block_id,
                            },
                            "field_citations": {"description": line},
                        }
                    )
                    prev_act_id = act_id
                    step_idx += 1

        # Build canonical Actors, Dependencies, Inputs, and Outputs from extracted activities
        cond_by_dec: Dict[str, Dict[str, Any]] = {c["decision_activity_id"]: c for c in conditions}
        exc_targets: Dict[tuple, str] = {
            (e["source_activity_id"], e["target_recovery_activity_id"]): e["trigger_condition"]
            for e in exceptions
            if e.get("target_recovery_activity_id")
        }
        apr_acts = {a["activity_id"] for a in approvals}

        dep_counter = 1
        io_counter = 1
        for act in activities:
            aid = act["activity_id"]
            role = act["responsible_role"]
            if role and role.upper() != "UNASSIGNED":
                if role not in actors_map:
                    actors_map[role] = {
                        "actor_id": f"ROLE-{len(actors_map) + 1:03d}",
                        "role_name": role,
                        "department": act.get("department", default_dept),
                        "is_approver": act.get("activity_type") == "approval" or aid in apr_acts,
                        "assigned_activity_ids": [aid],
                        "source_reference": act["source_reference"],
                    }
                else:
                    if aid not in actors_map[role]["assigned_activity_ids"]:
                        actors_map[role]["assigned_activity_ids"].append(aid)
                    if act.get("activity_type") == "approval" or aid in apr_acts:
                        actors_map[role]["is_approver"] = True

            for in_name in act.get("input", []):
                inputs_list.append(
                    {
                        "io_id": f"IN-{io_counter:03d}",
                        "name": in_name,
                        "io_type": "input",
                        "artifact_format": "Enterprise Record",
                        "associated_activity_id": aid,
                        "source_reference": act["source_reference"],
                    }
                )
                io_counter += 1

            for out_name in act.get("output", []):
                outputs_list.append(
                    {
                        "io_id": f"OUT-{io_counter:03d}",
                        "name": out_name,
                        "io_type": "output",
                        "artifact_format": "Enterprise Record",
                        "associated_activity_id": aid,
                        "source_reference": act["source_reference"],
                    }
                )
                io_counter += 1

            for upstream_id in act.get("dependencies", []):
                dep_type = "sequential"
                cond_label = None
                if (upstream_id, aid) in exc_targets:
                    dep_type = "exception_escalation"
                    cond_label = f"Exception: {exc_targets[(upstream_id, aid)][:48]}"
                elif upstream_id in cond_by_dec:
                    c_obj = cond_by_dec[upstream_id]
                    if c_obj.get("branch_when_true") == aid:
                        dep_type = "conditional_true"
                        cond_label = "Condition True"
                    elif c_obj.get("branch_when_false") == aid:
                        dep_type = "conditional_false"
                        cond_label = "Condition False"
                elif upstream_id in apr_acts:
                    dep_type = "approval_gated"
                    cond_label = "Approved"

                dependencies.append(
                    {
                        "dependency_id": f"DEP-{dep_counter:03d}",
                        "source_activity_id": upstream_id,
                        "target_activity_id": aid,
                        "dependency_type": dep_type,
                        "condition_label": cond_label,
                        "source_reference": act["source_reference"],
                    }
                )
                dep_counter += 1

        return {
            "process_name": parsed.metadata.title,
            "activities": activities,
            "actors": list(actors_map.values()),
            "conditions": conditions,
            "dependencies": dependencies,
            "inputs": inputs_list,
            "outputs": outputs_list,
            "exceptions": exceptions,
            "approvals": approvals,
        }

    def run(self, state: ExtractionGraphState) -> ExtractionGraphState:
        start_ts = time.perf_counter()
        parsed_struct = ParsedDocumentStructure.model_validate(state["parsed_document"])

        system_prompt = (
            "You are Agent 2 (Process Extraction) in ProcessMind AI. "
            "Extract activities, actors, inputs, outputs, dependencies, conditions, approvals, and exceptions "
            "from the provided SOP blocks into strict JSON."
        )
        user_prompt = f"Document ID: {parsed_struct.document_id}\nTitle: {parsed_struct.metadata.title}"

        extracted = llm_provider.invoke_structured_extraction(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            deterministic_fallback_fn=lambda: self._deterministic_extract(parsed_struct),
        )

        if state.get("custom_process_name"):
            extracted["process_name"] = state["custom_process_name"]

        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        trace = list(state.get("agent_trace") or [])
        trace.append(
            {
                "agent_name": self.AGENT_NAME,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "summary": (
                    f"Extracted {len(extracted.get('activities', []))} activities, "
                    f"{len(extracted.get('actors', []))} unique actors, "
                    f"{len(extracted.get('dependencies', []))} dependencies, "
                    f"{len(extracted.get('conditions', []))} decision rules, "
                    f"{len(extracted.get('approvals', []))} approval gates, and "
                    f"{len(extracted.get('exceptions', []))} exception paths."
                ),
                "items_processed": len(extracted.get("activities", [])),
                "warnings_count": 0,
                "retry_iteration": state.get("retry_count", 0),
            }
        )

        return {
            **state,
            "intermediate_extraction": extracted,
            "agent_trace": trace,
        }


agent2_extraction = ProcessExtractionAgent()
