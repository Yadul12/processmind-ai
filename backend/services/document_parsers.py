"""
Multi-Format Document Parser Service (PDF, DOCX, Excel .xlsx, TXT).
Preserves page, sheet, table, and section references for downstream Agent 1 (Document Understanding).
"""

import io
import re
from pathlib import Path
from typing import Dict, List, Tuple

import docx
import openpyxl
from pypdf import PdfReader

from backend.schemas.document import (
    DetectedTableSchema,
    DocumentFileTypeEnum,
    DocumentSectionBlock,
)


def detect_file_type(filename: str) -> DocumentFileTypeEnum:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext == "pdf":
        return DocumentFileTypeEnum.PDF
    if ext in ("docx", "doc"):
        return DocumentFileTypeEnum.DOCX
    if ext in ("xlsx", "xls"):
        return DocumentFileTypeEnum.XLSX
    if ext in ("txt", "md", "csv"):
        return DocumentFileTypeEnum.TXT
    raise ValueError(f"Unsupported document format '.{ext}'. Supported formats: PDF, DOCX, XLSX, TXT.")


class MultiFormatDocumentParser:
    """Extracts raw lines, page/sheet coordinates, and tabular structures from PDF, DOCX, XLSX, and TXT files."""

    SECTION_PATTERN = re.compile(
        r"^(?:===\s*)?(Section\s+\d+(?:\.\d+)?[^=]*|\d+\.\d+\s+[A-Za-z][^=]*)(?:\s*===)?$",
        re.IGNORECASE,
    )
    STEP_PATTERN = re.compile(r"^(?:Step\s+(\d+)|(\d+)\.\s+|\[?(ACT-\d+)\]?)", re.IGNORECASE)
    DECISION_KEYWORDS = re.compile(
        r"\b(DECISION RULE|IF\s+.*THEN|ELSE\s+IF|WHETHER|THRESHOLD|BRANCH|EVALUATE)\b",
        re.IGNORECASE,
    )
    APPROVAL_KEYWORDS = re.compile(
        r"\b(APPROVAL GATE|APPROVE|APPROVER|SIGN-OFF|AUTHORIZATION|DUAL-CUSTODY)\b",
        re.IGNORECASE,
    )
    EXCEPTION_KEYWORDS = re.compile(
        r"\b(EXCEPTION RULE|ESCALATE|ESCALATION|DISCREPANCY|VIOLATION|BREACH|QUARANTINE)\b",
        re.IGNORECASE,
    )

    def parse_bytes(
        self,
        content_bytes: bytes,
        filename: str,
        document_id: str,
    ) -> Tuple[DocumentFileTypeEnum, str, List[DocumentSectionBlock], List[DetectedTableSchema], int]:
        file_type = detect_file_type(filename)
        if file_type == DocumentFileTypeEnum.PDF:
            return self._parse_pdf(content_bytes, document_id)
        if file_type == DocumentFileTypeEnum.DOCX:
            return self._parse_docx(content_bytes, document_id)
        if file_type == DocumentFileTypeEnum.XLSX:
            return self._parse_xlsx(content_bytes, document_id)
        return self._parse_txt(content_bytes, document_id)

    def _classify_line(
        self,
        line: str,
        block_idx: int,
        current_section: str,
        page_or_sheet: str,
        line_or_row: str,
    ) -> Tuple[DocumentSectionBlock, str]:
        cleaned = line.strip()
        sec_match = self.SECTION_PATTERN.match(cleaned)
        if sec_match or cleaned.startswith("==="):
            sec_title = cleaned.strip("= ").strip()
            sec_title = re.sub(r"\(Page\s+\d+\)$", "", sec_title).strip()
            current_section = sec_title
            block = DocumentSectionBlock(
                block_id=f"BLK-{block_idx:04d}",
                section_ref=current_section,
                page_or_sheet=page_or_sheet,
                line_or_row=line_or_row,
                block_type="heading",
                text=cleaned,
            )
            return block, current_section

        step_match = self.STEP_PATTERN.match(cleaned)
        is_decision = bool(self.DECISION_KEYWORDS.search(cleaned))
        is_approval = bool(self.APPROVAL_KEYWORDS.search(cleaned))
        is_exception = bool(self.EXCEPTION_KEYWORDS.search(cleaned))

        role_hint = None
        if "Role:" in cleaned:
            after_role = cleaned.split("Role:", 1)[1]
            role_hint = after_role.split("|")[0].strip()

        if cleaned.startswith("DECISION RULE"):
            btype = "decision_statement"
        elif cleaned.startswith("EXCEPTION RULE"):
            btype = "exception_clause"
        elif step_match:
            btype = "numbered_step"
        elif is_decision:
            btype = "decision_statement"
        else:
            btype = "paragraph"

        step_num = None
        if step_match:
            step_num = step_match.group(1) or step_match.group(2) or step_match.group(3)

        block = DocumentSectionBlock(
            block_id=f"BLK-{block_idx:04d}",
            section_ref=current_section,
            page_or_sheet=page_or_sheet,
            line_or_row=line_or_row,
            block_type=btype,
            text=cleaned,
            detected_step_number=step_num,
            detected_role_hint=role_hint,
            is_decision_statement=is_decision,
            is_approval_statement=is_approval,
            is_exception_statement=is_exception,
        )
        return block, current_section

    def _parse_txt(
        self,
        content_bytes: bytes,
        document_id: str,
    ) -> Tuple[DocumentFileTypeEnum, str, List[DocumentSectionBlock], List[DetectedTableSchema], int]:
        raw_text = content_bytes.decode("utf-8", errors="replace")
        blocks: List[DocumentSectionBlock] = []
        current_section = "Section 1.0 - General"
        current_page = "Page 1"
        max_page = 1
        block_idx = 1

        for line_no, raw_line in enumerate(raw_text.splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            page_match = re.search(r"\(Page\s+(\d+)\)", stripped, re.IGNORECASE)
            if page_match:
                pnum = int(page_match.group(1))
                max_page = max(max_page, pnum)
                current_page = f"Page {pnum}"
            block, current_section = self._classify_line(
                stripped,
                block_idx,
                current_section,
                current_page,
                f"Line {line_no}",
            )
            blocks.append(block)
            block_idx += 1

        return DocumentFileTypeEnum.TXT, raw_text, blocks, [], max_page

    def _parse_pdf(
        self,
        content_bytes: bytes,
        document_id: str,
    ) -> Tuple[DocumentFileTypeEnum, str, List[DocumentSectionBlock], List[DetectedTableSchema], int]:
        reader = PdfReader(io.BytesIO(content_bytes))
        blocks: List[DocumentSectionBlock] = []
        raw_pages_text: List[str] = []
        current_section = "Section 1.0 - Document Root"
        block_idx = 1

        for page_idx, page in enumerate(reader.pages, start=1):
            page_ref = f"Page {page_idx}"
            page_text = page.extract_text() or ""
            raw_pages_text.append(f"--- {page_ref} ---\n{page_text}")
            for line_no, raw_line in enumerate(page_text.splitlines(), start=1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                block, current_section = self._classify_line(
                    stripped,
                    block_idx,
                    current_section,
                    page_ref,
                    f"Line {line_no}",
                )
                blocks.append(block)
                block_idx += 1

        page_count = max(1, len(reader.pages))
        return DocumentFileTypeEnum.PDF, "\n\n".join(raw_pages_text), blocks, [], page_count

    def _parse_docx(
        self,
        content_bytes: bytes,
        document_id: str,
    ) -> Tuple[DocumentFileTypeEnum, str, List[DocumentSectionBlock], List[DetectedTableSchema], int]:
        doc = docx.Document(io.BytesIO(content_bytes))
        blocks: List[DocumentSectionBlock] = []
        tables: List[DetectedTableSchema] = []
        raw_lines: List[str] = []
        current_section = "Section 1.0 - Overview"
        current_page = "Page 1"
        block_idx = 1

        for para_no, para in enumerate(doc.paragraphs, start=1):
            stripped = para.text.strip()
            if not stripped:
                continue
            raw_lines.append(stripped)
            style_name = (para.style.name if para.style else "").lower()
            if "heading" in style_name or stripped.startswith("Section "):
                current_section = stripped.strip("= ")
                if "Section 3" in current_section:
                    current_page = "Page 2"
                blocks.append(
                    DocumentSectionBlock(
                        block_id=f"BLK-{block_idx:04d}",
                        section_ref=current_section,
                        page_or_sheet=current_page,
                        line_or_row=f"Paragraph {para_no}",
                        block_type="heading",
                        text=stripped,
                    )
                )
                block_idx += 1
                continue

            block, current_section = self._classify_line(
                stripped,
                block_idx,
                current_section,
                current_page,
                f"Paragraph {para_no}",
            )
            blocks.append(block)
            block_idx += 1

        for t_idx, table in enumerate(doc.tables, start=1):
            headers: List[str] = []
            rows_data: List[Dict[str, str]] = []
            for r_idx, row in enumerate(table.rows):
                cells = [c.text.strip() for c in row.cells]
                if r_idx == 0:
                    headers = [h or f"Col_{i}" for i, h in enumerate(cells)]
                else:
                    row_dict = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
                    rows_data.append(row_dict)
            tables.append(
                DetectedTableSchema(
                    table_id=f"TBL-{t_idx:02d}",
                    page_or_sheet=current_page,
                    section_ref=current_section,
                    headers=headers,
                    rows=rows_data,
                )
            )

        page_count = 2 if current_page == "Page 2" else 1
        return DocumentFileTypeEnum.DOCX, "\n".join(raw_lines), blocks, tables, page_count

    def _parse_xlsx(
        self,
        content_bytes: bytes,
        document_id: str,
    ) -> Tuple[DocumentFileTypeEnum, str, List[DocumentSectionBlock], List[DetectedTableSchema], int]:
        wb = openpyxl.load_workbook(io.BytesIO(content_bytes), data_only=True)
        blocks: List[DocumentSectionBlock] = []
        tables: List[DetectedTableSchema] = []
        raw_lines: List[str] = []
        block_idx = 1

        for t_idx, sheet_name in enumerate(wb.sheetnames, start=1):
            ws = wb[sheet_name]
            sheet_ref = f"Sheet: {sheet_name}"
            raw_lines.append(f"=== {sheet_ref} ===")
            headers: List[str] = []
            rows_data: List[Dict[str, str]] = []
            current_section = f"Section 1.0 - {sheet_name}"

            for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                cells = [str(c).strip() if c is not None else "" for c in row]
                if not any(cells):
                    continue
                if r_idx == 1:
                    headers = [h or f"Col_{i}" for i, h in enumerate(cells)]
                    continue

                row_dict = {headers[i]: cells[i] for i in range(min(len(headers), len(cells)))}
                rows_data.append(row_dict)

                if sheet_name == "SOP_Overview" and len(cells) >= 2:
                    joined = f"{cells[0]}: {cells[1]}"
                    raw_lines.append(joined)
                    block, current_section = self._classify_line(
                        joined,
                        block_idx,
                        current_section,
                        sheet_ref,
                        f"Row {r_idx}",
                    )
                    blocks.append(block)
                    block_idx += 1
                else:
                    sec_val = row_dict.get("Section") or current_section
                    if sec_val != current_section:
                        current_section = sec_val
                        blocks.append(
                            DocumentSectionBlock(
                                block_id=f"BLK-{block_idx:04d}",
                                section_ref=current_section,
                                page_or_sheet=sheet_ref,
                                line_or_row=f"Row {r_idx}",
                                block_type="heading",
                                text=current_section,
                            )
                        )
                        block_idx += 1
                    instr = row_dict.get("Instruction_Line") or " | ".join(c for c in cells if c)
                    raw_lines.append(instr)
                    block, current_section = self._classify_line(
                        instr,
                        block_idx,
                        current_section,
                        sheet_ref,
                        f"Row {r_idx}",
                    )
                    blocks.append(block)
                    block_idx += 1

            tables.append(
                DetectedTableSchema(
                    table_id=f"TBL-XLSX-{t_idx:02d}",
                    page_or_sheet=sheet_ref,
                    section_ref=current_section,
                    headers=headers,
                    rows=rows_data,
                )
            )

        return DocumentFileTypeEnum.XLSX, "\n".join(raw_lines), blocks, tables, max(1, len(wb.sheetnames))


document_parser = MultiFormatDocumentParser()
