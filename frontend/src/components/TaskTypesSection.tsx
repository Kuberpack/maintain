import { useState } from 'react'
import { deleteTaskType } from '../api/taskTypes'
import { ApiError } from '../api/client'
import { TaskTypeForm } from './TaskTypeForm'
import { CreateTaskInstanceForm } from './CreateTaskInstanceForm'
import type { TaskType } from '../api/types'

interface TaskTypesSectionProps {
  machineId: string
  taskTypes: TaskType[]
  onTaskTypesChanged: () => void
  onTaskInstancesChanged: () => void
}

export function TaskTypesSection({ machineId, taskTypes, onTaskTypesChanged, onTaskInstancesChanged }: TaskTypesSectionProps) {
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [addingInstanceFor, setAddingInstanceFor] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  async function handleDelete(taskType: TaskType) {
    const confirmed = window.confirm(
      `Delete "${taskType.description}"? This also permanently deletes every scheduled and completed task instance under it.`,
    )
    if (!confirmed) return
    setDeleteError(null)
    setDeletingId(taskType.id)
    try {
      await deleteTaskType(taskType.id)
      onTaskTypesChanged()
      onTaskInstancesChanged()
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Could not delete task type')
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <section className="mb-8">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Task types</h2>
      {deleteError && <p className="mb-2 text-sm text-red-600">{deleteError}</p>}
      {taskTypes.length === 0 && !creating && <p className="mb-2 text-sm text-slate-500">No task types yet.</p>}
      <ul className="mb-3 flex flex-col gap-2">
        {taskTypes.map((taskType) => (
          <li key={taskType.id} className="rounded-md border border-slate-200 p-3">
            {editingId === taskType.id ? (
              <TaskTypeForm
                machineId={machineId}
                taskType={taskType}
                onSaved={() => {
                  setEditingId(null)
                  onTaskTypesChanged()
                }}
                onCancel={() => setEditingId(null)}
              />
            ) : (
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="font-medium text-slate-900">{taskType.description}</p>
                  <p className="text-sm text-slate-500">
                    {taskType.category}
                    {taskType.defaultIntervalDays != null ? ` · every ${taskType.defaultIntervalDays}d` : ''}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setAddingInstanceFor(addingInstanceFor === taskType.id ? null : taskType.id)}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Create instance
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(taskType.id)}
                    className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(taskType)}
                    disabled={deletingId === taskType.id}
                    className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {deletingId === taskType.id ? 'Deleting…' : 'Delete'}
                  </button>
                </div>
              </div>
            )}
            {addingInstanceFor === taskType.id && (
              <div className="mt-3">
                <CreateTaskInstanceForm
                  taskTypeId={taskType.id}
                  onCreated={() => {
                    setAddingInstanceFor(null)
                    onTaskInstancesChanged()
                  }}
                  onCancel={() => setAddingInstanceFor(null)}
                />
              </div>
            )}
          </li>
        ))}
      </ul>
      {creating ? (
        <TaskTypeForm
          machineId={machineId}
          onSaved={() => {
            setCreating(false)
            onTaskTypesChanged()
          }}
          onCancel={() => setCreating(false)}
        />
      ) : (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Add task type
        </button>
      )}
    </section>
  )
}
