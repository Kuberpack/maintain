import { useState } from 'react'
import type { FormEvent } from 'react'
import { createUser } from '../api/users'
import { ApiError } from '../api/client'
import type { UserRole } from '../api/types'

interface CreateUserFormProps {
  onCreated: () => void
  onCancel: () => void
}

const ROLES: { value: UserRole; label: string }[] = [
  { value: 'operator', label: 'Operator' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'management', label: 'Management' },
]

export function CreateUserForm({ onCreated, onCancel }: CreateUserFormProps) {
  const [name, setName] = useState('')
  const [role, setRole] = useState<UserRole>('operator')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [pin, setPin] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [whatsappNumber, setWhatsappNumber] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isManagement = role === 'management'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createUser({
        name,
        role,
        email: isManagement ? email : undefined,
        phoneNumber: isManagement ? undefined : phoneNumber,
        whatsappNumber: whatsappNumber || undefined,
        pin: isManagement ? undefined : pin,
        password: isManagement ? password : undefined,
      })
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create user')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3 sm:max-w-sm">
      <p className="text-sm font-semibold text-slate-900">Add user</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Name</span>
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Role</span>
        <select
          value={role}
          onChange={(e) => setRole(e.target.value as UserRole)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        >
          {ROLES.map((r) => (
            <option key={r.value} value={r.value}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
      {isManagement ? (
        <>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Email</span>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">Password (min. 8 characters)</span>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
              autoComplete="new-password"
            />
          </label>
        </>
      ) : (
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
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">PIN (4–6 digits)</span>
            <input
              type="password"
              inputMode="numeric"
              pattern="\d{4,6}"
              required
              value={pin}
              onChange={(e) => setPin(e.target.value)}
              className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
              autoComplete="new-password"
            />
          </label>
        </>
      )}
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">WhatsApp number (optional, for alerts)</span>
        <input
          type="tel"
          inputMode="numeric"
          value={whatsappNumber}
          onChange={(e) => setWhatsappNumber(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Adding…' : 'Add user'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
