import { useState } from 'react'
import type { FormEvent } from 'react'
import { createPartReplacement } from '../api/partReplacements'
import { ApiError } from '../api/client'

interface LogPartReplacementFormProps {
  machineId: string
  onLogged: () => void
}

function todayLocalDate(): string {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function LogPartReplacementForm({ machineId, onLogged }: LogPartReplacementFormProps) {
  const [open, setOpen] = useState(false)
  const [partName, setPartName] = useState('')
  const [replacedAt, setReplacedAt] = useState(todayLocalDate())
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function reset() {
    setPartName('')
    setReplacedAt(todayLocalDate())
    setNotes('')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createPartReplacement({
        machineId,
        partName,
        replacedAt,
        notes: notes || undefined,
      })
      reset()
      setOpen(false)
      onLogged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not log part replacement')
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
        Log a part replacement
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-slate-200 p-3">
      <p className="text-sm font-semibold text-slate-900">Log a part replacement</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Part name</span>
        <input
          type="text"
          required
          value={partName}
          onChange={(e) => setPartName(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Replaced on</span>
        <input
          type="date"
          required
          value={replacedAt}
          onChange={(e) => setReplacedAt(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Notes (optional)</span>
        <textarea
          rows={2}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
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
          {submitting ? 'Logging…' : 'Log replacement'}
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
