import { apiFetch } from './client'
import type { RepairLog } from './types'

export function listRepairLogs(params?: { machineId?: string; unresolvedOnly?: boolean }): Promise<RepairLog[]> {
  const search = new URLSearchParams()
  if (params?.machineId) search.set('machineId', params.machineId)
  if (params?.unresolvedOnly) search.set('unresolvedOnly', 'true')
  const qs = search.toString()
  return apiFetch<RepairLog[]>(`/repair-logs${qs ? `?${qs}` : ''}`)
}
