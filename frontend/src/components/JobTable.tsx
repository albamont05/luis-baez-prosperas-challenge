import React, { useState } from 'react';
import {
    CheckCircle2,
    XCircle,
    Loader2,
    Clock,
    FileText,
    PlusCircle,
    Download,
    ClipboardList,
} from 'lucide-react';
import type { Job, JobType } from '../types';

// ── Status badge ───────────────────────────────────────────────────────────

interface BadgeProps { status: Job['status'] }

const StatusBadge: React.FC<BadgeProps> = ({ status }) => {
    const map = {
        PENDING: {
            cls: 'bg-amber-100 text-amber-800 border border-amber-200',
            icon: <Clock className="w-3.5 h-3.5" />,
            label: 'Pendiente',
        },
        PROCESSING: {
            cls: 'bg-blue-100 text-blue-800 border border-blue-200 animate-pulse',
            icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
            label: 'Procesando',
        },
        COMPLETED: {
            cls: 'bg-emerald-100 text-emerald-800 border border-emerald-200',
            icon: <CheckCircle2 className="w-3.5 h-3.5" />,
            label: 'Completado',
        },
        FAILED: {
            cls: 'bg-red-100 text-red-800 border border-red-200',
            icon: <XCircle className="w-3.5 h-3.5" />,
            label: 'Fallido',
        },
    } as const;

    const { cls, icon, label } = map[status];
    return (
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${cls}`}>
            {icon}
            {label}
        </span>
    );
};

// ── Main component ─────────────────────────────────────────────────────────

interface JobTableProps {
    jobs: Job[];
    loading: boolean;
    onCreateJob: (type: JobType) => void;
    creatingJob: boolean;
}

const JobTable: React.FC<JobTableProps> = ({ jobs, loading, onCreateJob, creatingJob }) => {
    const [selectedType, setSelectedType] = useState<JobType>('CSV');

    const formatDate = (iso: string) =>
        new Intl.DateTimeFormat('es-ES', {
            dateStyle: 'medium',
            timeStyle: 'short',
        }).format(new Date(iso));

    return (
        <div className="flex flex-col gap-6">

            {/* ── Toolbar ───────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-2 text-slate-400 text-sm">
                    <ClipboardList className="w-4 h-4" />
                    <span>{jobs.length} report{jobs.length !== 1 ? 'es' : 'e'} encontrado{jobs.length !== 1 ? 's' : ''}</span>
                </div>

                <div className="flex items-center gap-2">
                    <select
                        value={selectedType}
                        onChange={(e) => setSelectedType(e.target.value as JobType)}
                        className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2
                       focus:outline-none focus:ring-2 focus:ring-violet-500 cursor-pointer"
                    >
                        <option value="CSV">CSV</option>
                        <option value="PDF">PDF</option>
                    </select>

                    <button
                        onClick={() => onCreateJob(selectedType)}
                        disabled={creatingJob}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold
                       bg-violet-600 hover:bg-violet-500 active:scale-95 disabled:opacity-60
                       text-white transition-all duration-150 shadow-lg shadow-violet-900/30"
                    >
                        {creatingJob
                            ? <Loader2 className="w-4 h-4 animate-spin" />
                            : <PlusCircle className="w-4 h-4" />
                        }
                        Nuevo Reporte
                    </button>
                </div>
            </div>

            {/* ── Table ─────────────────────────────────────────────────────── */}
            <div className="overflow-x-auto rounded-2xl border border-slate-700/60 shadow-xl">
                <table className="w-full text-sm text-left">
                    <thead className="bg-slate-800/80 text-slate-400 uppercase text-xs tracking-wider">
                        <tr>
                            <th className="px-5 py-3.5 font-medium">Job ID</th>
                            <th className="px-5 py-3.5 font-medium">Tipo</th>
                            <th className="px-5 py-3.5 font-medium">Estado</th>
                            <th className="px-5 py-3.5 font-medium hidden md:table-cell">Creado</th>
                            <th className="px-5 py-3.5 font-medium text-right">Resultado</th>
                        </tr>
                    </thead>

                    <tbody className="divide-y divide-slate-700/50">
                        {loading && jobs.length === 0 ? (
                            // Skeleton rows
                            Array.from({ length: 4 }).map((_, i) => (
                                <tr key={i} className="bg-slate-900/40">
                                    {Array.from({ length: 5 }).map((_, j) => (
                                        <td key={j} className="px-5 py-4">
                                            <div className="h-4 bg-slate-700/60 rounded animate-pulse" style={{ width: `${60 + j * 10}%` }} />
                                        </td>
                                    ))}
                                </tr>
                            ))
                        ) : jobs.length === 0 ? (
                            // Empty state
                            <tr>
                                <td colSpan={5}>
                                    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500">
                                        <FileText className="w-10 h-10 opacity-40" />
                                        <p className="font-medium">No hay reportes aún</p>
                                        <p className="text-xs text-slate-600">Crea tu primer reporte usando el botón de arriba</p>
                                    </div>
                                </td>
                            </tr>
                        ) : (
                            jobs.map((job) => (
                                <tr
                                    key={job.job_id}
                                    className="bg-slate-900/30 hover:bg-slate-800/50 transition-colors duration-150"
                                >
                                    {/* Job ID — truncated */}
                                    <td className="px-5 py-4">
                                        <span
                                            className="font-mono text-xs text-slate-400 bg-slate-800 px-2 py-1 rounded"
                                            title={job.job_id}
                                        >
                                            {job.job_id.slice(0, 8)}…
                                        </span>
                                    </td>

                                    {/* Report type */}
                                    <td className="px-5 py-4">
                                        <span className="inline-flex items-center gap-1.5 text-slate-300 font-medium">
                                            <FileText className="w-3.5 h-3.5 text-violet-400" />
                                            {job.report_type}
                                        </span>
                                    </td>

                                    {/* Status */}
                                    <td className="px-5 py-4">
                                        <StatusBadge status={job.status} />
                                    </td>

                                    {/* Created at */}
                                    <td className="px-5 py-4 text-slate-500 hidden md:table-cell">
                                        {formatDate(job.created_at)}
                                    </td>

                                    {/* Descarga — pre-signed URL */}
                                    <td className="px-5 py-4 text-right">
                                        {job.status === 'COMPLETED' ? (() => {
                                            const extension = job.report_type === 'CSV' ? 'csv' : 'pdf';
                                            const fallbackUrl = `http://localhost:4566/prosperas-reports-bucket/${job.job_id}.${extension}`;
                                            const downloadUrl = job.download_url || fallbackUrl;

                                            return (
                                                <button
                                                    onClick={() => window.open(downloadUrl, '_blank', 'noreferrer')}
                                                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                                                               bg-emerald-900/30 border border-emerald-500/30
                                                               text-emerald-400 hover:text-emerald-300
                                                               hover:bg-emerald-900/50 active:scale-95
                                                               text-xs font-semibold transition-all duration-150"
                                                >
                                                    <Download className="w-3.5 h-3.5" />
                                                    Descargar
                                                </button>
                                            );
                                        })() : (
                                            <span className="text-slate-600 text-xs">—</span>
                                        )}
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default JobTable;
