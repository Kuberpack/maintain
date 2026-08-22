import { createContext } from 'react'
import type { User } from '../api/types'

export interface AuthContextValue {
  user: User | null
  isLoading: boolean
  loginPin: (phoneNumber: string, pin: string) => Promise<void>
  loginPassword: (email: string, password: string) => Promise<void>
  logout: () => void
  // Re-fetches the current user (GET /auth/me) and updates the cached copy
  // -- needed after a self-edit (e.g. changing your own name) so the nav
  // bar and anywhere else reading the cached user reflect it immediately.
  refreshUser: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
