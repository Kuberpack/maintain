import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { getMe, loginWithPassword, loginWithPin } from '../api/auth'
import type { User } from '../api/types'
import { AuthContext } from './AuthContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('authToken')
    if (!token) {
      setIsLoading(false)
      return
    }
    getMe()
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('authToken')
      })
      .finally(() => setIsLoading(false))
  }, [])

  const loginPin = useCallback(async (phoneNumber: string, pin: string) => {
    const res = await loginWithPin(phoneNumber, pin)
    localStorage.setItem('authToken', res.accessToken)
    setUser(res.user)
  }, [])

  const loginPassword = useCallback(async (email: string, password: string) => {
    const res = await loginWithPassword(email, password)
    localStorage.setItem('authToken', res.accessToken)
    setUser(res.user)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('authToken')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, isLoading, loginPin, loginPassword, logout }),
    [user, isLoading, loginPin, loginPassword, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
