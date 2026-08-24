import type { ReviewStatus, TaskStatus } from '../api/types'

export type DisplayStatus = 'overdue' | 'upcoming' | 'ok' | 'done' | 'review' | 'rejected'

function startOfDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function daysUntilDue(dueDate: string, today: Date = new Date()): number {
  const due = new Date(`${dueDate}T00:00:00`)
  const diffMs = startOfDay(due).getTime() - startOfDay(today).getTime()
  return Math.round(diffMs / 86_400_000)
}

/** Live status for display. Awaiting review is not overdue even if the due
 * date has passed — the operator already submitted. */
export function computeDisplayStatus(
  dueDate: string,
  status: TaskStatus,
  upcomingDays: number,
  reviewStatus: ReviewStatus = 'none',
  today: Date = new Date(),
): DisplayStatus {
  if (reviewStatus === 'awaiting_review') return 'review'
  if (status === 'done') return 'done'
  if (reviewStatus === 'rejected') {
    const diff = daysUntilDue(dueDate, today)
    if (diff < 0) return 'overdue'
    return 'rejected'
  }
  const diff = daysUntilDue(dueDate, today)
  if (diff < 0) return 'overdue'
  if (diff <= upcomingDays) return 'upcoming'
  return 'ok'
}

const SEVERITY: Record<DisplayStatus, number> = {
  overdue: 5,
  rejected: 4,
  upcoming: 3,
  review: 2,
  ok: 1,
  done: 0,
}

export function worstStatus(statuses: DisplayStatus[]): DisplayStatus {
  if (statuses.length === 0) return 'ok'
  return statuses.reduce<DisplayStatus>((worst, s) => (SEVERITY[s] > SEVERITY[worst] ? s : worst), 'done')
}

export function isOpenWork(status: TaskStatus, reviewStatus: ReviewStatus): boolean {
  return status !== 'done' && reviewStatus !== 'awaiting_review'
}
