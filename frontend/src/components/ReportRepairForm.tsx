import { useState } from 'react'
import type { FormEvent } from 'react'
import { createRepairLog } from '../api/repairLogs'
import { ApiError } from '../api/client'

interface ReportRepairFormProps {
  machineId: string
  onReported: () => void
}

export function ReportRepairForm({ machineId, onReported }: ReportRepairFormProps) {
  const [open, setOpen] = useState(false)
  const [issueDescription, setIssueDescription] = useState('')
  const [downtimeMinutes, setDowntimeMinutes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setIssueDescription('')
    setDowntimeMinutes('')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createRepairLog({
        machineId,
        issueDescription,
        downtimeMinutes: downtimeMinutes ? Number(downtimeMinutes) : undefined,
      })
      reset()
      setOpen(false)
      onReported()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not report repair')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Report a repair
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-slate-200 p-3">
      <p className="text-sm font-semibold text-slate-900">Report a repair</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Issue description</span>
        <textarea
          required
          rows={2}
          value={issueDescription}
          onChange={(e) => setIssueDescription(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Downtime, minutes (optional)</span>
        <input
          type="number"
          min={0}
          value={downtimeMinutes}
          onChange={(e) => setDowntimeMinutes(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Reporting…' : 'Report repair'}
        </button>
        <button
          type="button"
          onClick={() => {
            reset()
            setOpen(false)
          }}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
