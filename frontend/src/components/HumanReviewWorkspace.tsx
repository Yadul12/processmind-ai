import React, { useMemo, useState } from 'react';
import {
  FileText,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Edit3,
  ThumbsUp,
  ThumbsDown,
  ShieldAlert,
  History,
  MessageSquare,
  Table,
  RefreshCw,
  Check,
  GitBranch,
  ShieldCheck,
  Flame,
} from 'lucide-react';
import {
  ActivityReviewDecision,
  DocumentDetail,
  ProcessActivity,
  ProcessModel,
  ProcessVersionHistory,
} from '../types/process';

interface HumanReviewWorkspaceProps {
  processModel: ProcessModel;
  documentDetail: DocumentDetail | null;
  versionHistory: ProcessVersionHistory | null;
  selectedActivityId: string | null;
  reviewerName: string;
  onReviewerNameChange: (name: string) => void;
  onSelectActivity: (activityId: string) => void;
  onEditActivity: (activity: ProcessActivity) => void;
  onReviewActivity: (activityId: string, decision: ActivityReviewDecision) => Promise<void>;
  onApproveProcess: (comment: string) => Promise<void>;
  onRejectProcess: (reason: string) => Promise<void>;
  onRevalidateProcess: () => Promise<void>;
}

export const HumanReviewWorkspace: React.FC<HumanReviewWorkspaceProps> = ({
  processModel,
  documentDetail,
  versionHistory,
  selectedActivityId,
  reviewerName,
  onReviewerNameChange,
  onSelectActivity,
  onEditActivity,
  onReviewActivity,
  onApproveProcess,
  onRejectProcess,
  onRevalidateProcess,
}) => {
  const [docTab, setDocTab] = useState<'blocks' | 'tables' | 'raw'>('blocks');
  const [filterMode, setFilterMode] = useState<'all' | 'uncertain' | 'pending'>('all');
  const [bottomTab, setBottomTab] = useState<'rules' | 'audit' | 'versions'>('rules');
  const [reviewComment, setReviewComment] = useState(
    'Verified extracted process activities, actor assignments, and conditional branches against source SOP.'
  );
  const [rejectionReason, setRejectionReason] = useState('');
  const [showRejectBox, setShowRejectBox] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [actionFeedback, setActionFeedback] = useState<{
    type: 'success' | 'error';
    text: string;
  } | null>(null);

  const selectedActivity = useMemo(
    () =>
      processModel.activities.find((a) => a.activity_id === selectedActivityId) ||
      processModel.activities[0] ||
      null,
    [processModel.activities, selectedActivityId]
  );

  const filteredActivities = useMemo(() => {
    return processModel.activities.filter((act) => {
      if (filterMode === 'uncertain') return act.is_uncertain;
      if (filterMode === 'pending') return act.review_decision === 'PENDING';
      return true;
    });
  }, [processModel.activities, filterMode]);

  const blockingErrorCount = useMemo(
    () => processModel.validation_errors.filter((e) => e.severity === 'ERROR').length,
    [processModel.validation_errors]
  );

  const uncertainCount = useMemo(
    () => processModel.activities.filter((a) => a.is_uncertain).length,
    [processModel.activities]
  );

  const handleApproveAllProcess = async () => {
    setSubmittingAction(true);
    setActionFeedback(null);
    try {
      await onApproveProcess(reviewComment);
      setActionFeedback({
        type: 'success',
        text: `Process model v${processModel.version} formally approved by ${reviewerName}.`,
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to approve process model',
      });
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleRejectAllProcess = async () => {
    if (rejectionReason.trim().length < 5) {
      setActionFeedback({
        type: 'error',
        text: 'Please provide a rejection explanation (minimum 5 characters).',
      });
      return;
    }
    setSubmittingAction(true);
    setActionFeedback(null);
    try {
      await onRejectProcess(rejectionReason.trim());
      setShowRejectBox(false);
      setRejectionReason('');
      setActionFeedback({
        type: 'success',
        text: `Process model v${processModel.version} marked as REJECTED.`,
      });
    } catch (err: unknown) {
      setActionFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Failed to reject process model',
      });
    } finally {
      setSubmittingAction(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Top Human Review Governance & Sign-Off Bar */}
      <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <div>
              <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                Human-in-the-Loop Governance Gate
              </div>
              <div className="text-sm font-bold text-white flex items-center gap-2 mt-0.5">
                <span>
                  {processModel.process_name} (v{processModel.version})
                </span>
                <span
                  className={`text-xs px-2 py-0.5 rounded font-semibold border ${
                    processModel.review_status === 'APPROVED'
                      ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                      : processModel.review_status === 'REJECTED'
                      ? 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                      : 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                  }`}
                >
                  {processModel.review_status}
                </span>
              </div>
            </div>

            {processModel.approved_by && (
              <div className="text-xs px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-emerald-200">
                Signed off by <span className="font-semibold">{processModel.approved_by}</span>
              </div>
            )}
            {processModel.rejected_by && (
              <div className="text-xs px-3 py-1.5 rounded-lg bg-rose-950/40 border border-rose-500/30 text-rose-200">
                Rejected by <span className="font-semibold">{processModel.rejected_by}</span>:{' '}
                {processModel.rejection_reason}
              </div>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1.5 bg-slate-950 px-2.5 py-1.5 rounded-lg border border-slate-800">
              <span className="text-xs text-slate-400">Reviewer:</span>
              <input
                type="text"
                value={reviewerName}
                onChange={(e) => onReviewerNameChange(e.target.value)}
                className="bg-transparent text-xs font-medium text-white focus:outline-none w-44"
              />
            </div>

            <button
              onClick={onRevalidateProcess}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Re-Validate (Agent 4)
            </button>

            <button
              onClick={() => setShowRejectBox((prev) => !prev)}
              disabled={submittingAction}
              className="px-3 py-1.5 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/40 text-xs font-semibold flex items-center gap-1.5"
            >
              <XCircle className="w-3.5 h-3.5" />
              Reject Process
            </button>

            <button
              onClick={handleApproveAllProcess}
              disabled={submittingAction}
              className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-emerald-600/20"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              Approve Complete Process Model
            </button>
          </div>
        </div>

        {/* Reviewer Sign-off Comment input */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 shrink-0">Sign-Off Audit Note:</span>
          <input
            type="text"
            value={reviewComment}
            onChange={(e) => setReviewComment(e.target.value)}
            className="flex-1 px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {showRejectBox && (
          <div className="p-3 rounded-lg bg-rose-950/30 border border-rose-500/40 flex flex-wrap items-center gap-2">
            <input
              type="text"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Enter mandatory rejection reason (e.g., contradictory instructions or missing role authority)..."
              className="flex-1 px-3 py-1.5 rounded-lg bg-slate-950 border border-rose-500/40 text-xs text-white focus:outline-none"
            />
            <button
              onClick={handleRejectAllProcess}
              disabled={submittingAction}
              className="px-3 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold"
            >
              Confirm Rejection
            </button>
          </div>
        )}

        {actionFeedback && (
          <div
            className={`p-3 rounded-lg text-xs flex items-center justify-between ${
              actionFeedback.type === 'success'
                ? 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-200'
                : 'bg-rose-500/15 border border-rose-500/40 text-rose-200'
            }`}
          >
            <span>{actionFeedback.text}</span>
            <button
              onClick={() => setActionFeedback(null)}
              className="text-xs underline ml-4 opacity-80 hover:opacity-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Agent 4 Validation Errors & Ambiguity Banner */}
        {processModel.validation_errors.length > 0 && (
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/40 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                <ShieldAlert className="w-4 h-4 text-amber-400" />
                Agent 4 Validation & Ambiguity Findings ({processModel.validation_errors.length} issue(s) —{' '}
                {blockingErrorCount} blocking error(s))
              </span>
              <span className="text-[11px] text-amber-200/80">
                Blocking ERRORs must be resolved via "Edit" before final process approval
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {processModel.validation_errors.map((err, idx) => (
                <div
                  key={idx}
                  onClick={() => err.activity_id && onSelectActivity(err.activity_id)}
                  className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                    err.severity === 'ERROR'
                      ? 'bg-rose-950/35 border-rose-500/40 text-rose-200 hover:border-rose-400'
                      : 'bg-slate-950/80 border-amber-500/30 text-amber-200 hover:border-amber-400'
                  }`}
                >
                  <div className="flex items-center justify-between font-mono text-[11px] font-bold">
                    <span>
                      [{err.severity}] {err.error_code}
                    </span>
                    <span className="text-slate-400">{err.field_path}</span>
                  </div>
                  <p className="mt-1 text-slate-200 leading-snug">{err.message}</p>
                  {err.suggested_remediation && (
                    <p className="mt-1 text-[11px] text-emerald-300">
                      Remediation: {err.suggested_remediation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Side-by-Side Split Workspace: Source Document (Left) vs Extracted Process Steps (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* LEFT PANE: Source Document Inspector */}
        <div className="lg:col-span-5 bg-slate-900/85 border border-slate-800 rounded-xl flex flex-col h-[640px] overflow-hidden">
          <div className="p-3.5 border-b border-slate-800 bg-slate-900 flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <span className="text-xs font-bold text-white">
                  Source Document: {processModel.document_source.filename}
                </span>
                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  {processModel.document_source.file_type}
                </span>
              </div>
              {documentDetail && (
                <div className="text-[11px] text-slate-400 mt-0.5">
                  {documentDetail.metadata.page_or_sheet_count} page(s)/sheet(s) •{' '}
                  {documentDetail.metadata.numbered_step_count} steps •{' '}
                  {documentDetail.metadata.table_count} table(s) •{' '}
                  {documentDetail.metadata.decision_statement_count} decision rules
                </div>
              )}
            </div>

            <div className="flex rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-[11px]">
              <button
                onClick={() => setDocTab('blocks')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  docTab === 'blocks' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Blocks
              </button>
              <button
                onClick={() => setDocTab('tables')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  docTab === 'tables' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Tables ({documentDetail?.parsed_structure.tables.length || 0})
              </button>
              <button
                onClick={() => setDocTab('raw')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  docTab === 'raw' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Raw
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3.5 space-y-2 text-xs">
            {!documentDetail ? (
              <div className="text-slate-400 p-4">Loading source document structure...</div>
            ) : docTab === 'blocks' ? (
              documentDetail.parsed_structure.blocks.map((blk) => {
                const isCitedBySelected =
                  selectedActivity &&
                  (selectedActivity.source_reference.block_id === blk.block_id ||
                    blk.text.includes(selectedActivity.activity_id) ||
                    selectedActivity.source_reference.exact_quote === blk.text);

                return (
                  <div
                    key={blk.block_id}
                    className={`p-2.5 rounded-lg border transition-all ${
                      isCitedBySelected
                        ? 'bg-indigo-950/60 border-indigo-400 ring-1 ring-indigo-400/60 shadow-md'
                        : blk.block_type === 'heading'
                        ? 'bg-slate-950/90 border-slate-800 font-bold text-indigo-300'
                        : 'bg-slate-950/40 border-slate-800/80 text-slate-300'
                    }`}
                  >
                    <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono mb-1">
                      <span>
                        {blk.block_id} • {blk.section_ref}
                      </span>
                      <span className="px-1.5 py-0.2 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {blk.page_or_sheet} | {blk.line_or_row}
                      </span>
                    </div>
                    <div className="font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                      {blk.text}
                    </div>
                    {isCitedBySelected && (
                      <div className="mt-1.5 text-[10px] font-semibold text-indigo-300 flex items-center gap-1">
                        <Check className="w-3 h-3" /> Active Source Citation for{' '}
                        {selectedActivity?.activity_id}
                      </div>
                    )}
                  </div>
                );
              })
            ) : docTab === 'tables' ? (
              documentDetail.parsed_structure.tables.length > 0 ? (
                documentDetail.parsed_structure.tables.map((tbl) => (
                  <div
                    key={tbl.table_id}
                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs font-semibold text-indigo-300">
                      <span className="flex items-center gap-1.5">
                        <Table className="w-3.5 h-3.5" />
                        {tbl.table_id} ({tbl.page_or_sheet})
                      </span>
                      <span className="text-[11px] text-slate-400">{tbl.section_ref}</span>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-[11px]">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            {tbl.headers.map((h, i) => (
                              <th key={i} className="py-1.5 px-2 font-semibold">
                                {h}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tbl.rows.map((row, rIdx) => (
                            <tr key={rIdx} className="border-b border-slate-900 text-slate-300">
                              {tbl.headers.map((h, cIdx) => (
                                <td key={cIdx} className="py-1.5 px-2">
                                  {row[h] || ''}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-center text-slate-500">
                  No structured tables detected in this document format (select DOCX or XLSX SOP to inspect extracted tables).
                </div>
              )
            ) : (
              <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 font-mono text-[11px] text-slate-300 whitespace-pre-wrap leading-relaxed">
                {documentDetail.raw_text}
              </pre>
            )}
          </div>
        </div>

        {/* RIGHT PANE: Extracted Process Activities & Side-by-Side Field Verification */}
        <div className="lg:col-span-7 bg-slate-900/85 border border-slate-800 rounded-xl flex flex-col h-[640px] overflow-hidden">
          <div className="p-3.5 border-b border-slate-800 bg-slate-900 flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-xs font-bold text-white">
                Extracted Process Steps ({filteredActivities.length} of {processModel.activities.length})
              </h3>
              <p className="text-[11px] text-slate-400">
                Click any activity to highlight its source block on the left; edit or approve individual steps
              </p>
            </div>

            <div className="flex rounded-lg bg-slate-950 p-0.5 border border-slate-800 text-[11px]">
              <button
                onClick={() => setFilterMode('all')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  filterMode === 'all' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                All ({processModel.activities.length})
              </button>
              <button
                onClick={() => setFilterMode('uncertain')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  filterMode === 'uncertain'
                    ? 'bg-amber-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Uncertain / Flagged ({uncertainCount})
              </button>
              <button
                onClick={() => setFilterMode('pending')}
                className={`px-2.5 py-1 rounded-md font-medium ${
                  filterMode === 'pending'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                Pending Review
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-3.5 space-y-3">
            {filteredActivities.map((act) => {
              const isSelected = selectedActivity?.activity_id === act.activity_id;
              const confPct = Math.round(act.confidence_score * 100);
              const isMissingActor = act.responsible_role.toUpperCase() === 'UNASSIGNED';

              return (
                <div
                  key={act.activity_id}
                  onClick={() => onSelectActivity(act.activity_id)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-slate-900 border-indigo-400 ring-1 ring-indigo-400/50'
                      : act.is_uncertain
                      ? 'bg-amber-950/15 border-amber-500/50 hover:border-amber-400'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {act.activity_id}
                      </span>
                      <span className="text-sm font-bold text-white">{act.activity_name}</span>
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {act.activity_type}
                      </span>
                      <span
                        className={`text-[11px] font-mono font-semibold px-2 py-0.5 rounded border ${
                          confPct >= 80
                            ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                            : 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                        }`}
                      >
                        Confidence: {confPct}%
                      </span>
                    </div>

                    <div
                      className="flex items-center gap-1.5"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => onReviewActivity(act.activity_id, 'APPROVED')}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1 border transition-colors ${
                          act.review_decision === 'APPROVED'
                            ? 'bg-emerald-500/25 border-emerald-500 text-emerald-200'
                            : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-emerald-500/50 hover:text-emerald-300'
                        }`}
                      >
                        <ThumbsUp className="w-3 h-3" />
                        {act.review_decision === 'APPROVED' ? 'Approved' : 'Approve'}
                      </button>

                      <button
                        onClick={() => onReviewActivity(act.activity_id, 'REJECTED')}
                        className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1 border transition-colors ${
                          act.review_decision === 'REJECTED'
                            ? 'bg-rose-500/25 border-rose-500 text-rose-200'
                            : 'bg-slate-900 border-slate-700 text-slate-300 hover:border-rose-500/50 hover:text-rose-300'
                        }`}
                      >
                        <ThumbsDown className="w-3 h-3" />
                        {act.review_decision === 'REJECTED' ? 'Rejected' : 'Reject'}
                      </button>

                      <button
                        onClick={() => onEditActivity(act)}
                        className="px-2.5 py-1 rounded-lg bg-indigo-600/25 hover:bg-indigo-600/40 text-indigo-200 border border-indigo-500/40 text-xs font-medium flex items-center gap-1"
                      >
                        <Edit3 className="w-3 h-3" />
                        Edit
                      </button>
                    </div>
                  </div>

                  {act.is_uncertain && (
                    <div className="mb-2.5 p-2.5 rounded-lg bg-amber-500/15 border border-amber-500/40 text-amber-200 text-xs flex items-start gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold">Uncertain Extraction Flagged: </span>
                        {act.uncertainty_reason}
                      </div>
                    </div>
                  )}

                  <p className="text-xs text-slate-300 mb-3 leading-relaxed">{act.description}</p>

                  {/* Extracted Fields Grid with Uncertain Field Highlighting */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-[11px] mb-2.5">
                    <div
                      className={`p-2 rounded-lg border ${
                        isMissingActor
                          ? 'bg-rose-950/40 border-rose-500/60 text-rose-200'
                          : 'bg-slate-900/90 border-slate-800 text-slate-300'
                      }`}
                    >
                      <span className="text-slate-500 block text-[10px]">Responsible Role</span>
                      <span className="font-semibold">{act.responsible_role}</span>
                      <span className="block text-[10px] text-slate-400">{act.department}</span>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
                      <span className="text-slate-500 block text-[10px]">Dependencies</span>
                      <span className="font-mono font-semibold">
                        {act.dependencies.length > 0 ? act.dependencies.join(', ') : 'Start Node'}
                      </span>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
                      <span className="text-slate-500 block text-[10px]">Inputs</span>
                      <span className="truncate block" title={act.input.join(', ')}>
                        {act.input.join(', ') || 'None'}
                      </span>
                    </div>

                    <div className="p-2 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-300">
                      <span className="text-slate-500 block text-[10px]">Outputs</span>
                      <span className="truncate block" title={act.output.join(', ')}>
                        {act.output.join(', ') || 'None'}
                      </span>
                    </div>
                  </div>

                  {/* Citation Comparison Footer */}
                  <div className="px-2.5 py-1.5 rounded bg-slate-900/70 border border-slate-800/90 flex items-center justify-between text-[11px] text-slate-400">
                    <span className="truncate font-mono">
                      Citation [{act.source_reference.section}, {act.source_reference.page_or_sheet}]: "
                      {act.source_reference.exact_quote}"
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Governance Panel: Business Rules/Approvals/Exceptions, Audit Trail, and Version History */}
      <div className="bg-slate-900/85 border border-slate-800 rounded-xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-slate-800 flex items-center gap-3 text-xs bg-slate-900">
          <button
            onClick={() => setBottomTab('rules')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 ${
              bottomTab === 'rules'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            Conditions ({processModel.conditions.length}) • Approvals ({processModel.approvals.length}) •
            Exceptions ({processModel.exceptions.length})
          </button>

          <button
            onClick={() => setBottomTab('audit')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 ${
              bottomTab === 'audit'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            Audit Logs ({processModel.audit_logs.length}) & Reviewer Comments (
            {processModel.reviewer_comments.length})
          </button>

          <button
            onClick={() => setBottomTab('versions')}
            className={`px-3 py-1.5 rounded-lg font-semibold flex items-center gap-1.5 ${
              bottomTab === 'versions'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            Version History ({versionHistory?.versions.length || 1})
          </button>
        </div>

        <div className="p-4 text-xs">
          {bottomTab === 'rules' ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2">
                <h4 className="font-bold text-amber-300 flex items-center gap-1.5">
                  <GitBranch className="w-4 h-4" /> Decision Conditions
                </h4>
                {processModel.conditions.map((c) => (
                  <div
                    key={c.condition_id}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1"
                  >
                    <div className="font-mono font-bold text-amber-300">
                      {c.condition_id} (Activity: {c.decision_activity_id})
                    </div>
                    <p className="text-slate-200 font-mono text-[11px]">{c.rule_expression}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-emerald-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4" /> Approval Gates
                </h4>
                {processModel.approvals.map((a) => (
                  <div
                    key={a.approval_id}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1"
                  >
                    <div className="font-mono font-bold text-emerald-300">
                      {a.approval_id} ({a.approver_role})
                    </div>
                    <p className="text-slate-200 text-[11px]">{a.approval_criteria}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-rose-300 flex items-center gap-1.5">
                  <Flame className="w-4 h-4" /> Exceptions & Escalation Paths
                </h4>
                {processModel.exceptions.map((ex) => (
                  <div
                    key={ex.exception_id}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1"
                  >
                    <div className="font-mono font-bold text-rose-300">
                      {ex.exception_id} → Escalate to: {ex.escalation_role}
                    </div>
                    <p className="text-slate-300 text-[11px]">Trigger: {ex.trigger_condition}</p>
                    <p className="text-slate-400 text-[11px]">Action: {ex.remediation_action}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : bottomTab === 'audit' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <h4 className="font-bold text-slate-200">Immutable Governance Audit Logs</h4>
                {processModel.audit_logs.map((log) => (
                  <div
                    key={log.log_id}
                    className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 flex items-start justify-between gap-2"
                  >
                    <div>
                      <span className="font-mono font-bold text-indigo-300">
                        [v{log.version}] {log.action}
                      </span>{' '}
                      by <span className="font-semibold text-white">{log.actor}</span>
                      <p className="text-slate-300 mt-0.5">{log.details}</p>
                    </div>
                    <span className="text-[10px] text-slate-500 shrink-0">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <h4 className="font-bold text-slate-200">Reviewer Comments</h4>
                {processModel.reviewer_comments.length > 0 ? (
                  processModel.reviewer_comments.map((cmt) => (
                    <div
                      key={cmt.comment_id}
                      className="p-2.5 rounded-lg bg-slate-950 border border-slate-800"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-indigo-300">{cmt.author}</span>
                        {cmt.activity_id && (
                          <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                            {cmt.activity_id}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-200 mt-1">{cmt.comment}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic">
                    No reviewer comments added yet. Approve, reject, or edit an activity to record comments.
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {versionHistory?.versions.map((ver) => (
                <div
                  key={ver.version}
                  className="p-3 rounded-lg bg-slate-950 border border-slate-800 flex flex-wrap items-center justify-between gap-2"
                >
                  <div>
                    <span className="font-mono font-bold text-indigo-300 mr-2">
                      Version {ver.version}
                    </span>
                    <span className="font-semibold text-white">{ver.change_summary}</span>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Changed by: {ver.changed_by} • Validation: {ver.validation_status} • Review:{' '}
                      {ver.review_status} • Confidence: {(ver.overall_confidence * 100).toFixed(1)}%
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-500">
                    {new Date(ver.created_at).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
