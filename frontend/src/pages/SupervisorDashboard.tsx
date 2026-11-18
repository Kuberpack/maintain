import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { listRepairLogs } from '../api/repairLogs'
import { getPublicConfig } from '../api/config'
import { computeDisplayStatus, daysUntilDue } from '../lib/status'
import { StatusBadge } from '../components/StatusBadge'
import { useLocale } from '../locale/localeContext'
import { useAuth } from '../auth/useAuth'
import { ErrorState, KpiCard, LoadingState, Page, PageHeader } from '../components/ui'
import type { ExceptionLevel } from '../api/types'
import type { DisplayStatus } from '../lib/status'

const RANK: Record<ExceptionLevel, number> = { critical: 0, attention: 1, none: 2 }

export function SupervisorDashboard() {
  const { user } = useAuth()
  const { t } = useLocale()
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const instances = useAsync(() => listTaskInstances(), [])
  const repairs = useAsync(() => listRepairLogs({ unresolvedOnly: true }), [])
  const config = useAsync(() => getPublicConfig(), [])

  const loading = machines.loading || taskTypes.loading || instances.loading || repairs.loading || config.loading
  const error = machines.error ?? taskTypes.error ?? instances.error ?? repairs.error ?? config.error

  if (loading) return <LoadingState label={t.loading} />
  if (error) return <ErrorState message={error} />
  if (!machines.data || !taskTypes.data || !instances.data || !config.data) return null

  const taskTypeById = new Map(taskTypes.data.map((tt) => [tt.id, tt]))
  const machineById = new Map(machines.data.map((m) => [m.id, m]))
  const cfg = config.data

  const described = instances.data.map((ti) => {
    const taskType = taskTypeById.get(ti.taskTypeId)
    const machine = taskType ? machineById.get(taskType.machineId) : undefined
    const display = computeDisplayStatus(ti.dueDate, ti.status, cfg.alertUpcomingDays, ti.reviewStatus)
    return { ti, taskType, machine, display }
  })

  const floor = described.filter(
    (row) => row.ti.status !== 'done' && (row.ti.reviewStatus === 'awaiting_review' || daysUntilDue(row.ti.dueDate) <= 0),
  )
  const late = floor.filter((row) => row.display === 'overdue' || row.display === 'rejected')
  const dueToday = floor.filter((row) => row.display === 'upcoming' || row.display === 'ok')
  const waiting = described
    .filter((row) => row.ti.reviewStatus === 'awaiting_review')
    .sort((a, b) => {
      const rank = RANK[a.ti.exceptionLevel] - RANK[b.ti.exceptionLevel]
      if (rank !== 0) return rank
      return (a.ti.completedAt ?? '').localeCompare(b.ti.completedAt ?? '')
    })
  const overdue = described
    .filter(
      (row) =>
        row.ti.status !== 'done' &&
        row.ti.reviewStatus !== 'awaiting_review' &&
        row.display === 'overdue',
    )
    .sort((a, b) => a.ti.dueDate.localeCompare(b.ti.dueDate))
  const openRepairs = repairs.data ?? []

  return (
    <Page>
      <PageHeader
        eyebrow={user?.role === 'admin' ? t.roleAdmin : t.roleSupervisor}
        title={user?.name ?? t.plantOverview}
        subtitle={t.plantOverview}
      />

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t.late} value={late.length} tone={late.length ? 'bad' : 'good'} />
        <KpiCard label={t.dueToday} value={dueToday.length} tone={dueToday.length ? 'warn' : 'good'} />
        <KpiCard label={t.review} value={waiting.length} tone={waiting.length ? 'info' : 'good'} />
        <KpiCard label={t.overdue} value={overdue.length} tone={overdue.length ? 'bad' : 'good'} />
      </div>

      {openRepairs.length > 0 ? (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3">
          <p className="font-semibold text-red-900">
            {openRepairs.length} {t.repairOpen}
          </p>
          <ul className="mt-1 text-sm text-red-800">
            {openRepairs.slice(0, 4).map((log) => (
              <li key={log.id}>
                <Link to={`/machines/${log.machineId}`} className="font-semibold underline-offset-2 hover:underline">
                  {machineById.get(log.machineId)?.name ?? t.machines}
                </Link>
                {' — '}
                {log.issueDescription}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-3">
        <Panel title={t.needsReview} href="/review" action={t.viewAll} empty={t.nothingWaiting} rows={waiting.slice(0, 4)} />
        <Panel title={t.overdue} href="/overdue" action={t.viewAll} empty={t.nothingWaiting} rows={overdue.slice(0, 4)} />
        <Panel title={t.dueToday} href="/today" action={t.viewAll} empty={t.nothingToday} rows={dueToday.slice(0, 4)} />
      </div>
    </Page>
  )
}

function Panel({
  title,
  href,
  action,
  empty,
  rows,
}: {
  title: string
  href: string
  action: string
  empty: string
  rows: Array<{
    ti: { id: string }
    taskType?: { description: string }
    machine?: { id: string; name: string }
    display: DisplayStatus
  }>
}) {
  return (
    <section className="min-w-0 rounded-2xl border border-line bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="text-base font-bold text-ink">{title}</h2>
        <Link to={href} className="text-sm font-semibold text-brand">
          {action}
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl bg-paper px-3 py-4 text-sm text-stone-500">{empty}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {rows.map((row) => (
            <li key={row.ti.id}>
              <Link
                to={row.machine ? `/machines/${row.machine.id}` : href}
                className="flex min-h-14 min-w-0 items-start justify-between gap-3 rounded-xl bg-paper px-3 py-3"
              >
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-semibold text-ink">{row.machine?.name ?? '—'}</span>
                  <span className="block truncate text-sm text-stone-600">{row.taskType?.description}</span>
                </span>
                <StatusBadge status={row.display} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
