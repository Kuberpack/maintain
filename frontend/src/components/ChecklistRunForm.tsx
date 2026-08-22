import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { listChecklistItems } from '../api/checklists'
import { markTaskInstanceDone } from '../api/taskInstances'
import { uploadPhoto } from '../api/photos'
import { ApiError } from '../api/client'
import { CameraCapture } from './CameraCapture'
import type { ChecklistItem, ChecklistItemStatus, TaskInstance } from '../api/types'

const STATUSES: { value: ChecklistItemStatus; label: string; hint: string }[] = [
  { value: 'ok', label: 'OK', hint: 'Green' },
  { value: 'attention', label: 'Attention', hint: 'Yellow' },
  { value: 'critical', label: 'Critical', hint: 'Red' },
  { value: 'planned', label: 'Planned', hint: 'Blue' },
]

interface ChecklistRunFormProps {
  instance: TaskInstance
  taskTypeId: string
  photo: File | null
  onPhotoChange: (file: File | null) => void
  onCompleted: () => void
  onCancel: () => void
}

interface Draft {
  itemStatus: ChecklistItemStatus | ''
  numericValue: string
  notes: string
}

export function ChecklistRunForm({
  instance,
  taskTypeId,
  photo,
  onPhotoChange,
  onCompleted,
  onCancel,
}: ChecklistRunFormProps) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoadError(null)
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

  const sections = useMemo(() => {
    if (!items) return []
    const order: string[] = []
    const grouped = new Map<string, ChecklistItem[]>()
    for (const item of items) {
      if (!grouped.has(item.section)) {
        grouped.set(item.section, [])
        order.push(item.section)
      }
      grouped.get(item.section)!.push(item)
    }
    return order.map((section) => ({ section, items: grouped.get(section)! }))
  }, [items])

  function updateDraft(id: string, patch: Partial<Draft>) {
    setDrafts((prev) => {
      const current: Draft = prev[id] ?? { itemStatus: '', numericValue: '', notes: '' }
      return { ...prev, [id]: { ...current, ...patch } }
    })
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!items) return
    setError(null)
    for (const item of items) {
      const draft = drafts[item.id]
      if (!draft?.itemStatus) {
        setError('Set a status on every inspection point')
        return
      }
      if (item.requiresValue && draft.numericValue.trim() === '') {
        setError(`Enter a reading for: ${item.description}`)
        return
      }
    }
    setSubmitting(true)
    try {
      const photoUrl = photo ? (await uploadPhoto(photo)).url : undefined
      await markTaskInstanceDone(instance.id, {
        photoUrl,
        results: items.map((item) => {
          const draft = drafts[item.id] ?? { itemStatus: '' as const, numericValue: '', notes: '' }
          const numeric = draft.numericValue.trim() === '' ? undefined : Number(draft.numericValue)
          return {
            checklistItemId: item.id,
            itemStatus: draft.itemStatus as ChecklistItemStatus,
            numericValue: Number.isFinite(numeric) ? numeric : undefined,
            notes: draft.notes.trim() || undefined,
          }
        }),
      })
      onCompleted()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not mark task done')
    } finally {
      setSubmitting(false)
    }
  }

  if (loadError) return <p className="text-sm text-red-600">{loadError}</p>
  if (!items) return <p className="text-sm text-slate-500">Loading checklist…</p>
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">This task type has no checklist items.</p>
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-4">
      {sections.map((group) => (
        <fieldset key={group.section} className="rounded-md border border-slate-200 p-3">
          <legend className="px-1 text-sm font-semibold text-slate-800">{group.section}</legend>
          <ul className="flex flex-col gap-3">
            {group.items.map((item) => {
              const draft = drafts[item.id]
              return (
                <li key={item.id} className="border-b border-slate-100 pb-3 last:border-b-0 last:pb-0">
                  <p className="mb-2 text-sm text-slate-900">{item.description}</p>
                  <div className="flex flex-wrap gap-2">
                    {STATUSES.map((s) => (
                      <label
                        key={s.value}
                        className="inline-flex items-center gap-1 rounded-md border border-slate-200 px-2 py-1 text-xs text-slate-700"
                      >
                        <input
                          type="radio"
                          name={`status-${item.id}`}
                          value={s.value}
                          checked={draft?.itemStatus === s.value}
                          onChange={() => updateDraft(item.id, { itemStatus: s.value })}
                        />
                        {s.label}
                      </label>
                    ))}
                  </div>
                  {item.requiresValue && (
                    <label className="mt-2 flex items-center gap-2 text-sm text-slate-700">
                      <span className="shrink-0">Reading{item.valueUnit ? ` (${item.valueUnit})` : ''}</span>
                      <input
                        type="number"
                        step="any"
                        required
                        value={draft?.numericValue ?? ''}
                        onChange={(e) => updateDraft(item.id, { numericValue: e.target.value })}
                        className="w-32 rounded-md border border-slate-300 px-2 py-1 text-base focus:border-slate-500 focus:outline-none"
                      />
                    </label>
                  )}
                  <input
                    type="text"
                    placeholder="Notes (optional)"
                    value={draft?.notes ?? ''}
                    onChange={(e) => updateDraft(item.id, { notes: e.target.value })}
                    className="mt-2 w-full rounded-md border border-slate-300 px-2 py-1 text-sm focus:border-slate-500 focus:outline-none"
                  />
                </li>
              )
            })}
          </ul>
        </fieldset>
      ))}
      <CameraCapture photo={photo} onPhotoChange={onPhotoChange} />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {submitting ? 'Saving…' : 'Mark done'}
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
