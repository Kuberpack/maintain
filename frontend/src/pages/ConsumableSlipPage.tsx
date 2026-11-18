import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/client'
import { closeSlipLine, confirmSlip, getSlip, returnCore, returnMaterial } from '../api/consumables'
import type { SlipLine, StoreSlip } from '../api/consumables'
import { useAuth } from '../auth/useAuth'
import { Page, PageHeader } from '../components/ui'
import { useAsync } from '../lib/useAsync'
import { formatAmount, formatInr, formatSlipDate, parseQty } from '../lib/consumableFormat'
import { BalanceChip, buttonClass, fieldClass, quietButtonClass } from './consumableShared'

export function ConsumableSlipPage() {
  const { id } = useParams()
  const slip = useAsync(() => (id ? getSlip(id) : Promise.reject(new Error('Missing slip'))), [id])
  if (slip.loading) {
    return (
      <Page>
        <p className="text-stone-500">Loading slip…</p>
      </Page>
    )
  }
  if (slip.error || !slip.data) {
    return (
      <Page>
        <p className="rounded-2xl bg-red-50 px-4 py-3 text-red-700">{slip.error ?? 'Slip not found'}</p>
      </Page>
    )
  }
  return <SlipSheet slip={slip.data} onChange={slip.refetch} />
}

function SlipSheet({ slip, onChange }: { slip: StoreSlip; onChange: () => void }) {
  const { user } = useAuth()
  const canSign = user?.role === 'supervisor' || user?.role === 'management' || user?.role === 'admin'
  return (
    <Page width="max-w-3xl">
      <Link to="/consumables" className="mb-3 inline-flex min-h-10 items-center text-sm font-semibold text-brand">
        ← All slips
      </Link>
      <article className="rounded-2xl border border-line bg-white p-4 shadow-sm sm:p-6">
        <PageHeader
          eyebrow="Kuber Paper and Pack Pvt Ltd"
          title={`${slip.financialYear} STORE ISSUE SLIP`}
          subtitle={`Slip no. ${slip.slipNoLabel}`}
          actions={
            <button type="button" className={`${quietButtonClass} no-print`} onClick={() => window.print()}>
              Print
            </button>
          }
        />
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Date</dt>
            <dd className="font-semibold">{formatSlipDate(slip.slipDate)}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Shift</dt>
            <dd className="font-semibold">{slip.shift}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Department</dt>
            <dd className="font-semibold">{slip.department}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Machine</dt>
            <dd className="font-semibold">{slip.machineName}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Issued by</dt>
            <dd className="font-semibold">{slip.issuedByName}</dd>
          </div>
          <div>
            <dt className="text-xs font-bold tracking-wide text-stone-500 uppercase">Operator received by</dt>
            <dd className="font-semibold">{slip.receivedByName}</dd>
          </div>
        </dl>
        <div className="mt-3 flex flex-wrap gap-2">
          {slip.stale ? <span className="rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold text-white">Open longer than 1 shift</span> : null}
          {slip.supervisorConfirmedAt ? (
            <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-bold text-green-800">
              Supervisor signed · {slip.supervisorConfirmedName}
            </span>
          ) : (
            <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-950">Supervisor signature blank</span>
          )}
        </div>
        {slip.supervisorNote ? <p className="mt-3 text-sm text-stone-700">Supervisor note: {slip.supervisorNote}</p> : null}
        <div className="mt-4 flex flex-col gap-4">
          {slip.lines.map((line) => (
            <LineCard key={line.id} slip={slip} line={line} onChange={onChange} />
          ))}
        </div>
        {slip.hodName ? <p className="mt-4 text-sm text-stone-600">HOD: {slip.hodName}</p> : <p className="mt-4 text-sm text-stone-400">HOD signature blank</p>}
      </article>
      {canSign && slip.needsSign ? <ConfirmBox slip={slip} onChange={onChange} /> : null}
    </Page>
  )
}

function LineCard({ slip, line, onChange }: { slip: StoreSlip; line: SlipLine; onChange: () => void }) {
  const open = line.closedAt == null
  return (
    <section className="rounded-2xl border border-line p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold text-stone-500">S.No {line.lineNo}</p>
          <h3 className="text-lg font-bold">{line.itemName}</h3>
          <p className="text-sm text-stone-600">
            Issued {formatAmount(line.qtyIssued)} {line.unit} · rate {formatInr(line.rate)}
          </p>
        </div>
        <BalanceChip status={line.balanceStatus} />
      </div>
      {line.returns.length > 0 ? (
        <ul className="mt-2 text-sm text-stone-700">
          {line.returns.map((row) => (
            <li key={row.id}>
              MIN {formatAmount(row.qty)} {line.unit} on {formatSlipDate(row.returnedOn)} by {row.returnedByName}
              {row.note ? ` — ${row.note}` : ''}
            </li>
          ))}
        </ul>
      ) : null}
      {line.coreDue ? (
        <p className={`mt-2 text-sm font-semibold ${line.coreReturned ? 'text-green-800' : 'text-amber-800'}`}>
          {line.coreReturned ? 'Empty core returned' : 'Empty core still out'}
        </p>
      ) : null}
      {!open ? (
        <ClosedFigures line={line} />
      ) : (
        <OpenActions slipId={slip.id} line={line} onChange={onChange} signed={slip.supervisorConfirmedAt != null} />
      )}
      {line.coreDue && !line.coreReturned ? <CoreButton slipId={slip.id} lineId={line.id} onChange={onChange} /> : null}
    </section>
  )
}

function ClosedFigures({ line }: { line: SlipLine }) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4">
      <Figure label="Used" value={`${formatAmount(line.qtyUsed)} ${line.unit}`} />
      <Figure label="Returned" value={`${formatAmount(line.qtyReturned)} ${line.unit}`} />
      <Figure label="Left at machine" value={`${formatAmount(line.qtyCarried)} ${line.unit}`} />
      <Figure
        label="Leakage"
        value={line.leakageQty != null && line.leakageQty > 0 ? `${formatAmount(line.leakageQty)} · ${formatInr(line.leakageValue)}` : 'None'}
        warn={line.leakageQty != null && line.leakageQty > 0}
      />
      {line.productionQty != null ? (
        <div className="col-span-2 rounded-xl bg-paper px-3 py-2 sm:col-span-4">
          <p className="text-xs font-bold tracking-wide text-stone-500 uppercase">Usage vs standard</p>
          {line.expectedQty != null ? (
            <p className="font-semibold">
              Expected {formatAmount(line.expectedQty)} {line.unit} · actual {formatAmount(line.qtyUsed)} {line.unit}
              {line.variancePct != null ? ` · variance ${line.variancePct}%` : ''}
            </p>
          ) : (
            <p>Production {formatAmount(line.productionQty)} recorded. This item has no usage standard yet.</p>
          )}
        </div>
      ) : null}
      {line.leakageNote ? <p className="col-span-2 text-sm text-red-800 sm:col-span-4">Supervisor note: {line.leakageNote}</p> : null}
    </div>
  )
}

function Figure({ label, value, warn = false }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className={`rounded-xl px-3 py-2 ${warn ? 'bg-red-50' : 'bg-paper'}`}>
      <p className="text-xs font-bold tracking-wide text-stone-500 uppercase">{label}</p>
      <p className={`font-semibold ${warn ? 'text-red-800' : ''}`}>{value}</p>
    </div>
  )
}

function OpenActions({ slipId, line, onChange, signed }: { slipId: string; line: SlipLine; onChange: () => void; signed: boolean }) {
  const { user } = useAuth()
  const [used, setUsed] = useState('')
  const [returned, setReturned] = useState(String(line.qtyReturned || ''))
  const [carried, setCarried] = useState('')
  const [production, setProduction] = useState('')
  const [note, setNote] = useState('')
  const [returnQty, setReturnQty] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const canNote = user?.role === 'supervisor' || user?.role === 'management' || user?.role === 'admin'

  const usedN = parseQty(used)
  const returnedN = parseQty(returned)
  const carriedN = parseQty(carried)
  const productionN = production.trim() === '' ? null : parseQty(production)
  const leakage =
    usedN != null && returnedN != null && carriedN != null
      ? Math.round((line.qtyIssued - usedN - returnedN - carriedN) * 1000) / 1000
      : null
  const expected =
    productionN != null && line.standardQty != null && line.standardPer
      ? Math.round(line.standardQty * (productionN / line.standardPer) * 1000) / 1000
      : null
  const variance = expected != null && expected !== 0 && usedN != null ? Math.round(((usedN - expected) / expected) * 1000) / 10 : null

  async function handleClose(event: FormEvent) {
    event.preventDefault()
    if (usedN == null || returnedN == null || carriedN == null) {
      setError('Enter used, returned, and left at the machine. Use 0 if none.')
      return
    }
    if (leakage != null && leakage < -0.0005) {
      setError('Those three quantities add up to more than was issued')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await closeSlipLine(slipId, line.id, {
        qtyUsed: usedN,
        qtyReturned: returnedN,
        qtyCarried: carriedN,
        productionQty: productionN,
        leakageNote: canNote ? note.trim() || null : null,
      })
      onChange()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not close this line')
    } finally {
      setSaving(false)
    }
  }

  async function handleReturn(event: FormEvent) {
    event.preventDefault()
    const qty = parseQty(returnQty)
    if (qty == null || qty <= 0) {
      setError('Enter how much is coming back to the store')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await returnMaterial(slipId, line.id, qty, 'MIN')
      onChange()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not record the return')
    } finally {
      setSaving(false)
    }
  }

  if (signed) return null
  return (
    <div className="mt-3 flex flex-col gap-3">
      <form onSubmit={(event) => void handleReturn(event)} className="flex flex-col gap-2 sm:flex-row sm:items-end">
        <label className="flex flex-1 flex-col gap-1 text-sm font-semibold">
          Return to store now (MIN)
          <input inputMode="decimal" value={returnQty} onChange={(event) => setReturnQty(event.target.value)} className={fieldClass} placeholder={`up to ${formatAmount(line.qtyIssued - line.qtyReturned)}`} />
        </label>
        <button type="submit" disabled={saving} className={quietButtonClass}>
          Record MIN
        </button>
      </form>
      <form onSubmit={(event) => void handleClose(event)} className="rounded-2xl bg-paper p-3">
        <p className="mb-2 text-sm font-bold">Shift-end close-out</p>
        <div className="grid gap-2 sm:grid-cols-3">
          <QtyField label="Qty used" value={used} onChange={setUsed} />
          <QtyField label="Qty returned" value={returned} onChange={setReturned} />
          <QtyField label="Left at machine" value={carried} onChange={setCarried} />
        </div>
        <label className="mt-2 flex flex-col gap-1 text-sm font-semibold">
          Production this shift
          <span className="text-xs font-medium text-stone-500">
            {line.standardQty != null && line.standardPer != null
              ? `Standard: ${formatAmount(line.standardQty)} ${line.unit} per ${formatAmount(line.standardPer)} ${line.standardBasis ?? ''}`
              : 'No usage standard on this item yet. The number is still saved.'}
          </span>
          <input inputMode="decimal" value={production} onChange={(event) => setProduction(event.target.value)} className={fieldClass} />
        </label>
        {leakage != null ? (
          <p className={`mt-2 text-sm font-bold ${leakage > 0.0005 ? 'text-red-700' : 'text-green-800'}`}>
            {leakage > 0.0005 ? `LEAKAGE ${formatAmount(leakage)} ${line.unit} · ${formatInr(leakage * line.rate)}` : 'Accounted in full'}
          </p>
        ) : null}
        {expected != null && usedN != null ? (
          <p className="mt-1 text-sm">
            Expected {formatAmount(expected)} {line.unit} · actual {formatAmount(usedN)} {line.unit}
            {variance != null ? ` · variance ${variance}%` : ''}
          </p>
        ) : null}
        {canNote && leakage != null && leakage > 0.0005 ? (
          <label className="mt-2 flex flex-col gap-1 text-sm font-semibold">
            Supervisor note for the leakage
            <textarea value={note} onChange={(event) => setNote(event.target.value)} className={fieldClass} rows={2} />
          </label>
        ) : null}
        {!canNote && leakage != null && leakage > 0.0005 ? (
          <p className="mt-2 text-sm text-amber-900">A supervisor has to note this leakage before they can sign the slip.</p>
        ) : null}
        {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
        <button type="submit" disabled={saving} className={`${buttonClass} mt-3 w-full`}>
          {saving ? 'Saving…' : 'Close this line'}
        </button>
      </form>
    </div>
  )
}

function QtyField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-semibold">
      {label}
      <input inputMode="decimal" value={value} onChange={(event) => onChange(event.target.value)} className={fieldClass} />
    </label>
  )
}

function CoreButton({ slipId, lineId, onChange }: { slipId: string; lineId: string; onChange: () => void }) {
  const [error, setError] = useState<string | null>(null)
  async function mark() {
    setError(null)
    try {
      await returnCore(slipId, lineId)
      onChange()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not mark the core')
    }
  }
  return (
    <div className="mt-2">
      <button type="button" onClick={() => void mark()} className={quietButtonClass}>
        Empty core returned
      </button>
      {error ? <p className="mt-1 text-sm text-red-700">{error}</p> : null}
    </div>
  )
}

function ConfirmBox({ slip, onChange }: { slip: StoreSlip; onChange: () => void }) {
  const [note, setNote] = useState('')
  const [lineNotes, setLineNotes] = useState<Record<string, string>>(() =>
    Object.fromEntries(slip.lines.filter((line) => (line.leakageQty ?? 0) > 0).map((line) => [line.id, line.leakageNote ?? ''])),
  )
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const leakageLines = slip.lines.filter((line) => (line.leakageQty ?? 0) > 0)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      await confirmSlip(slip.id, {
        note: note.trim() || null,
        lineNotes: leakageLines.map((line) => ({ lineId: line.id, leakageNote: (lineNotes[line.id] ?? '').trim() })),
      })
      onChange()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mt-4 rounded-2xl border border-line bg-white p-4">
      <h2 className="text-lg font-bold">Supervisor signature</h2>
      <p className="mb-3 text-sm text-stone-600">This replaces the blank signature on the paper slip. Leakage still needs a note.</p>
      {leakageLines.map((line) => (
        <label key={line.id} className="mb-2 flex flex-col gap-1 text-sm font-semibold">
          Note for {line.itemName} ({formatAmount(line.leakageQty)} {line.unit})
          <textarea
            required
            value={lineNotes[line.id] ?? ''}
            onChange={(event) => setLineNotes((current) => ({ ...current, [line.id]: event.target.value }))}
            className={fieldClass}
            rows={2}
          />
        </label>
      ))}
      <label className="flex flex-col gap-1 text-sm font-semibold">
        Slip note (optional)
        <textarea value={note} onChange={(event) => setNote(event.target.value)} className={fieldClass} rows={2} />
      </label>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={saving} className={`${buttonClass} mt-3 w-full`}>
        {saving ? 'Signing…' : 'Sign slip'}
      </button>
    </form>
  )
}
