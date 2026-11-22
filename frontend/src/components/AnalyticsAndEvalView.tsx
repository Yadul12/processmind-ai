import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  CartesianGrid,
} from 'recharts';
import {
  Cpu,
  CheckCircle2,
  AlertTriangle,
  Award,
  Layers,
  RefreshCw,
} from 'lucide-react';
import { EvalGuardSuiteReport, ProcessModel } from '../types/process';

interface AnalyticsAndEvalViewProps {
  processModel: ProcessModel;
  evalReport: EvalGuardSuiteReport | null;
  loadingEval: boolean;
  onRefreshEval: () => Promise<void>;
}

const COLORS = ['#6366f1', '#10b981', '#f59e0b', '#06b6d4', '#a855f7', '#f43f5e'];

export const AnalyticsAndEvalView: React.FC<AnalyticsAndEvalViewProps> = ({
  processModel,
  evalReport,
  loadingEval,
  onRefreshEval,
}) => {
  // Activity category breakdown for active process
  const typeDistribution = React.useMemo(() => {
    const counts: Record<string, number> = {};
    processModel.activities.forEach((a) => {
      counts[a.activity_type] = (counts[a.activity_type] || 0) + 1;
    });
    return Object.entries(counts).map(([name, count]) => ({
      name: name.toUpperCase(),
      count,
    }));
  }, [processModel.activities]);

  // Activity confidence breakdown
  const activityConfidenceData = React.useMemo(() => {
    return processModel.activities.map((a) => ({
      id: a.activity_id,
      name: a.activity_name.slice(0, 24),
      confidence: Math.round(a.confidence_score * 100),
    }));
  }, [processModel.activities]);

  // EvalGuard Adapter Aggregate Metrics Chart
  const evalMetricBars = React.useMemo(() => {
    if (!evalReport) return [];
    return [
      { metric: 'Activity Precision', score: evalReport.mean_activity_precision },
      { metric: 'Activity Recall', score: evalReport.mean_activity_recall },
      { metric: 'Activity F1', score: evalReport.mean_activity_f1 },
      { metric: 'Actor Accuracy', score: evalReport.mean_actor_accuracy },
      { metric: 'Dependency Acc.', score: evalReport.mean_dependency_accuracy },
      { metric: 'Decision Rule Acc.', score: evalReport.mean_decision_condition_accuracy },
      { metric: 'Schema Pass Rate', score: evalReport.schema_validation_pass_rate },
      { metric: 'Citation Fidelity', score: evalReport.mean_source_citation_correctness },
    ];
  }, [evalReport]);

  return (
    <div className="space-y-6">
      {/* 5-Agent LangGraph Execution Pipeline Telemetry */}
      <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Cpu className="w-4 h-4 text-indigo-400" />
              LangGraph 5-Agent Execution Pipeline Telemetry ({processModel.process_id})
            </h3>
            <p className="text-xs text-slate-400">
              Controlled state transitions, Pydantic v2 validation checks, and confidence scoring trace
            </p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
            Schema v{processModel.schema_version}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {processModel.agent_trace.map((step, idx) => (
            <div
              key={idx}
              className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between space-y-2"
            >
              <div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                  <span className="font-mono font-bold text-indigo-400">STAGE {idx + 1}</span>
                  <span className="font-mono">{step.duration_ms.toFixed(1)} ms</span>
                </div>
                <div className="text-xs font-bold text-white leading-snug">{step.agent_name}</div>
                <p className="text-[11px] text-slate-400 mt-1.5 leading-relaxed">{step.summary}</p>
              </div>
              <div className="flex items-center justify-between pt-2 border-t border-slate-900 text-[10px]">
                <span className="text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> {step.status}
                </span>
                {step.warnings_count > 0 && (
                  <span className="text-amber-300 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> {step.warnings_count} flag(s)
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Process Model Charts (Recharts) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            Active Process — Activity Classification Breakdown
          </h4>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={typeDistribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="count" radius={[6, 6, 0, 0]}>
                  {typeDistribution.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-300 mb-4 flex items-center gap-2">
            <Award className="w-4 h-4 text-emerald-400" />
            Active Process — Activity Confidence Scores (%)
          </h4>
          <div className="h-60">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={activityConfidenceData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="id" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis domain={[0, 100]} tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0f172a',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    fontSize: '12px',
                  }}
                />
                <Bar dataKey="confidence" radius={[6, 6, 0, 0]}>
                  {activityConfidenceData.map((entry, index) => (
                    <Cell
                      key={index}
                      fill={entry.confidence >= 75 ? '#10b981' : '#f59e0b'}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* EvalGuard Adapter Quality Verification Suite */}
      <div className="p-5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <Award className="w-4 h-4 text-emerald-400" />
              EvalGuard Adapter — Ground-Truth Process Extraction Quality Suite
            </h3>
            <p className="text-xs text-slate-400">
              Evaluates Activity P/R/F1, Actor Accuracy, Dependency Accuracy, Decision-Condition Accuracy,
              Schema Pass Rate, and Citation Correctness across 5 Enterprise SOPs + 3 Adversarial Edge Cases
            </p>
          </div>

          <button
            onClick={onRefreshEval}
            disabled={loadingEval}
            className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingEval ? 'animate-spin' : ''}`} />
            {loadingEval ? 'Evaluating...' : 'Run Evaluation Adapter'}
          </button>
        </div>

        {evalReport && (
          <>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5">
              {evalMetricBars.map((m) => (
                <div
                  key={m.metric}
                  className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-center"
                >
                  <div className="text-[10px] text-slate-400 uppercase font-semibold truncate">
                    {m.metric}
                  </div>
                  <div className="text-lg font-bold text-emerald-400 font-mono mt-1">
                    {m.score.toFixed(1)}%
                  </div>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400">
                    <th className="py-2 px-3">Case ID</th>
                    <th className="py-2 px-3">Document</th>
                    <th className="py-2 px-3">Category</th>
                    <th className="py-2 px-3">Activity P / R / F1</th>
                    <th className="py-2 px-3">Actor Acc.</th>
                    <th className="py-2 px-3">Dependency Acc.</th>
                    <th className="py-2 px-3">Decision Acc.</th>
                    <th className="py-2 px-3">Citations</th>
                    <th className="py-2 px-3">Schema & Edge Check</th>
                  </tr>
                </thead>
                <tbody>
                  {evalReport.results.map((r) => (
                    <tr
                      key={r.case_id}
                      className="border-b border-slate-800/60 hover:bg-slate-950/50 text-slate-200"
                    >
                      <td className="py-2 px-3 font-mono font-bold text-indigo-300">{r.case_id}</td>
                      <td className="py-2 px-3 font-mono text-[11px]">{r.document_filename}</td>
                      <td className="py-2 px-3">{r.category}</td>
                      <td className="py-2 px-3 font-mono text-emerald-300">
                        {r.activity_precision}% / {r.activity_recall}% / {r.activity_f1}%
                      </td>
                      <td className="py-2 px-3 font-mono">{r.actor_accuracy}%</td>
                      <td className="py-2 px-3 font-mono">{r.dependency_accuracy}%</td>
                      <td className="py-2 px-3 font-mono">{r.decision_condition_accuracy}%</td>
                      <td className="py-2 px-3 font-mono">{r.source_citation_correctness}%</td>
                      <td className="py-2 px-3">
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold">
                          ✓ PASS ({r.notes[0]?.slice(0, 38)}...)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  );
};
