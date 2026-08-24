import { apiFetch } from './client'
import type { Machine } from './types'

export function listMachines(): Promise<Machine[]> {
  return apiFetch<Machine[]>('/machines')
}

export function getMachine(id: string): Promise<Machine> {
  return apiFetch<Machine>(`/machines/${id}`)
}

export function createMachine(payload: {
  name: string
  type: string
  location?: string
  operatorId?: string | null
}): Promise<Machine> {
  return apiFetch<Machine>('/machines', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateMachine(
  id: string,
  payload: { name: string; type: string; location?: string; operatorId?: string | null },
): Promise<Machine> {
  return apiFetch<Machine>(`/machines/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteMachine(id: string): Promise<void> {
  return apiFetch<void>(`/machines/${id}`, { method: 'DELETE' })
}
