import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError } from '../api/client'
import { createConsumableItem, listConsumableItems, receiveInward, recordStockCount, updateConsumableItem } from '../api/consumables'
import type { ConsumableItem } from '../api/consumables'
import { Page, PageHeader } from '../components/ui'
import { useAsync } from '../lib/useAsync'
import { formatAmount, formatInr, parseQty } from '../lib/consumableFormat'
import { ConsumableNav, buttonClass, fieldClass, quietButtonClass } from './consumableShared'

export function ConsumableItemsPage() {
  const [search, setSearch] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [reload, setReload] = useState(0)
  const items = useAsync(() => listConsumableItems({ search: search.trim() || undefined, lowStock: lowOnly }), [search, lowOnly, reload])
  const [editing, setEditing] = useState<ConsumableItem | null | undefined>(undefined)
  const lowCount = useMemo(() => (items.data ?? []).filter((item) => item.lowStock).length, [items.data])

  return (
    <Page>
      <PageHeader
        eyebrow="Item master"
        title="Consumables"
        subtitle="Group, supplier, rate, min and max, and what is on the shelf. Low stock is flagged."
        actions={
          <button type="button" className={buttonClass} onClick={() => setEditing(null)}>
            Add item
          </button>
        }
      />
      <ConsumableNav />
      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Search name, group, supplier"
          className={fieldClass}
        />
        <button type="button" className={lowOnly ? buttonClass : quietButtonClass} onClick={() => setLowOnly((value) => !value)}>
          Low stock{items.data ? ` (${lowOnly ? items.data.length : lowCount})` : ''}
        </button>
      </div>
      {editing !== undefined ? (
        <ItemEditor
          item={editing}
          onClose={() => setEditing(undefined)}
          onSaved={() => {
            setEditing(undefined)
            setReload((value) => value + 1)
          }}
        />
      ) : null}
      {items.loading ? <p className="text-stone-500">Loading items…</p> : null}
      {items.error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-red-700">{items.error}</p> : null}
      <div className="table-wrap">
        <table className="data-table w-full text-sm">
          <thead>
            <tr className="text-left text-xs tracking-wide text-stone-500 uppercase">
              <th className="px-3 py-2">Item</th>
              <th className="px-3 py-2">Group</th>
              <th className="px-3 py-2">Supplier</th>
              <th className="px-3 py-2">Stock</th>
              <th className="px-3 py-2">Min / max</th>
              <th className="px-3 py-2">Rate</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {(items.data ?? []).map((item) => (
              <tr key={item.id} className="border-t border-line bg-white">
                <td className="px-3 py-3 font-semibold" data-label="Item">
                  {item.name}
                  {item.tracksEmptyCore ? <span className="mt-1 block text-xs font-medium text-stone-500">Empty core tracked · {item.coresOutstanding} out</span> : null}
                </td>
                <td className="px-3 py-3" data-label="Group">{item.itemGroup || '—'}</td>
                <td className="px-3 py-3" data-label="Supplier">
                  {item.partyName || '—'}
                  {item.partyAddress ? <span className="block text-xs text-stone-500">{item.partyAddress}</span> : null}
                </td>
                <td className="px-3 py-3" data-label="Stock">
                  <span className={item.lowStock ? 'font-bold text-red-700' : 'font-semibold'}>
                    {formatAmount(item.qtyOnHand)} {item.unit}
                  </span>
                  {item.lowStock ? <span className="mt-1 block text-xs font-bold text-red-700">Low stock</span> : null}
                </td>
                <td className="px-3 py-3" data-label="Min / max">
                  {formatAmount(item.minStock)} / {item.maxStock == null ? '—' : formatAmount(item.maxStock)}
                </td>
                <td className="px-3 py-3" data-label="Rate">{formatInr(item.rate)}</td>
                <td className="px-3 py-3" data-label="">
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" className={quietButtonClass} onClick={() => setEditing(item)}>
                      Edit
                    </button>
                    <StockActions item={item} onSaved={() => setReload((value) => value + 1)} />
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  )
}

function StockActions({ item, onSaved }: { item: ConsumableItem; onSaved: () => void }) {
  const [counted, setCounted] = useState('')
  const [inward, setInward] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function count(event: FormEvent) {
    event.preventDefault()
    const qty = parseQty(counted)
    if (qty == null) {
      setError('Counted quantity must be zero or more')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await recordStockCount(item.id, qty)
      setCounted('')
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the count')
    } finally {
      setSaving(false)
    }
  }

  async function receive(event: FormEvent) {
    event.preventDefault()
    const qty = parseQty(inward)
    if (qty == null || qty <= 0) {
      setError('Inward quantity must be above zero')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await receiveInward(item.id, qty)
      setInward('')
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not record the receipt')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <form onSubmit={(event) => void count(event)} className="flex gap-2">
        <input inputMode="decimal" value={counted} onChange={(event) => setCounted(event.target.value)} placeholder="Counted qty" className={`${fieldClass} min-w-0`} aria-label={`Counted quantity for ${item.name}`} />
        <button type="submit" disabled={saving} className={quietButtonClass}>
          Count
        </button>
      </form>
      <form onSubmit={(event) => void receive(event)} className="flex gap-2">
        <input inputMode="decimal" value={inward} onChange={(event) => setInward(event.target.value)} placeholder="Inward qty" className={`${fieldClass} min-w-0`} aria-label={`Inward quantity for ${item.name}`} />
        <button type="submit" disabled={saving} className={quietButtonClass}>
          In
        </button>
      </form>
      {error ? <p className="text-xs text-red-700">{error}</p> : null}
    </div>
  )
}

function ItemEditor({ item, onClose, onSaved }: { item: ConsumableItem | null; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(item?.name ?? '')
  const [itemGroup, setItemGroup] = useState(item?.itemGroup ?? '')
  const [partyName, setPartyName] = useState(item?.partyName ?? '')
  const [partyAddress, setPartyAddress] = useState(item?.partyAddress ?? '')
  const [contactNo, setContactNo] = useState(item?.contactNo ?? '')
  const [lead, setLead] = useState(item?.leadTimeDays == null ? '' : String(item.leadTimeDays))
  const [minStock, setMinStock] = useState(item ? String(item.minStock) : '')
  const [maxStock, setMaxStock] = useState(item?.maxStock == null ? '' : String(item.maxStock))
  const [rate, setRate] = useState(item ? String(item.rate) : '')
  const [unit, setUnit] = useState(item?.unit ?? '')
  const [opening, setOpening] = useState(item ? '' : '')
  const [core, setCore] = useState(item?.tracksEmptyCore ?? false)
  const [standardQty, setStandardQty] = useState(item?.standardQty == null ? '' : String(item.standardQty))
  const [standardPer, setStandardPer] = useState(item?.standardPer == null ? '' : String(item.standardPer))
  const [standardBasis, setStandardBasis] = useState(item?.standardBasis ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const min = parseQty(minStock)
    const max = maxStock.trim() === '' ? null : parseQty(maxStock)
    const price = parseQty(rate)
    const openingQty = parseQty(opening)
    if (!name.trim() || !unit.trim() || min == null || price == null) {
      setError('Name, unit, minimum, and rate are required')
      return
    }
    if (maxStock.trim() !== '' && max == null) {
      setError('Max stock must be a number')
      return
    }
    setSaving(true)
    setError(null)
    const standardPayload = {
      standardQty: standardQty.trim() === '' ? null : parseQty(standardQty),
      standardPer: standardPer.trim() === '' ? null : parseQty(standardPer),
      standardBasis: standardBasis.trim() || null,
    }
    try {
      if (item) {
        await updateConsumableItem(item.id, {
          name: name.trim(),
          itemGroup,
          partyName,
          partyAddress,
          contactNo,
          leadTimeDays: lead.trim() === '' ? null : Number(lead),
          minStock: min,
          maxStock: max,
          clearMaxStock: max == null,
          rate: price,
          unit: unit.trim(),
          tracksEmptyCore: core,
          ...standardPayload,
          clearStandard: !standardPayload.standardQty && !standardPayload.standardPer && !standardPayload.standardBasis,
        })
      } else {
        if (openingQty == null) {
          setError('Opening stock is required for a new item')
          setSaving(false)
          return
        }
        await createConsumableItem({
          name: name.trim(),
          itemGroup,
          partyName,
          partyAddress,
          contactNo,
          leadTimeDays: lead.trim() === '' ? null : Number(lead),
          minStock: min,
          maxStock: max,
          rate: price,
          unit: unit.trim(),
          qtyOnHand: openingQty,
          tracksEmptyCore: core,
          standardQty: standardPayload.standardQty,
          standardPer: standardPayload.standardPer,
          standardBasis: standardPayload.standardBasis,
        })
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the item')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mb-4 rounded-2xl border border-line bg-white p-4">
      <h2 className="mb-3 text-lg font-bold">{item ? 'Edit item' : 'New item'}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Name" value={name} onChange={setName} />
        <Field label="Group" value={itemGroup} onChange={setItemGroup} />
        <Field label="Supplier" value={partyName} onChange={setPartyName} />
        <Field label="Address" value={partyAddress} onChange={setPartyAddress} />
        <Field label="Contact" value={contactNo} onChange={setContactNo} />
        <Field label="Lead time days" value={lead} onChange={setLead} />
        <Field label="Unit" value={unit} onChange={setUnit} />
        <Field label="Rate ₹" value={rate} onChange={setRate} />
        <Field label="Min stock" value={minStock} onChange={setMinStock} />
        <Field label="Max stock" value={maxStock} onChange={setMaxStock} />
        {item ? null : <Field label="Opening stock" value={opening} onChange={setOpening} />}
        <Field label="Standard qty" value={standardQty} onChange={setStandardQty} />
        <Field label="Per quantity" value={standardPer} onChange={setStandardPer} />
        <Field label="Basis (boxes, ton of board)" value={standardBasis} onChange={setStandardBasis} />
      </div>
      <label className="mt-3 flex min-h-12 items-center gap-2 text-sm font-semibold">
        <input type="checkbox" checked={core} onChange={(event) => setCore(event.target.checked)} />
        Empty core must come back (rolls, tapes, coils)
      </label>
      {error ? <p className="mt-2 text-sm text-red-700">{error}</p> : null}
      <div className="mt-3 flex gap-2">
        <button type="submit" disabled={saving} className={buttonClass}>
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button type="button" onClick={onClose} className={quietButtonClass}>
          Cancel
        </button>
      </div>
    </form>
  )
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-semibold">
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} className={fieldClass} />
    </label>
  )
}
