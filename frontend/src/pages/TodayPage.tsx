import { useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { listRepairLogs } from '../api/repairLogs'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, daysUntilDue } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { ChecklistRunForm } from '../components/ChecklistRunForm'
import { CameraCapture } from '../components/CameraCapture'
import { markTaskInstanceDone } from '../api/taskInstances'
import { uploadPhoto } from '../api/photos'
import { ApiError } from '../api/client'
import { hi } from '../lib/i18n'
import { useAuth } from '../auth/useAuth'
import type { TaskInstance } from '../api/types'

export function TodayPage() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  const focusMachine = params.get('machine')
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const instances = useAsync(() => listTaskInstances(), [])
  const repairs = useAsync(() => listRepairLogs({ unresolvedOnly: true }), [])
  const config = useAsync(() => getPublicConfig(), [])

  const [runningId, setRunningId] = useState<string | null>(null)
  const [photos, setPhotos] = useState<Record<string, File | null>>({})
  const [markingId, setMarkingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const loading = machines.loading || taskTypes.loading || instances.loading || repairs.loading || config.loading
  const loadError = machines.error ?? taskTypes.error ?? instances.error ?? repairs.error ?? config.error

  const cards = useMemo(() => {
    if (!machines.data || !taskTypes.data || !instances.data || !config.data) return []
    const cfg = config.data
    const taskTypeById = new Map(taskTypes.data.map((tt) => [tt.id, tt]))
    const machineById = new Map(machines.data.map((m) => [m.id, m]))
    return instances.data
      .filter((ti) => ti.status !== 'done')
      .filter((ti) => {
        if (ti.reviewStatus === 'awaiting_review') return true
        return daysUntilDue(ti.dueDate) <= 0
      })
      .filter((ti) => {
        if (!focusMachine) return true
        const tt = taskTypeById.get(ti.taskTypeId)
        return tt?.machineId === focusMachine
      })
      .map((ti) => {
        const taskType = taskTypeById.get(ti.taskTypeId)
        const machine = taskType ? machineById.get(taskType.machineId) : undefined
        const display = computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays, ti.reviewStatus)
        return { ti, taskType, machine, display }
      })
      .sort((a, b) => a.ti.dueDate.localeCompare(b.ti.dueDate))
  }, [machines.data, taskTypes.data, instances.data, config.data, focusMachine])

  if (loading) return <p className="p-6 text-lg text-slate-500">लोड हो रहा है… / Loading…</p>
  if (loadError) return <p className="p-6 text-lg text-red-600">{loadError}</p>

  const late = cards.filter((c) => c.display === 'overdue' || c.display === 'rejected')
  const dueToday = cards.filter((c) => c.display === 'upcoming' || c.display === 'ok')
  const waiting = cards.filter((c) => c.display === 'review')
  const openRepairs = repairs.data ?? []

  async function handleSimpleDone(instance: TaskInstance) {
    const photo = photos[instance.id]
    if (!photo) {
      setError(hi.photo)
      return
    }
    setError(null)
    setMarkingId(instance.id)
    try {
      const uploaded = await uploadPhoto(photo)
      await markTaskInstanceDone(instance.id, { photoUrl: uploaded.url, startedAt: new Date().toISOString() })
      setPhotos((prev) => ({ ...prev, [instance.id]: null }))
      await instances.refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not submit')
    } finally {
      setMarkingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-lg p-4 pb-16">
      <h1 className="mb-1 text-2xl font-bold text-slate-900">{hi.today}</h1>
      <p className="mb-4 text-base text-slate-600">{user?.name}</p>
      {error && <p className="mb-3 text-base text-red-600">{error}</p>}

      {openRepairs.length > 0 && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-3">
          <p className="font-semibold text-red-800">{hi.repairOpen}</p>
          <ul className="mt-1 text-sm text-red-700">
            {openRepairs.slice(0, 5).map((log) => (
              <li key={log.id}>{log.issueDescription}</li>
            ))}
          </ul>
        </div>
      )}

      {cards.length === 0 && <p className="rounded-xl border border-slate-200 bg-white p-6 text-lg text-slate-600">{hi.nothingToday}</p>}

      <Section title={hi.late} items={late} />
      <Section title={hi.dueToday} items={dueToday} />
      <Section title={hi.waiting} items={waiting} waiting />
    </div>
  )

  function Section({
    title,
    items,
    waiting: isWaiting,
  }: {
    title: string
    items: typeof cards
    waiting?: boolean
  }) {
    if (items.length === 0) return null
    return (
      <section className="mb-6">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h2>
        <ul className="flex flex-col gap-3">
          {items.map(({ ti, taskType, machine, display }) => (
            <li key={ti.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-start justify-between gap-2">
                <div>
                  <p className="text-xl font-semibold text-slate-900">{machine?.name}</p>
                  <p className="text-base text-slate-600">{taskType?.description}</p>
                </div>
                <StatusBadge status={display} />
              </div>
              {ti.reviewStatus === 'rejected' && ti.reviewNotes && (
                <p className="mb-3 rounded-md bg-orange-50 px-3 py-2 text-base text-orange-900">
                  {hi.rejectReason}: {ti.reviewNotes}
                </p>
              )}
              {isWaiting ? (
                <p className="text-base text-slate-500">{hi.waiting}</p>
              ) : runningId === ti.id && taskType?.category === 'preventive' ? (
                <ChecklistRunForm
                  instance={ti}
                  taskTypeId={taskType.id}
                  onCompleted={async () => {
                    setRunningId(null)
                    await instances.refetch()
                  }}
                  onCancel={() => setRunningId(null)}
                />
              ) : taskType?.category === 'preventive' ? (
                <button
                  type="button"
                  onClick={() => setRunningId(ti.id)}
                  className="mt-2 min-h-16 w-full rounded-xl bg-slate-900 text-lg font-semibold text-white"
                >
                  {hi.start}
                </button>
              ) : (
                <div className="mt-2 flex flex-col gap-2">
                  <CameraCapture
                    photo={photos[ti.id] ?? null}
                    onPhotoChange={(file) => setPhotos((prev) => ({ ...prev, [ti.id]: file }))}
                    label={hi.photo}
                    required
                    large
                  />
                  <button
                    type="button"
                    disabled={markingId === ti.id}
                    onClick={() => void handleSimpleDone(ti)}
                    className="min-h-16 rounded-xl bg-slate-900 text-lg font-semibold text-white disabled:opacity-50"
                  >
                    {markingId === ti.id ? hi.saving : hi.submit}
                  </button>
                </div>
              )}
              <Link to={`/machines/${machine?.id ?? ''}`} className="mt-2 inline-block text-sm text-slate-500">
                Machine details
              </Link>
            </li>
          ))}
        </ul>
      </section>
    )
  }
}
