import React, { useEffect, useRef, useState } from 'react';
import {
  Workflow,
  FileCheck2,
  BarChart3,
  Upload,
  Download,
  FileUp,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  RefreshCw,
  FileText,
  Layers,
  Users,
  GitBranch,
  ShieldCheck,
} from 'lucide-react';
import { api } from './services/api';
import {
  ActivityReviewDecision,
  DocumentDetail,
  EvalGuardSuiteReport,
  ProcessActivity,
  ProcessModel,
  ProcessSummary,
  ProcessVersionHistory,
} from './types/process';
import { ProcessFlowCanvas } from './components/ProcessFlowCanvas';
import { HumanReviewWorkspace } from './components/HumanReviewWorkspace';
import { AnalyticsAndEvalView } from './components/AnalyticsAndEvalView';
import { ActivityEditModal } from './components/ActivityEditModal';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'flow' | 'review' | 'analytics'>('flow');
  const [processes, setProcesses] = useState<ProcessSummary[]>([]);
  const [activeProcess, setActiveProcess] = useState<ProcessModel | null>(null);
  const [activeDocument, setActiveDocument] = useState<DocumentDetail | null>(null);
  const [versionHistory, setVersionHistory] = useState<ProcessVersionHistory | null>(null);
  const [evalReport, setEvalReport] = useState<EvalGuardSuiteReport | null>(null);
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(null);
  const [editingActivity, setEditingActivity] = useState<ProcessActivity | null>(null);
  const [reviewerName, setReviewerName] = useState('Clara Vance (Principal Process Architect)');
  const [healthInfo, setHealthInfo] = useState<{
    status: string;
    llm_provider: string;
    sample_documents_loaded: number;
  } | null>(null);

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [loadingEval, setLoadingEval] = useState(false);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const fileUploadRef = useRef<HTMLInputElement | null>(null);
  const jsonImportRef = useRef<HTMLInputElement | null>(null);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => setToast(null), 5000);
  };

  const loadProcessDetails = async (processId: string) => {
    try {
      const proc = await api.getProcess(processId);
      setActiveProcess(proc);
      setSelectedActivityId(proc.activities[0]?.activity_id || null);

      const [doc, versions] = await Promise.all([
        api.getDocument(proc.document_source.document_id).catch(() => null),
        api.getProcessVersions(processId).catch(() => null),
      ]);
      setActiveDocument(doc);
      setVersionHistory(versions);
    } catch (err: unknown) {
      showToast('error', err instanceof Error ? err.message : 'Failed to load process model');
    }
  };

  const refreshProcessList = async (selectProcessId?: string) => {
    const list = await api.listProcesses();
    setProcesses(list);
    const targetId = selectProcessId || activeProcess?.process_id || list[0]?.process_id;
    if (targetId) {
      await loadProcessDetails(targetId);
    }
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        const [health, list, evalData] = await Promise.all([
          api.getHealth().catch(() => null),
          api.listProcesses(),
          api.getEvalGuardReport().catch(() => null),
        ]);
        if (health) setHealthInfo(health);
        setProcesses(list);
        if (evalData) setEvalReport(evalData);
        if (list.length > 0) {
          await loadProcessDetails(list[0].process_id);
        }
      } catch (err: unknown) {
        showToast(
          'error',
          err instanceof Error ? err.message : 'Could not connect to ProcessMind AI API'
        );
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const uploadedDoc = await api.uploadDocument(file);
      const extractedProc = await api.extractProcess(uploadedDoc.id, undefined, true);
      await refreshProcessList(extractedProc.process_id);
      showToast(
        'success',
        `Ingested '${file.name}' and ran 5-Agent LangGraph extraction (${extractedProc.activities.length} activities).`
      );
    } catch (err: unknown) {
      showToast('error', err instanceof Error ? err.message : 'Upload and extraction failed');
    } finally {
      setUploading(false);
      if (fileUploadRef.current) fileUploadRef.current.value = '';
    }
  };

  const handleExportJson = () => {
    if (!activeProcess) return;
    const blob = new Blob([JSON.stringify(activeProcess, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${activeProcess.process_id}_v${activeProcess.version}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImportJson = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as ProcessModel;
      const imported = await api.importProcessJson(parsed, reviewerName);
      await refreshProcessList(imported.process_id);
      showToast('success', `Imported structured process model '${imported.process_name}'.`);
    } catch (err: unknown) {
      showToast('error', err instanceof Error ? err.message : 'Invalid ProcessModel JSON file');
    } finally {
      if (jsonImportRef.current) jsonImportRef.current.value = '';
    }
  };

  const handleSaveEditedActivity = async (
    updatedActivity: ProcessActivity,
    changeSummary: string,
    comment?: string
  ) => {
    if (!activeProcess) return;
    const updatedList = activeProcess.activities.map((a) =>
      a.activity_id === updatedActivity.activity_id ? updatedActivity : a
    );
    const saved = await api.updateProcess(activeProcess.process_id, {
      activities: updatedList,
      reviewer_name: reviewerName,
      change_summary: changeSummary,
      comment,
    });
    setActiveProcess(saved);
    await refreshProcessList(saved.process_id);
    showToast(
      'success',
      `Updated activity ${updatedActivity.activity_id} → Process bumped to v${saved.version} & re-validated.`
    );
  };

  const handleReviewActivity = async (
    activityId: string,
    decision: ActivityReviewDecision
  ) => {
    if (!activeProcess) return;
    const updated = await api.reviewActivity(
      activeProcess.process_id,
      activityId,
      decision,
      reviewerName,
      `Marked ${activityId} as ${decision}`
    );
    setActiveProcess(updated);
    await refreshProcessList(updated.process_id);
  };

  const handleApproveProcess = async (comment: string) => {
    if (!activeProcess) return;
    const approved = await api.approveProcess(
      activeProcess.process_id,
      reviewerName,
      comment,
      true
    );
    setActiveProcess(approved);
    await refreshProcessList(approved.process_id);
  };

  const handleRejectProcess = async (reason: string) => {
    if (!activeProcess) return;
    const rejected = await api.rejectProcess(
      activeProcess.process_id,
      reviewerName,
      reason
    );
    setActiveProcess(rejected);
    await refreshProcessList(rejected.process_id);
  };

  const handleRevalidateProcess = async () => {
    if (!activeProcess) return;
    const res = await api.validateProcess(activeProcess.process_id);
    await loadProcessDetails(activeProcess.process_id);
    showToast(
      res.error_count === 0 ? 'success' : 'error',
      `Agent 4 Validation Complete: ${res.validation_status} (${res.error_count} error(s), ${res.warning_count} warning(s), ${res.ambiguity_count} ambiguity flag(s)).`
    );
  };

  const handleRefreshEval = async () => {
    setLoadingEval(true);
    try {
      const rep = await api.getEvalGuardReport(true);
      setEvalReport(rep);
      showToast('success', 'Refreshed EvalGuard extraction benchmark report across all 8 SOP test cases.');
    } finally {
      setLoadingEval(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Enterprise Header */}
      <header className="border-b border-slate-800/90 bg-slate-900/95 backdrop-blur sticky top-0 z-30">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Workflow className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold tracking-tight text-white">
                  ProcessMind AI
                </h1>
                <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  LangGraph 5-Agent Engine
                </span>
              </div>
              <p className="text-xs text-slate-400">
                SOP-to-Process Intelligence Agent • Validated Pydantic v2 Process Models
              </p>
            </div>
          </div>

          {/* Process Selector & Document Actions */}
          <div className="flex flex-wrap items-center gap-2.5">
            <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-xl px-3 py-1.5">
              <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
              <span className="text-xs text-slate-400">Active Process:</span>
              <select
                value={activeProcess?.process_id || ''}
                onChange={(e) => loadProcessDetails(e.target.value)}
                className="bg-slate-950 text-xs font-semibold text-white focus:outline-none max-w-[340px]"
              >
                {processes.map((p) => (
                  <option key={p.process_id} value={p.process_id}>
                    [{p.review_status}] {p.process_name} ({p.document_filename}) — v{p.version}
                  </option>
                ))}
              </select>
            </div>

            <input
              ref={fileUploadRef}
              type="file"
              accept=".pdf,.docx,.xlsx,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileUploadRef.current?.click()}
              disabled={uploading}
              className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-600/20 cursor-pointer"
            >
              {uploading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Upload className="w-3.5 h-3.5" />
              )}
              {uploading ? 'Extracting SOP...' : 'Upload SOP (PDF/DOCX/XLSX/TXT)'}
            </button>

            <button
              onClick={handleExportJson}
              disabled={!activeProcess}
              title="Export versioned ProcessModel JSON"
              className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700 cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              Export JSON
            </button>

            <input
              ref={jsonImportRef}
              type="file"
              accept=".json"
              onChange={handleImportJson}
              className="hidden"
            />
            <button
              onClick={() => jsonImportRef.current?.click()}
              title="Import ProcessModel JSON"
              className="px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium flex items-center gap-1.5 border border-slate-700 cursor-pointer"
            >
              <FileUp className="w-3.5 h-3.5" />
              Import JSON
            </button>
          </div>
        </div>

        {/* Sub-Header Navigation & Process KPIs */}
        {activeProcess && (
          <div className="max-w-[1600px] mx-auto px-4 py-2 border-t border-slate-800/70 bg-slate-950/60 flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('flow')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'flow'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <Workflow className="w-3.5 h-3.5" />
                1. Visual Process Model Editor (React Flow)
              </button>

              <button
                onClick={() => setActiveTab('review')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'review'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <FileCheck2 className="w-3.5 h-3.5" />
                2. Human Review & Citation Workspace
                {activeProcess.validation_errors.length > 0 && (
                  <span className="px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-mono">
                    {activeProcess.validation_errors.length}
                  </span>
                )}
              </button>

              <button
                onClick={() => setActiveTab('analytics')}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors cursor-pointer ${
                  activeTab === 'analytics'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                3. Multi-Agent Trace & EvalGuard Quality Suite
              </button>
            </div>

            {/* Process Telemetry Pills */}
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="flex items-center gap-1 text-slate-300">
                <Layers className="w-3.5 h-3.5 text-indigo-400" />
                <strong>{activeProcess.activities.length}</strong> Activities
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <Users className="w-3.5 h-3.5 text-sky-400" />
                <strong>{activeProcess.actors.length}</strong> Actors
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <GitBranch className="w-3.5 h-3.5 text-amber-400" />
                <strong>{activeProcess.conditions.length}</strong> Decisions
              </span>
              <span className="flex items-center gap-1 text-slate-300">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <strong>{activeProcess.approvals.length}</strong> Approvals
              </span>

              <span
                className={`px-2 py-0.5 rounded font-mono text-[11px] font-semibold border ${
                  activeProcess.validation_status === 'VALID'
                    ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300'
                    : activeProcess.validation_status === 'VALID_WITH_WARNINGS'
                    ? 'bg-amber-500/15 border-amber-500/30 text-amber-300'
                    : 'bg-rose-500/20 border-rose-500/40 text-rose-300'
                }`}
              >
                Validation: {activeProcess.validation_status}
              </span>

              <span className="px-2 py-0.5 rounded font-mono text-[11px] font-semibold bg-slate-900 border border-slate-700 text-slate-200">
                Confidence: {(activeProcess.overall_confidence * 100).toFixed(1)}%
              </span>

              {healthInfo && (
                <span className="text-[11px] text-slate-500 font-mono">
                  Provider: {healthInfo.llm_provider.toUpperCase()}
                </span>
              )}
            </div>
          </div>
        )}
      </header>

      {/* Toast Notification Banner */}
      {toast && (
        <div className="max-w-[1600px] mx-auto px-4 pt-3 w-full">
          <div
            className={`px-4 py-2.5 rounded-xl border text-xs font-medium flex items-center justify-between shadow-lg ${
              toast.type === 'success'
                ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-200'
                : 'bg-rose-950/90 border-rose-500/50 text-rose-200'
            }`}
          >
            <div className="flex items-center gap-2">
              {toast.type === 'success' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
              )}
              <span>{toast.message}</span>
            </div>
            <button
              onClick={() => setToast(null)}
              className="text-xs underline ml-4 opacity-80 hover:opacity-100"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Main Workspace Container */}
      <main className="flex-1 max-w-[1600px] w-full mx-auto p-4">
        {loading ? (
          <div className="h-96 flex flex-col items-center justify-center gap-3 text-slate-400">
            <Sparkles className="w-8 h-8 text-indigo-400 animate-pulse" />
            <p className="text-sm font-medium">
              Loading ProcessMind AI Multi-Agent Workspace...
            </p>
          </div>
        ) : !activeProcess ? (
          <div className="p-12 text-center bg-slate-900/60 border border-slate-800 rounded-2xl">
            <p className="text-slate-300 text-sm">
              No extracted process models found. Upload a PDF, DOCX, XLSX, or TXT SOP document to begin.
            </p>
          </div>
        ) : activeTab === 'flow' ? (
          <ProcessFlowCanvas
            processModel={activeProcess}
            selectedActivityId={selectedActivityId}
            onSelectActivity={setSelectedActivityId}
            onEditActivity={(act) => setEditingActivity(act)}
            onReviewActivity={handleReviewActivity}
            onJumpToDocumentCitation={(act) => {
              setSelectedActivityId(act.activity_id);
              setActiveTab('review');
            }}
          />
        ) : activeTab === 'review' ? (
          <HumanReviewWorkspace
            processModel={activeProcess}
            documentDetail={activeDocument}
            versionHistory={versionHistory}
            selectedActivityId={selectedActivityId}
            reviewerName={reviewerName}
            onReviewerNameChange={setReviewerName}
            onSelectActivity={setSelectedActivityId}
            onEditActivity={(act) => setEditingActivity(act)}
            onReviewActivity={handleReviewActivity}
            onApproveProcess={handleApproveProcess}
            onRejectProcess={handleRejectProcess}
            onRevalidateProcess={handleRevalidateProcess}
          />
        ) : (
          <AnalyticsAndEvalView
            processModel={activeProcess}
            evalReport={evalReport}
            loadingEval={loadingEval}
            onRefreshEval={handleRefreshEval}
          />
        )}
      </main>

      {/* Activity Field Editor Modal */}
      {editingActivity && activeProcess && (
        <ActivityEditModal
          activity={editingActivity}
          allActivityIds={activeProcess.activities.map((a) => a.activity_id)}
          reviewerName={reviewerName}
          onClose={() => setEditingActivity(null)}
          onSave={handleSaveEditedActivity}
        />
      )}
    </div>
  );
};

export default App;
