import { apiFetch } from './client'
import type { PartReplacement } from './types'

export function listPartReplacements(machineId?: string): Promise<PartReplacement[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<PartReplacement[]>(`/part-replacements${qs}`)
}
