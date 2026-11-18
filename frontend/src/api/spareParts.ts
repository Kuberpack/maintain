import { apiFetch } from './client'
import type { SparePart } from './types'

export interface SparePartInput {
  name: string
  itemGroup?: string
  category: string
  qtyOnHand: number
  unit?: string | null
  minQty?: number | null
  machineId?: string | null
}

export function listSpareParts(): Promise<SparePart[]> {
  return apiFetch<SparePart[]>('/spare-parts')
}

export function createSparePart(payload: SparePartInput): Promise<SparePart> {
  return apiFetch<SparePart>('/spare-parts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSparePart(id: string, payload: Partial<SparePartInput>): Promise<SparePart> {
  return apiFetch<SparePart>(`/spare-parts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteSparePart(id: string): Promise<void> {
  return apiFetch<void>(`/spare-parts/${id}`, { method: 'DELETE' })
}
