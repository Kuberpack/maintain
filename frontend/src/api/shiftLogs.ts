import { apiFetch } from './client'
import type { OutputUnit, ShiftLog } from './types'

export function listShiftLogs(params?: {
  machineId?: string
  dateFrom?: string
  dateTo?: string
}): Promise<ShiftLog[]> {
  const search = new URLSearchParams()
  if (params?.machineId) search.set('machineId', params.machineId)
  if (params?.dateFrom) search.set('dateFrom', params.dateFrom)
  if (params?.dateTo) search.set('dateTo', params.dateTo)
  const qs = search.toString()
  return apiFetch<ShiftLog[]>(`/shift-logs${qs ? `?${qs}` : ''}`)
}

export interface ShiftLogInput {
  machineId: string
  logDate: string
  startTime?: string | null
  endTime?: string | null
  outputQty?: number | null
  outputUnit: OutputUnit
  jobChangeCount?: number | null
  wastageBoardline?: number | null
  wastageMachine?: number | null
  delayReason?: string | null
  delayMinutes?: number | null
}

/** One row per machine per day, so saving is an upsert rather than create. */
export function saveShiftLog(payload: ShiftLogInput): Promise<ShiftLog> {
  return apiFetch<ShiftLog>('/shift-logs', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
