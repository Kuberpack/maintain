import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { listRepairLogs } from '../api/repairLogs'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, worstStatus } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { CreateMachineForm } from '../components/CreateMachineForm'
import { useAuth } from '../auth/useAuth'
import { hi } from '../lib/i18n'

export function MachineListPage() {
  const { user } = useAuth()
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const taskInstances = useAsync(() => listTaskInstances(), [])
  const repairs = useAsync(() => listRepairLogs({ unresolvedOnly: true }), [])
  const config = useAsync(() => getPublicConfig(), [])

  const loading = machines.loading || taskTypes.loading || taskInstances.loading || repairs.loading || config.loading
  const error = machines.error ?? taskTypes.error ?? taskInstances.error ?? repairs.error ?? config.error

  if (loading) return <p className="p-6 text-slate-500">Loading machines…</p>
  if (error) return <p className="p-6 text-red-600">{error}</p>
  if (!machines.data || !taskTypes.data || !taskInstances.data || !config.data) return null

  const machineList = machines.data
  const taskTypeList = taskTypes.data
  const taskInstanceList = taskInstances.data
  const cfg = config.data
  const openRepairIds = new Set((repairs.data ?? []).map((r) => r.machineId))

  const taskTypeToMachine = new Map(taskTypeList.map((tt) => [tt.id, tt.machineId]))

  return (
    <div className="mx-auto max-w-5xl p-4">
      <h1 className="mb-4 text-xl font-semibold text-slate-900">Machines</h1>
      {(user?.role === 'supervisor' || user?.role === 'admin') && (
        <CreateMachineForm onCreated={() => void machines.refetch()} />
      )}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {machineList.map((machine) => {
          const activeStatuses = taskInstanceList
            .filter((ti) => taskTypeToMachine.get(ti.taskTypeId) === machine.id && ti.status !== 'done')
            .map((ti) => computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays, ti.reviewStatus))
          const status = worstStatus(activeStatuses)
          const hasRepair = openRepairIds.has(machine.id)

          return (
            <Link
              key={machine.id}
              to={`/machines/${machine.id}`}
              className="flex items-start justify-between gap-2 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-slate-300 hover:shadow"
            >
              <div>
                <h2 className="font-medium text-slate-900">{machine.name}</h2>
                <p className="text-sm text-slate-500">
                  {machine.type}
                  {machine.location ? ` · ${machine.location}` : ''}
                </p>
                {hasRepair && <p className="mt-1 text-sm font-medium text-red-700">{hi.repairOpen}</p>}
              </div>
              <StatusBadge status={status} />
            </Link>
          )
        })}
      </div>
    </div>
  )
}
