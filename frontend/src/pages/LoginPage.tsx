import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'

type Mode = 'pin' | 'password'

export function LoginPage() {
  const { user, loginPin, loginPassword } = useAuth()
  const [mode, setMode] = useState<Mode>('pin')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [pin, setPin] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to={user.role === 'management' ? '/summary' : '/'} replace />
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'pin') {
        await loginPin(phoneNumber, pin)
      } else {
        await loginPassword(email, password)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Login failed')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-1 text-lg font-semibold text-slate-900">Machine Maintenance Tracker</h1>
        <p className="mb-6 text-sm text-slate-500">Kuberpack — Sonipat plant</p>

        <div className="mb-6 flex rounded-md border border-slate-200 p-1 text-sm">
          <button
            type="button"
            onClick={() => setMode('pin')}
            className={`flex-1 rounded px-3 py-1.5 font-medium ${mode === 'pin' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}
          >
            Phone + PIN
          </button>
          <button
            type="button"
            onClick={() => setMode('password')}
            className={`flex-1 rounded px-3 py-1.5 font-medium ${mode === 'password' ? 'bg-slate-900 text-white' : 'text-slate-600'}`}
          >
            Email + Password
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          {mode === 'pin' ? (
            <>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-700">Phone number</span>
                <input
                  type="tel"
                  inputMode="numeric"
                  required
                  value={phoneNumber}
                  onChange={(e) => setPhoneNumber(e.target.value)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
                  autoComplete="username"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-700">PIN</span>
                <input
                  type="password"
                  inputMode="numeric"
                  pattern="\d{4,6}"
                  required
                  value={pin}
                  onChange={(e) => setPin(e.target.value)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
                  autoComplete="current-password"
                />
              </label>
            </>
          ) : (
            <>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-700">Email</span>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
                  autoComplete="username"
                />
              </label>
              <label className="flex flex-col gap-1 text-sm">
                <span className="font-medium text-slate-700">Password</span>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
                  autoComplete="current-password"
                />
              </label>
            </>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
