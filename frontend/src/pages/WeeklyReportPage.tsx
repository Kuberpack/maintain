import { useMemo, useState } from 'react'
import { useAsync } from '../lib/useAsync'
import { getWeeklyReport, downloadWeeklyPdf } from '../api/reports'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { listUsers } from '../api/users'
import { ApiError } from '../api/client'
import type { ExceptionLevel, ReviewStatus } from '../api/types'

export function WeeklyReportPage() {
  const report = useAsync(() => getWeeklyReport(), [])
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const instances = useAsync(() => listTaskInstances(), [])
  const users = useAsync(() => listUsers(), [])

  const [machineId, setMachineId] = useState('')
  const [personId, setPersonId] = useState('')
  const [fromDate, setFromDate] = useState('')
  const [criticalOnly, setCriticalOnly] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState<string | null>(null)

  const filtered = useMemo(() => {
    if (!instances.data || !taskTypes.data) return []
    const ttById = new Map(taskTypes.data.map((tt) => [tt.id, tt]))
    return instances.data.filter((ti) => {
      const tt = ttById.get(ti.taskTypeId)
      if (machineId && tt?.machineId !== machineId) return false
      if (personId && ti.completedBy !== personId) return false
      if (fromDate && (ti.completedAt ?? ti.dueDate) < fromDate) return false
      if (criticalOnly && ti.exceptionLevel !== 'critical') return false
      return ti.status === 'done' || ti.reviewStatus === 'awaiting_review' || ti.reviewStatus === 'rejected'
    })
  }, [instances.data, taskTypes.data, machineId, personId, fromDate, criticalOnly])

  async function handlePdf() {
    setDownloadError(null)
    setDownloading(true)
    try {
      const blob = await downloadWeeklyPdf()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'weekly-maintenance.pdf'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.message : 'Could not download PDF')
    } finally {
      setDownloading(false)
    }
  }

  const loading = report.loading || machines.loading || taskTypes.loading || instances.loading || users.loading
  const error = report.error ?? machines.error ?? taskTypes.error ?? instances.error ?? users.error

  if (loading) return <p className="p-6 text-slate-500">Loading report…</p>
  if (error) return <p className="p-6 text-red-600">{error}</p>
  if (!report.data || !machines.data || !taskTypes.data || !users.data) return null

  const ttById = new Map(taskTypes.data.map((tt) => [tt.id, tt]))
  const machineById = new Map(machines.data.map((m) => [m.id, m]))
  const userById = new Map(users.data.map((u) => [u.id, u]))

  return (
    <div className="mx-auto max-w-5xl p-4">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Weekly report</h1>
          <p className="text-sm text-slate-500">
            {report.data.weekStart} – {report.data.weekEnd}
          </p>
        </div>
        <div className="flex flex-col items-end gap-1">
          <button
            type="button"
            onClick={() => void handlePdf()}
            disabled={downloading}
            className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {downloading ? 'Downloading…' : 'Download PDF'}
          </button>
          <button type="button" onClick={() => window.print()} className="text-sm text-slate-600 underline">
            Print this page
          </button>
          {downloadError && <p className="text-sm text-red-600">{downloadError}</p>}
        </div>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <Stat label="Approved" value={report.data.approved} />
        <Stat label="Overdue" value={report.data.overdue} accent="red" />
        <Stat label="Rejected" value={report.data.rejected} />
        <Stat label="Waiting" value={report.data.awaitingReview} />
        <Stat label="Critical" value={report.data.critical} accent="red" />
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Search history</h2>
      <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-4">
        <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className="rounded-md border border-slate-300 px-2 py-2 text-sm">
          <option value="">All machines</option>
          {machines.data.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name}
            </option>
          ))}
        </select>
        <select value={personId} onChange={(e) => setPersonId(e.target.value)} className="rounded-md border border-slate-300 px-2 py-2 text-sm">
          <option value="">Anyone</option>
          {users.data.map((u) => (
            <option key={u.id} value={u.id}>
              {u.name}
            </option>
          ))}
        </select>
        <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="rounded-md border border-slate-300 px-2 py-2 text-sm" />
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={criticalOnly} onChange={(e) => setCriticalOnly(e.target.checked)} />
          Critical only
        </label>
      </div>

      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table className="w-full min-w-[640px] text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Machine</th>
              <th className="px-3 py-2 font-medium">Task</th>
              <th className="px-3 py-2 font-medium">When</th>
              <th className="px-3 py-2 font-medium">Who</th>
              <th className="px-3 py-2 font-medium">Review</th>
              <th className="px-3 py-2 font-medium">Flag</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((ti) => {
              const tt = ttById.get(ti.taskTypeId)
              const machine = tt ? machineById.get(tt.machineId) : undefined
              return (
                <tr key={ti.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{machine?.name}</td>
                  <td className="px-3 py-2">{tt?.description}</td>
                  <td className="px-3 py-2">{(ti.completedAt ?? ti.dueDate).slice(0, 10)}</td>
                  <td className="px-3 py-2">{ti.completedBy ? userById.get(ti.completedBy)?.name : '—'}</td>
                  <td className="px-3 py-2">{labelReview(ti.reviewStatus)}</td>
                  <td className="px-3 py-2">{labelLevel(ti.exceptionLevel)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Stat({ label, value, accent }: { label: string; value: number; accent?: 'red' }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs uppercase text-slate-500">{label}</p>
      <p className={`text-2xl font-semibold ${accent === 'red' ? 'text-red-600' : 'text-slate-900'}`}>{value}</p>
    </div>
  )
}

function labelReview(status: ReviewStatus): string {
  if (status === 'awaiting_review') return 'Waiting'
  if (status === 'approved') return 'Approved'
  if (status === 'rejected') return 'Rejected'
  return '—'
}

function labelLevel(level: ExceptionLevel): string {
  if (level === 'critical') return 'Critical'
  if (level === 'attention') return 'Attention'
  return ''
}
