import { useState } from 'react'
import type { FormEvent } from 'react'
import { createMachine } from '../api/machines'
import { listUsers } from '../api/users'
import { listMachines } from '../api/machines'
import { ApiError } from '../api/client'
import { useAsync } from '../lib/useAsync'

interface CreateMachineFormProps {
  onCreated: () => void
}

export function CreateMachineForm({ onCreated }: CreateMachineFormProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [type, setType] = useState('')
  const [location, setLocation] = useState('')
  const [operatorId, setOperatorId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const users = useAsync(() => listUsers(), [])
  const machines = useAsync(() => listMachines(), [])

  function reset() {
    setName('')
    setType('')
    setLocation('')
    setOperatorId('')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createMachine({
        name,
        type,
        location: location || undefined,
        operatorId: operatorId || null,
      })
      reset()
      setOpen(false)
      onCreated()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create machine')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mb-4 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        + Add machine
      </button>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="mb-4 flex flex-col gap-3 rounded-md border border-slate-200 bg-white p-3 sm:max-w-sm">
      <p className="text-sm font-semibold text-slate-900">Add machine</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Name</span>
        <input
          type="text"
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Corrugator 1"
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
          placeholder="e.g. corrugator, printer, laminator"
          className="rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none"
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">Location (optional)</span>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="e.g. Bay A"
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
            .filter((u) => !(machines.data ?? []).some((m) => m.operatorId === u.id))
            .map((u) => (
              <option key={u.id} value={u.id}>
                {u.name}
              </option>
            ))}
        </select>
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Adding…' : 'Add machine'}
        </button>
        <button
          type="button"
          onClick={() => {
            reset()
            setOpen(false)
          }}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}
