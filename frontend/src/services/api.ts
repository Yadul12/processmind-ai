import {
  ActivityReviewDecision,
  DocumentDetail,
  DocumentSummary,
  EvalGuardSuiteReport,
  ProcessActivity,
  ProcessModel,
  ProcessSummary,
  ProcessVersionHistory,
} from '../types/process';

const API_BASE = '';

async function handleResponse<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let errText = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      errText = data.detail || JSON.stringify(data);
    } catch {
      errText = await resp.text();
    }
    throw new Error(errText);
  }
  return resp.json() as Promise<T>;
}

export const api = {
  async getHealth(): Promise<{
    status: string;
    service: string;
    version: string;
    llm_provider: string;
    database_connected: boolean;
    sample_documents_loaded: number;
  }> {
    const resp = await fetch(`${API_BASE}/api/health`);
    return handleResponse(resp);
  },

  async listDocuments(): Promise<DocumentSummary[]> {
    const resp = await fetch(`${API_BASE}/api/documents`);
    return handleResponse(resp);
  },

  async getDocument(id: string): Promise<DocumentDetail> {
    const resp = await fetch(`${API_BASE}/api/documents/${encodeURIComponent(id)}`);
    return handleResponse(resp);
  },

  async uploadDocument(file: File): Promise<DocumentDetail> {
    const formData = new FormData();
    formData.append('file', file);
    const resp = await fetch(`${API_BASE}/api/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(resp);
  },

  async listProcesses(): Promise<ProcessSummary[]> {
    const resp = await fetch(`${API_BASE}/api/processes`);
    return handleResponse(resp);
  },

  async getProcess(id: string): Promise<ProcessModel> {
    const resp = await fetch(`${API_BASE}/api/processes/${encodeURIComponent(id)}`);
    return handleResponse(resp);
  },

  async extractProcess(
    documentId: string,
    customProcessName?: string,
    forceReextract = false
  ): Promise<ProcessModel> {
    const resp = await fetch(`${API_BASE}/api/processes/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_id: documentId,
        custom_process_name: customProcessName || null,
        force_reextract: forceReextract,
      }),
    });
    return handleResponse(resp);
  },

  async updateProcess(
    processId: string,
    payload: {
      process_name?: string;
      activities?: ProcessActivity[];
      reviewer_name: string;
      change_summary: string;
      comment?: string;
    }
  ): Promise<ProcessModel> {
    const resp = await fetch(`${API_BASE}/api/processes/${encodeURIComponent(processId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(resp);
  },

  async reviewActivity(
    processId: string,
    activityId: string,
    decision: ActivityReviewDecision,
    reviewerName: string,
    reviewerNote?: string
  ): Promise<ProcessModel> {
    const resp = await fetch(
      `${API_BASE}/api/processes/${encodeURIComponent(processId)}/activities/${encodeURIComponent(activityId)}/review`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          reviewer_name: reviewerName,
          reviewer_note: reviewerNote || null,
        }),
      }
    );
    return handleResponse(resp);
  },

  async validateProcess(processId: string): Promise<{
    process_id: string;
    version: number;
    validation_status: string;
    is_schema_valid: boolean;
    error_count: number;
    warning_count: number;
    ambiguity_count: number;
  }> {
    const resp = await fetch(
      `${API_BASE}/api/processes/${encodeURIComponent(processId)}/validate`,
      { method: 'POST' }
    );
    return handleResponse(resp);
  },

  async approveProcess(
    processId: string,
    reviewerName: string,
    comment: string,
    approveAllPending = true
  ): Promise<ProcessModel> {
    const resp = await fetch(
      `${API_BASE}/api/processes/${encodeURIComponent(processId)}/approve`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_name: reviewerName,
          comment,
          approve_all_pending_activities: approveAllPending,
        }),
      }
    );
    return handleResponse(resp);
  },

  async rejectProcess(
    processId: string,
    reviewerName: string,
    reason: string
  ): Promise<ProcessModel> {
    const resp = await fetch(
      `${API_BASE}/api/processes/${encodeURIComponent(processId)}/reject`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reviewer_name: reviewerName,
          reason,
        }),
      }
    );
    return handleResponse(resp);
  },

  async getProcessVersions(processId: string): Promise<ProcessVersionHistory> {
    const resp = await fetch(
      `${API_BASE}/api/processes/${encodeURIComponent(processId)}/versions`
    );
    return handleResponse(resp);
  },

  async importProcessJson(processModel: ProcessModel, importedBy = 'Process Architect'): Promise<ProcessModel> {
    const resp = await fetch(`${API_BASE}/api/processes/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        process_model: processModel,
        imported_by: importedBy,
      }),
    });
    return handleResponse(resp);
  },

  async getEvalGuardReport(refresh = false): Promise<EvalGuardSuiteReport> {
    const resp = await fetch(`${API_BASE}/api/evaluations/report?refresh=${refresh}`);
    return handleResponse(resp);
  },
};
