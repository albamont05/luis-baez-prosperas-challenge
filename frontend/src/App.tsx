import { useState, useEffect, useCallback } from 'react';
import {
  LayoutDashboard,
  LogOut,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  Clock,
  Loader2,
  XCircle,
  FileBarChart,
} from 'lucide-react';

import { login, fetchJobs, createJob } from './services/api';
import { useJobWebSocket } from './hooks/useJobWebSocket';
import JobTable from './components/JobTable';
import type { Job, JobType, WSJobUpdate } from './types';

// ── Constants ──────────────────────────────────────────────────────────────
const TOKEN_KEY = 'token';

// ── Stat card ──────────────────────────────────────────────────────────────
interface StatCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
}

function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div className={`rounded-2xl border ${color} bg-slate-900/60 backdrop-blur-sm p-5 flex items-center gap-4 shadow-lg`}>
      <div className="p-3 rounded-xl bg-slate-800/70">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-slate-100">{value}</p>
        <p className="text-xs text-slate-400 font-medium mt-0.5">{label}</p>
      </div>
    </div>
  );
}

// ── App ────────────────────────────────────────────────────────────────────
function App() {
  // Auth state
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState<string | null>(null);
  const [loggingIn, setLoggingIn] = useState(false);

  // Jobs state
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loadingJobs, setLoadingJobs] = useState(false);
  const [jobsError, setJobsError] = useState<string | null>(null);
  const [creatingJob, setCreatingJob] = useState(false);

  // ── Fetch initial job list ───────────────────────────────────────────────
  const loadJobs = useCallback(async () => {
    setLoadingJobs(true);
    setJobsError(null);
    try {
      const data = await fetchJobs();
      setJobs(data);
    } catch {
      setJobsError('No se pudo cargar la lista de reportes.');
    } finally {
      setLoadingJobs(false);
    }
  }, []);

  useEffect(() => {
    if (token) loadJobs();
  }, [token, loadJobs]);

  // ── WebSocket patch-by-id (no flicker) ──────────────────────────────────
  const handleWsUpdate = useCallback((update: WSJobUpdate) => {
    setJobs((prev) => {
      const idx = prev.findIndex((j) => j.job_id === update.job_id);
      if (idx === -1) {
        // Brand-new job: fetch full list to get all fields
        fetchJobs().then(setJobs).catch(() => null);
        return prev;
      }
      // Patch only the changed job
      const next = [...prev];
      next[idx] = {
        ...next[idx],
        status: update.status,
        result_url: update.result_url,
      };
      return next;
    });
  }, []);

  useJobWebSocket({ token, enabled: !!token, onUpdate: handleWsUpdate });

  // ── Login handler ────────────────────────────────────────────────────────
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError(null);
    setLoggingIn(true);
    try {
      const { access_token } = await login(username, password);
      localStorage.setItem(TOKEN_KEY, access_token);
      setToken(access_token);
    } catch {
      setAuthError('Credenciales inválidas. Intenta de nuevo.');
    } finally {
      setLoggingIn(false);
    }
  };

  // ── Logout ───────────────────────────────────────────────────────────────
  const handleLogout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setJobs([]);
    setUsername('');
    setPassword('');
  };

  // ── Create job ───────────────────────────────────────────────────────────
  const handleCreateJob = async (type: JobType) => {
    setCreatingJob(true);
    try {
      const newJob = await createJob(type);
      setJobs((prev) => [newJob, ...prev]);
    } catch {
      setJobsError('Error al crear el reporte.');
    } finally {
      setCreatingJob(false);
    }
  };

  // ── Derived stats ────────────────────────────────────────────────────────
  const stats = {
    total: jobs.length,
    pending: jobs.filter((j) => j.status === 'PENDING').length,
    processing: jobs.filter((j) => j.status === 'PROCESSING').length,
    completed: jobs.filter((j) => j.status === 'COMPLETED').length,
    failed: jobs.filter((j) => j.status === 'FAILED').length,
  };

  // ════════════════════════════════════════════════════════════════════════
  // ── Login Screen ────────────────────────────────────────────────────────
  // ════════════════════════════════════════════════════════════════════════
  if (!token) {
    return (
      <div className="min-h-screen w-full bg-slate-950 flex items-center justify-center p-6"
        style={{ background: 'radial-gradient(ellipse 80% 60% at 50% -10%, #4c1d95 0%, #0f172a 70%)' }}>
        <div className="w-full max-w-md">

          {/* Logo */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-violet-600/20
                            border border-violet-500/30 backdrop-blur-sm mb-4 shadow-xl shadow-violet-900/40">
              <FileBarChart className="w-8 h-8 text-violet-400" />
            </div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Prosperas Reports</h1>
            <p className="text-slate-400 mt-1 text-sm">Sistema de reportes asíncronos</p>
          </div>

          {/* Card */}
          <div className="bg-slate-900/70 backdrop-blur-md border border-slate-700/60 rounded-3xl p-8 shadow-2xl">
            <form onSubmit={handleLogin} className="flex flex-col gap-5">

              {authError && (
                <div className="flex items-center gap-2.5 bg-red-900/30 border border-red-500/40
                                text-red-300 rounded-xl px-4 py-3 text-sm">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />
                  {authError}
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Usuario</label>
                <input
                  id="username"
                  type="text"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="tu_usuario"
                  className="bg-slate-800 border border-slate-700 text-slate-100 rounded-xl px-4 py-3
                             placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500
                             focus:border-transparent transition-all text-sm"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Contraseña</label>
                <input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="bg-slate-800 border border-slate-700 text-slate-100 rounded-xl px-4 py-3
                             placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-violet-500
                             focus:border-transparent transition-all text-sm"
                />
              </div>

              <button
                type="submit"
                disabled={loggingIn}
                className="mt-2 flex items-center justify-center gap-2 w-full py-3 rounded-xl font-bold
                           bg-violet-600 hover:bg-violet-500 active:scale-95 disabled:opacity-60
                           text-white transition-all duration-150 shadow-lg shadow-violet-900/40 text-sm"
              >
                {loggingIn
                  ? <><Loader2 className="w-4 h-4 animate-spin" /> Iniciando sesión…</>
                  : 'Iniciar Sesión'
                }
              </button>
            </form>
          </div>
        </div>
      </div>
    );
  }

  // ════════════════════════════════════════════════════════════════════════
  // ── Dashboard ───────────────────────────────────────────────────────────
  // ════════════════════════════════════════════════════════════════════════
  return (
    <div className="min-h-screen w-full bg-slate-950 text-slate-100"
      style={{ background: 'radial-gradient(ellipse 100% 40% at 50% 0%, #2e1065 0%, #0f172a 55%)' }}>

      {/* ── Top bar ──────────────────────────────────────────────────────── */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-violet-600/20 border border-violet-500/30">
              <FileBarChart className="w-5 h-5 text-violet-400" />
            </div>
            <div>
              <h1 className="font-extrabold text-base tracking-tight text-white">Prosperas Reports</h1>
              <p className="text-xs text-slate-500 leading-none">Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={loadJobs}
              disabled={loadingJobs}
              title="Recargar"
              className="p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800
                         disabled:opacity-50 transition-all"
            >
              <RefreshCw className={`w-4 h-4 ${loadingJobs ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={handleLogout}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                         text-slate-400 hover:text-red-400 hover:bg-red-900/20 transition-all"
            >
              <LogOut className="w-4 h-4" />
              Salir
            </button>
          </div>
        </div>
      </header>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-10 flex flex-col gap-8">

        {/* Page title */}
        <div>
          <div className="flex items-center gap-2 text-violet-400 text-xs font-semibold uppercase tracking-widest mb-1">
            <LayoutDashboard className="w-3.5 h-3.5" />
            Panel de Control
          </div>
          <h2 className="text-2xl font-extrabold text-white">Mis Reportes</h2>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Pendientes"
            value={stats.pending}
            color="border-amber-500/20"
            icon={<Clock className="w-5 h-5 text-amber-400" />}
          />
          <StatCard
            label="En proceso"
            value={stats.processing}
            color="border-blue-500/20"
            icon={<Loader2 className="w-5 h-5 text-blue-400 animate-spin" />}
          />
          <StatCard
            label="Completados"
            value={stats.completed}
            color="border-emerald-500/20"
            icon={<CheckCircle2 className="w-5 h-5 text-emerald-400" />}
          />
          <StatCard
            label="Fallidos"
            value={stats.failed}
            color="border-red-500/20"
            icon={<XCircle className="w-5 h-5 text-red-400" />}
          />
        </div>

        {/* Error banner */}
        {jobsError && (
          <div className="flex items-center gap-2.5 bg-red-900/30 border border-red-500/40
                          text-red-300 rounded-xl px-4 py-3 text-sm">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            {jobsError}
          </div>
        )}

        {/* Jobs table */}
        <JobTable
          jobs={jobs}
          loading={loadingJobs}
          onCreateJob={handleCreateJob}
          creatingJob={creatingJob}
        />
      </main>
    </div>
  );
}

export default App;