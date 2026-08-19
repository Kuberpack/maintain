import { apiFetch } from './client'
import type { Machine } from './types'

export function listMachines(): Promise<Machine[]> {
  return apiFetch<Machine[]>('/machines')
}

export function getMachine(id: string): Promise<Machine> {
  return apiFetch<Machine>(`/machines/${id}`)
}
