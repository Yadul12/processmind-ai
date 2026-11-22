"""
LangGraph Multi-Agent Orchestrator for ProcessMind AI.
Orchestrates the 5 specialized agents with controlled state transitions,
conditional retry routing, and bounded execution.
"""

import logging
from typing import Literal, Optional

from langgraph.graph import END, StateGraph

from backend.agents.agent1_understanding import agent1_understanding
from backend.agents.agent2_extraction import agent2_extraction
from backend.agents.agent3_normalization import agent3_normalization
from backend.agents.agent4_validation import agent4_validation
from backend.agents.agent5_review_prep import agent5_review_prep
from backend.agents.state import ExtractionGraphState
from backend.config import settings
from backend.schemas.document import ParsedDocumentStructure
from backend.schemas.process import ProcessModelSchema

logger = logging.getLogger("processmind.orchestrator")


def _route_after_validation(
    state: ExtractionGraphState,
) -> Literal["agent2_extraction", "agent5_review_prep"]:
    """Controlled transition: retry extraction if Agent 4 requested a retry within max_retries."""
    if state.get("needs_retry") and int(state.get("retry_count", 0)) <= int(state.get("max_retries", 2)):
        logger.info("LangGraph routing back to Agent 2 for bounded retry #%d", state.get("retry_count", 0))
        return "agent2_extraction"
    return "agent5_review_prep"


class ProcessMindLangGraphOrchestrator:
    """Compiles and executes the 5-agent LangGraph StateGraph workflow."""

    def __init__(self) -> None:
        workflow = StateGraph(ExtractionGraphState)

        workflow.add_node("agent1_understanding", agent1_understanding.run)
        workflow.add_node("agent2_extraction", agent2_extraction.run)
        workflow.add_node("agent3_normalization", agent3_normalization.run)
        workflow.add_node("agent4_validation", agent4_validation.run)
        workflow.add_node("agent5_review_prep", agent5_review_prep.run)

        workflow.set_entry_point("agent1_understanding")
        workflow.add_edge("agent1_understanding", "agent2_extraction")
        workflow.add_edge("agent2_extraction", "agent3_normalization")
        workflow.add_edge("agent3_normalization", "agent4_validation")
        workflow.add_conditional_edges(
            "agent4_validation",
            _route_after_validation,
            {
                "agent2_extraction": "agent2_extraction",
                "agent5_review_prep": "agent5_review_prep",
            },
        )
        workflow.add_edge("agent5_review_prep", END)

        self.compiled_graph = workflow.compile()

    def execute_pipeline(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        checksum_sha256: str,
        raw_text: str,
        parsed_document: Optional[ParsedDocumentStructure] = None,
        custom_process_name: Optional[str] = None,
    ) -> ProcessModelSchema:
        initial_state: ExtractionGraphState = {
            "document_id": document_id,
            "filename": filename,
            "file_type": file_type,
            "checksum_sha256": checksum_sha256,
            "raw_text": raw_text,
            "custom_process_name": custom_process_name,
            "parsed_document": parsed_document.model_dump(mode="json") if parsed_document else {},
            "retry_count": 0,
            "max_retries": settings.langgraph_max_retries,
            "agent_trace": [],
        }

        final_state = self.compiled_graph.invoke(
            initial_state,
            config={"recursion_limit": 20},
        )
        return ProcessModelSchema.model_validate(final_state["final_process_model"])


process_orchestrator = ProcessMindLangGraphOrchestrator()
