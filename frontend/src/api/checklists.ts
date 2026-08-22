import { apiFetch } from './client'
import type { ChecklistItem } from './types'

export function listChecklistItems(taskTypeId: string): Promise<ChecklistItem[]> {
  return apiFetch<ChecklistItem[]>(`/task-types/${taskTypeId}/checklist-items`)
}
