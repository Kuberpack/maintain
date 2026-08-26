import { useState } from 'react'
import type { FormEvent } from 'react'
import { updateMachine } from '../api/machines'
import { listUsers } from '../api/users'
import { ApiError } from '../api/client'
import { useAsync } from '../lib/useAsync'
import type { Machine } from '../api/types'

interface EditMachineFormProps {
  machine: Machine
  onSaved: () => void
}

export function EditMachineForm({ machine, onSaved }: EditMachineFormProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(machine.name)
  const [type, setType] = useState(machine.type)
  const [location, setLocation] = useState(machine.location ?? '')
  const [operatorId, setOperatorId] = useState(machine.operatorId ?? '')
  const [supervisorId, setSupervisorId] = useState(machine.supervisorId ?? '')
  const [kind, setKind] = useState(machine.kind)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const users = useAsync(() => listUsers(), [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await updateMachine(machine.id, {
        name,
        type,
        location: location || undefined,
        operatorId: operatorId || null,
        supervisorId: supervisorId || null,
        kind,
      })
      setOpen(false)
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save changes')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Edit machine
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-6 flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3 sm:max-w-sm">
      <p className="text-sm font-semibold text-slate-900">Edit machine</p>
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
        <span className="font-medium text-slate-700">Type</span>
        <input
          type="text"
          required
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Location (optional)</span>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Operator (optional)</span>
        <select
          value={operatorId}
          onChange={(e) => setOperatorId(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        >
          <option value="">Unassigned</option>
          {(users.data ?? [])
            .filter((u) => u.role === 'operator')
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Supervisor (optional)</span>
        <select
          value={supervisorId}
          onChange={(e) => setSupervisorId(e.target.value)}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        >
          <option value="">No dedicated supervisor</option>
          {(users.data ?? [])
            .filter((u) => u.role === 'supervisor' || u.role === 'admin')
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Kind</span>
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value as 'production' | 'utility')}
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        >
          <option value="production">Production machine</option>
          <option value="utility">Plant equipment</option>
        </select>
      </label>
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
          onClick={() => setOpen(false)}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
