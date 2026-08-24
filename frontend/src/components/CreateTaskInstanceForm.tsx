import { useState } from 'react'
import type { FormEvent } from 'react'
import { createTaskInstance } from '../api/taskInstances'
import { ApiError } from '../api/client'
import { todayLocalDate } from '../lib/date'

interface CreateTaskInstanceFormProps {
  taskTypeId: string
  onCreated: () => void
  onCancel: () => void
}

export function CreateTaskInstanceForm({ taskTypeId, onCreated, onCancel }: CreateTaskInstanceFormProps) {
  const [dueDate, setDueDate] = useState(todayLocalDate())
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createTaskInstance({ taskTypeId, dueDate, notes: notes || undefined })
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create task instance')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="flex flex-col gap-2 rounded-md border border-slate-200 bg-slate-50 p-3 sm:flex-row sm:flex-wrap sm:items-end"
    >
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Due date</span>
        <input
          type="date"
          required
          value={dueDate}
          onChange={(e) => setDueDate(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-1 flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Notes (optional)</span>
        <input
          type="text"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="e.g. one-off, machine was idle"
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
          {submitting ? 'Creating…' : 'Create instance'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
