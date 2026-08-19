import type { TaskStatus } from '../api/types'

export type DisplayStatus = 'overdue' | 'upcoming' | 'ok' | 'done'

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function daysUntilDue(dueDate: string, today: Date = new Date()): number {
  const due = new Date(`${dueDate}T00:00:00`)
  const diffMs = startOfDay(due).getTime() - startOfDay(today).getTime()
  return Math.round(diffMs / 86_400_000)
}

/** Live status for display, computed from due_date rather than trusting the
 * stored `status` column -- that column is only updated by the daily
 * scheduler job, which can be up to 24h stale. */
export function computeDisplayStatus(
  dueDate: string,
  status: TaskStatus,
  upcomingDays: number,
  today: Date = new Date(),
): DisplayStatus {
  if (status === 'done') return 'done'
  const diff = daysUntilDue(dueDate, today)
  if (diff < 0) return 'overdue'
  if (diff <= upcomingDays) return 'upcoming'
  return 'ok'
}

const SEVERITY: Record<DisplayStatus, number> = { overdue: 3, upcoming: 2, ok: 1, done: 0 }

export function worstStatus(statuses: DisplayStatus[]): DisplayStatus {
  if (statuses.length === 0) return 'ok'
  return statuses.reduce<DisplayStatus>((worst, s) => (SEVERITY[s] > SEVERITY[worst] ? s : worst), 'done')
}
