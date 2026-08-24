import { useEffect, useState } from 'react'
import { listChecklistItems } from '../api/checklists'
import { markTaskInstanceDone } from '../api/taskInstances'
import { uploadPhoto } from '../api/photos'
import { ApiError } from '../api/client'
import { CameraCapture } from './CameraCapture'
import { hi } from '../lib/i18n'
import type { ChecklistItem, ChecklistItemStatus, TaskInstance } from '../api/types'

interface ChecklistRunFormProps {
  instance: TaskInstance
  taskTypeId: string
  onCompleted: () => void
  onCancel: () => void
}

interface Draft {
  itemStatus: ChecklistItemStatus | ''
  numericValue: string
  notes: string
}

const CHOICES: { value: ChecklistItemStatus; label: string; className: string }[] = [
  { value: 'ok', label: hi.ok, className: 'bg-green-600 text-white' },
  { value: 'attention', label: hi.problem, className: 'bg-amber-500 text-white' },
  { value: 'critical', label: hi.stop, className: 'bg-red-600 text-white' },
]

export function ChecklistRunForm({ instance, taskTypeId, onCompleted, onCancel }: ChecklistRunFormProps) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [step, setStep] = useState(0)
  const [photo, setPhoto] = useState<File | null>(null)
  const [exceptionPhoto, setExceptionPhoto] = useState<File | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startedAt] = useState(() => new Date().toISOString())

  useEffect(() => {
    let cancelled = false
    listChecklistItems(taskTypeId)
      .then((data) => {
        if (cancelled) return
        setItems(data)
        const next: Record<string, Draft> = {}
        for (const item of data) {
          next[item.id] = { itemStatus: '', numericValue: '', notes: '' }
        }
        setDrafts(next)
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(err instanceof ApiError ? err.message : 'Could not load checklist')
      })
    return () => {
      cancelled = true
    }
  }, [taskTypeId])

  function updateDraft(id: string, patch: Partial<Draft>) {
    setDrafts((prev) => {
      const current: Draft = prev[id] ?? { itemStatus: '', numericValue: '', notes: '' }
      return { ...prev, [id]: { ...current, ...patch } }
    })
  }

  const hasException =
    items?.some((item) => {
      const status = drafts[item.id]?.itemStatus
      return status === 'attention' || status === 'critical'
    }) ?? false

  const photoStep = items ? items.length : 0
  const exceptionStep = photoStep + 1
  const lastStep = hasException ? exceptionStep : photoStep
  const onItems = items !== null && step < items.length
  const item = onItems && items ? items[step] : null
  const draft = item ? drafts[item.id] : null

  async function handleSubmit() {
    if (!items) return
    setError(null)
    for (const row of items) {
      const d = drafts[row.id]
      if (!d?.itemStatus) {
        setError('Set a status on every inspection point')
        return
      }
      if (row.requiresValue && d.numericValue.trim() === '') {
        setError(`Enter a reading for: ${row.description}`)
        return
      }
    }
    if (!photo) {
      setError(hi.photo)
      return
    }
    if (hasException && !exceptionPhoto) {
      setError(hi.extraPhoto)
      return
    }
    setSubmitting(true)
    try {
      const uploaded = await uploadPhoto(photo)
      const extra = exceptionPhoto ? await uploadPhoto(exceptionPhoto) : undefined
      await markTaskInstanceDone(instance.id, {
        photoUrl: uploaded.url,
        exceptionPhotoUrl: extra?.url,
        startedAt,
        results: items.map((row) => {
          const d = drafts[row.id] ?? { itemStatus: '' as const, numericValue: '', notes: '' }
          const numeric = d.numericValue.trim() === '' ? undefined : Number(d.numericValue)
          return {
            checklistItemId: row.id,
            itemStatus: d.itemStatus as ChecklistItemStatus,
            numericValue: Number.isFinite(numeric) ? numeric : undefined,
            notes: d.notes.trim() || undefined,
          }
        }),
      })
      onCompleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit')
    } finally {
      setSubmitting(false)
    }
  }

  function canAdvanceItem(): boolean {
    if (!item || !draft) return false
    if (!draft.itemStatus) return false
    if (item.requiresValue && draft.numericValue.trim() === '') return false
    return true
  }

  if (loadError) return <p className="text-base text-red-600">{loadError}</p>
  if (!items) return <p className="text-base text-slate-500">Loading…</p>
  if (items.length === 0) {
    return <p className="text-base text-slate-500">This task type has no checklist items.</p>
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-lg font-semibold text-slate-800">
        {hi.progress(Math.min(step + 1, lastStep + 1), lastStep + 1)}
      </p>

      {item && draft && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-1 text-sm font-medium uppercase tracking-wide text-slate-500">{item.section}</p>
          <p className="mb-4 text-xl font-semibold text-slate-900">{item.description}</p>
          {item.requiresValue && (
            <label className="mb-4 flex flex-col gap-1 text-base">
              <span className="font-medium text-slate-700">
                {hi.reading}
                {item.valueUnit ? ` (${item.valueUnit})` : ''}
                {item.minValue != null || item.maxValue != null
                  ? ` · ${item.minValue ?? '—'}–${item.maxValue ?? '—'}`
                  : ''}
              </span>
              <input
                type="number"
                inputMode="decimal"
                step="any"
                required
                value={draft.numericValue}
                onChange={(e) => updateDraft(item.id, { numericValue: e.target.value })}
                className="min-h-14 rounded-lg border border-slate-300 px-3 text-2xl focus:border-slate-500 focus:outline-none"
              />
            </label>
          )}
          <div className="flex flex-col gap-2">
            {CHOICES.map((choice) => (
              <button
                key={choice.value}
                type="button"
                onClick={() => updateDraft(item.id, { itemStatus: choice.value })}
                className={`min-h-16 rounded-xl px-4 text-lg font-semibold ${
                  draft.itemStatus === choice.value ? choice.className : 'border border-slate-300 bg-white text-slate-800'
                }`}
              >
                {choice.label}
              </button>
            ))}
            <button
              type="button"
              onClick={() => updateDraft(item.id, { itemStatus: 'planned' })}
              className={`min-h-12 rounded-xl px-4 text-base ${
                draft.itemStatus === 'planned' ? 'bg-sky-600 text-white' : 'border border-slate-200 text-slate-600'
              }`}
            >
              {hi.later}
            </button>
          </div>
          {(draft.itemStatus === 'attention' || draft.itemStatus === 'critical') && (
            <input
              type="text"
              placeholder={hi.notes}
              value={draft.notes}
              onChange={(e) => updateDraft(item.id, { notes: e.target.value })}
              className="mt-3 min-h-12 w-full rounded-lg border border-slate-300 px-3 text-base"
            />
          )}
        </div>
      )}

      {step === photoStep && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="mb-3 text-xl font-semibold text-slate-900">{hi.photo}</p>
          <CameraCapture photo={photo} onPhotoChange={setPhoto} label={hi.photo} required large />
        </div>
      )}

      {hasException && step === exceptionStep && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="mb-3 text-xl font-semibold text-slate-900">{hi.extraPhoto}</p>
          <CameraCapture
            photo={exceptionPhoto}
            onPhotoChange={setExceptionPhoto}
            label={hi.extraPhoto}
            required
            large
          />
        </div>
      )}

      {error && <p className="text-base text-red-600">{error}</p>}

      <div className="flex flex-col gap-2">
        {step < lastStep && (
          <button
            type="button"
            disabled={onItems && !canAdvanceItem()}
            onClick={() => setStep((s) => s + 1)}
            className="min-h-16 rounded-xl bg-slate-900 text-lg font-semibold text-white disabled:opacity-40"
          >
            {hi.next}
          </button>
        )}
        {step === lastStep && (
          <button
            type="button"
            disabled={submitting || !photo || (hasException && !exceptionPhoto)}
            onClick={() => void handleSubmit()}
            className="min-h-16 rounded-xl bg-slate-900 text-lg font-semibold text-white disabled:opacity-40"
          >
            {submitting ? hi.saving : hi.submit}
          </button>
        )}
        {step > 0 && (
          <button
            type="button"
            onClick={() => setStep((s) => s - 1)}
            className="min-h-12 rounded-xl border border-slate-300 text-base font-medium text-slate-700"
          >
            {hi.back}
          </button>
        )}
        <button type="button" onClick={onCancel} className="min-h-12 text-base text-slate-500">
          Cancel
        </button>
      </div>
    </div>
  )
}
