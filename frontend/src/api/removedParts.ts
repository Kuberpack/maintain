import { apiFetch } from './client'
import type { RemovedPart, RemovedPartStatus, RemovedPartsReport } from './types'

export interface RemovedPartFilters {
  status?: string
  machineId?: string
  from?: string
  to?: string
  pendingOnly?: boolean
  staleOnly?: boolean
  staleDays?: number
}

export function listRemovedParts(filters: RemovedPartFilters = {}): Promise<RemovedPart[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set('status', filters.status)
  if (filters.machineId) params.set('machineId', filters.machineId)
  if (filters.from) params.set('from', filters.from)
  if (filters.to) params.set('to', filters.to)
  if (filters.pendingOnly) params.set('pendingOnly', 'true')
  if (filters.staleOnly) params.set('staleOnly', 'true')
  if (filters.staleDays != null) params.set('staleDays', String(filters.staleDays))
  const qs = params.toString()
  return apiFetch<RemovedPart[]>(`/removed-parts${qs ? `?${qs}` : ''}`)
}

export function getRemovedPartsReport(staleDays = 7): Promise<RemovedPartsReport> {
  return apiFetch<RemovedPartsReport>(`/removed-parts/report?staleDays=${staleDays}`)
}

export function setRemovedPartDisposition(
  id: string,
  payload: {
    status: RemovedPartStatus
    condition?: string
    notes?: string
    photoUrl?: string
    location?: string
    vendor?: string
    sentOn?: string
    sparePartId?: string
    quantity?: number
    scrapOn?: string
    scrapQty?: number
    scrapUnit?: string
    scrapBuyer?: string
    saleBuyer?: string
    saleAmount?: number
    saleOn?: string
    warrantyNote?: string
  },
): Promise<RemovedPart> {
  return apiFetch<RemovedPart>(`/removed-parts/${id}/disposition`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
