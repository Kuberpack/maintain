import { useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadConsumableExport, getDailySheet, getLeakageReport } from '../api/consumables'
import type { DailySheet, LeakageBucket, LeakageReport } from '../api/consumables'
import { KpiCard, Page, PageHeader } from '../components/ui'
import { useAsync } from '../lib/useAsync'
import { currentMonthInput, formatAmount, formatInr, formatSlipDate } from '../lib/consumableFormat'
import { ConsumableNav, buttonClass, fieldClass, quietButtonClass } from './consumableShared'

export function ConsumableReportsPage() {
  const [month, setMonth] = useState(currentMonthInput())
  const [applied, setApplied] = useState(month)
  const report = useAsync(() => getLeakageReport(applied), [applied])
  const sheet = useAsync(() => getDailySheet(applied), [applied])
  const [exportError, setExportError] = useState<string | null>(null)

  async function download(kind: 'daily' | 'leakage', format: 'csv' | 'xlsx') {
    setExportError(null)
    try {
      await downloadConsumableExport(applied, kind, format)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'Export failed')
    }
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Management"
        title="Consumable reports"
        subtitle="Leakage and usage variance in quantity and rupees, open slips older than one shift, and the daily sheet that replaces the Google Sheet."
      />
      <ConsumableNav />
      <form
        className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end"
        onSubmit={(event) => {
          event.preventDefault()
          setApplied(month)
        }}
      >
        <label className="flex flex-col gap-1 text-sm font-semibold">
          Month
          <input type="month" value={month} onChange={(event) => setMonth(event.target.value)} className={fieldClass} />
        </label>
        <button type="submit" className={buttonClass}>
          Show
        </button>
      </form>
      <div className="mb-4 flex flex-wrap gap-2">
        <button type="button" className={quietButtonClass} onClick={() => void download('leakage', 'xlsx')}>
          Leakage Excel
        </button>
        <button type="button" className={quietButtonClass} onClick={() => void download('leakage', 'csv')}>
          Leakage CSV
        </button>
        <button type="button" className={quietButtonClass} onClick={() => void download('daily', 'xlsx')}>
          Daily sheet Excel
        </button>
        <button type="button" className={quietButtonClass} onClick={() => void download('daily', 'csv')}>
          Daily sheet CSV
        </button>
      </div>
      {exportError ? <p className="mb-3 text-sm text-red-700">{exportError}</p> : null}
      {report.loading ? <p className="text-stone-500">Loading report…</p> : null}
      {report.error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-red-700">{report.error}</p> : null}
      {report.data ? <ReportBody report={report.data} /> : null}
      <h2 className="mt-8 mb-2 text-xl font-bold">Daily consumption</h2>
      <p className="mb-3 text-sm text-stone-600">
        Same columns as the consumable sheet: opening stock, then inward and consumption by day. A return shows as negative consumption so the month still ties to book stock.
      </p>
      {sheet.loading ? <p className="text-stone-500">Loading sheet…</p> : null}
      {sheet.error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-red-700">{sheet.error}</p> : null}
      {sheet.data ? <DailyBody key={sheet.data.month} sheet={sheet.data} /> : null}
    </Page>
  )
}

function ReportBody({ report }: { report: LeakageReport }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <KpiCard label="Leakage qty" value={formatAmount(report.totalQty)} tone={report.totalQty > 0 ? 'bad' : 'good'} />
        <KpiCard label="Leakage ₹" value={formatInr(report.totalValueInr)} tone={report.totalValueInr > 0 ? 'bad' : 'good'} />
        <KpiCard label="Open > 1 shift" value={report.staleSlips.length} tone={report.staleSlips.length > 0 ? 'warn' : 'good'} />
      </div>
      <BucketTable title="Top leakage items" rows={report.topItems} />
      <BucketTable title="By item" rows={report.byItem} />
      <BucketTable title="By machine" rows={report.byMachine} />
      <BucketTable title="By operator" rows={report.byOperator} />
      <section className="rounded-2xl border border-line bg-white p-4">
        <h3 className="mb-2 font-bold">By month (this financial year)</h3>
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {report.byMonth.map((row) => (
            <li key={row.month} className={`rounded-xl px-3 py-2 text-sm ${row.month === report.month ? 'bg-brand text-white' : 'bg-paper'}`}>
              <p className="font-bold">{row.month}</p>
              <p>{formatAmount(row.qty)} · {formatInr(row.valueInr)}</p>
            </li>
          ))}
        </ul>
      </section>
      <section className="rounded-2xl border border-line bg-white p-4">
        <h3 className="mb-2 font-bold">Open slips older than one shift</h3>
        {report.staleSlips.length === 0 ? <p className="text-sm text-stone-500">None.</p> : null}
        <ul className="flex flex-col gap-2">
          {report.staleSlips.map((slip) => (
            <li key={slip.id}>
              <Link to={`/consumables/slips/${slip.id}`} className="block rounded-xl bg-red-50 px-3 py-3 text-sm">
                <span className="font-bold">
                  {slip.financialYear}/{slip.slipNoLabel}
                </span>{' '}
                {formatSlipDate(slip.slipDate)} shift {slip.shift} · {slip.machineName} · {slip.receivedByName}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

function BucketTable({ title, rows }: { title: string; rows: LeakageBucket[] }) {
  const visible = rows.filter((row) => row.qty > 0 || (row.variancePct != null && row.variancePct !== 0))
  return (
    <section>
      <h3 className="mb-2 font-bold">{title}</h3>
      {visible.length === 0 ? <p className="text-sm text-stone-500">Nothing in this month.</p> : null}
      <div className="table-wrap">
        <table className="data-table w-full text-sm">
          <thead>
            <tr className="text-left text-xs tracking-wide text-stone-500 uppercase">
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">Qty</th>
              <th className="px-3 py-2">₹</th>
              <th className="px-3 py-2">Variance</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr key={row.key} className="border-t border-line bg-white">
                <td className="px-3 py-2 font-semibold" data-label="Name">{row.label}</td>
                <td className="px-3 py-2" data-label="Qty">{formatAmount(row.qty)}</td>
                <td className="px-3 py-2" data-label="₹">{formatInr(row.valueInr)}</td>
                <td className="px-3 py-2" data-label="Variance">{row.variancePct == null ? '—' : `${row.variancePct}%`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function DailyBody({ sheet }: { sheet: DailySheet }) {
  const [itemId, setItemId] = useState(sheet.rows[0]?.itemId ?? '')
  const row = sheet.rows.find((item) => item.itemId === itemId) ?? sheet.rows[0]
  if (!row) return <p className="text-sm text-stone-500">No items.</p>
  return (
    <div>
      <label className="mb-3 flex flex-col gap-1 text-sm font-semibold lg:hidden">
        Item
        <select value={row.itemId} onChange={(event) => setItemId(event.target.value)} className={fieldClass}>
          {sheet.rows.map((item) => (
            <option key={item.itemId} value={item.itemId}>
              {item.itemName}
            </option>
          ))}
        </select>
      </label>
      <article className="mb-4 rounded-2xl border border-line bg-white p-4 lg:hidden">
        <h3 className="font-bold">{row.itemName}</h3>
        <p className="text-sm text-stone-600">
          {row.itemGroup} · {row.partyName ?? 'No supplier'} · {formatInr(row.rate)} / {row.unit}
        </p>
        <p className="mt-2 text-sm">
          Op. stock {formatAmount(row.openingStock)} {row.unit} · closing {formatAmount(row.closingStock)} {row.unit}
        </p>
        <ul className="mt-3 divide-y divide-line">
          {row.days
            .filter((day) => day.inward !== 0 || day.consumption !== 0)
            .map((day) => (
              <li key={day.day} className="flex items-center justify-between py-2 text-sm">
                <span className="font-semibold">Day {day.day}</span>
                <span>
                  In {formatAmount(day.inward)} · Cons {formatAmount(day.consumption)}
                </span>
              </li>
            ))}
        </ul>
        {row.days.every((day) => day.inward === 0 && day.consumption === 0) ? (
          <p className="mt-2 text-sm text-stone-500">No inward or consumption this month.</p>
        ) : null}
      </article>
      <div className="hidden overflow-x-auto rounded-2xl border border-line bg-white lg:block">
        <table className="min-w-max text-xs">
          <thead>
            <tr className="border-b border-line text-left">
              <th className="sticky left-0 bg-white px-2 py-2">Item</th>
              <th className="px-2 py-2">Group</th>
              <th className="px-2 py-2">Op.</th>
              <th className="px-2 py-2">Unit</th>
              {Array.from({ length: sheet.daysInMonth }, (_, index) => (
                <th key={index} className="px-2 py-2 text-center" colSpan={1}>
                  {index + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sheet.rows.map((item) => (
              <tr key={item.itemId} className="border-t border-line">
                <td className="sticky left-0 bg-white px-2 py-1 font-semibold">{item.itemName}</td>
                <td className="px-2 py-1">{item.itemGroup}</td>
                <td className="px-2 py-1">{formatAmount(item.openingStock)}</td>
                <td className="px-2 py-1">{item.unit}</td>
                {item.days.map((day) => (
                  <td key={day.day} className="px-2 py-1 text-right whitespace-nowrap">
                    {day.inward === 0 && day.consumption === 0 ? '' : `${formatAmount(day.inward)} / ${formatAmount(day.consumption)}`}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="px-2 py-2 text-xs text-stone-500">Each day is inward / consumption. Consumption can be negative when material is returned.</p>
      </div>
    </div>
  )
}
