import { apiFetch } from './client'
import type { PartReplacement } from './types'

export function listPartReplacements(machineId?: string): Promise<PartReplacement[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<PartReplacement[]>(`/part-replacements${qs}`)
}

export function createPartReplacement(payload: {
  machineId: string
  partName: string
  replacedAt: string
  notes?: string
  sparePartId?: string
  quantityUsed?: number
  removed?: {
    partName?: string
    condition: string
    status: string
    quantity: number
    location?: string
    notes?: string
    photoUrl?: string
  }
}): Promise<PartReplacement> {
  return apiFetch<PartReplacement>('/part-replacements', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deletePartReplacement(id: string): Promise<void> {
  return apiFetch<void>(`/part-replacements/${id}`, { method: 'DELETE' })
}
