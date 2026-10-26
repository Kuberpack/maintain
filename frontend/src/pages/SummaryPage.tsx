import { Link } from 'react-router-dom'
import { useAsync } from '../lib/useAsync'
import { listMachines } from '../api/machines'
import { listTaskTypes } from '../api/taskTypes'
import { listTaskInstances } from '../api/taskInstances'
import { getPublicConfig } from '../api/config'
import { getWeeklyReport } from '../api/reports'
import { computeDisplayStatus, isOpenWork } from '../lib/status'
import type { DisplayStatus } from '../lib/status'
import { useLocale } from '../locale/localeContext'
import { useAuth } from '../auth/useAuth'
import { ErrorState, KpiCard, LoadingState, Page, PageHeader } from '../components/ui'

export function SummaryPage() {
  const { user } = useAuth()
  const { t } = useLocale()
  const machines = useAsync(() => listMachines(), [])
  const taskTypes = useAsync(() => listTaskTypes(), [])
  const taskInstances = useAsync(() => listTaskInstances(), [])
  const config = useAsync(() => getPublicConfig(), [])
  const weekly = useAsync(() => getWeeklyReport(), [])

  const loading = machines.loading || taskTypes.loading || taskInstances.loading || config.loading
  const error = machines.error ?? taskTypes.error ?? taskInstances.error ?? config.error

  if (loading) return <LoadingState label={t.loading} />
  if (error) return <ErrorState message={error} />
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

  const roleEyebrow = user?.role === 'management' ? t.roleManagement : user?.role === 'admin' ? t.roleAdmin : t.roleSupervisor

  return (
    <Page>
      <PageHeader eyebrow={roleEyebrow} title={t.summary} subtitle={t.complianceBlurb} />

      <div className="mb-4 flex flex-wrap items-center gap-4 rounded-2xl border border-line bg-white p-4 shadow-sm">
        <ComplianceRing pct={compliancePct} label={t.compliance} />
        <p className="text-sm text-stone-600">
          <span className="font-semibold text-ink">{approvedCount}</span> {t.approved}
          <span className="mx-2 text-stone-300">·</span>
          <span className="font-semibold text-ink">{awaitingCount}</span> {t.waitingReview}
        </p>
      </div>

      <div className="mb-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label={t.overdue} value={overdueCount} tone={overdueCount ? 'bad' : 'good'} />
        <KpiCard label={t.dueSoon} value={upcomingCount} tone={upcomingCount ? 'warn' : 'good'} />
        <KpiCard label={t.onTrack} value={okCount} tone="good" />
        <KpiCard label={t.waitingReview} value={awaitingCount} tone={awaitingCount ? 'info' : 'good'} />
      </div>

      <div className="mb-6 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Shortcut to="/reports" label={t.reports} />
        <Shortcut to="/overdue" label={t.overdue} />
        <Shortcut to="/shift" label={t.shift} />
        <Shortcut to="/spares" label={t.spares} />
      </div>

      {weekly.data ? (
        <section className="mb-6">
          <h2 className="mb-2 text-sm font-bold tracking-wide text-stone-500 uppercase">
            {t.thisWeek}
            <span className="ml-2 font-medium tracking-normal text-stone-400 normal-case">
              · {weekly.data.weekStart} – {weekly.data.weekEnd}
            </span>
          </h2>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
            <KpiCard label={t.approved} value={weekly.data.approved} tone="good" />
            <KpiCard label={t.overdue} value={weekly.data.overdue} tone={weekly.data.overdue ? 'bad' : 'good'} />
            <KpiCard label={t.rejected} value={weekly.data.rejected} tone={weekly.data.rejected ? 'warn' : 'neutral'} />
            <KpiCard label={t.waitingReview} value={weekly.data.awaitingReview} tone="info" />
            <KpiCard label={t.critical} value={weekly.data.critical} tone={weekly.data.critical ? 'bad' : 'good'} />
          </div>
        </section>
      ) : null}

      <h2 className="mb-2 text-sm font-bold tracking-wide text-stone-500 uppercase">{t.perMachine}</h2>
      {perMachine.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-line bg-white px-4 py-6 text-sm text-stone-500">{t.nothingWaiting}</p>
      ) : (
        <div className="table-wrap overflow-x-auto rounded-2xl border border-line bg-white shadow-sm">
          <table className="data-table w-full min-w-[480px] text-sm">
            <thead className="bg-paper text-left text-stone-500">
              <tr>
                <th className="px-3 py-2 font-semibold">{t.machines}</th>
                <th className="px-3 py-2 font-semibold">{t.overdue}</th>
                <th className="px-3 py-2 font-semibold">{t.dueSoon}</th>
                <th className="px-3 py-2 font-semibold">{t.onTrack}</th>
              </tr>
            </thead>
            <tbody>
              {perMachine.map((row) => (
                <tr key={row.machine.id} className="border-t border-line">
                  <td className="px-3 py-3 font-semibold text-ink" data-label={t.machines}>
                    <Link to={`/machines/${row.machine.id}`} className="hover:text-brand">
                      {row.machine.name}
                    </Link>
                  </td>
                  <td className="px-3 py-3 font-semibold text-red-700" data-label={t.overdue}>
                    {row.overdue}
                  </td>
                  <td className="px-3 py-3 font-semibold text-amber-700" data-label={t.dueSoon}>
                    {row.upcoming}
                  </td>
                  <td className="px-3 py-3 font-semibold text-green-700" data-label={t.onTrack}>
                    {row.ok}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Page>
  )
}

function ComplianceRing({ pct, label }: { pct: number; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        className="grid h-16 w-16 place-items-center rounded-full"
        style={{ background: `conic-gradient(#15803d ${pct}%, #efe7de 0)` }}
        aria-hidden="true"
      >
        <div className="grid h-12 w-12 place-items-center rounded-full bg-white text-sm font-bold text-ink">{pct}%</div>
      </div>
      <div>
        <p className="text-xs font-bold tracking-wide text-stone-500 uppercase">{label}</p>
      </div>
    </div>
  )
}

function Shortcut({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="flex min-h-14 items-center justify-between rounded-2xl border border-line bg-white px-4 text-sm font-semibold text-ink shadow-sm hover:border-brand"
    >
      {label}
      <span aria-hidden="true" className="text-brand">
        →
      </span>
    </Link>
  )
}
