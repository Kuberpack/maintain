import { apiFetch } from './client'
import type { VendorContact, VendorSpecialty } from './types'

export function listVendorContacts(machineId?: string): Promise<VendorContact[]> {
  const qs = machineId ? `?machineId=${machineId}` : ''
  return apiFetch<VendorContact[]>(`/vendor-contacts${qs}`)
}

export interface VendorContactInput {
  name: string
  company?: string | null
  specialty: VendorSpecialty
  phoneNumber: string
  whatsappNumber?: string | null
  notes?: string | null
  machineId?: string | null
}

export function createVendorContact(payload: VendorContactInput): Promise<VendorContact> {
  return apiFetch<VendorContact>('/vendor-contacts', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateVendorContact(id: string, payload: Partial<VendorContactInput>): Promise<VendorContact> {
  return apiFetch<VendorContact>(`/vendor-contacts/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteVendorContact(id: string): Promise<void> {
  return apiFetch<void>(`/vendor-contacts/${id}`, { method: 'DELETE' })
}
