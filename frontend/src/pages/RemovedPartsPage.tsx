import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { listMachines } from '../api/machines'
import { uploadPhoto } from '../api/photos'
import { getRemovedPartsReport, listRemovedParts, setRemovedPartDisposition } from '../api/removedParts'
import { listSpareParts } from '../api/spareParts'
import type { Machine, RemovedPart, RemovedPartStatus, SparePart } from '../api/types'
import { CameraCapture } from '../components/CameraCapture'
import { ProofPhoto } from '../components/ProofPhoto'
import { EmptyState, ErrorState, KpiCard, LoadingState, Page, PageHeader } from '../components/ui'
import { formatQty, parseWholeQty } from '../lib/qty'
import {
  CONDITION_LABEL,
  STATUS_LABEL,
  STATUS_ORDER,
  eventDetail,
  formatWhen,
  inr,
  isStalePending,
  scrapText,
} from '../lib/removedParts'
import { useAsync } from '../lib/useAsync'
import { useLocale } from '../locale/localeContext'

const inputClass = 'min-h-11 w-full rounded-xl border border-line bg-white px-3 text-sm text-ink'

export function RemovedPartsPage() {
  const { t } = useLocale()
  const { user } = useAuth()
  const canUpdate = user?.role === 'supervisor' || user?.role === 'admin'
  const [status, setStatus] = useState('')
  const [machineId, setMachineId] = useState('')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [pendingOnly, setPendingOnly] = useState(false)
  const [staleOnly, setStaleOnly] = useState(false)
  const [staleDays, setStaleDays] = useState(7)

  const machines = useAsync(() => listMachines(), [])
  const report = useAsync(() => getRemovedPartsReport(staleDays), [staleDays])
  const parts = useAsync(
    () =>
      listRemovedParts({
        status: status || undefined,
        machineId: machineId || undefined,
        from: from || undefined,
        to: to || undefined,
        pendingOnly,
        staleOnly,
        staleDays,
      }),
    [status, machineId, from, to, pendingOnly, staleOnly, staleDays],
  )
  const stock = useAsync(
    () => (canUpdate ? listSpareParts().catch(() => [] as SparePart[]) : Promise.resolve([] as SparePart[])),
    [canUpdate],
  )

  const partRows = parts.data
  const reportData = report.data
  const machineRows = machines.data
  const firstLoad = (parts.loading && !partRows) || (report.loading && !reportData) || (machines.loading && !machineRows)
  if (firstLoad) return <LoadingState label={t.loading} />
  if ((parts.error && !partRows) || (report.error && !reportData)) {
    return <ErrorState message={parts.error ?? report.error ?? 'Could not load removed parts'} />
  }
  if (!partRows || !reportData || !machineRows) return null

  const roleEyebrow = user?.role === 'management' ? t.roleManagement : user?.role === 'admin' ? t.roleAdmin : t.roleSupervisor

  return (
    <Page>
      <PageHeader
        eyebrow={roleEyebrow}
        title={t.removedParts}
        subtitle="Where each part that came off a machine is now, and how it ended."
      />

      {reportData.pendingOlderThanDays > 0 && (
        <p className="mb-4 rounded-2xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm font-medium text-amber-900">
          {reportData.pendingOlderThanDays} pending more than {reportData.staleDays} days
        </p>
      )}

      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {reportData.byStatus.map((row) => (
          <KpiCard
            key={row.status}
            label={STATUS_LABEL[row.status]}
            value={row.count}
            tone={row.status === 'pending_decision' && row.count > 0 ? 'warn' : row.status === 'scrapped' ? 'bad' : 'neutral'}
          />
        ))}
      </div>

      <section className="mb-6">
        <h2 className="mb-2 text-xs font-bold tracking-wide text-stone-500 uppercase">Scrap and resale</h2>
        {reportData.months.length === 0 ? (
          <EmptyState title="No scrap or resale yet" />
        ) : (
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {reportData.months.map((month) => (
              <li key={month.month} className="rounded-2xl border border-line bg-white px-4 py-3 shadow-sm">
                <p className="text-sm font-semibold text-ink">{month.month}</p>
                <p className="mt-1 text-sm text-stone-600">
                  Scrap {month.scrapCount} · {scrapText(month.scrap)}
                </p>
                <p className="text-sm text-stone-600">
                  Resale {month.resaleCount} · {month.resaleCount ? inr(month.resaleAmount) : '—'}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mb-6">
        <h2 className="mb-2 text-xs font-bold tracking-wide text-stone-500 uppercase">Machines with most replacements</h2>
        {reportData.machines.length === 0 ? (
          <EmptyState title="No replacements yet" />
        ) : (
          <ul className="flex flex-col gap-2">
            {reportData.machines.map((row) => (
              <li key={row.machineId} className="flex items-center justify-between rounded-2xl border border-line bg-white px-4 py-3 shadow-sm">
                <Link to={`/machines/${row.machineId}`} className="font-semibold text-ink">
                  {row.machineName}
                </Link>
                <span className="text-sm tabular-nums text-stone-600">{row.replacements}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-xs font-bold tracking-wide text-stone-500 uppercase">Trail</h2>
        <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <select value={status} onChange={(e) => setStatus(e.target.value)} className={inputClass} aria-label="Status">
            <option value="">All statuses</option>
            {STATUS_ORDER.map((item) => (
              <option key={item} value={item}>
                {STATUS_LABEL[item]}
              </option>
            ))}
          </select>
          <select value={machineId} onChange={(e) => setMachineId(e.target.value)} className={inputClass} aria-label="Machine">
            <option value="">All machines</option>
            {machineRows.map((machine) => (
              <option key={machine.id} value={machine.id}>
                {machine.name}
              </option>
            ))}
          </select>
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={inputClass} aria-label="From" />
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={inputClass} aria-label="To" />
        </div>
        <div className="mb-4 flex flex-wrap items-center gap-4 text-sm">
          <label className="inline-flex min-h-11 items-center gap-2">
            <input type="checkbox" checked={pendingOnly} onChange={(e) => setPendingOnly(e.target.checked)} />
            Pending only
          </label>
          <label className="inline-flex min-h-11 items-center gap-2">
            <input type="checkbox" checked={staleOnly} onChange={(e) => setStaleOnly(e.target.checked)} />
            Pending longer than
            <input
              type="number"
              min={1}
              max={365}
              value={staleDays}
              onChange={(e) => setStaleDays(Math.max(1, Number(e.target.value) || 1))}
              className="w-16 rounded-xl border border-line px-2 py-1"
              aria-label="Days pending"
            />
            days
          </label>
        </div>
        {parts.error && <p className="mb-2 text-sm text-red-600">{parts.error}</p>}
        {partRows.length === 0 ? (
          <EmptyState title="No removed parts" body="They appear when someone logs a part replacement." />
        ) : (
          <ul className="flex flex-col gap-3">
            {partRows.map((part) => (
              <RemovedPartCard
                key={part.id}
                part={part}
                machines={machineRows}
                spares={stock.data ?? []}
                staleDays={staleDays}
                canUpdate={canUpdate}
                onChanged={() => {
                  void parts.refetch()
                  void report.refetch()
                }}
              />
            ))}
          </ul>
        )}
      </section>
    </Page>
  )
}

function RemovedPartCard({
  part,
  machines,
  spares,
  staleDays,
  canUpdate,
  onChanged,
}: {
  part: RemovedPart
  machines: Machine[]
  spares: SparePart[]
  staleDays: number
  canUpdate: boolean
  onChanged: () => void
}) {
  const [open, setOpen] = useState(false)
  const stale = isStalePending(part, staleDays)
  const machineName = part.machineName || machines.find((machine) => machine.id === part.machineId)?.name || 'Machine'
  return (
    <li className={`rounded-2xl border px-4 py-3 shadow-sm ${stale ? 'border-amber-400 bg-amber-50' : 'border-line bg-white'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-base font-semibold text-ink">{part.partName}</p>
          <p className="text-sm text-stone-600">
            <Link to={`/machines/${part.machineId}`} className="font-medium text-ink">
              {machineName}
            </Link>
            {' · '}
            {part.replacedAt}
            {part.removedByName ? ` · ${part.removedByName}` : ''}
          </p>
          <p className="mt-1 text-sm text-stone-700">
            {CONDITION_LABEL[part.condition]} · {STATUS_LABEL[part.status]}
            {part.location ? ` · ${part.location}` : ''}
            {part.quantity > 1 ? ` · ${part.quantity}` : ''}
          </p>
          <DispositionLine part={part} />
          {stale && <p className="mt-1 text-sm font-semibold text-amber-800">Pending {part.ageDays} days</p>}
        </div>
        {canUpdate && (
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="min-h-11 rounded-full border border-line px-3 text-sm font-semibold text-ink"
          >
            {open ? 'Close' : 'Update'}
          </button>
        )}
      </div>
      {part.events.length > 0 && (
        <ol className="mt-3 flex flex-col gap-2 border-t border-line/80 pt-3">
          {part.events.map((event) => (
            <li key={event.id} className="text-sm text-stone-600">
              <span className="font-medium text-ink">{formatWhen(event.at)}</span>
              {' · '}
              {event.actorName} · {STATUS_LABEL[event.status]}
              {eventDetail(event) ? ` · ${eventDetail(event)}` : ''}
              {event.photoUrl && (
                <span className="mt-1 block">
                  <ProofPhoto url={event.photoUrl} alt="" className="h-16 w-16 rounded-lg object-cover" zoomable />
                </span>
              )}
            </li>
          ))}
        </ol>
      )}
      {open && canUpdate && (
        <DispositionForm part={part} spares={spares} onSaved={() => { setOpen(false); onChanged() }} onCancel={() => setOpen(false)} />
      )}
    </li>
  )
}

function DispositionLine({ part }: { part: RemovedPart }) {
  if (part.status === 'sent_for_repair' || part.status === 'returned_to_vendor') {
    return (
      <p className="mt-1 text-sm text-stone-600">
        {part.vendor}
        {part.sentOn ? ` · ${part.sentOn}` : ''}
        {part.warrantyNote ? ` · ${part.warrantyNote}` : ''}
      </p>
    )
  }
  if (part.status === 'returned_to_stock' && part.refurbSpareName) {
    return (
      <p className="mt-1 text-sm text-stone-600">
        {part.creditedQty ?? part.quantity} back on {part.refurbSpareName}
      </p>
    )
  }
  if (part.status === 'scrapped') {
    return (
      <p className="mt-1 text-sm text-stone-600">
        {part.scrapOn} · {part.scrapQty} {part.scrapUnit} · {part.scrapBuyer}
      </p>
    )
  }
  if (part.status === 'sold') {
    return (
      <p className="mt-1 text-sm text-stone-600">
        {part.saleBuyer}
        {part.saleAmount != null ? ` · ${inr(part.saleAmount)}` : ''}
        {part.saleOn ? ` · ${part.saleOn}` : ''}
      </p>
    )
  }
  return null
}

function DispositionForm({
  part,
  spares,
  onSaved,
  onCancel,
}: {
  part: RemovedPart
  spares: SparePart[]
  onSaved: () => void
  onCancel: () => void
}) {
  const [status, setStatus] = useState<RemovedPartStatus>(part.status)
  const [location, setLocation] = useState(part.location ?? '')
  const [vendor, setVendor] = useState(part.vendor ?? '')
  const [sentOn, setSentOn] = useState(part.sentOn ?? '')
  const [sparePartId, setSparePartId] = useState(part.creditedSparePartId ?? '')
  const [quantity, setQuantity] = useState(String(part.creditedQty ?? part.quantity))
  const [stockQuery, setStockQuery] = useState('')
  const [scrapOn, setScrapOn] = useState(part.scrapOn ?? '')
  const [scrapQty, setScrapQty] = useState(part.scrapQty == null ? '' : String(part.scrapQty))
  const [scrapUnit, setScrapUnit] = useState(part.scrapUnit ?? 'kg')
  const [scrapBuyer, setScrapBuyer] = useState(part.scrapBuyer ?? '')
  const [saleBuyer, setSaleBuyer] = useState(part.saleBuyer ?? '')
  const [saleAmount, setSaleAmount] = useState(part.saleAmount == null ? '' : String(part.saleAmount))
  const [saleOn, setSaleOn] = useState(part.saleOn ?? '')
  const [warrantyNote, setWarrantyNote] = useState(part.warrantyNote ?? '')
  const [notes, setNotes] = useState('')
  const [photo, setPhoto] = useState<File | null>(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const matches = useMemo(() => {
    const query = stockQuery.trim().toLowerCase()
    if (!query) return []
    return spares
      .filter((spare) => `${spare.name} ${spare.itemGroup} ${spare.category}`.toLowerCase().includes(query))
      .slice(0, 8)
  }, [spares, stockQuery])
  const selected = spares.find((spare) => spare.id === sparePartId) ?? null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    let qty: number | undefined
    if (status === 'returned_to_stock') {
      const parsed = parseWholeQty(quantity)
      if (!sparePartId) {
        setError('Choose the refurbished spare')
        return
      }
      if (parsed == null || parsed < 1) {
        setError('Quantity returned must be a whole number of at least 1')
        return
      }
      qty = parsed
    }
    let weight: number | undefined
    if (status === 'scrapped') {
      const parsed = Number(scrapQty)
      if (!scrapOn || !scrapBuyer.trim() || !Number.isFinite(parsed) || parsed <= 0) {
        setError('Scrap date, weight or quantity, and buyer are required')
        return
      }
      weight = parsed
    }
    let amount: number | undefined
    if (status === 'sold') {
      const parsed = Number(saleAmount)
      if (!saleBuyer.trim() || !saleOn || !Number.isFinite(parsed) || parsed < 0) {
        setError('Buyer, amount, and date are required')
        return
      }
      amount = parsed
    }
    if ((status === 'sent_for_repair' || status === 'returned_to_vendor') && (!vendor.trim() || !sentOn)) {
      setError('Vendor and date are required')
      return
    }
    setSaving(true)
    try {
      const photoUrl = photo ? (await uploadPhoto(photo)).url : undefined
      await setRemovedPartDisposition(part.id, {
        status,
        location: location.trim() || undefined,
        vendor: vendor.trim() || undefined,
        sentOn: sentOn || undefined,
        sparePartId: status === 'returned_to_stock' ? sparePartId : undefined,
        quantity: qty,
        scrapOn: scrapOn || undefined,
        scrapQty: weight,
        scrapUnit: status === 'scrapped' ? scrapUnit : undefined,
        scrapBuyer: scrapBuyer.trim() || undefined,
        saleBuyer: saleBuyer.trim() || undefined,
        saleAmount: amount,
        saleOn: saleOn || undefined,
        warrantyNote: warrantyNote.trim() || undefined,
        notes: notes.trim() || undefined,
        photoUrl,
      })
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not update disposition')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mt-3 flex flex-col gap-3 border-t border-line/80 pt-3">
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-stone-700">Disposition</span>
        <select value={status} onChange={(e) => setStatus(e.target.value as RemovedPartStatus)} className={inputClass}>
          {STATUS_ORDER.map((item) => (
            <option key={item} value={item}>
              {STATUS_LABEL[item]}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-stone-700">Location</span>
        <input value={location} onChange={(e) => setLocation(e.target.value)} className={inputClass} />
      </label>
      {(status === 'sent_for_repair' || status === 'returned_to_vendor') && (
        <>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Vendor</span>
            <input required value={vendor} onChange={(e) => setVendor(e.target.value)} className={inputClass} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">{status === 'sent_for_repair' ? 'Sent on' : 'Returned on'}</span>
            <input required type="date" value={sentOn} onChange={(e) => setSentOn(e.target.value)} className={inputClass} />
          </label>
          {status === 'returned_to_vendor' && (
            <label className="flex flex-col gap-1 text-sm">
              <span className="font-medium text-stone-700">Warranty note</span>
              <input value={warrantyNote} onChange={(e) => setWarrantyNote(e.target.value)} className={inputClass} />
            </label>
          )}
        </>
      )}
      {status === 'returned_to_stock' && (
        <div className="flex flex-col gap-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Refurbished spare</span>
            <input
              value={stockQuery}
              onChange={(e) => setStockQuery(e.target.value)}
              placeholder="Search stock, e.g. Used Refurbish"
              className={inputClass}
            />
          </label>
          {matches.length > 0 && (
            <ul className="flex flex-col gap-1">
              {matches.map((spare) => (
                <li key={spare.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSparePartId(spare.id)
                      setStockQuery('')
                    }}
                    className="min-h-11 w-full rounded-xl border border-line px-3 text-left text-sm"
                  >
                    <span className="font-medium">{spare.name}</span>
                    <span className="text-stone-500">
                      {' '}
                      · {spare.category} · {formatQty(spare.qtyOnHand)}
                      {spare.unit ? ` ${spare.unit}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {selected && <p className="text-sm text-stone-700">Adding back to {selected.name}</p>}
          {!selected && part.refurbSpareName && sparePartId && (
            <p className="text-sm text-stone-700">Adding back to {part.refurbSpareName}</p>
          )}
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Quantity</span>
            <input
              type="number"
              inputMode="numeric"
              min={1}
              step={1}
              required
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              className={inputClass}
            />
          </label>
        </div>
      )}
      {status === 'scrapped' && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Scrap date</span>
            <input required type="date" value={scrapOn} onChange={(e) => setScrapOn(e.target.value)} className={inputClass} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Qty / weight</span>
            <input
              required
              type="number"
              min={0.001}
              step={0.001}
              value={scrapQty}
              onChange={(e) => setScrapQty(e.target.value)}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Unit</span>
            <select value={scrapUnit} onChange={(e) => setScrapUnit(e.target.value)} className={inputClass}>
              <option value="kg">kg</option>
              <option value="pcs">pcs</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Scrap buyer</span>
            <input required value={scrapBuyer} onChange={(e) => setScrapBuyer(e.target.value)} className={inputClass} />
          </label>
        </div>
      )}
      {status === 'sold' && (
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="flex flex-col gap-1 text-sm sm:col-span-2">
            <span className="font-medium text-stone-700">Buyer</span>
            <input required value={saleBuyer} onChange={(e) => setSaleBuyer(e.target.value)} className={inputClass} />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Amount (₹)</span>
            <input
              required
              type="number"
              min={0}
              step={0.01}
              value={saleAmount}
              onChange={(e) => setSaleAmount(e.target.value)}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            <span className="font-medium text-stone-700">Date</span>
            <input required type="date" value={saleOn} onChange={(e) => setSaleOn(e.target.value)} className={inputClass} />
          </label>
        </div>
      )}
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-stone-700">Notes</span>
        <textarea rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className={inputClass} />
      </label>
      <CameraCapture photo={photo} onPhotoChange={setPhoto} label="Photo (optional)" />
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex flex-col gap-2 sm:flex-row">
        <button
          type="submit"
          disabled={saving}
          className="min-h-11 rounded-full bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save disposition'}
        </button>
        <button type="button" onClick={onCancel} className="min-h-11 rounded-full border border-line px-4 text-sm font-semibold">
          Cancel
        </button>
      </div>
    </form>
  )
}
