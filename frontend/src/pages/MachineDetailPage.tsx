import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { getMachine } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances, markTaskInstanceDone } from '../api/taskInstances'
import { listRepairLogs } from '../api/repairLogs'
import { listPartReplacements } from '../api/partReplacements'
import { getPublicConfig } from '../api/config'
import { uploadPhoto } from '../api/photos'
import { computeDisplayStatus } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { CameraCapture } from '../components/CameraCapture'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import type { PartReplacement, RepairLog, TaskInstance } from '../api/types'

type TimelineEntry =
  | { kind: 'task'; date: string; instance: TaskInstance }
  | { kind: 'repair'; date: string; log: RepairLog }
  | { kind: 'part'; date: string; part: PartReplacement }

export function MachineDetailPage() {
  const { id } = useParams<{ id: string }>()
  const machineId = id ?? ''
  const { user } = useAuth()
  const canMarkDone = user?.role === 'operator' || user?.role === 'supervisor'

  const machine = useAsync(() => getMachine(machineId), [machineId])
  const taskTypes = useAsync(() => listTaskTypes(machineId), [machineId])
  const taskInstances = useAsync(() => listTaskInstances({ machineId }), [machineId])
  const repairLogs = useAsync(() => listRepairLogs({ machineId }), [machineId])
  const partReplacements = useAsync(() => listPartReplacements(machineId), [machineId])
  const config = useAsync(() => getPublicConfig(), [])

  const [markingId, setMarkingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [photos, setPhotos] = useState<Record<string, File | null>>({})

  const loading =
    machine.loading ||
    taskTypes.loading ||
    taskInstances.loading ||
    repairLogs.loading ||
    partReplacements.loading ||
    config.loading
  const error =
    machine.error ?? taskTypes.error ?? taskInstances.error ?? repairLogs.error ?? partReplacements.error ?? config.error

  if (loading) return <p className="p-6 text-slate-500">Loading…</p>
  if (error) return <p className="p-6 text-red-600">{error}</p>
  if (!machine.data || !taskTypes.data || !taskInstances.data || !repairLogs.data || !partReplacements.data || !config.data) {
    return null
  }

  const machineData = machine.data
  const taskTypeList = taskTypes.data
  const taskInstanceList = taskInstances.data
  const repairLogList = repairLogs.data
  const partReplacementList = partReplacements.data
  const cfg = config.data

  const taskTypeById = new Map(taskTypeList.map((tt) => [tt.id, tt]))

  async function handleMarkDone(taskInstanceId: string) {
    setActionError(null)
    setMarkingId(taskInstanceId)
    try {
      const photo = photos[taskInstanceId]
      const photoUrl = photo ? (await uploadPhoto(photo)).url : undefined
      await markTaskInstanceDone(taskInstanceId, { photoUrl })
      setPhotos((prev) => ({ ...prev, [taskInstanceId]: null }))
      await taskInstances.refetch()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not mark task done')
    } finally {
      setMarkingId(null)
    }
  }

  const pendingInstances = taskInstanceList
    .filter((ti) => ti.status !== 'done')
    .sort((a, b) => a.dueDate.localeCompare(b.dueDate))

  const timeline: TimelineEntry[] = [
    ...taskInstanceList
      .filter((ti) => ti.status === 'done')
      .map((instance): TimelineEntry => ({ kind: 'task', date: instance.completedAt ?? instance.dueDate, instance })),
    ...repairLogList.map((log): TimelineEntry => ({ kind: 'repair', date: log.reportedAt, log })),
    ...partReplacementList.map((part): TimelineEntry => ({ kind: 'part', date: part.replacedAt, part })),
  ].sort((a, b) => b.date.localeCompare(a.date))

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="text-xl font-semibold text-slate-900">{machineData.name}</h1>
      <p className="mb-6 text-sm text-slate-500">
        {machineData.type}
        {machineData.location ? ` · ${machineData.location}` : ''}
      </p>

      <section className="mb-8">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Pending tasks</h2>
        {actionError && <p className="mb-2 text-sm text-red-600">{actionError}</p>}
        {pendingInstances.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing pending.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {pendingInstances.map((instance) => {
              const taskType = taskTypeById.get(instance.taskTypeId)
              const displayStatus = computeDisplayStatus(instance.dueDate, instance.status, cfg.alertUpcomingDays)
              return (
                <li
                  key={instance.id}
                  className="flex flex-col gap-3 rounded-md border border-slate-200 p-3 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <p className="font-medium text-slate-900">{taskType?.description ?? 'Task'}</p>
                    <p className="text-sm text-slate-500">
                      {taskType?.category} · Due {instance.dueDate}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={displayStatus} />
                    {canMarkDone && (
                      <>
                        <CameraCapture
                          photo={photos[instance.id] ?? null}
                          onPhotoChange={(file) => setPhotos((prev) => ({ ...prev, [instance.id]: file }))}
                        />
                        <button
                          onClick={() => handleMarkDone(instance.id)}
                          disabled={markingId === instance.id}
                          className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                        >
                          {markingId === instance.id ? 'Saving…' : 'Mark done'}
                        </button>
                      </>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">History</h2>
        {timeline.length === 0 ? (
          <p className="text-sm text-slate-500">No history yet.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {timeline.map((entry) => (
              <li
                key={
                  entry.kind === 'task'
                    ? `task-${entry.instance.id}`
                    : entry.kind === 'repair'
                      ? `repair-${entry.log.id}`
                      : `part-${entry.part.id}`
                }
                className="rounded-md border border-slate-200 p-3"
              >
                {entry.kind === 'task' && (
                  <div className="flex items-center gap-3">
                    <p className="text-sm text-slate-700">
                      <span className="font-medium">Completed:</span>{' '}
                      {taskTypeById.get(entry.instance.taskTypeId)?.description ?? 'Task'}{' '}
                      <span className="text-slate-400">· {entry.instance.completedAt?.slice(0, 10)}</span>
                    </p>
                    {entry.instance.photoUrl && (
                      <img
                        src={entry.instance.photoUrl}
                        alt="Proof of completion"
                        className="h-8 w-8 rounded object-cover"
                      />
                    )}
                  </div>
                )}
                {entry.kind === 'repair' && (
                  <p className="text-sm text-slate-700">
                    <span className="font-medium">Repair:</span> {entry.log.issueDescription}{' '}
                    <span className="text-slate-400">
                      · {entry.log.reportedAt.slice(0, 10)} · {entry.log.resolvedAt ? 'resolved' : 'open'}
                    </span>
                  </p>
                )}
                {entry.kind === 'part' && (
                  <p className="text-sm text-slate-700">
                    <span className="font-medium">Part replaced:</span> {entry.part.partName}{' '}
                    <span className="text-slate-400">· {entry.part.replacedAt}</span>
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
