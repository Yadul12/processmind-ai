"""
Typed State Definition for the LangGraph 5-Agent Process Extraction Pipeline.
"""

from typing import Any, Dict, List, Optional, TypedDict


class ExtractionGraphState(TypedDict, total=False):
    # Input context
    document_id: str
    filename: str
    file_type: str
    checksum_sha256: str
    raw_text: str
    custom_process_name: Optional[str]

    # Agent 1 output
    parsed_document: Dict[str, Any]

    # Agent 2 output
    intermediate_extraction: Dict[str, Any]

    # Agent 3 output
    normalized_extraction: Dict[str, Any]

    # Agent 4 output
    validation_errors: List[Dict[str, Any]]
    validation_status: str
    needs_retry: bool
    retry_count: int
    max_retries: int
    retry_feedback: List[str]

    # Agent 5 output
    final_process_model: Dict[str, Any]

    # Execution telemetry across all agents
    agent_trace: List[Dict[str, Any]]
