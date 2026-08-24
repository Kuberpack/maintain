import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, isOpenWork } from '../lib/status'
import type { DisplayStatus } from '../lib/status'

export function SummaryPage() {
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const taskInstances = useAsync(() => listTaskInstances(), [])
  const config = useAsync(() => getPublicConfig(), [])

  const loading = machines.loading || taskTypes.loading || taskInstances.loading || config.loading
  const error = machines.error ?? taskTypes.error ?? taskInstances.error ?? config.error

  if (loading) return <p className="p-6 text-slate-500">Loading…</p>
  if (error) return <p className="p-6 text-red-600">{error}</p>
  if (!machines.data || !taskTypes.data || !taskInstances.data || !config.data) return null

  const machineList = machines.data
  const taskTypeList = taskTypes.data
  const taskInstanceList = taskInstances.data
  const cfg = config.data

  const taskTypeToMachine = new Map(taskTypeList.map((tt) => [tt.id, tt.machineId]))

  const openInstances = taskInstanceList.filter((ti) => isOpenWork(ti.status, ti.reviewStatus))
  const awaitingCount = taskInstanceList.filter((ti) => ti.reviewStatus === 'awaiting_review').length
  const approvedCount = taskInstanceList.filter((ti) => ti.reviewStatus === 'approved').length
  const withStatus = openInstances.map((ti) => ({
    instance: ti,
    status: computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays, ti.reviewStatus),
  }))

  const overdueCount = withStatus.filter((x) => x.status === 'overdue').length
  const upcomingCount = withStatus.filter((x) => x.status === 'upcoming').length
  const okCount = withStatus.filter((x) => x.status === 'ok').length
  const compliancePct =
    openInstances.length === 0 ? 100 : Math.round(((openInstances.length - overdueCount) / openInstances.length) * 100)

  const perMachine = machineList.map((machine) => {
    const statuses: DisplayStatus[] = withStatus
      .filter((x) => taskTypeToMachine.get(x.instance.taskTypeId) === machine.id)
      .map((x) => x.status)
    return {
      machine,
      overdue: statuses.filter((s) => s === 'overdue').length,
      upcoming: statuses.filter((s) => s === 'upcoming').length,
      ok: statuses.filter((s) => s === 'ok').length,
    }
  })

  return (
    <div className="mx-auto max-w-5xl p-4">
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Compliance summary</h1>
      <p className="mb-4 text-sm text-slate-500">
        Compliance counts only work that is still open (not submitted for review, not approved). {approvedCount}{' '}
        approved this cycle · {awaitingCount} waiting for a supervisor.
      </p>

      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
        <StatTile label="Compliance" value={`${compliancePct}%`} />
        <StatTile label="Overdue" value={String(overdueCount)} accent="red" />
        <StatTile label="Due soon" value={String(upcomingCount)} accent="amber" />
        <StatTile label="On track" value={String(okCount)} accent="green" />
        <StatTile label="Waiting review" value={String(awaitingCount)} />
      </div>

      <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">Per-machine</h2>
      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table className="w-full min-w-[480px] text-sm">
          <thead className="bg-slate-50 text-left text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Machine</th>
              <th className="px-3 py-2 font-medium">Overdue</th>
              <th className="px-3 py-2 font-medium">Due soon</th>
              <th className="px-3 py-2 font-medium">On track</th>
            </tr>
          </thead>
          <tbody>
            {perMachine.map((row) => (
              <tr key={row.machine.id} className="border-t border-slate-100">
                <td className="px-3 py-2 font-medium text-slate-900">{row.machine.name}</td>
                <td className="px-3 py-2 text-red-600">{row.overdue}</td>
                <td className="px-3 py-2 text-amber-600">{row.upcoming}</td>
                <td className="px-3 py-2 text-green-600">{row.ok}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function StatTile({ label, value, accent }: { label: string; value: string; accent?: 'red' | 'amber' | 'green' }) {
  const color =
    accent === 'red'
      ? 'text-red-600'
      : accent === 'amber'
        ? 'text-amber-600'
        : accent === 'green'
          ? 'text-green-600'
          : 'text-slate-900'
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-2xl font-semibold ${color}`}>{value}</p>
    </div>
  )
}
