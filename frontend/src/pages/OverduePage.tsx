import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, daysUntilDue } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { useLocale } from '../locale/localeContext'
import { ErrorState, KpiCard, LoadingState, Page, PageHeader } from '../components/ui'

export function OverduePage() {
  const { t } = useLocale()
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const taskInstances = useAsync(() => listTaskInstances(), [])
  const config = useAsync(() => getPublicConfig(), [])

  const loading = machines.loading || taskTypes.loading || taskInstances.loading || config.loading
  const error = machines.error ?? taskTypes.error ?? taskInstances.error ?? config.error

  if (loading) return <LoadingState label={t.loading} />
  if (error) return <ErrorState message={error} />
  if (!machines.data || !taskTypes.data || !taskInstances.data || !config.data) return null

  const machineList = machines.data
  const taskTypeList = taskTypes.data
  const taskInstanceList = taskInstances.data
  const cfg = config.data

  const machineById = new Map(machineList.map((m) => [m.id, m]))
  const taskTypeById = new Map(taskTypeList.map((tt) => [tt.id, tt]))

  const overdueInstances = taskInstanceList
    .filter(
      (ti) =>
        ti.status !== 'done' &&
        ti.reviewStatus !== 'awaiting_review' &&
        computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays, ti.reviewStatus) === 'overdue',
    )
    .sort((a, b) => a.dueDate.localeCompare(b.dueDate))

  return (
    <Page width="max-w-4xl">
      <PageHeader title={t.overdue} />
      <div className="mb-5 max-w-xs">
        <KpiCard label={t.overdue} value={overdueInstances.length} tone={overdueInstances.length ? 'bad' : 'good'} />
      </div>

      {overdueInstances.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white p-6 text-base text-stone-500">{t.nothingWaiting}</p>
      ) : (
        <div className="table-wrap overflow-x-auto rounded-2xl border border-line bg-white shadow-sm">
          <table className="data-table w-full min-w-[560px] text-sm">
            <thead className="bg-paper text-left text-stone-500">
              <tr>
                <th className="px-3 py-2 font-semibold">{t.machines}</th>
                <th className="px-3 py-2 font-semibold">{t.task}</th>
                <th className="px-3 py-2 font-semibold">{t.due}</th>
                <th className="px-3 py-2 font-semibold">{t.overdueBy}</th>
              </tr>
            </thead>
            <tbody>
              {overdueInstances.map((instance) => {
                const taskType = taskTypeById.get(instance.taskTypeId)
                const machine = taskType ? machineById.get(taskType.machineId) : undefined
                return (
                  <tr key={instance.id} className="border-t border-line">
                    <td className="px-3 py-3" data-label={t.machines}>
                      {machine ? (
                        <Link to={`/machines/${machine.id}`} className="font-semibold text-ink hover:text-brand">
                          {machine.name}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="px-3 py-3 text-stone-700" data-label={t.task}>
                      {taskType?.description ?? t.task}
                    </td>
                    <td className="px-3 py-3 text-stone-700" data-label={t.due}>
                      {instance.dueDate}
                    </td>
                    <td className="px-3 py-3" data-label={t.overdueBy}>
                      <div className="flex items-center justify-end gap-2 sm:justify-start">
                        <StatusBadge status="overdue" />
                        <span className="text-stone-500">{-daysUntilDue(instance.dueDate)}d</span>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  )
}
