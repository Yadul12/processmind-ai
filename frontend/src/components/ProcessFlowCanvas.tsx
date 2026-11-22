import React, { useMemo, useState } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  Node,
  Edge,
  NodeProps,
} from '@xyflow/react';
import {
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  GitBranch,
  Cpu,
  UserCheck,
  Bell,
  Flame,
  FileText,
  Edit3,
  ThumbsUp,
  ThumbsDown,
  Building2,
  ArrowRight,
} from 'lucide-react';
import {
  ActivityReviewDecision,
  ProcessActivity,
  ProcessModel,
} from '../types/process';

interface ProcessFlowCanvasProps {
  processModel: ProcessModel;
  selectedActivityId: string | null;
  onSelectActivity: (activityId: string) => void;
  onEditActivity: (activity: ProcessActivity) => void;
  onReviewActivity: (activityId: string, decision: ActivityReviewDecision) => Promise<void>;
  onJumpToDocumentCitation: (activity: ProcessActivity) => void;
}

const TYPE_STYLES: Record<
  string,
  {
    border: string;
    bg: string;
    badgeBg: string;
    badgeText: string;
    label: string;
  }
> = {
  manual: {
    border: 'border-sky-500/60',
    bg: 'bg-slate-900/95',
    badgeBg: 'bg-sky-500/20 border-sky-500/40',
    badgeText: 'text-sky-300',
    label: 'MANUAL STEP',
  },
  automated: {
    border: 'border-indigo-500/60',
    bg: 'bg-slate-900/95',
    badgeBg: 'bg-indigo-500/20 border-indigo-500/40',
    badgeText: 'text-indigo-300',
    label: 'AUTOMATED',
  },
  decision: {
    border: 'border-amber-400/80',
    bg: 'bg-amber-950/25',
    badgeBg: 'bg-amber-500/20 border-amber-500/40',
    badgeText: 'text-amber-300',
    label: 'DECISION GATE',
  },
  approval: {
    border: 'border-emerald-500/70',
    bg: 'bg-emerald-950/20',
    badgeBg: 'bg-emerald-500/20 border-emerald-500/40',
    badgeText: 'text-emerald-300',
    label: 'APPROVAL GATE',
  },
  notification: {
    border: 'border-purple-500/60',
    bg: 'bg-slate-900/95',
    badgeBg: 'bg-purple-500/20 border-purple-500/40',
    badgeText: 'text-purple-300',
    label: 'NOTIFICATION',
  },
  escalation: {
    border: 'border-rose-500/80',
    bg: 'bg-rose-950/25',
    badgeBg: 'bg-rose-500/20 border-rose-500/40',
    badgeText: 'text-rose-300',
    label: 'EXCEPTION / ESCALATION',
  },
  integration: {
    border: 'border-cyan-500/60',
    bg: 'bg-slate-900/95',
    badgeBg: 'bg-cyan-500/20 border-cyan-500/40',
    badgeText: 'text-cyan-300',
    label: 'INTEGRATION',
  },
};

function getActivityIcon(type: string) {
  switch (type) {
    case 'automated':
      return <Cpu className="w-3.5 h-3.5" />;
    case 'decision':
      return <GitBranch className="w-3.5 h-3.5" />;
    case 'approval':
      return <ShieldCheck className="w-3.5 h-3.5" />;
    case 'notification':
      return <Bell className="w-3.5 h-3.5" />;
    case 'escalation':
      return <Flame className="w-3.5 h-3.5" />;
    default:
      return <UserCheck className="w-3.5 h-3.5" />;
  }
}

const CustomActivityNode: React.FC<NodeProps> = ({ data }) => {
  const act = data.activity as ProcessActivity;
  const isSelected = Boolean(data.isSelected);
  const style = TYPE_STYLES[act.activity_type] || TYPE_STYLES.manual;
  const confPct = Math.round(act.confidence_score * 100);

  return (
    <div
      className={`w-[300px] rounded-xl border-2 p-3.5 shadow-xl transition-all cursor-pointer ${
        style.bg
      } ${style.border} ${
        isSelected ? 'ring-2 ring-indigo-400 shadow-indigo-500/25 scale-[1.02]' : ''
      } ${act.is_uncertain ? 'ring-2 ring-amber-500/70' : ''}`}
    >
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-slate-900"
      />

      <div className="flex items-center justify-between gap-1.5 mb-2">
        <div className="flex items-center gap-1.5">
          <span className="text-[11px] font-mono font-bold px-1.5 py-0.5 rounded bg-slate-800 text-slate-200 border border-slate-700">
            {act.activity_id}
          </span>
          <span
            className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded border ${style.badgeBg} ${style.badgeText}`}
          >
            {getActivityIcon(act.activity_type)}
            {style.label}
          </span>
        </div>

        <span
          className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded ${
            confPct >= 85
              ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
              : confPct >= 75
              ? 'bg-sky-500/15 text-sky-300 border border-sky-500/30'
              : 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
          }`}
        >
          {confPct}%
        </span>
      </div>

      <h4 className="text-xs font-bold text-white leading-snug mb-1.5 line-clamp-2">
        {act.activity_name}
      </h4>

      <p className="text-[11px] text-slate-400 line-clamp-2 mb-2.5">
        {act.description}
      </p>

      <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-[11px]">
        <div className="truncate">
          <div
            className={`font-medium truncate ${
              act.responsible_role === 'UNASSIGNED'
                ? 'text-rose-400 font-bold'
                : 'text-slate-200'
            }`}
          >
            {act.responsible_role}
          </div>
          <div className="text-[10px] text-slate-500 flex items-center gap-1 truncate">
            <Building2 className="w-2.5 h-2.5 shrink-0" />
            {act.department}
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-1">
          {act.is_uncertain && (
            <span
              title={act.uncertainty_reason || 'Needs review'}
              className="p-1 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40"
            >
              <AlertTriangle className="w-3.5 h-3.5" />
            </span>
          )}
          {act.review_decision === 'APPROVED' && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
              ✓ Approved
            </span>
          )}
          {act.review_decision === 'REJECTED' && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">
              ✕ Rejected
            </span>
          )}
          {act.review_decision === 'EDITED' && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              ✎ Edited
            </span>
          )}
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-indigo-400 !border-2 !border-slate-900"
      />
    </div>
  );
};

const nodeTypes = {
  processActivity: CustomActivityNode,
};

export const ProcessFlowCanvas: React.FC<ProcessFlowCanvasProps> = ({
  processModel,
  selectedActivityId,
  onSelectActivity,
  onEditActivity,
  onReviewActivity,
  onJumpToDocumentCitation,
}) => {
  const [reviewing, setReviewing] = useState(false);

  const selectedActivity = useMemo(
    () =>
      processModel.activities.find((a) => a.activity_id === selectedActivityId) ||
      processModel.activities[0] ||
      null,
    [processModel.activities, selectedActivityId]
  );

  // Compute topological layered layout so sequential steps, branches, approvals, and escalations render clearly
  const { nodes, edges } = useMemo(() => {
    const activities = processModel.activities;
    const actMap = new Map<string, ProcessActivity>();
    activities.forEach((a) => actMap.set(a.activity_id, a));

    const levels = new Map<string, number>();
    activities.forEach((act, idx) => {
      if (act.dependencies.length === 0) {
        levels.set(act.activity_id, 0);
      } else {
        let maxParentLevel = 0;
        for (const dep of act.dependencies) {
          const pLvl = levels.get(dep);
          if (pLvl !== undefined) {
            maxParentLevel = Math.max(maxParentLevel, pLvl + 1);
          } else {
            maxParentLevel = Math.max(maxParentLevel, idx);
          }
        }
        levels.set(act.activity_id, maxParentLevel);
      }
    });

    // Group activities by level for horizontal spacing
    const byLevel = new Map<number, ProcessActivity[]>();
    activities.forEach((act) => {
      const lvl = levels.get(act.activity_id) ?? 0;
      const list = byLevel.get(lvl) || [];
      list.push(act);
      byLevel.set(lvl, list);
    });

    const computedNodes: Node[] = [];
    Array.from(byLevel.entries())
      .sort((a, b) => a[0] - b[0])
      .forEach(([lvl, actsInLvl]) => {
        const totalWidth = (actsInLvl.length - 1) * 370;
        const startX = 420 - totalWidth / 2;
        actsInLvl.forEach((act, colIdx) => {
          const xOffset =
            act.activity_type === 'escalation' && actsInLvl.length === 1 ? 340 : 0;
          computedNodes.push({
            id: act.activity_id,
            type: 'processActivity',
            position: {
              x: startX + colIdx * 370 + xOffset,
              y: 50 + lvl * 210,
            },
            data: {
              activity: act,
              isSelected: selectedActivity?.activity_id === act.activity_id,
            },
          });
        });
      });

    const computedEdges: Edge[] = processModel.dependencies.map((dep) => {
      let stroke = '#6366f1';
      let animated = false;
      let strokeDasharray: string | undefined = undefined;
      let label = dep.condition_label || '';

      if (dep.dependency_type === 'conditional_true') {
        stroke = '#10b981';
        animated = true;
        label = dep.condition_label || 'Condition True';
      } else if (dep.dependency_type === 'conditional_false') {
        stroke = '#06b6d4';
        animated = true;
        label = dep.condition_label || 'Alternative Path';
      } else if (dep.dependency_type === 'approval_gated') {
        stroke = '#f59e0b';
        label = dep.condition_label || 'Approved';
      } else if (dep.dependency_type === 'exception_escalation') {
        stroke = '#f43f5e';
        animated = true;
        strokeDasharray = '6 4';
        label = dep.condition_label || 'Escalation Path';
      }

      return {
        id: dep.dependency_id,
        source: dep.source_activity_id,
        target: dep.target_activity_id,
        animated,
        label,
        labelStyle: { fill: '#e2e8f0', fontSize: 10, fontWeight: 600 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.9 },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 4,
        style: {
          stroke,
          strokeWidth: 2.2,
          strokeDasharray,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
        },
      };
    });

    return { nodes: computedNodes, edges: computedEdges };
  }, [processModel, selectedActivity]);

  const relatedConditions = useMemo(
    () =>
      selectedActivity
        ? processModel.conditions.filter(
            (c) => c.decision_activity_id === selectedActivity.activity_id
          )
        : [],
    [processModel.conditions, selectedActivity]
  );

  const relatedApprovals = useMemo(
    () =>
      selectedActivity
        ? processModel.approvals.filter(
            (a) => a.activity_id === selectedActivity.activity_id
          )
        : [],
    [processModel.approvals, selectedActivity]
  );

  const relatedExceptions = useMemo(
    () =>
      selectedActivity
        ? processModel.exceptions.filter(
            (e) =>
              e.source_activity_id === selectedActivity.activity_id ||
              e.target_recovery_activity_id === selectedActivity.activity_id
          )
        : [],
    [processModel.exceptions, selectedActivity]
  );

  const relatedErrors = useMemo(
    () =>
      selectedActivity
        ? processModel.validation_errors.filter(
            (err) => err.activity_id === selectedActivity.activity_id
          )
        : [],
    [processModel.validation_errors, selectedActivity]
  );

  const handleQuickDecision = async (decision: ActivityReviewDecision) => {
    if (!selectedActivity) return;
    setReviewing(true);
    try {
      await onReviewActivity(selectedActivity.activity_id, decision);
    } finally {
      setReviewing(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 h-[calc(100vh-180px)] min-h-[640px]">
      {/* React Flow Visual Graph Canvas */}
      <div className="lg:col-span-8 bg-slate-900/70 border border-slate-800 rounded-xl overflow-hidden flex flex-col relative">
        {/* Legend Bar */}
        <div className="px-4 py-2.5 bg-slate-900/95 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-3">
            <span className="font-semibold text-slate-300">Graph Legend:</span>
            <span className="inline-flex items-center gap-1.5 text-slate-300">
              <span className="w-3 h-0.5 bg-indigo-500 inline-block" /> Sequential
            </span>
            <span className="inline-flex items-center gap-1.5 text-emerald-300">
              <span className="w-3 h-0.5 bg-emerald-500 inline-block" /> Decision Branch
            </span>
            <span className="inline-flex items-center gap-1.5 text-amber-300">
              <span className="w-3 h-0.5 bg-amber-500 inline-block" /> Approval Gate
            </span>
            <span className="inline-flex items-center gap-1.5 text-rose-300">
              <span className="w-3 h-0.5 border-b-2 border-dashed border-rose-500 inline-block" />{' '}
              Exception / Escalation
            </span>
          </div>
          <span className="text-[11px] text-slate-400">
            Click any process node to inspect its source SOP citation & edit fields
          </span>
        </div>

        <div className="flex-1 w-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={(_, node) => onSelectActivity(node.id)}
            fitView
            fitViewOptions={{ padding: 0.18 }}
            minZoom={0.3}
            maxZoom={1.5}
          >
            <Background color="#1e293b" gap={20} size={1} />
            <Controls />
            <MiniMap
              nodeColor={(n) => {
                const act = n.data?.activity as ProcessActivity | undefined;
                if (!act) return '#6366f1';
                if (act.activity_type === 'decision') return '#f59e0b';
                if (act.activity_type === 'approval') return '#10b981';
                if (act.activity_type === 'escalation') return '#f43f5e';
                return '#6366f1';
              }}
              maskColor="rgba(9, 13, 22, 0.75)"
              style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b' }}
            />
          </ReactFlow>
        </div>
      </div>

      {/* Node Inspector & Source Citation Drawer */}
      <div className="lg:col-span-4 bg-slate-900/90 border border-slate-800 rounded-xl flex flex-col overflow-hidden">
        {selectedActivity ? (
          <>
            <div className="p-4 border-b border-slate-800 bg-slate-900">
              <div className="flex items-center justify-between gap-2 mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {selectedActivity.activity_id}
                  </span>
                  <span className="text-xs uppercase font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                    {selectedActivity.activity_type}
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => handleQuickDecision('APPROVED')}
                    disabled={reviewing}
                    title="Approve this activity"
                    className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition-colors ${
                      selectedActivity.review_decision === 'APPROVED'
                        ? 'bg-emerald-500/25 border-emerald-500 text-emerald-200'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-emerald-300'
                    }`}
                  >
                    <ThumbsUp className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => handleQuickDecision('REJECTED')}
                    disabled={reviewing}
                    title="Reject this activity"
                    className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition-colors ${
                      selectedActivity.review_decision === 'REJECTED'
                        ? 'bg-rose-500/25 border-rose-500 text-rose-200'
                        : 'bg-slate-800 border-slate-700 text-slate-300 hover:text-rose-300'
                    }`}
                  >
                    <ThumbsDown className="w-3.5 h-3.5" />
                  </button>
                  <button
                    onClick={() => onEditActivity(selectedActivity)}
                    className="px-2.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                    Edit
                  </button>
                </div>
              </div>

              <h3 className="text-base font-bold text-white leading-snug">
                {selectedActivity.activity_name}
              </h3>
              <p className="text-xs text-slate-400 mt-1">
                {selectedActivity.description}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
              {/* Source Document Citation Card */}
              <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/40 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-indigo-300 flex items-center gap-1.5">
                    <FileText className="w-4 h-4 text-indigo-400" />
                    Source Document Citation
                  </span>
                  <button
                    onClick={() => onJumpToDocumentCitation(selectedActivity)}
                    className="text-[11px] font-medium text-indigo-300 hover:text-white underline flex items-center gap-1"
                  >
                    Inspect in Document <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300 bg-slate-950/60 p-2 rounded-lg border border-slate-800">
                  <div>
                    <span className="text-slate-500 block">Section:</span>
                    <span className="font-medium">{selectedActivity.source_reference.section}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Location:</span>
                    <span className="font-medium">
                      {selectedActivity.source_reference.page_or_sheet} ({selectedActivity.source_reference.line_or_row})
                    </span>
                  </div>
                </div>
                <blockquote className="p-2.5 rounded-lg bg-slate-950 border-l-2 border-indigo-400 font-mono text-[11px] text-slate-200 leading-relaxed">
                  "{selectedActivity.source_reference.exact_quote}"
                </blockquote>
              </div>

              {/* Validation & Uncertainty Alerts on Node */}
              {relatedErrors.length > 0 && (
                <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/40 space-y-2">
                  <div className="font-semibold text-amber-300 flex items-center gap-1.5">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    Agent 4 Validation & Ambiguity Flags ({relatedErrors.length})
                  </div>
                  {relatedErrors.map((err, idx) => (
                    <div
                      key={idx}
                      className="p-2 rounded bg-slate-950/80 border border-amber-500/20 text-[11px]"
                    >
                      <div className="font-mono font-bold text-amber-300">
                        [{err.severity}] {err.error_code} ({err.field_path})
                      </div>
                      <p className="text-slate-300 mt-0.5">{err.message}</p>
                      {err.suggested_remediation && (
                        <p className="text-emerald-300 mt-1">
                          Fix: {err.suggested_remediation}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Actor & Department Info */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-500 block mb-0.5">Responsible Actor</span>
                  <span
                    className={`font-semibold ${
                      selectedActivity.responsible_role === 'UNASSIGNED'
                        ? 'text-rose-400'
                        : 'text-white'
                    }`}
                  >
                    {selectedActivity.responsible_role}
                  </span>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-500 block mb-0.5">Department</span>
                  <span className="font-semibold text-white">{selectedActivity.department}</span>
                </div>
              </div>

              {/* Preconditions, Postconditions, Inputs, Outputs */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-400 font-semibold block mb-1">Inputs</span>
                  {selectedActivity.input.length > 0 ? (
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {selectedActivity.input.map((inp, i) => (
                        <li key={i}>{inp}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic">None</span>
                  )}
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-400 font-semibold block mb-1">Outputs</span>
                  {selectedActivity.output.length > 0 ? (
                    <ul className="list-disc list-inside text-slate-300 space-y-0.5">
                      {selectedActivity.output.map((out, i) => (
                        <li key={i}>{out}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-500 italic">None</span>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-400 font-semibold block mb-1">Preconditions</span>
                  <p className="text-slate-300">
                    {selectedActivity.preconditions.join('; ') || 'None specified'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-400 font-semibold block mb-1">Postconditions</span>
                  <p className="text-slate-300">
                    {selectedActivity.postconditions.join('; ') || 'None specified'}
                  </p>
                </div>
              </div>

              {/* Branching Conditions, Approvals, and Exception Paths */}
              {relatedConditions.length > 0 && (
                <div className="p-3 rounded-lg bg-amber-950/20 border border-amber-500/30 space-y-1.5">
                  <div className="font-semibold text-amber-300 flex items-center gap-1.5">
                    <GitBranch className="w-3.5 h-3.5" />
                    Decision Branching Conditions
                  </div>
                  {relatedConditions.map((c) => (
                    <div key={c.condition_id} className="text-[11px] text-slate-200 font-mono">
                      [{c.condition_id}] {c.rule_expression}
                    </div>
                  ))}
                </div>
              )}

              {relatedApprovals.length > 0 && (
                <div className="p-3 rounded-lg bg-emerald-950/20 border border-emerald-500/30 space-y-1.5">
                  <div className="font-semibold text-emerald-300 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Approval Gate Requirements
                  </div>
                  {relatedApprovals.map((ap) => (
                    <div key={ap.approval_id} className="text-[11px] text-slate-200 space-y-0.5">
                      <div>
                        <span className="text-slate-400">Approver:</span> {ap.approver_role}
                      </div>
                      <div>
                        <span className="text-slate-400">Criteria:</span> {ap.approval_criteria}
                      </div>
                      {ap.sla_hours && (
                        <div>
                          <span className="text-slate-400">SLA:</span> {ap.sla_hours} hours
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {relatedExceptions.length > 0 && (
                <div className="p-3 rounded-lg bg-rose-950/20 border border-rose-500/30 space-y-1.5">
                  <div className="font-semibold text-rose-300 flex items-center gap-1.5">
                    <Flame className="w-3.5 h-3.5" />
                    Exception & Escalation Path
                  </div>
                  {relatedExceptions.map((ex) => (
                    <div key={ex.exception_id} className="text-[11px] text-slate-200 space-y-0.5">
                      <div>
                        <span className="text-slate-400">Trigger:</span> {ex.trigger_condition}
                      </div>
                      <div>
                        <span className="text-slate-400">Escalate To:</span> {ex.escalation_role}
                      </div>
                      <div>
                        <span className="text-slate-400">Remediation:</span> {ex.remediation_action}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Agent 5 Documented Confidence Scoring Breakdown */}
              {selectedActivity.confidence_breakdown && (
                <div className="p-3 rounded-lg bg-slate-950/90 border border-slate-800 space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      Agent 5 Confidence Rubric
                    </span>
                    <span className="font-mono font-bold text-emerald-300">
                      {(selectedActivity.confidence_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="font-mono text-[10px] text-slate-400">
                    {selectedActivity.confidence_breakdown.scoring_rationale}
                  </p>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="p-8 text-center text-slate-400 text-sm">
            Select a process node on the canvas to inspect its source citation and details.
          </div>
        )}
      </div>
    </div>
  );
};
