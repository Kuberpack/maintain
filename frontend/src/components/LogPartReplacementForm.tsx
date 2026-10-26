import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { createPartReplacement } from '../api/partReplacements'
import { listSpareParts } from '../api/spareParts'
import { ApiError } from '../api/client'
import { todayLocalDate } from '../lib/date'
import { formatQty, parseWholeQty } from '../lib/qty'
import { useAsync } from '../lib/useAsync'
import { useAuth } from '../auth/useAuth'
import { useLocale } from '../locale/localeContext'
import type { SparePart } from '../api/types'

interface LogPartReplacementFormProps {
  machineId: string
  onLogged: () => void
  /** Phone-sized controls for the operator's Today page. */
  large?: boolean
}

export function LogPartReplacementForm({ machineId, onLogged, large = false }: LogPartReplacementFormProps) {
  const { t } = useLocale()
  const { user } = useAuth()
  const canDrawStock = user?.role === 'supervisor' || user?.role === 'admin'
  const stock = useAsync(
    () => (canDrawStock ? listSpareParts().catch(() => [] as SparePart[]) : Promise.resolve([] as SparePart[])),
    [canDrawStock],
  )
  const [open, setOpen] = useState(false)
  const [partName, setPartName] = useState('')
  const [replacedAt, setReplacedAt] = useState(todayLocalDate())
  const [notes, setNotes] = useState('')
  const [stockQuery, setStockQuery] = useState('')
  const [sparePartId, setSparePartId] = useState('')
  const [quantityUsed, setQuantityUsed] = useState('1')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const stockMatches = useMemo(() => {
    const query = stockQuery.trim().toLowerCase()
    if (!query) return []
    return (stock.data ?? [])
      .filter((part) => `${part.name} ${part.itemGroup} ${part.category}`.toLowerCase().includes(query))
      .slice(0, 8)
  }, [stock.data, stockQuery])
  const selectedSpare = (stock.data ?? []).find((part) => part.id === sparePartId) ?? null

  const inputClass = large
    ? 'rounded-xl border border-slate-300 px-3 py-3 text-lg focus:border-slate-500 focus:outline-none'
    : 'rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none'
  const submitClass = large
    ? 'min-h-14 rounded-xl bg-slate-900 px-4 text-lg font-semibold text-white disabled:opacity-50'
    : 'rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50'
  const secondaryClass = large
    ? 'min-h-14 rounded-xl border border-slate-300 px-4 text-lg font-medium text-slate-700'
    : 'rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50'

  function reset() {
    setPartName('')
    setReplacedAt(todayLocalDate())
    setNotes('')
    setStockQuery('')
    setSparePartId('')
    setQuantityUsed('1')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    let used: number | undefined
    if (sparePartId) {
      const onHand = selectedSpare == null ? 0 : Math.trunc(selectedSpare.qtyOnHand)
      const parsed = parseWholeQty(quantityUsed)
      if (onHand < 1) {
        setError('None on hand')
        return
      }
      if (parsed == null || parsed < 1) {
        setError('Quantity used must be a whole number of at least 1')
        return
      }
      if (parsed > onHand) {
        setError(`Only ${onHand} on hand`)
        return
      }
      used = parsed
    }
    setError(null)
    setSubmitting(true)
    try {
      await createPartReplacement({
        machineId,
        partName,
        replacedAt,
        notes: notes || undefined,
        sparePartId: sparePartId || undefined,
        quantityUsed: used,
      })
      reset()
      setOpen(false)
      onLogged()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not log part replacement')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={
          large
            ? 'min-h-14 w-full rounded-xl border-2 border-slate-900 px-4 text-lg font-semibold text-slate-900'
            : 'rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50'
        }
      >
        {t.logReplacement}
      </button>
    )
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className={`flex w-full flex-col gap-3 border border-slate-200 p-3 ${large ? 'rounded-xl' : 'rounded-md'}`}
    >
      <p className="text-sm font-semibold text-slate-900">{t.logReplacement}</p>
      {canDrawStock && (stock.data?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-slate-700">From stock ({t.optional})</span>
            <input
              type="text"
              value={stockQuery}
              onChange={(e) => setStockQuery(e.target.value)}
              placeholder="Search stock"
              className={inputClass}
            />
          </label>
          {stockMatches.length > 0 && (
            <ul className="flex flex-col gap-1">
              {stockMatches.map((part) => (
                <li key={part.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSparePartId(part.id)
                      setPartName(part.name)
                      setStockQuery('')
                    }}
                    className="w-full rounded-md border border-slate-200 px-3 py-2 text-left text-sm hover:bg-slate-50"
                  >
                    <span className="font-medium text-slate-900">{part.name}</span>
                    <span className="text-slate-500">
                      {' '}
                      · {part.category}
                      {part.itemGroup ? ` · ${part.itemGroup}` : ''} · {formatQty(part.qtyOnHand)}
                      {part.unit ? ` ${part.unit}` : ''} on hand
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {selectedSpare && (
            <div className="flex flex-wrap items-end gap-2">
              <p className="text-sm text-slate-700">
                Taking <span className="font-medium">{selectedSpare.name}</span> ({formatQty(selectedSpare.qtyOnHand)}
                {selectedSpare.unit ? ` ${selectedSpare.unit}` : ''} on hand)
              </p>
              {Math.trunc(selectedSpare.qtyOnHand) < 1 ? (
                <p className="text-sm text-amber-800">None on hand.</p>
              ) : (
                <label className="flex flex-col gap-1 text-sm">
                  <span className="font-medium text-slate-700">Qty used</span>
                  {/* min and step stay on the same integer grid. min 0.001 with step 1 rejects 1. */}
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={Math.trunc(selectedSpare.qtyOnHand)}
                    step={1}
                    required
                    value={quantityUsed}
                    onChange={(e) => setQuantityUsed(e.target.value)}
                    className={inputClass}
                  />
                </label>
              )}
              <button
                type="button"
                onClick={() => {
                  setSparePartId('')
                  setQuantityUsed('1')
                }}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">{t.partName}</span>
        <input
          type="text"
          required
          value={partName}
          onChange={(e) => setPartName(e.target.value)}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">{t.replacedOn}</span>
        <input
          type="date"
          required
          value={replacedAt}
          onChange={(e) => setReplacedAt(e.target.value)}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">
          {t.notes} ({t.optional})
        </span>
        <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className={inputClass} />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className={`flex gap-2 ${large ? 'flex-col' : ''}`}>
        <button type="submit" disabled={submitting} className={submitClass}>
          {submitting ? t.saving : t.logReplacement}
        </button>
        <button
          type="button"
          onClick={() => {
            reset()
            setOpen(false)
          }}
          className={secondaryClass}
        >
          {t.cancel}
        </button>
      </div>
    </form>
  )
}
