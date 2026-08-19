import { apiFetch } from './client'
import type { TaskInstanceMarkDoneResponse, TaskInstance, TaskStatus } from './types'

export function listTaskInstances(params?: { machineId?: string; status?: TaskStatus }): Promise<TaskInstance[]> {
  const search = new URLSearchParams()
  if (params?.machineId) search.set('machineId', params.machineId)
  if (params?.status) search.set('status', params.status)
  const qs = search.toString()
  return apiFetch<TaskInstance[]>(`/task-instances${qs ? `?${qs}` : ''}`)
}

export function markTaskInstanceDone(
  id: string,
  payload: { notes?: string; photoUrl?: string },
): Promise<TaskInstanceMarkDoneResponse> {
  return apiFetch<TaskInstanceMarkDoneResponse>(`/task-instances/${id}/mark-done`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
