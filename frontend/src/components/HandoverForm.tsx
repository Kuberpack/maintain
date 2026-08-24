import { useState } from 'react'
import type { FormEvent } from 'react'
import { createHandoverNote } from '../api/handover'
import { ApiError } from '../api/client'
import { useLocale } from '../locale/localeContext'
import type { HandoverNote } from '../api/types'

export function HandoverForm({
  machineId,
  latest,
  onSaved,
}: {
  machineId: string
  latest: HandoverNote | null
  onSaved: () => void
}) {
  const { t } = useLocale()
  const [note, setNote] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!note.trim()) return
    setError(null)
    setSubmitting(true)
    try {
      await createHandoverNote({ machineId, note: note.trim() })
      setNote('')
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save note')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <section className="mb-6 rounded-xl border border-slate-200 bg-white p-4">
      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{t.machineNote}</h2>
      {latest ? (
        <p className="mb-3 text-base text-slate-800">
          {latest.note}
          <span className="mt-1 block text-sm text-slate-500">{new Date(latest.createdAt).toLocaleString()}</span>
        </p>
      ) : (
        <p className="mb-3 text-sm text-slate-500">{t.noNoteYet}</p>
      )}
      <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-2">
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="bearing noise on SF-1"
          className="min-h-16 rounded-md border border-slate-300 px-3 py-2 text-base"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="min-h-12 rounded-md bg-slate-900 px-4 text-base font-medium text-white disabled:opacity-50"
        >
          {submitting ? t.saving : t.saveNote}
        </button>
      </form>
    </section>
  )
}
