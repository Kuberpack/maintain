import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useAsync } from '../lib/useAsync'
import { formatQty, parseWholeQty } from '../lib/qty'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { listMachines } from '../api/machines'
import { createSparePart, deleteSparePart, listSpareParts, updateSparePart } from '../api/spareParts'
import type { Machine, SparePart } from '../api/types'

function qtyLabel(part: Pick<SparePart, 'qtyOnHand' | 'unit'>): string {
  const text = formatQty(part.qtyOnHand)
  return part.unit ? `${text} ${part.unit}` : text
}

interface Draft {
  name: string
  itemGroup: string
  category: string
  qtyOnHand: string
  unit: string
  minQty: string
  machineId: string
}

function emptyDraft(category: string): Draft {
  return {
    name: '',
    itemGroup: '',
    category,
    qtyOnHand: '',
    unit: '',
    minQty: '',
    machineId: '',
  }
}

function draftFromPart(part: SparePart): Draft {
  return {
    name: part.name,
    itemGroup: part.itemGroup,
    category: part.category,
    qtyOnHand: formatQty(part.qtyOnHand),
    unit: part.unit ?? '',
    minQty: part.minQty == null ? '' : formatQty(part.minQty),
    machineId: part.machineId ?? '',
  }
}

function SpareEditor({
  part,
  machines,
  categories,
  onSaved,
  onCancel,
}: {
  part: SparePart | null
  machines: Machine[]
  categories: string[]
  onSaved: () => void
  onCancel: () => void
}) {
  const [draft, setDraft] = useState<Draft>(() => (part ? draftFromPart(part) : emptyDraft(categories[0] ?? '')))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const machineChoices = useMemo(() => {
    const options = machines.map((machine) => ({ id: machine.id, name: machine.name }))
    if (part?.machineId && !options.some((machine) => machine.id === part.machineId)) {
      options.push({ id: part.machineId, name: part.machineName ?? 'Linked machine' })
    }
    options.sort((a, b) => a.name.localeCompare(b.name))
    return options
  }, [machines, part])

  function setField(field: keyof Draft, value: string) {
    setDraft((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const qty = parseWholeQty(draft.qtyOnHand)
    const minText = draft.minQty.trim()
    const min = minText === '' ? null : parseWholeQty(minText)
    if (!draft.name.trim() || !draft.category.trim()) {
      setError('Name and area are required')
      return
    }
    if (qty == null) {
      setError('On-hand quantity must be a whole number, zero or more')
      return
    }
    if (minText !== '' && min == null) {
      setError('Minimum quantity must be a whole number, zero or more')
      return
    }
    setSaving(true)
    setError(null)
    const payload = {
      name: draft.name.trim(),
      itemGroup: draft.itemGroup.trim(),
      category: draft.category.trim(),
      qtyOnHand: qty,
      unit: draft.unit.trim() || null,
      minQty: min,
      machineId: draft.machineId || null,
    }
    try {
      if (part) {
        await updateSparePart(part.id, payload)
      } else {
        await createSparePart(payload)
      }
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save spare')
    } finally {
      setSaving(false)
    }
  }

  const inputClass = 'rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none'

  return (
    <form onSubmit={(event) => void handleSubmit(event)} className="mb-4 rounded-xl border border-slate-200 bg-white p-4">
      <p className="mb-3 text-sm font-semibold text-slate-900">{part ? 'Edit spare' : 'Add spare'}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Name</span>
          <input required value={draft.name} onChange={(event) => setField('name', event.target.value)} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Area</span>
          <input
            required
            list="spare-areas"
            value={draft.category}
            onChange={(event) => setField('category', event.target.value)}
            className={inputClass}
          />
          <datalist id="spare-areas">
            {categories.map((category) => (
              <option key={category} value={category} />
            ))}
          </datalist>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Item group</span>
          <input value={draft.itemGroup} onChange={(event) => setField('itemGroup', event.target.value)} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Machine</span>
          <select value={draft.machineId} onChange={(event) => setField('machineId', event.target.value)} className={inputClass}>
            <option value="">Not linked</option>
            {machineChoices.map((machine) => (
              <option key={machine.id} value={machine.id}>
                {machine.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">On hand</span>
          <input
            required
            type="number"
            inputMode="numeric"
            min={0}
            step={1}
            value={draft.qtyOnHand}
            onChange={(event) => setField('qtyOnHand', event.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Unit</span>
          <input value={draft.unit} onChange={(event) => setField('unit', event.target.value)} className={inputClass} placeholder="pcs, Mtr, pkt" />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Minimum (optional)</span>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            step={1}
            value={draft.minQty}
            onChange={(event) => setField('minQty', event.target.value)}
            className={inputClass}
          />
        </label>
      </div>
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <div className="mt-3 flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save'}
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

export function SparesPage() {
  const { user } = useAuth()
  const canEdit = user?.role === 'supervisor' || user?.role === 'admin'
  const parts = useAsync(() => listSpareParts(), [])
  const machines = useAsync(() => listMachines().catch(() => [] as Machine[]), [])

  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [group, setGroup] = useState('')
  const [lowOnly, setLowOnly] = useState(false)
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const partList = useMemo(() => parts.data ?? [], [parts.data])
  const categories = useMemo(() => [...new Set(partList.map((part) => part.category))].sort(), [partList])
  const groups = useMemo(() => {
    const inArea = partList.filter((part) => !category || part.category === category)
    return [...new Set(inArea.map((part) => part.itemGroup))].sort()
  }, [partList, category])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return partList.filter((part) => {
      if (category && part.category !== category) return false
      if (group === '__blank__' && part.itemGroup !== '') return false
      if (group && group !== '__blank__' && part.itemGroup !== group) return false
      if (lowOnly && !part.lowStock) return false
      if (!query) return true
      return `${part.name} ${part.itemGroup} ${part.category}`.toLowerCase().includes(query)
    })
  }, [partList, search, category, group, lowOnly])

  const lowCount = partList.filter((part) => part.lowStock).length
  const editing = partList.find((part) => part.id === editingId) ?? null

  async function handleDelete(part: SparePart) {
    const confirmed = window.confirm(`Remove ${part.name} from stock?`)
    if (!confirmed) return
    setError(null)
    setDeletingId(part.id)
    try {
      await deleteSparePart(part.id)
      if (editingId === part.id) setEditingId(null)
      parts.refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not delete spare')
    } finally {
      setDeletingId(null)
    }
  }

  if (parts.loading) return <p className="p-6 text-slate-500">Loading…</p>
  if (parts.error) return <p className="p-6 text-red-600">{parts.error}</p>

  return (
    <div className="mx-auto max-w-5xl p-4 pb-16">
      <h1 className="mb-1 text-2xl font-bold text-slate-900">Spares</h1>
      <p className="mb-4 text-sm text-slate-600">
        {partList.length} items · {lowCount} low. A row is highlighted when on-hand is zero or at the minimum.
      </p>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end">
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Search</span>
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Name, group, or area"
            className="rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Area</span>
          <select
            value={category}
            onChange={(event) => {
              setCategory(event.target.value)
              setGroup('')
            }}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All areas</option>
            {categories.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Group</span>
          <select
            value={group}
            onChange={(event) => setGroup(event.target.value)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">All groups</option>
            {groups.includes('') && <option value="__blank__">(No group)</option>}
            {groups
              .filter((name) => name !== '')
              .map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
          </select>
        </label>
        <label className="flex items-center gap-2 pb-2 text-sm text-slate-700">
          <input type="checkbox" checked={lowOnly} onChange={(event) => setLowOnly(event.target.checked)} />
          Low stock only
        </label>
        {canEdit && !creating && !editing && (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            + Add spare
          </button>
        )}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {creating && (
        <SpareEditor
          part={null}
          machines={machines.data ?? []}
          categories={categories}
          onSaved={() => {
            setCreating(false)
            parts.refetch()
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {editing && (
        <SpareEditor
          part={editing}
          machines={machines.data ?? []}
          categories={categories}
          onSaved={() => {
            setEditingId(null)
            parts.refetch()
          }}
          onCancel={() => setEditingId(null)}
        />
      )}

      <p className="mb-2 text-sm text-slate-500">Showing {filtered.length}</p>

      {filtered.length === 0 ? (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-slate-600">No spares match.</p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-3 py-2 font-semibold">Item</th>
                <th className="px-3 py-2 font-semibold">Group</th>
                <th className="px-3 py-2 font-semibold">Area</th>
                <th className="px-3 py-2 font-semibold">On hand</th>
                <th className="px-3 py-2 font-semibold">Min</th>
                <th className="px-3 py-2 font-semibold">Machine</th>
                {canEdit && <th className="px-3 py-2 font-semibold"> </th>}
              </tr>
            </thead>
            <tbody>
              {filtered.map((part) => (
                <tr key={part.id} className={part.lowStock ? 'bg-amber-50' : 'odd:bg-white even:bg-slate-50'}>
                  <td className="px-3 py-2 font-medium text-slate-900">
                    {part.name}
                    {part.lowStock && (
                      <span className="ml-2 rounded-full bg-amber-200 px-2 py-0.5 text-xs font-semibold text-amber-900">
                        Low
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-slate-600">{part.itemGroup || '—'}</td>
                  <td className="px-3 py-2 text-slate-600">{part.category}</td>
                  <td className="px-3 py-2 text-slate-900">{qtyLabel(part)}</td>
                  <td className="px-3 py-2 text-slate-600">{part.minQty == null ? '—' : formatQty(part.minQty)}</td>
                  <td className="px-3 py-2 text-slate-600">{part.machineName ?? '—'}</td>
                  {canEdit && (
                    <td className="px-3 py-2 text-right whitespace-nowrap">
                      <button
                        type="button"
                        onClick={() => {
                          setCreating(false)
                          setEditingId(part.id)
                        }}
                        className="mr-2 text-sm font-medium text-slate-700 hover:underline"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        disabled={deletingId === part.id}
                        onClick={() => void handleDelete(part)}
                        className="text-sm font-medium text-red-700 hover:underline disabled:opacity-50"
                      >
                        {deletingId === part.id ? 'Removing…' : 'Remove'}
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
