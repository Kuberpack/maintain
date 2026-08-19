import { apiFetch } from './client'
import type { TaskType } from './types'

export function listTaskTypes(machineId?: string): Promise<TaskType[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<TaskType[]>(`/task-types${qs}`)
}
