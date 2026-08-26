import { apiFetch } from './client'
import type { Machine, MachineKind } from './types'

export function listMachines(): Promise<Machine[]> {
  return apiFetch<Machine[]>('/machines')
}

export function getMachine(id: string): Promise<Machine> {
  return apiFetch<Machine>(`/machines/${id}`)
}

export interface MachineInput {
  name: string
  type: string
  location?: string
  operatorId?: string | null
  supervisorId?: string | null
  groupName?: string | null
  kind?: MachineKind
}

export function createMachine(payload: MachineInput): Promise<Machine> {
  return apiFetch<Machine>('/machines', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateMachine(id: string, payload: MachineInput): Promise<Machine> {
  return apiFetch<Machine>(`/machines/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function setOperatorAssignments(
  assignments: Array<{ machineId: string; operatorId: string | null }>,
): Promise<Machine[]> {
  return apiFetch<Machine[]>('/machines/operator-assignments', {
    method: 'PUT',
    body: JSON.stringify({ assignments }),
  })
}

export function setSupervisorAssignments(
  assignments: Array<{ machineId: string; supervisorId: string | null }>,
): Promise<Machine[]> {
  return apiFetch<Machine[]>('/machines/supervisor-assignments', {
    method: 'PUT',
    body: JSON.stringify({ assignments }),
  })
}

export function deleteMachine(id: string): Promise<void> {
  return apiFetch<void>(`/machines/${id}`, { method: 'DELETE' })
}
