import { apiFetch } from './client'
import type {
  ChecklistItemResult,
  ChecklistItemResultInput,
  ReviewStatus,
  TaskInstanceMarkDoneResponse,
  TaskInstance,
  TaskStatus,
} from './types'

export function listTaskInstances(params?: {
  machineId?: string
  status?: TaskStatus
  reviewStatus?: ReviewStatus
}): Promise<TaskInstance[]> {
  const search = new URLSearchParams()
  if (params?.machineId) search.set('machineId', params.machineId)
  if (params?.status) search.set('status', params.status)
  if (params?.reviewStatus) search.set('reviewStatus', params.reviewStatus)
  const qs = search.toString()
  return apiFetch<TaskInstance[]>(`/task-instances${qs ? `?${qs}` : ''}`)
}

export function markTaskInstanceDone(
  id: string,
  payload: {
    notes?: string
    photoUrl?: string
    exceptionPhotoUrl?: string
    startedAt?: string
    results?: ChecklistItemResultInput[]
  },
): Promise<TaskInstanceMarkDoneResponse> {
  return apiFetch<TaskInstanceMarkDoneResponse>(`/task-instances/${id}/mark-done`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function approveTaskInstance(id: string): Promise<TaskInstanceMarkDoneResponse> {
  return apiFetch<TaskInstanceMarkDoneResponse>(`/task-instances/${id}/approve`, {
    method: 'POST',
  })
}

export function rejectTaskInstance(id: string, notes: string): Promise<TaskInstance> {
  return apiFetch<TaskInstance>(`/task-instances/${id}/reject`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  })
}

export function listChecklistResults(taskInstanceId: string): Promise<ChecklistItemResult[]> {
  return apiFetch<ChecklistItemResult[]>(`/task-instances/${taskInstanceId}/checklist-results`)
}

export function reopenTaskInstance(id: string): Promise<TaskInstance> {
  return apiFetch<TaskInstance>(`/task-instances/${id}/reopen`, {
    method: 'PATCH',
  })
}

export function createTaskInstance(payload: {
  taskTypeId: string
  dueDate: string
  notes?: string
}): Promise<TaskInstance> {
  return apiFetch<TaskInstance>('/task-instances', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function rescheduleTaskInstance(
  id: string,
  payload: { dueDate: string; notes?: string },
): Promise<TaskInstance> {
  return apiFetch<TaskInstance>(`/task-instances/${id}/reschedule`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}
