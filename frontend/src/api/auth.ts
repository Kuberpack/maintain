import { apiFetch } from './client'
import type { TokenResponse, User } from './types'

export function loginWithPin(phoneNumber: string, pin: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>('/auth/login/pin', {
    method: 'POST',
    body: JSON.stringify({ phoneNumber, pin }),
  })
}

export function loginWithPassword(email: string, password: string): Promise<TokenResponse> {
  return apiFetch<TokenResponse>('/auth/login/password', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function getMe(): Promise<User> {
  return apiFetch<User>('/auth/me')
}
