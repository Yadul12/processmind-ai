export type ActivityType =
  | 'manual'
  | 'automated'
  | 'approval'
  | 'decision'
  | 'notification'
  | 'escalation'
  | 'integration';

export type ValidationStatus =
  | 'VALID'
  | 'VALID_WITH_WARNINGS'
  | 'NEEDS_REVIEW'
  | 'INVALID';

export type ReviewStatus =
  | 'PENDING_REVIEW'
  | 'IN_REVIEW'
  | 'APPROVED'
  | 'REJECTED';

export type ActivityReviewDecision =
  | 'PENDING'
  | 'APPROVED'
  | 'REJECTED'
  | 'EDITED';

export type DependencyType =
  | 'sequential'
  | 'conditional_true'
  | 'conditional_false'
  | 'approval_gated'
  | 'exception_escalation'
  | 'parallel_join';

export interface SourceReference {
  document_id: string;
  section: string;
  page_or_sheet: string;
  line_or_row: string;
  exact_quote: string;
  block_id?: string | null;
}

export interface ConfidenceBreakdown {
  citation_anchoring_score: number;
  actor_specificity_score: number;
  io_completeness_score: number;
  graph_coherence_score: number;
  ambiguity_penalty: number;
  final_score: number;
  scoring_rationale: string;
}

export interface FieldLevelValidationError {
  error_code: string;
  severity: 'ERROR' | 'WARNING' | 'AMBIGUITY';
  field_path: string;
  activity_id?: string | null;
  message: string;
  suggested_remediation?: string | null;
  source_quote?: string | null;
}

export interface ProcessActivity {
  activity_id: string;
  activity_name: string;
  description: string;
  activity_type: ActivityType;
  responsible_role: string;
  department: string;
  input: string[];
  output: string[];
  preconditions: string[];
  postconditions: string[];
  dependencies: string[];
  source_reference: SourceReference;
  confidence_score: number;
  field_citations: Record<string, string>;
  confidence_breakdown?: ConfidenceBreakdown | null;
  is_uncertain: boolean;
  uncertainty_reason?: string | null;
  potential_duplicate_of?: string | null;
  review_decision: ActivityReviewDecision;
  reviewer_note?: string | null;
}

export interface ProcessActor {
  actor_id: string;
  role_name: string;
  department: string;
  is_approver: boolean;
  assigned_activity_ids: string[];
  source_reference?: SourceReference | null;
}

export interface BusinessCondition {
  condition_id: string;
  name: string;
  rule_expression: string;
  decision_activity_id: string;
  branch_when_true?: string | null;
  branch_when_false?: string | null;
  source_reference: SourceReference;
  confidence_score: number;
}

export interface ActivityDependency {
  dependency_id: string;
  source_activity_id: string;
  target_activity_id: string;
  dependency_type: DependencyType;
  condition_label?: string | null;
  source_reference?: SourceReference | null;
}

export interface ProcessIO {
  io_id: string;
  name: string;
  io_type: string;
  artifact_format: string;
  associated_activity_id: string;
  source_reference?: SourceReference | null;
}

export interface ProcessException {
  exception_id: string;
  exception_name: string;
  trigger_condition: string;
  source_activity_id: string;
  escalation_role: string;
  target_recovery_activity_id?: string | null;
  remediation_action: string;
  sla_hours?: number | null;
  source_reference: SourceReference;
  confidence_score: number;
}

export interface ApprovalGate {
  approval_id: string;
  activity_id: string;
  approver_role: string;
  department: string;
  approval_criteria: string;
  threshold_rule?: string | null;
  rejection_target_activity_id?: string | null;
  sla_hours?: number | null;
  source_reference: SourceReference;
  confidence_score: number;
}

export interface DocumentSourceRef {
  document_id: string;
  filename: string;
  file_type: string;
  checksum_sha256: string;
  extracted_at: string;
}

export interface AgentExecutionStep {
  agent_name: string;
  status: string;
  duration_ms: number;
  summary: string;
  items_processed: number;
  warnings_count: number;
  retry_iteration: number;
}

export interface ReviewerComment {
  comment_id: string;
  author: string;
  role: string;
  activity_id?: string | null;
  comment: string;
  created_at: string;
}

export interface AuditLogEntry {
  log_id: string;
  version: number;
  action: string;
  actor: string;
  details: string;
  timestamp: string;
}

export interface ProcessModel {
  process_id: string;
  process_name: string;
  document_source: DocumentSourceRef;
  version: number;
  activities: ProcessActivity[];
  actors: ProcessActor[];
  conditions: BusinessCondition[];
  dependencies: ActivityDependency[];
  inputs: ProcessIO[];
  outputs: ProcessIO[];
  exceptions: ProcessException[];
  approvals: ApprovalGate[];
  validation_status: ValidationStatus;
  schema_version: string;
  review_status: ReviewStatus;
  overall_confidence: number;
  needs_human_review: boolean;
  review_routing_reasons: string[];
  validation_errors: FieldLevelValidationError[];
  agent_trace: AgentExecutionStep[];
  reviewer_comments: ReviewerComment[];
  audit_logs: AuditLogEntry[];
  approved_by?: string | null;
  approved_at?: string | null;
  rejected_by?: string | null;
  rejected_at?: string | null;
  rejection_reason?: string | null;
}

export interface ProcessSummary {
  process_id: string;
  process_name: string;
  document_id: string;
  document_filename: string;
  version: number;
  activity_count: number;
  actor_count: number;
  condition_count: number;
  approval_count: number;
  exception_count: number;
  validation_status: ValidationStatus;
  review_status: ReviewStatus;
  overall_confidence: number;
  needs_human_review: boolean;
  validation_error_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentSectionBlock {
  block_id: string;
  section_ref: string;
  page_or_sheet: string;
  line_or_row: string;
  block_type: string;
  text: string;
  detected_step_number?: string | null;
  detected_role_hint?: string | null;
  is_decision_statement: boolean;
  is_approval_statement: boolean;
  is_exception_statement: boolean;
}

export interface DetectedTable {
  table_id: string;
  page_or_sheet: string;
  section_ref: string;
  headers: string[];
  rows: Record<string, string>[];
}

export interface DocumentMetadata {
  title: string;
  document_code?: string | null;
  department?: string | null;
  effective_date?: string | null;
  owner_role?: string | null;
  page_or_sheet_count: number;
  section_count: number;
  numbered_step_count: number;
  table_count: number;
  decision_statement_count: number;
}

export interface ParsedDocumentStructure {
  document_id: string;
  filename: string;
  file_type: 'pdf' | 'docx' | 'xlsx' | 'txt';
  metadata: DocumentMetadata;
  headings: string[];
  blocks: DocumentSectionBlock[];
  tables: DetectedTable[];
  numbered_steps: string[];
  decision_statements: string[];
}

export interface DocumentSummary {
  id: string;
  filename: string;
  file_type: 'pdf' | 'docx' | 'xlsx' | 'txt';
  file_size_bytes: number;
  checksum_sha256: string;
  metadata: DocumentMetadata;
  created_at: string;
}

export interface DocumentDetail extends DocumentSummary {
  raw_text: string;
  parsed_structure: ParsedDocumentStructure;
}

export interface ProcessVersionItem {
  version: number;
  validation_status: ValidationStatus;
  review_status: ReviewStatus;
  overall_confidence: number;
  change_summary: string;
  changed_by: string;
  created_at: string;
  process_model: ProcessModel;
}

export interface ProcessVersionHistory {
  process_id: string;
  current_version: number;
  versions: ProcessVersionItem[];
}

export interface DocumentExtractionEvalResult {
  case_id: string;
  document_filename: string;
  process_name: string;
  category: string;
  activity_precision: number;
  activity_recall: number;
  activity_f1: number;
  actor_accuracy: number;
  dependency_accuracy: number;
  decision_condition_accuracy: number;
  schema_validation_passed: boolean;
  source_citation_correctness: number;
  evalguard_faithfulness: number;
  evalguard_hallucination_rate: number;
  evalguard_overall_score: number;
  expected_activity_count: number;
  extracted_activity_count: number;
  matched_activity_count: number;
  ambiguity_detection_passed: boolean;
  notes: string[];
}

export interface EvalGuardSuiteReport {
  adapter_name: string;
  evaluated_at: string;
  total_cases: number;
  mean_activity_precision: number;
  mean_activity_recall: number;
  mean_activity_f1: number;
  mean_actor_accuracy: number;
  mean_dependency_accuracy: number;
  mean_decision_condition_accuracy: number;
  schema_validation_pass_rate: number;
  mean_source_citation_correctness: number;
  mean_evalguard_faithfulness: number;
  mean_evalguard_hallucination_rate: number;
  mean_evalguard_overall_score: number;
  edge_case_pass_rate: number;
  results: DocumentExtractionEvalResult[];
}
