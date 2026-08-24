import { apiFetch } from './client'
import type { HandoverNote } from './types'

export function listHandoverNotes(machineId?: string): Promise<HandoverNote[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<HandoverNote[]>(`/handover-notes${qs}`)
}

export function createHandoverNote(payload: { machineId: string; note: string }): Promise<HandoverNote> {
  return apiFetch<HandoverNote>('/handover-notes', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
