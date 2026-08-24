import { useMemo, useState } from 'react'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { approveTaskInstance, listTaskInstances, rejectTaskInstance } from '../api/taskInstances'
import { listUsers } from '../api/users'
import { ApiError } from '../api/client'
import { ChecklistResultsView } from '../components/ChecklistResultsView'
import { ProofPhoto } from '../components/ProofPhoto'
import type { ExceptionLevel, TaskInstance } from '../api/types'

const RANK: Record<ExceptionLevel, number> = { critical: 0, attention: 1, none: 2 }

export function ReviewPage() {
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const instances = useAsync(() => listTaskInstances({ reviewStatus: 'awaiting_review' }), [])
  const users = useAsync(() => listUsers(), [])

  const [actingId, setActingId] = useState<string | null>(null)
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const loading = machines.loading || taskTypes.loading || instances.loading || users.loading
  const loadError = machines.error ?? taskTypes.error ?? instances.error ?? users.error

  const queue = useMemo(() => {
    if (!instances.data) return []
    return [...instances.data].sort((a, b) => {
      const rank = RANK[a.exceptionLevel] - RANK[b.exceptionLevel]
      if (rank !== 0) return rank
      return (a.completedAt ?? '').localeCompare(b.completedAt ?? '')
    })
  }, [instances.data])

  if (loading) return <p className="p-6 text-slate-500">Loading review queue…</p>
  if (loadError) return <p className="p-6 text-red-600">{loadError}</p>
  if (!machines.data || !taskTypes.data || !users.data) return null

  const machineByTaskType = new Map(
    taskTypes.data.map((tt) => [tt.id, machines.data?.find((m) => m.id === tt.machineId)]),
  )
  const taskTypeById = new Map(taskTypes.data.map((tt) => [tt.id, tt]))
  const userById = new Map(users.data.map((u) => [u.id, u]))

  async function handleApprove(id: string) {
    setError(null)
    setActingId(id)
    try {
      await approveTaskInstance(id)
      await instances.refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not approve')
    } finally {
      setActingId(null)
    }
  }

  async function handleReject(instance: TaskInstance) {
    if (!rejectReason.trim()) {
      setError('Write a short reason so the operator knows what to redo')
      return
    }
    setError(null)
    setActingId(instance.id)
    try {
      await rejectTaskInstance(instance.id, rejectReason.trim())
      setRejectingId(null)
      setRejectReason('')
      await instances.refetch()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reject')
    } finally {
      setActingId(null)
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-4">
      <h1 className="mb-1 text-xl font-semibold text-slate-900">Review queue</h1>
      <p className="mb-4 text-sm text-slate-500">
        {queue.length} submission(s) waiting. Critical and Attention are at the top.
      </p>
      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}
      {queue.length === 0 ? (
        <p className="rounded-md border border-slate-200 bg-white p-4 text-slate-500">Nothing waiting.</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {queue.map((instance) => {
            const taskType = taskTypeById.get(instance.taskTypeId)
            const machine = machineByTaskType.get(instance.taskTypeId)
            const who = instance.completedBy ? userById.get(instance.completedBy)?.name : 'Unknown'
            const when = instance.completedAt ? new Date(instance.completedAt).toLocaleString() : ''
            return (
              <li key={instance.id} className="rounded-xl border border-slate-200 bg-white p-4">
                <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <p className="text-lg font-semibold text-slate-900">{machine?.name ?? 'Machine'}</p>
                    <p className="text-sm text-slate-600">{taskType?.description}</p>
                    <p className="text-sm text-slate-500">
                      {who} · {when}
                    </p>
                  </div>
                  <ExceptionBadge level={instance.exceptionLevel} />
                </div>
                {instance.isFastSubmit && (
                  <p className="mb-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
                    Finished very fast
                    {instance.durationSeconds != null ? ` (${Math.round(instance.durationSeconds / 60)} min)` : ''}.
                    Check the photo before accepting.
                  </p>
                )}
                {instance.photoUrl && (
                  <ProofPhoto url={instance.photoUrl} alt="Proof photo" className="mb-2 h-56 w-full rounded-lg object-cover" zoomable />
                )}
                {instance.exceptionPhotoUrl && (
                  <ProofPhoto
                    url={instance.exceptionPhotoUrl}
                    alt="Problem photo"
                    className="mb-2 h-40 w-full rounded-lg object-cover"
                    zoomable
                  />
                )}
                {taskType?.category === 'preventive' && (
                  <ChecklistResultsView taskTypeId={taskType.id} taskInstanceId={instance.id} />
                )}
                <div className="mt-3 flex flex-col gap-2">
                  <button
                    type="button"
                    disabled={actingId === instance.id}
                    onClick={() => void handleApprove(instance.id)}
                    className="min-h-12 rounded-lg bg-green-700 px-4 text-base font-semibold text-white disabled:opacity-50"
                  >
                    {actingId === instance.id ? 'Saving…' : 'Accept'}
                  </button>
                  {rejectingId === instance.id ? (
                    <div className="flex flex-col gap-2">
                      <textarea
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="Why should they redo this?"
                        className="min-h-20 rounded-md border border-slate-300 px-3 py-2 text-base"
                      />
                      <button
                        type="button"
                        disabled={actingId === instance.id}
                        onClick={() => void handleReject(instance)}
                        className="min-h-12 rounded-lg bg-red-700 px-4 text-base font-semibold text-white"
                      >
                        Reject and send back
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => {
                        setRejectingId(instance.id)
                        setRejectReason('')
                      }}
                      className="min-h-12 rounded-lg border border-red-300 px-4 text-base font-medium text-red-700"
                    >
                      Reject
                    </button>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function ExceptionBadge({ level }: { level: ExceptionLevel }) {
  if (level === 'critical') {
    return <span className="rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800">Critical</span>
  }
  if (level === 'attention') {
    return <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800">Attention</span>
  }
  return <span className="rounded-full bg-slate-100 px-3 py-1 text-sm font-medium text-slate-600">All OK</span>
}
