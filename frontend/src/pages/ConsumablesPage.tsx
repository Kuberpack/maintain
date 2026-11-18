import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { createSlip, getConsumablePolicy, listConsumableItems, listSlips } from '../api/consumables'
import type { StoreSlip } from '../api/consumables'
import { listMachines } from '../api/machines'
import { listUsers } from '../api/users'
import { useAuth } from '../auth/useAuth'
import { Page, PageHeader } from '../components/ui'
import { useAsync } from '../lib/useAsync'
import { formatAmount, formatInr, formatSlipDate, localDateInput, parseQty } from '../lib/consumableFormat'
import { BalanceChip, ConsumableNav, buttonClass, fieldClass, quietButtonClass } from './consumableShared'

type Filter = 'all' | 'open' | 'leakage' | 'sign' | 'stale'

export function ConsumablesPage() {
  const { user } = useAuth()
  const canIssue = user?.role === 'supervisor' || user?.role === 'management' || user?.role === 'admin'
  const slips = useAsync(() => listSlips(), [])
  const [filter, setFilter] = useState<Filter>('all')
  const [showForm, setShowForm] = useState(false)

  const filtered = useMemo(() => {
    const rows = slips.data ?? []
    if (filter === 'open') return rows.filter((slip) => slip.status === 'open')
    if (filter === 'leakage') return rows.filter((slip) => slip.hasLeakage)
    if (filter === 'sign') return rows.filter((slip) => slip.needsSign)
    if (filter === 'stale') return rows.filter((slip) => slip.stale)
    return rows
  }, [slips.data, filter])

  return (
    <Page>
      <PageHeader
        eyebrow="Kuber Paper and Pack"
        title="Store issue"
        subtitle="Who took material, what was used, what came back, and what is missing."
        actions={
          canIssue ? (
            <button type="button" className={buttonClass} onClick={() => setShowForm((open) => !open)}>
              {showForm ? 'Close form' : 'New slip'}
            </button>
          ) : null
        }
      />
      <ConsumableNav />
      {showForm && canIssue ? (
        <IssueForm
          onCreated={() => {
            setShowForm(false)
            slips.refetch()
          }}
        />
      ) : null}
      {slips.loading ? <p className="text-stone-500">Loading slips…</p> : null}
      {slips.error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-red-700">{slips.error}</p> : null}
      <div className="mb-4 flex gap-2 overflow-x-auto">
        {(
          [
            ['all', 'All'],
            ['open', 'Open'],
            ['leakage', 'Leakage'],
            ['sign', 'Needs sign'],
            ['stale', 'Older than 1 shift'],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`min-h-10 shrink-0 rounded-full px-3 text-sm font-semibold ${
              filter === key ? 'bg-ink text-white' : 'bg-white text-stone-700 border border-line'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {slips.data && filtered.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white px-4 py-8 text-center text-stone-600">
          {user?.role === 'operator' ? 'No store slips in your name.' : 'No slips in this view.'}
        </p>
      ) : null}
      <ul className="flex flex-col gap-3">
        {filtered.map((slip) => (
          <li key={slip.id}>
            <SlipCard slip={slip} />
          </li>
        ))}
      </ul>
    </Page>
  )
}

function SlipCard({ slip }: { slip: StoreSlip }) {
  return (
    <Link
      to={`/consumables/slips/${slip.id}`}
      className="block rounded-2xl border border-line bg-white p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-bold tracking-[0.14em] text-brand uppercase">
            {slip.financialYear} · Slip {slip.slipNoLabel}
          </p>
          <h2 className="text-lg font-bold text-ink">
            {formatSlipDate(slip.slipDate)} · Shift {slip.shift}
          </h2>
          <p className="text-sm text-stone-600">
            {slip.department} · {slip.machineName}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {slip.lines.map((line) => (
            <BalanceChip key={line.id} status={line.balanceStatus} />
          ))}
          {slip.stale ? <span className="rounded-full bg-red-600 px-2.5 py-1 text-xs font-bold text-white">Older than 1 shift</span> : null}
          {slip.needsSign ? <span className="rounded-full bg-amber-200 px-2.5 py-1 text-xs font-bold text-amber-950">Sign blank</span> : null}
          {slip.supervisorConfirmedAt ? (
            <span className="rounded-full bg-green-100 px-2.5 py-1 text-xs font-bold text-green-800">Signed</span>
          ) : null}
        </div>
      </div>
      <p className="mt-3 text-sm text-stone-700">
        Issued by {slip.issuedByName} · Received by {slip.receivedByName}
      </p>
      <ul className="mt-2 text-sm text-stone-800">
        {slip.lines.map((line) => (
          <li key={line.id}>
            {line.itemName}: {formatAmount(line.qtyIssued)} {line.unit}
            {line.leakageQty != null && line.leakageQty > 0 ? (
              <span className="font-semibold text-red-700"> · leakage {formatAmount(line.leakageQty)} ({formatInr(line.leakageValue)})</span>
            ) : null}
          </li>
        ))}
      </ul>
    </Link>
  )
}

function IssueForm({ onCreated }: { onCreated: (id: string) => void }) {
  const navigate = useNavigate()
  const { user } = useAuth()
  const policy = useAsync(() => getConsumablePolicy(), [])
  const items = useAsync(() => listConsumableItems(), [])
  const machines = useAsync(() => listMachines(), [])
  const users = useAsync(() => listUsers(), [])
  const [slipDate, setSlipDate] = useState(localDateInput())
  const [shift, setShift] = useState(() => {
    const hour = new Date().getHours()
    if (hour >= 6 && hour < 14) return 'A'
    if (hour >= 14 && hour < 22) return 'B'
    return 'C'
  })
  const [department, setDepartment] = useState('')
  const [machineId, setMachineId] = useState('')
  const [receivedById, setReceivedById] = useState('')
  const [hodName, setHodName] = useState('')
  const [lines, setLines] = useState<{ itemId: string; qty: string }[]>([{ itemId: '', qty: '' }])
  const [override, setOverride] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const operators = (users.data ?? []).filter((person) => person.role === 'operator')
  const catalog = items.data ?? []
  const corePolicy = policy.data?.corePolicy ?? 'warn'
  const canOverride = user?.role === 'management' || user?.role === 'admin'
  const blockedCores = lines.some((line) => {
    const item = catalog.find((row) => row.id === line.itemId)
    return Boolean(item?.tracksEmptyCore && item.coresOutstanding > 0)
  })

  function chooseMachine(id: string) {
    setMachineId(id)
    const machine = (machines.data ?? []).find((row) => row.id === id)
    if (!machine) return
    if (!department.trim()) {
      setDepartment(machine.name.toLowerCase().includes('stitch') ? 'Auto Semi' : machine.groupName || machine.name)
    }
    if (machine.operatorId) setReceivedById(machine.operatorId)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const payloadLines = lines.map((line) => ({ itemId: line.itemId, qty: parseQty(line.qty) }))
    if (!machineId || !receivedById || !department.trim()) {
      setError('Department, machine, and the operator who received the material are required')
      return
    }
    if (payloadLines.some((line) => !line.itemId || line.qty == null || line.qty <= 0)) {
      setError('Each line needs an item and a quantity above zero')
      return
    }
    if (corePolicy === 'block' && blockedCores && !(canOverride && override)) {
      setError('An empty core from the previous issue has not come back. This issue is blocked.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const created = await createSlip({
        slipDate,
        shift,
        department: department.trim(),
        machineId,
        receivedById,
        hodName: hodName.trim() || null,
        lines: payloadLines.map((line) => ({ itemId: line.itemId, qty: line.qty as number })),
        overrideMissingCores: override,
      })
      if (created.coreWarnings.length > 0) {
        window.alert(created.coreWarnings.join('\n'))
      }
      onCreated(created.slip.id)
      navigate(`/consumables/slips/${created.slip.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not issue this slip')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mb-5 rounded-2xl border border-line bg-white p-4 shadow-sm">
      <p className="text-xs font-bold tracking-[0.14em] text-brand uppercase">Store issue slip</p>
      <h2 className="mb-3 text-xl font-bold">New issue</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Date
          <input type="date" required value={slipDate} onChange={(event) => setSlipDate(event.target.value)} className={fieldClass} />
        </label>
        <fieldset>
          <legend className="mb-1 text-sm font-semibold">Shift</legend>
          <div className="grid grid-cols-3 gap-2">
            {(policy.data?.shifts ?? [
              { id: 'A', label: 'Shift A', starts: '06:00', ends: '14:00' },
              { id: 'B', label: 'Shift B', starts: '14:00', ends: '22:00' },
              { id: 'C', label: 'Shift C', starts: '22:00', ends: '06:00' },
            ]).map((row) => (
              <button
                key={row.id}
                type="button"
                onClick={() => setShift(row.id)}
                className={`min-h-14 rounded-xl border px-2 text-sm font-semibold ${
                  shift === row.id ? 'border-brand bg-brand text-white' : 'border-line bg-paper text-ink'
                }`}
              >
                {row.id}
                <span className="block text-[11px] font-medium opacity-80">
                  {row.starts}–{row.ends}
                </span>
              </button>
            ))}
          </div>
          <p className="mt-1 text-xs text-stone-500">Shift times are provisional.</p>
        </fieldset>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Department
          <input value={department} onChange={(event) => setDepartment(event.target.value)} className={fieldClass} placeholder="Auto Semi" />
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Machine
          <select required value={machineId} onChange={(event) => chooseMachine(event.target.value)} className={fieldClass}>
            <option value="">Select machine</option>
            {(machines.data ?? []).map((machine) => (
              <option key={machine.id} value={machine.id}>
                {machine.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold sm:col-span-2">
          Operator received by
          <select required value={receivedById} onChange={(event) => setReceivedById(event.target.value)} className={fieldClass}>
            <option value="">Select operator</option>
            {operators.map((person) => (
              <option key={person.id} value={person.id}>
                {person.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm font-semibold sm:col-span-2">
          HOD name (optional)
          <input value={hodName} onChange={(event) => setHodName(event.target.value)} className={fieldClass} />
        </label>
      </div>
      <div className="mt-4 flex flex-col gap-3">
        {lines.map((line, index) => {
          const item = catalog.find((row) => row.id === line.itemId)
          return (
            <div key={index} className="rounded-2xl bg-paper p-3">
              <div className="grid gap-2 sm:grid-cols-[1fr_8rem]">
                <label className="flex flex-col gap-1 text-sm font-semibold">
                  Item
                  <select
                    required
                    value={line.itemId}
                    onChange={(event) =>
                      setLines((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, itemId: event.target.value } : row)))
                    }
                    className={fieldClass}
                  >
                    <option value="">Select item</option>
                    {catalog.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.name} · {formatAmount(row.qtyOnHand)} {row.unit}
                        {row.lowStock ? ' · low' : ''}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex flex-col gap-1 text-sm font-semibold">
                  Qty {item ? `(${item.unit})` : ''}
                  <input
                    inputMode="decimal"
                    value={line.qty}
                    onChange={(event) =>
                      setLines((current) => current.map((row, rowIndex) => (rowIndex === index ? { ...row, qty: event.target.value } : row)))
                    }
                    className={fieldClass}
                  />
                </label>
              </div>
              {item?.tracksEmptyCore && item.coresOutstanding > 0 ? (
                <p className="mt-2 text-sm font-semibold text-amber-800">
                  Previous empty core not returned ({item.coresOutstanding} open).
                  {corePolicy === 'block' ? ' A new issue is blocked until it comes back.' : ' You can still issue, but it will be flagged.'}
                </p>
              ) : null}
            </div>
          )
        })}
        <button
          type="button"
          className={quietButtonClass}
          onClick={() => setLines((current) => [...current, { itemId: '', qty: '' }])}
        >
          Add line
        </button>
      </div>
      {corePolicy === 'block' && blockedCores && canOverride ? (
        <label className="mt-3 flex min-h-12 items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={override} onChange={(event) => setOverride(event.target.checked)} />
          Management override: issue even though a core is missing
        </label>
      ) : null}
      {error ? <p className="mt-3 text-sm text-red-700">{error}</p> : null}
      <button type="submit" disabled={saving || items.loading} className={`${buttonClass} mt-4 w-full sm:w-auto`}>
        {saving ? 'Issuing…' : 'Issue and reduce stock'}
      </button>
    </form>
  )
}
