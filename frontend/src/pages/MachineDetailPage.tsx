import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { getMachine, deleteMachine } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances, markTaskInstanceDone, reopenTaskInstance } from '../api/taskInstances'
import { listRepairLogs } from '../api/repairLogs'
import { listPartReplacements } from '../api/partReplacements'
import { listHandoverNotes } from '../api/handover'
import { listUsers } from '../api/users'
import { getPublicConfig } from '../api/config'
import { uploadPhoto } from '../api/photos'
import { computeDisplayStatus } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { CameraCapture } from '../components/CameraCapture'
import { ReportRepairForm } from '../components/ReportRepairForm'
import { LogPartReplacementForm } from '../components/LogPartReplacementForm'
import { EditMachineForm } from '../components/EditMachineForm'
import { TaskTypesSection } from '../components/TaskTypesSection'
import { RescheduleTaskInstanceForm } from '../components/RescheduleTaskInstanceForm'
import { ChecklistRunForm } from '../components/ChecklistRunForm'
import { ChecklistResultsView } from '../components/ChecklistResultsView'
import { ResolveRepairLogForm } from '../components/ResolveRepairLogForm'
import { HandoverForm } from '../components/HandoverForm'
import { MachineQr } from '../components/MachineQr'
import { ProofPhoto } from '../components/ProofPhoto'
import { useAuth } from '../auth/useAuth'
import { ApiError } from '../api/client'
import { hi } from '../lib/i18n'
import type { PartReplacement, RepairLog, TaskInstance, User } from '../api/types'

type TimelineEntry =
  | { kind: 'task'; date: string; instance: TaskInstance }
  | { kind: 'repair'; date: string; log: RepairLog }
  | { kind: 'part'; date: string; part: PartReplacement }

export function MachineDetailPage() {
  const { id } = useParams<{ id: string }>()
  const machineId = id ?? ''
  const navigate = useNavigate()
  const { user } = useAuth()
  const canDoFloorWork = user?.role === 'operator' || user?.role === 'supervisor' || user?.role === 'admin'
  const canManageSetup = user?.role === 'supervisor' || user?.role === 'admin'
  const canListUsers = user?.role === 'admin' || user?.role === 'supervisor' || user?.role === 'management'

  const machine = useAsync(() => getMachine(machineId), [machineId])
  const taskTypes = useAsync(() => listTaskTypes(machineId), [machineId])
  const taskInstances = useAsync(() => listTaskInstances({ machineId }), [machineId])
  const repairLogs = useAsync(() => listRepairLogs({ machineId }), [machineId])
  const partReplacements = useAsync(() => listPartReplacements(machineId), [machineId])
  const handover = useAsync(() => listHandoverNotes(machineId), [machineId])
  const users = useAsync(() => (canListUsers ? listUsers() : Promise.resolve([] as User[])), [canListUsers])
  const config = useAsync(() => getPublicConfig(), [])

  const [markingId, setMarkingId] = useState<string | null>(null)
  const [checklistInstanceId, setChecklistInstanceId] = useState<string | null>(null)
  const [historyChecklistId, setHistoryChecklistId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [reopeningId, setReopeningId] = useState<string | null>(null)
  const [reopenError, setReopenError] = useState<string | null>(null)
  const [photos, setPhotos] = useState<Record<string, File | null>>({})
  const [deletingMachine, setDeletingMachine] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const loading =
    machine.loading ||
    taskTypes.loading ||
    taskInstances.loading ||
    repairLogs.loading ||
    partReplacements.loading ||
    handover.loading ||
    users.loading ||
    config.loading
  const error =
    machine.error ??
    taskTypes.error ??
    taskInstances.error ??
    repairLogs.error ??
    partReplacements.error ??
    handover.error ??
    users.error ??
    config.error

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
  const userById = new Map((users.data ?? []).map((u) => [u.id, u]))
  const openRepairs = repairLogList.filter((log) => !log.resolvedAt)
  const latestHandover = handover.data?.[0] ?? null

  const taskTypeById = new Map(taskTypeList.map((tt) => [tt.id, tt]))

  async function handleDeleteMachine() {
    const confirmed = window.confirm(
      `Delete "${machineData.name}"? This permanently deletes its task types, task instances, repair logs, and part replacements. This cannot be undone.`,
    )
    if (!confirmed) return
    setDeleteError(null)
    setDeletingMachine(true)
    try {
      await deleteMachine(machineId)
      navigate('/')
    } catch (err) {
      setDeleteError(err instanceof ApiError ? err.message : 'Could not delete machine')
      setDeletingMachine(false)
    }
  }

  async function handleMarkDone(taskInstanceId: string) {
    const photo = photos[taskInstanceId]
    if (!photo) {
      setActionError(hi.photo)
      return
    }
    setActionError(null)
    setMarkingId(taskInstanceId)
    try {
      const photoUrl = (await uploadPhoto(photo)).url
      await markTaskInstanceDone(taskInstanceId, { photoUrl, startedAt: new Date().toISOString() })
      setPhotos((prev) => ({ ...prev, [taskInstanceId]: null }))
      await taskInstances.refetch()
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : 'Could not submit for review')
    } finally {
      setMarkingId(null)
    }
  }

  async function handleReopen(taskInstanceId: string) {
    const confirmed = window.confirm(
      'Reopen this approved task? It moves back to Pending, and its completion notes/photo are cleared.',
    )
    if (!confirmed) return
    setReopenError(null)
    setReopeningId(taskInstanceId)
    try {
      await reopenTaskInstance(taskInstanceId)
      await taskInstances.refetch()
    } catch (err) {
      setReopenError(err instanceof ApiError ? err.message : 'Could not reopen task')
    } finally {
      setReopeningId(null)
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
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">{machineData.name}</h1>
          <p className="text-sm text-slate-500">
            {machineData.type}
            {machineData.location ? ` · ${machineData.location}` : ''}
          </p>
          <p className={`mt-1 text-sm ${machineData.operator ? 'text-slate-600' : 'font-medium text-amber-700'}`}>
            {machineData.operator ? `Operator: ${machineData.operator.name}` : 'No operator assigned'}
          </p>
        </div>
        {canManageSetup && (
          <div className="flex flex-col items-start gap-2 sm:items-end">
            <EditMachineForm machine={machineData} onSaved={() => void machine.refetch()} />
            <button
              type="button"
              onClick={() => void handleDeleteMachine()}
              disabled={deletingMachine}
              className="rounded-md border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50 disabled:opacity-50"
            >
              {deletingMachine ? 'Deleting…' : 'Delete machine'}
            </button>
            {deleteError && <p className="text-sm text-red-600">{deleteError}</p>}
            <MachineQr machineId={machineId} machineName={machineData.name} />
          </div>
        )}
      </div>

      {openRepairs.length > 0 && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="font-semibold text-red-800">{hi.repairOpen}</p>
          <ul className="mt-1 text-sm text-red-700">
            {openRepairs.map((log) => (
              <li key={log.id}>{log.issueDescription}</li>
            ))}
          </ul>
        </div>
      )}

      {canDoFloorWork && (
        <HandoverForm machineId={machineId} latest={latestHandover} onSaved={() => void handover.refetch()} />
      )}

      {canDoFloorWork && (
        <section className="mb-8">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Actions</h2>
          <div className="flex flex-wrap items-start gap-2">
            <ReportRepairForm machineId={machineId} onReported={() => void repairLogs.refetch()} />
            <LogPartReplacementForm machineId={machineId} onLogged={() => void partReplacements.refetch()} />
          </div>
        </section>
      )}

      {canManageSetup && (
        <TaskTypesSection
          machineId={machineId}
          taskTypes={taskTypeList}
          onTaskTypesChanged={() => void taskTypes.refetch()}
          onTaskInstancesChanged={() => void taskInstances.refetch()}
        />
      )}

      <section className="mb-8">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Pending tasks</h2>
        {actionError && <p className="mb-2 text-sm text-red-600">{actionError}</p>}
        {pendingInstances.length === 0 ? (
          <p className="text-sm text-slate-500">Nothing pending.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {pendingInstances.map((instance) => {
              const taskType = taskTypeById.get(instance.taskTypeId)
              const displayStatus = computeDisplayStatus(
                instance.dueDate,
                instance.status,
                cfg.alertUpcomingDays,
                instance.reviewStatus,
              )
              const waiting = instance.reviewStatus === 'awaiting_review'
              return (
                <li key={instance.id} className="flex flex-col gap-3 rounded-md border border-slate-200 p-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="font-medium text-slate-900">{taskType?.description ?? 'Task'}</p>
                      <p className="text-sm text-slate-500">
                        {taskType?.category} · Due {instance.dueDate}
                      </p>
                      {instance.reviewStatus === 'rejected' && instance.reviewNotes && (
                        <p className="mt-1 text-sm text-orange-800">
                          {hi.rejectReason}: {instance.reviewNotes}
                        </p>
                      )}
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={displayStatus} />
                      {waiting && <span className="text-sm text-indigo-700">{hi.waiting}</span>}
                      {canDoFloorWork && !waiting && taskType?.category === 'preventive' && checklistInstanceId !== instance.id && (
                        <button
                          type="button"
                          onClick={() => setChecklistInstanceId(instance.id)}
                          className="min-h-12 rounded-md bg-slate-900 px-4 py-2 text-base font-medium text-white hover:bg-slate-800"
                        >
                          {hi.start}
                        </button>
                      )}
                      {canDoFloorWork && !waiting && taskType?.category !== 'preventive' && (
                        <>
                          <CameraCapture
                            photo={photos[instance.id] ?? null}
                            onPhotoChange={(file) => setPhotos((prev) => ({ ...prev, [instance.id]: file }))}
                            label={hi.photo}
                            required
                          />
                          <button
                            onClick={() => handleMarkDone(instance.id)}
                            disabled={markingId === instance.id}
                            className="min-h-12 rounded-md bg-slate-900 px-4 py-2 text-base font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                          >
                            {markingId === instance.id ? hi.saving : hi.submit}
                          </button>
                        </>
                      )}
                      {canManageSetup && !waiting && (
                        <RescheduleTaskInstanceForm
                          taskInstanceId={instance.id}
                          currentDueDate={instance.dueDate}
                          onRescheduled={() => void taskInstances.refetch()}
                        />
                      )}
                    </div>
                  </div>
                  {canDoFloorWork && taskType?.category === 'preventive' && checklistInstanceId === instance.id && (
                    <ChecklistRunForm
                      instance={instance}
                      taskTypeId={taskType.id}
                      onCompleted={async () => {
                        setChecklistInstanceId(null)
                        await taskInstances.refetch()
                      }}
                      onCancel={() => setChecklistInstanceId(null)}
                    />
                  )}
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">History</h2>
        {reopenError && <p className="mb-2 text-sm text-red-600">{reopenError}</p>}
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
                  <div>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex items-center gap-3">
                        <p className="text-sm text-slate-700">
                          <span className="font-medium">Completed:</span>{' '}
                          {taskTypeById.get(entry.instance.taskTypeId)?.description ?? 'Task'}{' '}
                          <span className="text-slate-400">
                            · {entry.instance.completedAt?.slice(0, 10)}
                            {entry.instance.completedBy && userById.get(entry.instance.completedBy)
                              ? ` · ${userById.get(entry.instance.completedBy)?.name}`
                              : ''}
                          </span>
                        </p>
                        {entry.instance.photoUrl && (
                          <ProofPhoto
                            url={entry.instance.photoUrl}
                            alt="Proof of completion"
                            className="h-16 w-16 rounded object-cover"
                            zoomable
                          />
                        )}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {taskTypeById.get(entry.instance.taskTypeId)?.category === 'preventive' && (
                          <button
                            type="button"
                            onClick={() =>
                              setHistoryChecklistId(historyChecklistId === entry.instance.id ? null : entry.instance.id)
                            }
                            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
                          >
                            {historyChecklistId === entry.instance.id ? 'Hide checklist' : 'View checklist'}
                          </button>
                        )}
                        {canManageSetup && (
                          <button
                            type="button"
                            onClick={() => void handleReopen(entry.instance.id)}
                            disabled={reopeningId === entry.instance.id}
                            className="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                          >
                            {reopeningId === entry.instance.id ? 'Reopening…' : 'Reopen'}
                          </button>
                        )}
                      </div>
                    </div>
                    {historyChecklistId === entry.instance.id && (
                      <ChecklistResultsView
                        taskTypeId={entry.instance.taskTypeId}
                        taskInstanceId={entry.instance.id}
                      />
                    )}
                  </div>
                )}
                {entry.kind === 'repair' && (
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm text-slate-700">
                      <span className="font-medium">Repair:</span> {entry.log.issueDescription}{' '}
                      <span className="text-slate-400">
                        · {entry.log.reportedAt.slice(0, 10)} · {entry.log.resolvedAt ? 'resolved' : 'open'}
                      </span>
                    </p>
                    {canManageSetup && !entry.log.resolvedAt && (
                      <ResolveRepairLogForm repairLogId={entry.log.id} onResolved={() => void repairLogs.refetch()} />
                    )}
                  </div>
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
