import { useState } from 'react'
import type { FormEvent } from 'react'
import { resolveRepairLog } from '../api/repairLogs'
import { ApiError } from '../api/client'

interface ResolveRepairLogFormProps {
  repairLogId: string
  onResolved: () => void
}

export function ResolveRepairLogForm({ repairLogId, onResolved }: ResolveRepairLogFormProps) {
  const [open, setOpen] = useState(false)
  const [resolutionNotes, setResolutionNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await resolveRepairLog(repairLogId, { resolutionNotes: resolutionNotes || undefined })
      setOpen(false)
      onResolved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not resolve repair')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
      >
        Resolve
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 flex w-full flex-col gap-2 rounded-md border border-slate-200 bg-slate-50 p-2">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Resolution notes (optional)</span>
        <textarea
          rows={2}
          value={resolutionNotes}
          onChange={(e) => setResolutionNotes(e.target.value)}
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
          {submitting ? 'Resolving…' : 'Mark resolved'}
        </button>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
