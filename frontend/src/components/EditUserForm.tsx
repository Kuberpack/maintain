import { useState } from 'react'
import type { FormEvent } from 'react'
import { updateUser } from '../api/users'
import { ApiError } from '../api/client'
import type { User, UserRole } from '../api/types'

interface EditUserFormProps {
  user: User
  onSaved: () => void
  onCancel: () => void
}

const ROLES: { value: UserRole; label: string }[] = [
  { value: 'operator', label: 'Operator' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'management', label: 'Management' },
]

// operator/supervisor log in with a PIN, management with a password -- matches
// backend/app/routers/users.py::update_user, which clears whichever hash no
// longer applies the moment role crosses this boundary and then requires the
// other one to be present.
function credentialFamily(role: UserRole): 'pin' | 'password' {
  return role === 'management' ? 'password' : 'pin'
}

export function EditUserForm({ user, onSaved, onCancel }: EditUserFormProps) {
  const [name, setName] = useState(user.name)
  const [role, setRole] = useState<UserRole>(user.role)
  const [phoneNumber, setPhoneNumber] = useState(user.phoneNumber ?? '')
  const [email, setEmail] = useState(user.email ?? '')
  const [whatsappNumber, setWhatsappNumber] = useState(user.whatsappNumber ?? '')
  const [pin, setPin] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isManagement = role === 'management'
  // Crossing the pin/password boundary clears the old credential server-side,
  // so the new one becomes mandatory here, not just optional.
  const credentialRequired = credentialFamily(user.role) !== credentialFamily(role)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await updateUser(user.id, {
        name,
        role,
        email: isManagement ? email : undefined,
        phoneNumber: isManagement ? undefined : phoneNumber,
        whatsappNumber: whatsappNumber || undefined,
        pin: !isManagement && pin ? pin : undefined,
        password: isManagement && password ? password : undefined,
      })
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save changes')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3">
      <p className="text-sm font-semibold text-slate-900">Edit user</p>
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
      ) : (
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
      {isManagement ? (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {credentialRequired ? 'Password (required — role changed to management)' : 'New password (optional, leave blank to keep current)'}
          </span>
          <input
            type="password"
            required={credentialRequired}
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
            autoComplete="new-password"
          />
        </label>
      ) : (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">
            {credentialRequired ? 'PIN (required — role changed from management)' : 'New PIN (optional, leave blank to keep current)'}
          </span>
          <input
            type="password"
            inputMode="numeric"
            pattern="\d{4,6}"
            required={credentialRequired}
            value={pin}
            onChange={(e) => setPin(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
            autoComplete="new-password"
          />
        </label>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Save changes'}
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
