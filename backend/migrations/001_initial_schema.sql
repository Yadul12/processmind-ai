-- ProcessMind AI — PostgreSQL Schema Migration (001_initial_schema.sql)
-- Supports PostgreSQL 15/16+ and SQLite-compatible relational persistence

CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(64) PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documents (
    id VARCHAR(64) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(32) NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    checksum_sha256 VARCHAR(128) NOT NULL,
    storage_path TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    parsed_structure_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_documents_filename ON documents (filename);
CREATE INDEX IF NOT EXISTS ix_documents_checksum ON documents (checksum_sha256);

CREATE TABLE IF NOT EXISTS processes (
    process_id VARCHAR(64) PRIMARY KEY,
    process_name VARCHAR(255) NOT NULL,
    document_id VARCHAR(64) NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    current_version INTEGER NOT NULL DEFAULT 1,
    validation_status VARCHAR(32) NOT NULL DEFAULT 'NEEDS_REVIEW',
    review_status VARCHAR(32) NOT NULL DEFAULT 'PENDING_REVIEW',
    overall_confidence REAL NOT NULL DEFAULT 0.0,
    needs_human_review BOOLEAN NOT NULL DEFAULT TRUE,
    process_model_json TEXT NOT NULL,
    validation_errors_json TEXT NOT NULL DEFAULT '[]',
    agent_trace_json TEXT NOT NULL DEFAULT '[]',
    reviewer_comments_json TEXT NOT NULL DEFAULT '[]',
    approved_by VARCHAR(128),
    approved_at TIMESTAMP,
    rejected_by VARCHAR(128),
    rejected_at TIMESTAMP,
    rejection_reason TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_processes_document_id ON processes (document_id);
CREATE INDEX IF NOT EXISTS ix_processes_review_status ON processes (review_status);
CREATE INDEX IF NOT EXISTS ix_processes_validation_status ON processes (validation_status);

CREATE TABLE IF NOT EXISTS process_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id VARCHAR(64) NOT NULL REFERENCES processes(process_id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    validation_status VARCHAR(32) NOT NULL,
    review_status VARCHAR(32) NOT NULL,
    overall_confidence REAL NOT NULL DEFAULT 0.0,
    process_model_json TEXT NOT NULL,
    change_summary TEXT NOT NULL,
    changed_by VARCHAR(128) NOT NULL DEFAULT 'system',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_process_versions_pid_ver ON process_versions (process_id, version);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id VARCHAR(64) NOT NULL REFERENCES processes(process_id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    action VARCHAR(64) NOT NULL,
    actor VARCHAR(128) NOT NULL,
    details TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_audit_logs_process_id ON audit_logs (process_id);
