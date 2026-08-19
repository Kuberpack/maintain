import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, daysUntilDue } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'

export function OverduePage() {
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

  const machineById = new Map(machineList.map((m) => [m.id, m]))
  const taskTypeById = new Map(taskTypeList.map((tt) => [tt.id, tt]))

  const overdueInstances = taskInstanceList
    .filter((ti) => ti.status !== 'done' && computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays) === 'overdue')
    .sort((a, b) => a.dueDate.localeCompare(b.dueDate))

  return (
    <div className="mx-auto max-w-4xl p-4">
      <h1 className="mb-1 text-xl font-semibold text-slate-900">Overdue tasks</h1>
      <p className="mb-4 text-sm text-slate-500">{overdueInstances.length} task(s) past due, across all machines.</p>

      {overdueInstances.length === 0 ? (
        <p className="rounded-md border border-slate-200 bg-white p-4 text-sm text-slate-500">Nothing overdue.</p>
      ) : (
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-3 py-2 font-medium">Machine</th>
                <th className="px-3 py-2 font-medium">Task</th>
                <th className="px-3 py-2 font-medium">Due</th>
                <th className="px-3 py-2 font-medium">Overdue by</th>
              </tr>
            </thead>
            <tbody>
              {overdueInstances.map((instance) => {
                const taskType = taskTypeById.get(instance.taskTypeId)
                const machine = taskType ? machineById.get(taskType.machineId) : undefined
                return (
                  <tr key={instance.id} className="border-t border-slate-100">
                    <td className="px-3 py-2">
                      {machine ? (
                        <Link to={`/machines/${machine.id}`} className="font-medium text-slate-900 hover:underline">
                          {machine.name}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-3 py-2 text-slate-700">{taskType?.description ?? 'Task'}</td>
                    <td className="px-3 py-2 text-slate-700">{instance.dueDate}</td>
                    <td className="px-3 py-2">
                      <div className="flex items-center gap-2">
                        <StatusBadge status="overdue" />
                        <span className="text-slate-500">{-daysUntilDue(instance.dueDate)}d</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
