import { useState } from 'react'
import type { FormEvent } from 'react'
import { saveShiftLog } from '../api/shiftLogs'
import { ApiError } from '../api/client'
import { todayLocalDate } from '../lib/date'
import { useLocale } from '../locale/localeContext'
import type { OutputUnit, ShiftLog } from '../api/types'

/** Trim a "HH:MM:SS" time from the API down to what <input type="time"> wants. */
function toTimeInput(value: string | null): string {
  return value ? value.slice(0, 5) : ''
}

function toNumberOrNull(value: string): number | null {
  return value.trim() === '' ? null : Number(value)
}

export function ShiftLogForm({
  machineId,
  logDate = todayLocalDate(),
  existing,
  large = false,
  onSaved,
}: {
  machineId: string
  logDate?: string
  existing: ShiftLog | null
  large?: boolean
  onSaved: () => void
}) {
  const { t } = useLocale()
  const [startTime, setStartTime] = useState(toTimeInput(existing?.startTime ?? null))
  const [endTime, setEndTime] = useState(toTimeInput(existing?.endTime ?? null))
  const [outputQty, setOutputQty] = useState(existing?.outputQty?.toString() ?? '')
  const [outputUnit, setOutputUnit] = useState<OutputUnit>(existing?.outputUnit ?? 'kg')
  const [jobChangeCount, setJobChangeCount] = useState(existing?.jobChangeCount?.toString() ?? '')
  const [wastageBoardline, setWastageBoardline] = useState(existing?.wastageBoardline?.toString() ?? '')
  const [wastageMachine, setWastageMachine] = useState(existing?.wastageMachine?.toString() ?? '')
  const [delayReason, setDelayReason] = useState(existing?.delayReason ?? '')
  const [delayMinutes, setDelayMinutes] = useState(existing?.delayMinutes?.toString() ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const inputClass = large
    ? 'rounded-xl border border-slate-300 px-3 py-3 text-lg focus:border-slate-500 focus:outline-none'
    : 'rounded-md border border-slate-300 px-3 py-2 text-base focus:border-slate-500 focus:outline-none'

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSaved(false)
    setSubmitting(true)
    try {
      await saveShiftLog({
        machineId,
        logDate,
        startTime: startTime || null,
        endTime: endTime || null,
        outputQty: toNumberOrNull(outputQty),
        outputUnit,
        jobChangeCount: toNumberOrNull(jobChangeCount),
        wastageBoardline: toNumberOrNull(wastageBoardline),
        wastageMachine: toNumberOrNull(wastageMachine),
        delayReason: delayReason.trim() || null,
        delayMinutes: toNumberOrNull(delayMinutes),
      })
      setSaved(true)
      onSaved()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save shift log')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={(e) => void handleSubmit(e)} className="flex flex-col gap-3">
      <div className="grid grid-cols-2 gap-3">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.startTime}</span>
          <input
            type="time"
            value={startTime}
            onChange={(e) => setStartTime(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.endTime}</span>
          <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className={inputClass} />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.output}</span>
          <input
            type="number"
            min={0}
            step="any"
            inputMode="decimal"
            value={outputQty}
            onChange={(e) => setOutputQty(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">Unit</span>
          <select
            value={outputUnit}
            onChange={(e) => setOutputUnit(e.target.value as OutputUnit)}
            className={inputClass}
          >
            <option value="kg">kg</option>
            <option value="pcs">pcs</option>
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.jobChanges}</span>
          <input
            type="number"
            min={0}
            inputMode="numeric"
            value={jobChangeCount}
            onChange={(e) => setJobChangeCount(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.delayMinutes}</span>
          <input
            type="number"
            min={0}
            inputMode="numeric"
            value={delayMinutes}
            onChange={(e) => setDelayMinutes(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.wastageBoardline}</span>
          <input
            type="number"
            min={0}
            step="any"
            inputMode="decimal"
            value={wastageBoardline}
            onChange={(e) => setWastageBoardline(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium text-slate-700">{t.wastageMachine}</span>
          <input
            type="number"
            min={0}
            step="any"
            inputMode="decimal"
            value={wastageMachine}
            onChange={(e) => setWastageMachine(e.target.value)}
            className={inputClass}
          />
        </label>
      </div>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">
          {t.delayReason} ({t.optional})
        </span>
        <textarea
          rows={2}
          value={delayReason}
          onChange={(e) => setDelayReason(e.target.value)}
          className={inputClass}
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {saved && !error && <p className="text-sm text-green-700">{t.shiftLogSaved}</p>}
      <button
        type="submit"
        disabled={submitting}
        className={
          large
            ? 'min-h-14 rounded-xl bg-slate-900 px-4 text-lg font-semibold text-white disabled:opacity-50'
            : 'rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50'
        }
      >
        {submitting ? t.saving : t.save}
      </button>
    </form>
  )
}
