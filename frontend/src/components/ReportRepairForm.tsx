import { useState } from 'react'
import type { FormEvent } from 'react'
import { createRepairLog } from '../api/repairLogs'
import { ApiError } from '../api/client'
import { useLocale } from '../locale/localeContext'

interface ReportRepairFormProps {
  machineId: string
  onReported: () => void
  /** Phone-sized controls for the operator's Today page. */
  large?: boolean
}

export function ReportRepairForm({ machineId, onReported, large = false }: ReportRepairFormProps) {
  const { t } = useLocale()
  const [open, setOpen] = useState(false)
  const [issueDescription, setIssueDescription] = useState('')
  const [impact, setImpact] = useState('')
  const [downtimeMinutes, setDowntimeMinutes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
    setIssueDescription('')
    setImpact('')
    setDowntimeMinutes('')
    setError(null)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await createRepairLog({
        machineId,
        issueDescription,
        impact,
        downtimeMinutes: downtimeMinutes ? Number(downtimeMinutes) : undefined,
      })
      reset()
      setOpen(false)
      onReported()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not report repair')
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
        {t.reportRepair}
      </button>
    )
  }

  return (
    <form
      onSubmit={(e) => void handleSubmit(e)}
      className={`flex w-full flex-col gap-3 border border-slate-200 p-3 ${large ? 'rounded-xl' : 'rounded-md'}`}
    >
      <p className="text-sm font-semibold text-slate-900">{t.reportRepair}</p>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">{t.issueDescription}</span>
        <textarea
          required
          rows={2}
          value={issueDescription}
          onChange={(e) => setIssueDescription(e.target.value)}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">{t.repairImpact}</span>
        <textarea
          required
          rows={2}
          placeholder={t.repairImpactHint}
          value={impact}
          onChange={(e) => setImpact(e.target.value)}
          className={inputClass}
        />
      </label>
      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium text-slate-700">
          {t.downtimeMinutes} ({t.optional})
        </span>
        <input
          type="number"
          min={0}
          inputMode="numeric"
          value={downtimeMinutes}
          onChange={(e) => setDowntimeMinutes(e.target.value)}
          className={inputClass}
        />
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className={`flex gap-2 ${large ? 'flex-col' : ''}`}>
        <button type="submit" disabled={submitting} className={submitClass}>
          {submitting ? t.saving : t.reportRepair}
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
