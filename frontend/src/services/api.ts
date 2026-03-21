import axios from 'axios';
import type { Job, JobType, TokenResponse } from '../types';

// ── Axios instance ─────────────────────────────────────────────────────────
const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000',
});

// Inject JWT on every request if available
api.interceptors.request.use((config) => {
    const token = localStorage.getItem('token');
    if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
});

// ── Auth ───────────────────────────────────────────────────────────────────

/**
 * POST /login — uses URLSearchParams (form data) as required by
 * FastAPI's OAuth2PasswordRequestForm.
 */
export async function login(username: string, password: string): Promise<TokenResponse> {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const { data } = await api.post<TokenResponse>('/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return data;
}

// ── Jobs ───────────────────────────────────────────────────────────────────

/** GET /jobs — returns paginated list of the current user's jobs */
export async function fetchJobs(skip = 0, limit = 20): Promise<Job[]> {
    const { data } = await api.get<Job[]>('/jobs', { params: { skip, limit } });
    return data;
}

/** POST /jobs — queues a new report generation job */
export async function createJob(report_type: JobType): Promise<Job> {
    const { data } = await api.post<Job>('/jobs', { report_type });
    return data;
}
