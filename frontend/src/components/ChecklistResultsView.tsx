import { useEffect, useState } from 'react'
import { listChecklistItems } from '../api/checklists'
import { listChecklistResults } from '../api/taskInstances'
import { ApiError } from '../api/client'
import type { ChecklistItem, ChecklistItemResult, ChecklistItemStatus } from '../api/types'

const LABELS: Record<ChecklistItemStatus, string> = {
  ok: 'ठीक है / OK',
  attention: 'ध्यान / Attention',
  critical: 'खराब / Critical',
  planned: 'बाद में / Planned',
}

const COLORS: Record<ChecklistItemStatus, string> = {
  ok: 'text-green-700',
  attention: 'text-amber-700',
  critical: 'text-red-700',
  planned: 'text-sky-700',
}

export function ChecklistResultsView({ taskTypeId, taskInstanceId }: { taskTypeId: string; taskInstanceId: string }) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null)
  const [results, setResults] = useState<ChecklistItemResult[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    Promise.all([listChecklistItems(taskTypeId), listChecklistResults(taskInstanceId)])
      .then(([itemList, resultList]) => {
        if (cancelled) return
        setItems(itemList)
        setResults(resultList)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Could not load checklist results')
      })
    return () => {
      cancelled = true
    }
  }, [taskTypeId, taskInstanceId])

  if (error) return <p className="mt-2 text-sm text-red-600">{error}</p>
  if (!items || !results) return <p className="mt-2 text-sm text-slate-500">Loading checklist…</p>
  if (items.length === 0) return null

  const byItem = new Map(results.map((r) => [r.checklistItemId, r]))

  return (
    <ul className="mt-3 max-h-96 overflow-auto text-sm text-slate-700">
      {items.map((item) => {
        const result = byItem.get(item.id)
        return (
          <li key={item.id} className="border-t border-slate-100 py-2">
            <p className="text-slate-900">{item.description}</p>
            {result && (
              <p className={COLORS[result.itemStatus]}>
                {LABELS[result.itemStatus]}
                {result.numericValue != null
                  ? ` · ${result.numericValue}${item.valueUnit ? ` ${item.valueUnit}` : ''}`
                  : ''}
              </p>
            )}
            {result?.notes ? <p className="text-slate-500">{result.notes}</p> : null}
          </li>
        )
      })}
    </ul>
  )
}
