import { useEffect, useState } from 'react'
import { listChecklistItems } from '../api/checklists'
import { listChecklistResults } from '../api/taskInstances'
import { ApiError } from '../api/client'
import type { ChecklistItem, ChecklistItemResult, ChecklistItemStatus } from '../api/types'

const LABELS: Record<ChecklistItemStatus, string> = {
  ok: 'OK',
  attention: 'Attention',
  critical: 'Critical',
  planned: 'Planned',
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
    <ul className="mt-2 max-h-64 overflow-auto text-xs text-slate-600">
      {items.map((item) => {
        const result = byItem.get(item.id)
        return (
          <li key={item.id} className="border-t border-slate-100 py-1">
            <span className="text-slate-800">{item.description}</span>
            {result && (
              <span className="text-slate-500">
                {' '}
                · {LABELS[result.itemStatus]}
                {result.numericValue != null
                  ? ` · ${result.numericValue}${item.valueUnit ? ` ${item.valueUnit}` : ''}`
                  : ''}
              </span>
            )}
          </li>
        )
      })}
    </ul>
  )
}
