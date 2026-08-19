import { apiFetch } from './client'
import type { User, UserRole } from './types'

export function listUsers(): Promise<User[]> {
  return apiFetch<User[]>('/users')
}

export function createUser(payload: {
  name: string
  role: UserRole
  email?: string
  phoneNumber?: string
  whatsappNumber?: string
  pin?: string
  password?: string
}): Promise<User> {
  return apiFetch<User>('/users', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateUser(
  id: string,
  payload: {
    name?: string
    role?: UserRole
    email?: string
    phoneNumber?: string
    whatsappNumber?: string
    pin?: string
    password?: string
  },
): Promise<User> {
  return apiFetch<User>(`/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function deleteUser(id: string): Promise<void> {
  return apiFetch<void>(`/users/${id}`, { method: 'DELETE' })
}
