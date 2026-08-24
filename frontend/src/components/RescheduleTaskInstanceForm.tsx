import { useState } from 'react'
import type { FormEvent } from 'react'
import { rescheduleTaskInstance } from '../api/taskInstances'
import { ApiError } from '../api/client'

interface RescheduleTaskInstanceFormProps {
  taskInstanceId: string
  currentDueDate: string
  onRescheduled: () => void
}

export function RescheduleTaskInstanceForm({ taskInstanceId, currentDueDate, onRescheduled }: RescheduleTaskInstanceFormProps) {
  const [open, setOpen] = useState(false)
  const [dueDate, setDueDate] = useState(currentDueDate)
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await rescheduleTaskInstance(taskInstanceId, { dueDate, notes: notes || undefined })
      setOpen(false)
      onRescheduled()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reschedule')
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
        Reschedule
      </button>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex w-full flex-col gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:flex-wrap sm:items-end"
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">New due date</span>
        <input
          type="date"
          required
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-1 flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Reason (optional)</span>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. machine idle, breakdown"
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      {error && <p className="w-full text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save'}
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
