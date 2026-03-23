// ── Job enums ──────────────────────────────────────────────────────────────
export type JobStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
export type JobType = 'CSV' | 'PDF';

// ── REST Response ──────────────────────────────────────────────────────────
export interface Job {
    job_id: string;
    user_id: string;
    report_type: JobType;
    status: JobStatus;
    result_url: string | null;
    /** Pre-signed URL generada dinámicamente por el backend. Sólo presente cuando status === 'COMPLETED'. */
    download_url?: string | null;
    created_at: string;
    updated_at: string | null;
}

// ── WebSocket payload ──────────────────────────────────────────────────────
export interface WSJobUpdate {
    event: 'job_update';
    job_id: string;
    report_type: string;
    status: JobStatus;
    result_url: string | null;   // Cambiado de ? a | null
    download_url: string | null; // Cambiado de ? a | null
}

// ── Auth ───────────────────────────────────────────────────────────────────
export interface TokenResponse {
    access_token: string;
    token_type: string;
}
