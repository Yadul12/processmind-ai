"""
Agent 3 — Classification and Normalisation Agent
Responsibilities:
- Standardise activity names and role names.
- Classify activities into categories such as manual, automated, approval, decision, notification, escalation, integration.
- Detect potentially duplicate activities.
- Normalise business terminology without changing original meaning.
"""

import copy
import re
import time
from typing import Any, Dict, List, Set

from backend.agents.state import ExtractionGraphState
from backend.schemas.process import ActivityTypeEnum


class ClassificationNormalizationAgent:
    """Agent 3: Standardizes terminology, classifies activity types, and flags potential duplicates."""

    AGENT_NAME = "Agent 3 — Classification & Normalisation"

    VALID_TYPES = {e.value for e in ActivityTypeEnum}

    TERMINOLOGY_ABBREVIATIONS = {
        r"\bpo\b": "PO",
        r"\berp\b": "ERP",
        r"\bhris\b": "HRIS",
        r"\bsso\b": "SSO",
        r"\bsla\b": "SLA",
        r"\bocr\b": "OCR",
        r"\bach\b": "ACH",
        r"\bgl\b": "GL",
        r"\bpam\b": "PAM",
        r"\bjit\b": "JIT",
        r"\biam\b": "IAM",
        r"\bsoc\b": "SOC",
        r"\bciso\b": "CISO",
        r"\bcfo\b": "CFO",
        r"\bfx\b": "FX",
        r"\bswift\b": "SWIFT",
    }

    def _standardize_name(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", text.strip())
        if not cleaned:
            return cleaned
        # Ensure initial capital without clobbering existing enterprise acronyms
        cleaned = cleaned[0].upper() + cleaned[1:]
        for pattern, replacement in self.TERMINOLOGY_ABBREVIATIONS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        return cleaned

    def _standardize_role(self, role: str) -> str:
        cleaned = re.sub(r"\s+", " ", (role or "").strip())
        if not cleaned or cleaned.upper() in ("NONE", "UNKNOWN", "TBD", "N/A", "UNASSIGNED", "SOMEONE"):
            return "UNASSIGNED"
        return self._standardize_name(cleaned)

    def _classify_activity_type(self, raw_type: str, name: str, description: str) -> str:
        candidate = (raw_type or "").strip().lower()
        combined = f"{name} {description}".lower()

        if candidate in self.VALID_TYPES:
            return candidate

        if any(w in combined for w in ("approve", "sign-off", "authorization", "dual-custody")):
            return ActivityTypeEnum.APPROVAL.value
        if any(w in combined for w in ("evaluate", "triage", "decide", "determine whether", "threshold")):
            return ActivityTypeEnum.DECISION.value
        if any(w in combined for w in ("escalate", "discrepancy", "quarantine", "breach", "adverse")):
            return ActivityTypeEnum.ESCALATION.value
        if any(w in combined for w in ("notify", "notification", "dispatch final", "welcome")):
            return ActivityTypeEnum.NOTIFICATION.value
        if any(w in combined for w in ("automated", "engine", "bot", "daemon", "ocr", "mint ephemeral")):
            return ActivityTypeEnum.AUTOMATED.value
        return ActivityTypeEnum.MANUAL.value

    @staticmethod
    def _token_set(text: str) -> Set[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        stop = {"the", "and", "or", "to", "in", "for", "of", "with", "a", "an", "on", "by"}
        return {t for t in tokens if len(t) > 2 and t not in stop}

    def _detect_duplicates(self, activities: List[Dict[str, Any]]) -> int:
        dup_count = 0
        token_cache = [
            (act["activity_id"], self._token_set(f"{act['activity_name']} {act['description']}"))
            for act in activities
        ]
        for i, act in enumerate(activities):
            act["potential_duplicate_of"] = None
            _, tokens_i = token_cache[i]
            if not tokens_i:
                continue
            for j in range(i):
                prev_id, tokens_j = token_cache[j]
                if not tokens_j:
                    continue
                inter = len(tokens_i & tokens_j)
                union = len(tokens_i | tokens_j)
                jaccard = inter / union if union > 0 else 0.0
                if jaccard >= 0.78:
                    act["potential_duplicate_of"] = prev_id
                    dup_count += 1
                    break
        return dup_count

    def run(self, state: ExtractionGraphState) -> ExtractionGraphState:
        start_ts = time.perf_counter()
        intermediate = copy.deepcopy(state.get("intermediate_extraction") or {})
        activities = intermediate.get("activities", [])

        role_canonical_map: Dict[str, str] = {}
        for act in activities:
            act["activity_name"] = self._standardize_name(act.get("activity_name", ""))
            raw_role = act.get("responsible_role", "UNASSIGNED")
            norm_role = self._standardize_role(raw_role)
            role_canonical_map[raw_role] = norm_role
            act["responsible_role"] = norm_role
            act["activity_type"] = self._classify_activity_type(
                act.get("activity_type", ""),
                act["activity_name"],
                act.get("description", ""),
            )

        for actor in intermediate.get("actors", []):
            actor["role_name"] = self._standardize_role(actor.get("role_name", ""))

        dup_count = self._detect_duplicates(activities)

        duration_ms = round((time.perf_counter() - start_ts) * 1000.0, 2)
        trace = list(state.get("agent_trace") or [])
        trace.append(
            {
                "agent_name": self.AGENT_NAME,
                "status": "COMPLETED",
                "duration_ms": duration_ms,
                "summary": (
                    f"Standardised {len(activities)} activity names and {len(intermediate.get('actors', []))} role names; "
                    f"classified activity categories; detected {dup_count} potential duplicate(s)."
                ),
                "items_processed": len(activities),
                "warnings_count": dup_count,
                "retry_iteration": state.get("retry_count", 0),
            }
        )

        return {
            **state,
            "normalized_extraction": intermediate,
            "agent_trace": trace,
        }


agent3_normalization = ClassificationNormalizationAgent()
