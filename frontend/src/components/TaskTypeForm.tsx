import { useState } from 'react'
import type { FormEvent } from 'react'
import { createTaskType, updateTaskType } from '../api/taskTypes'
import { ApiError } from '../api/client'
import type { TaskCategory, TaskType } from '../api/types'

interface TaskTypeFormProps {
  machineId: string
  taskType?: TaskType
  onSaved: () => void
  onCancel: () => void
}

const CATEGORIES: { value: TaskCategory; label: string }[] = [
  { value: 'preventive', label: 'Preventive' },
  { value: 'cleaning', label: 'Cleaning' },
  { value: 'oiling', label: 'Oiling' },
  { value: 'part_replacement', label: 'Part replacement' },
  { value: 'repair', label: 'Repair' },
]

export function TaskTypeForm({ machineId, taskType, onSaved, onCancel }: TaskTypeFormProps) {
  const isEdit = Boolean(taskType)
  const [category, setCategory] = useState<TaskCategory>(taskType?.category ?? 'preventive')
  const [description, setDescription] = useState(taskType?.description ?? '')
  const [intervalDays, setIntervalDays] = useState(
    taskType?.defaultIntervalDays != null ? String(taskType.defaultIntervalDays) : '',
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isRepair = category === 'repair'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (taskType) {
        await updateTaskType(taskType.id, {
          category,
          description,
          defaultIntervalDays: isRepair ? null : Number(intervalDays),
        })
      } else {
        await createTaskType({
          machineId,
          category,
          description,
          defaultIntervalDays: isRepair ? undefined : Number(intervalDays),
        })
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save task type')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3">
      <p className="text-sm font-semibold text-slate-900">{isEdit ? 'Edit task type' : 'Add task type'}</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Category</span>
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value as TaskCategory)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        >
          {CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Description</span>
        <input
          type="text"
          required
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="e.g. clean rollers, grease bearing #3"
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      {isRepair ? (
        <p className="text-sm text-slate-500">Repair task types are event-driven — no recurring interval.</p>
      ) : (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Repeat every (days)</span>
          <input
            type="number"
            min={1}
            required
            value={intervalDays}
            onChange={(e) => setIntervalDays(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
          />
        </label>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Saving…' : isEdit ? 'Save changes' : 'Add task type'}
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
