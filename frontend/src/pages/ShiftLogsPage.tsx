import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listShiftLogs } from '../api/shiftLogs'
import { listMachines } from '../api/machines'
import { listRepairLogs } from '../api/repairLogs'
import { todayLocalDate } from '../lib/date'
import type { ShiftLog } from '../api/types'

// The plant runs around the clock, so utilization is measured against a full
// day. The sheet's own "Factory Working hrs" column is 24 on normal days.
const PLANT_DAY_MINUTES = 24 * 60

function daysAgo(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() - days)
  const month = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${month}-${day}`
}

function sum(values: Array<number | null>): number {
  return values.reduce<number>((total, v) => total + (v ?? 0), 0)
}

function hours(minutes: number): string {
  return (minutes / 60).toFixed(1)
}

function pct(part: number, whole: number): string {
  if (whole <= 0) return '—'
  return `${((part / whole) * 100).toFixed(1)}%`
}

export function ShiftLogsPage() {
  const [days, setDays] = useState(7)
  const today = todayLocalDate()
  const dateFrom = useMemo(() => daysAgo(days - 1), [days])

  const logs = useAsync(() => listShiftLogs({ dateFrom, dateTo: today }), [dateFrom, today])
  const machines = useAsync(() => listMachines(), [])
  const repairs = useAsync(() => listRepairLogs({ unresolvedOnly: true }), [])

  const loading = logs.loading || machines.loading || repairs.loading
  const error = logs.error ?? machines.error ?? repairs.error

  if (loading) return <p className="p-6 text-slate-500">Loading…</p>
  if (error) return <p className="p-6 text-red-600">{error}</p>
  if (!logs.data || !machines.data) return null

  const logList = logs.data
  const machineList = machines.data
  const openRepairs = repairs.data ?? []

  const byMachine = new Map<string, ShiftLog[]>()
  for (const log of logList) {
    const existing = byMachine.get(log.machineId)
    if (existing) existing.push(log)
    else byMachine.set(log.machineId, [log])
  }

  const totalRunning = sum(logList.map((l) => l.runningMinutes))
  const totalOutput = sum(logList.map((l) => l.outputQty))
  const totalWastage = sum(logList.map((l) => (l.wastageBoardline ?? 0) + (l.wastageMachine ?? 0)))
  const totalDelay = sum(logList.map((l) => l.delayMinutes))
  const totalJobChanges = sum(logList.map((l) => l.jobChangeCount))

  const loggedToday = new Set(logList.filter((l) => l.logDate === today).map((l) => l.machineId))
  const missingToday = machineList.filter((m) => !loggedToday.has(m.id))

  // Same reason typed on different days is the signal worth acting on -- one
  // ink-roll note is a bad shift, ten is a machine that needs a part.
  const delayReasons = new Map<string, { count: number; minutes: number }>()
  for (const log of logList) {
    const reason = log.delayReason?.trim()
    if (!reason) continue
    const key = reason.toLowerCase()
    const current = delayReasons.get(key) ?? { count: 0, minutes: 0 }
    delayReasons.set(key, { count: current.count + 1, minutes: current.minutes + (log.delayMinutes ?? 0) })
  }
  const topReasons = [...delayReasons.entries()].sort((a, b) => b[1].count - a[1].count).slice(0, 8)

  const rows = machineList.map((machine) => {
    const machineLogs = byMachine.get(machine.id) ?? []
    const running = sum(machineLogs.map((l) => l.runningMinutes))
    const output = sum(machineLogs.map((l) => l.outputQty))
    const wastage = sum(machineLogs.map((l) => (l.wastageBoardline ?? 0) + (l.wastageMachine ?? 0)))
    return {
      machine,
      logCount: machineLogs.length,
      running,
      output,
      wastage,
      boardlineWastage: sum(machineLogs.map((l) => l.wastageBoardline)),
      machineWastage: sum(machineLogs.map((l) => l.wastageMachine)),
      delay: sum(machineLogs.map((l) => l.delayMinutes)),
      jobChanges: sum(machineLogs.map((l) => l.jobChangeCount)),
      openRepairs: openRepairs.filter((r) => r.machineId === machine.id).length,
    }
  })

  return (
    <div className="mx-auto max-w-5xl p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-slate-900">Shift log insights</h1>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Range
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value={1}>Today</option>
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </label>
      </div>
      <p className="mb-4 text-sm text-slate-500">
        {dateFrom} to {today} · {logList.length} shift log{logList.length === 1 ? '' : 's'} submitted. Production
        numbers only — gum, starch, and fuel costs stay in the existing spreadsheet.
      </p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
        <Tile label="Running hours" value={hours(totalRunning)} />
        <Tile
          label="Utilization"
          value={pct(totalRunning, PLANT_DAY_MINUTES * Math.max(1, logList.length))}
          accent="amber"
        />
        <Tile label="Total output" value={totalOutput ? totalOutput.toLocaleString() : '—'} />
        <Tile label="Output per hour" value={totalRunning > 0 ? (totalOutput / (totalRunning / 60)).toFixed(0) : '—'} />
        <Tile label="Wastage" value={pct(totalWastage, totalOutput + totalWastage)} accent="red" />
        <Tile label="Delay hours" value={hours(totalDelay)} accent="red" />
        <Tile label="Job changes" value={totalJobChanges ? String(totalJobChanges) : '—'} />
        <Tile
          label="Output per job change"
          value={totalJobChanges > 0 && totalOutput > 0 ? (totalOutput / totalJobChanges).toFixed(0) : '—'}
        />
      </div>

      {missingToday.length > 0 && (
        <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
          <p className="font-medium text-amber-900">No shift log today ({missingToday.length})</p>
          <ul className="mt-1 text-sm text-amber-800">
            {missingToday.map((m) => (
              <li key={m.id}>
                {m.name} — {m.operator ? m.operator.name : 'no operator assigned'}
              </li>
            ))}
          </ul>
        </div>
      )}

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Per machine</h2>
      <div className="mb-6 overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table className="w-full min-w-[720px] text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Machine</th>
              <th className="px-3 py-2 font-medium">Logs</th>
              <th className="px-3 py-2 font-medium">Run hrs</th>
              <th className="px-3 py-2 font-medium">Output</th>
              <th className="px-3 py-2 font-medium">Per hr</th>
              <th className="px-3 py-2 font-medium">Waste %</th>
              <th className="px-3 py-2 font-medium">Job chg</th>
              <th className="px-3 py-2 font-medium">Delay min</th>
              <th className="px-3 py-2 font-medium">Open repairs</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.machine.id} className="border-t border-slate-100">
                <td className="px-3 py-2">
                  <Link to={`/machines/${row.machine.id}`} className="text-slate-900 hover:underline">
                    {row.machine.name}
                  </Link>
                </td>
                <td className="px-3 py-2 text-slate-600">{row.logCount || '—'}</td>
                <td className="px-3 py-2 text-slate-600">{row.running ? hours(row.running) : '—'}</td>
                <td className="px-3 py-2 text-slate-600">{row.output ? row.output.toLocaleString() : '—'}</td>
                <td className="px-3 py-2 text-slate-600">
                  {row.running > 0 && row.output > 0 ? (row.output / (row.running / 60)).toFixed(0) : '—'}
                </td>
                <td className="px-3 py-2 text-slate-600">
                  {row.wastage > 0 ? pct(row.wastage, row.output + row.wastage) : '—'}
                </td>
                <td className="px-3 py-2 text-slate-600">{row.jobChanges || '—'}</td>
                <td className="px-3 py-2 text-slate-600">{row.delay || '—'}</td>
                <td className={`px-3 py-2 ${row.openRepairs > 0 ? 'font-medium text-red-700' : 'text-slate-600'}`}>
                  {row.openRepairs || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Repeated delay reasons</h2>
      {topReasons.length === 0 ? (
        <p className="text-sm text-slate-500">No delays recorded in this range.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {topReasons.map(([reason, stat]) => (
            <li key={reason} className="text-sm text-slate-700">
              <span className="font-medium text-slate-900">{stat.count}×</span> {reason}
              {stat.minutes > 0 ? ` · ${stat.minutes} min lost` : ''}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Tile({ label, value, accent }: { label: string; value: string; accent?: 'red' | 'amber' }) {
  const accentClass =
    accent === 'red' ? 'text-red-700' : accent === 'amber' ? 'text-amber-700' : 'text-slate-900'
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-semibold ${accentClass}`}>{value}</p>
    </div>
  )
}
