import { createContext } from 'react'
import type { User } from '../api/types'

export interface AuthContextValue {
  user: User | null
  isLoading: boolean
  loginPin: (phoneNumber: string, pin: string) => Promise<void>
  loginPassword: (email: string, password: string) => Promise<void>
  logout: () => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
