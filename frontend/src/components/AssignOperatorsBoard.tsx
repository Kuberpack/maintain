import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { listUsers } from '../api/users'
import { setOperatorAssignments } from '../api/machines'
import { ApiError } from '../api/client'
import { useAsync } from '../lib/useAsync'
import { useLocale } from '../locale/localeContext'
import type { Machine } from '../api/types'

/** One operator may cover several units (Suresh on four FAC heads). */
export function AssignOperatorsBoard({
  machines,
  onSaved,
}: {
  machines: Machine[]
  onSaved: () => void
}) {
  const { t } = useLocale()
  const users = useAsync(() => listUsers(), [])
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    Object.fromEntries(machines.map((m) => [m.id, m.operatorId ?? ''])),
  )
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setDraft(Object.fromEntries(machines.map((m) => [m.id, m.operatorId ?? ''])))
  }, [machines])

  const operators = (users.data ?? []).filter((u) => u.role === 'operator')

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      await setOperatorAssignments(
        machines.map((m) => ({
          machineId: m.id,
          operatorId: draft[m.id] || null,
        })),
      )
      setSaved(true)
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save assignments')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className="mb-6 rounded-lg border border-slate-200 bg-white p-4"
    >
      <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">{t.assignOperators}</h2>
      <p className="mt-1 mb-3 text-sm text-slate-600">{t.assignOperatorsHint}</p>

      <ul className="flex flex-col gap-2">
        {machines.map((machine) => (
          <li key={machine.id} className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-3">
            <span className="min-w-0 flex-1 text-sm font-medium text-slate-900">{machine.name}</span>
            <select
              value={draft[machine.id] ?? ''}
              onChange={(e) => setDraft((prev) => ({ ...prev, [machine.id]: e.target.value }))}
              className="rounded-md border border-slate-300 px-3 py-2 text-sm sm:w-64"
            >
              <option value="">{t.unassigned}</option>
              {operators.map((op) => (
                <option key={op.id} value={op.id}>
                  {op.name}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>

      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      {saved && !error && <p className="mt-2 text-sm text-green-700">{t.assignmentsSaved}</p>}

      <button
        type="submit"
        disabled={submitting || users.loading}
        className="mt-3 rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {submitting ? t.saving : t.saveAssignments}
      </button>
    </form>
  )
}
