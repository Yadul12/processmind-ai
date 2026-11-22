"""
Document Understanding & Ingestion Schemas (Pydantic v2).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DocumentFileTypeEnum(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"


class DocumentSectionBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    block_id: str = Field(..., min_length=1)
    section_ref: str = Field(..., description="Section heading or number, e.g. 'Section 3.2'")
    page_or_sheet: str = Field(..., description="Page N or Sheet: <Name> reference")
    line_or_row: str = Field(default="Line 1", description="Line number or Row index reference")
    block_type: str = Field(
        default="paragraph",
        description="heading | numbered_step | table_row | decision_statement | exception_clause | paragraph",
    )
    text: str = Field(..., min_length=1)
    detected_step_number: Optional[str] = None
    detected_role_hint: Optional[str] = None
    is_decision_statement: bool = False
    is_approval_statement: bool = False
    is_exception_statement: bool = False


class DetectedTableSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    table_id: str
    page_or_sheet: str
    section_ref: str
    headers: List[str]
    rows: List[Dict[str, str]]


class DocumentMetadataSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    document_code: Optional[str] = None
    department: Optional[str] = None
    effective_date: Optional[str] = None
    owner_role: Optional[str] = None
    page_or_sheet_count: int = Field(default=1, ge=1)
    section_count: int = Field(default=0, ge=0)
    numbered_step_count: int = Field(default=0, ge=0)
    table_count: int = Field(default=0, ge=0)
    decision_statement_count: int = Field(default=0, ge=0)


class ParsedDocumentStructure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    filename: str
    file_type: DocumentFileTypeEnum
    metadata: DocumentMetadataSchema
    headings: List[str] = Field(default_factory=list)
    blocks: List[DocumentSectionBlock] = Field(default_factory=list)
    tables: List[DetectedTableSchema] = Field(default_factory=list)
    numbered_steps: List[str] = Field(default_factory=list)
    decision_statements: List[str] = Field(default_factory=list)


class DocumentRecordSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    filename: str
    file_type: DocumentFileTypeEnum
    file_size_bytes: int
    checksum_sha256: str
    raw_text: str
    parsed_structure: ParsedDocumentStructure
    metadata: DocumentMetadataSchema
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
