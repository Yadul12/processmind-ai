import React, { useState } from 'react';
import { X, Save, AlertTriangle, FileText } from 'lucide-react';
import { ActivityType, ProcessActivity } from '../types/process';

interface ActivityEditModalProps {
  activity: ProcessActivity;
  allActivityIds: string[];
  reviewerName: string;
  onClose: () => void;
  onSave: (
    updatedActivity: ProcessActivity,
    changeSummary: string,
    comment?: string
  ) => Promise<void>;
}

const ACTIVITY_TYPES: ActivityType[] = [
  'manual',
  'automated',
  'approval',
  'decision',
  'notification',
  'escalation',
  'integration',
];

export const ActivityEditModal: React.FC<ActivityEditModalProps> = ({
  activity,
  allActivityIds,
  reviewerName,
  onClose,
  onSave,
}) => {
  const [name, setName] = useState(activity.activity_name);
  const [description, setDescription] = useState(activity.description);
  const [activityType, setActivityType] = useState<ActivityType>(activity.activity_type);
  const [role, setRole] = useState(activity.responsible_role);
  const [department, setDepartment] = useState(activity.department || 'Operations');
  const [inputsStr, setInputsStr] = useState(activity.input.join(', '));
  const [outputsStr, setOutputsStr] = useState(activity.output.join(', '));
  const [preconditionsStr, setPreconditionsStr] = useState(activity.preconditions.join('; '));
  const [postconditionsStr, setPostconditionsStr] = useState(activity.postconditions.join('; '));
  const [selectedDeps, setSelectedDeps] = useState<string[]>(activity.dependencies);
  const [reviewerNote, setReviewerNote] = useState(activity.reviewer_note || '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleDependency = (depId: string) => {
    if (depId === activity.activity_id) return;
    setSelectedDeps((prev) =>
      prev.includes(depId) ? prev.filter((d) => d !== depId) : [...prev, depId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !role.trim()) {
      setError('Activity Name and Responsible Role are required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated: ProcessActivity = {
        ...activity,
        activity_name: name.trim(),
        description: description.trim(),
        activity_type: activityType,
        responsible_role: role.trim(),
        department: department.trim() || 'Operations',
        input: inputsStr
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        output: outputsStr
          .split(',')
          .map((s) => s.trim())
          .filter(Boolean),
        preconditions: preconditionsStr
          .split(';')
          .map((s) => s.trim())
          .filter(Boolean),
        postconditions: postconditionsStr
          .split(';')
          .map((s) => s.trim())
          .filter(Boolean),
        dependencies: selectedDeps,
        review_decision: 'EDITED',
        reviewer_note: reviewerNote.trim() || activity.reviewer_note,
      };
      await onSave(
        updated,
        `Edited activity ${activity.activity_id} (${updated.activity_name}) by ${reviewerName}`,
        reviewerNote.trim() || undefined
      );
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update activity');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              {activity.activity_id}
            </span>
            <h3 className="text-lg font-semibold text-white mt-1">
              Edit Extracted Process Activity
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="overflow-y-auto p-6 space-y-4 text-sm">
          {activity.is_uncertain && (
            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-200 flex items-start gap-2.5">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold">Flagged for Review: </span>
                {activity.uncertainty_reason || 'Low confidence score or validation issue detected.'}
              </div>
            </div>
          )}

          <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-xs text-slate-300">
            <div className="flex items-center gap-1.5 text-slate-400 font-medium mb-1">
              <FileText className="w-3.5 h-3.5 text-indigo-400" />
              <span>
                Source Reference: {activity.source_reference.section} ({activity.source_reference.page_or_sheet},{' '}
                {activity.source_reference.line_or_row})
              </span>
            </div>
            <p className="font-mono text-slate-300 italic">
              "{activity.source_reference.exact_quote}"
            </p>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/40 text-rose-200 text-xs">
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Activity Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Activity Classification Type *
              </label>
              <select
                value={activityType}
                onChange={(e) => setActivityType(e.target.value as ActivityType)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              >
                {ACTIVITY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Responsible Role (Actor) *
              </label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                placeholder="e.g. Finance Controller"
                className={`w-full px-3 py-2 rounded-lg bg-slate-950 border text-white focus:outline-none ${
                  role.toUpperCase() === 'UNASSIGNED'
                    ? 'border-rose-500/70 bg-rose-950/20'
                    : 'border-slate-700 focus:border-indigo-500'
                }`}
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Department
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Activity Description & Execution Instructions *
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              required
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Inputs (comma-separated)
              </label>
              <input
                type="text"
                value={inputsStr}
                onChange={(e) => setInputsStr(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Outputs (comma-separated)
              </label>
              <input
                type="text"
                value={outputsStr}
                onChange={(e) => setOutputsStr(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Preconditions (semicolon-separated)
              </label>
              <input
                type="text"
                value={preconditionsStr}
                onChange={(e) => setPreconditionsStr(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Postconditions (semicolon-separated)
              </label>
              <input
                type="text"
                value={postconditionsStr}
                onChange={(e) => setPostconditionsStr(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Upstream Activity Dependencies (click to toggle)
            </label>
            <div className="flex flex-wrap gap-2">
              {allActivityIds
                .filter((id) => id !== activity.activity_id)
                .map((id) => {
                  const active = selectedDeps.includes(id);
                  return (
                    <button
                      type="button"
                      key={id}
                      onClick={() => toggleDependency(id)}
                      className={`px-2.5 py-1 rounded-md text-xs font-mono border transition-colors ${
                        active
                          ? 'bg-indigo-600/30 border-indigo-400 text-indigo-200'
                          : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                      }`}
                    >
                      {active ? '✓ ' : '+ '}
                      {id}
                    </button>
                  );
                })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Reviewer Audit Note (recorded in version & audit log)
            </label>
            <input
              type="text"
              value={reviewerNote}
              onChange={(e) => setReviewerNote(e.target.value)}
              placeholder="Explain why this activity was modified or clarified..."
              className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-lg shadow-indigo-600/20"
            >
              <Save className="w-3.5 h-3.5" />
              {saving ? 'Saving & Re-validating...' : 'Save Changes (New Version)'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
