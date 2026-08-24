import { apiFetch } from './client'
import type { TaskCategory, TaskType } from './types'

export function listTaskTypes(machineId?: string): Promise<TaskType[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<TaskType[]>(`/task-types${qs}`)
}

export function createTaskType(payload: {
  machineId: string
  category: TaskCategory
  description: string
  defaultIntervalDays?: number
}): Promise<TaskType> {
  return apiFetch<TaskType>('/task-types', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTaskType(
  id: string,
  payload: { category: TaskCategory; description: string; defaultIntervalDays: number | null },
): Promise<TaskType> {
  return apiFetch<TaskType>(`/task-types/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteTaskType(id: string): Promise<void> {
  return apiFetch<void>(`/task-types/${id}`, { method: 'DELETE' })
}
