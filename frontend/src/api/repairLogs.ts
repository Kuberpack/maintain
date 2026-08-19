import { apiFetch } from './client'
import type { RepairLog } from './types'

export function listRepairLogs(params?: { machineId?: string; unresolvedOnly?: boolean }): Promise<RepairLog[]> {
  const search = new URLSearchParams()
  if (params?.machineId) search.set('machineId', params.machineId)
  if (params?.unresolvedOnly) search.set('unresolvedOnly', 'true')
  const qs = search.toString()
  return apiFetch<RepairLog[]>(`/repair-logs${qs ? `?${qs}` : ''}`)
}

export function createRepairLog(payload: {
  machineId: string
  issueDescription: string
  downtimeMinutes?: number
}): Promise<RepairLog> {
  return apiFetch<RepairLog>('/repair-logs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
