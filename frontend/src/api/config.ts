import { apiFetch } from './client'
import type { PublicConfig } from './types'

export function getPublicConfig(): Promise<PublicConfig> {
  return apiFetch<PublicConfig>('/config')
}
