import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { useAsync } from '../lib/useAsync'
import { listTaskInstances } from '../api/taskInstances'
import { daysUntilDue } from '../lib/status'
import type { UserRole } from '../api/types'

interface NavItem {
  to: string
  label: string
  end: boolean
  roles?: readonly UserRole[]
  badge?: 'review' | 'today'
}

const LINKS: NavItem[] = [
  { to: '/today', label: 'Today', end: false, badge: 'today' },
  { to: '/', label: 'Machines', end: true },
  { to: '/review', label: 'Review', end: false, roles: ['admin', 'supervisor'], badge: 'review' },
  { to: '/overdue', label: 'Overdue', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/summary', label: 'Summary', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/reports', label: 'Reports', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/users', label: 'Users', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/profile', label: 'My Profile', end: false },
]

function linkClass({ isActive }: { isActive: boolean }): string {
  return `block rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
  }`
}

export function NavBar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const reviewQueue = useAsync(
    () =>
      user?.role === 'supervisor' || user?.role === 'admin'
        ? listTaskInstances({ reviewStatus: 'awaiting_review' })
        : Promise.resolve([]),
    [user?.role],
  )
  const todayWork = useAsync(
    () => (user?.role === 'operator' ? listTaskInstances() : Promise.resolve([])),
    [user?.role],
  )

  if (!user) return null

  const reviewCount = reviewQueue.data?.length ?? 0
  const todayCount =
    todayWork.data?.filter((ti) => ti.status !== 'done' && ti.reviewStatus !== 'awaiting_review' && daysUntilDue(ti.dueDate) <= 0)
      .length ?? 0

  const links = LINKS.filter((link) => !link.roles || link.roles.includes(user.role))

  function badgeFor(link: NavItem): number {
    if (link.badge === 'review') return reviewCount
    if (link.badge === 'today' && user?.role === 'operator') return todayCount
    return 0
  }

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="font-semibold text-slate-900">Kuberpack Maintenance</span>
          <div className="hidden gap-1 sm:flex">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} className={linkClass} end={link.end}>
                {link.label}
                {badgeFor(link) > 0 ? (
                  <span className="ml-1 inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-xs text-white">
                    {badgeFor(link)}
                  </span>
                ) : null}
              </NavLink>
            ))}
          </div>
        </div>

        <div className="hidden items-center gap-3 sm:flex">
          <span className="text-sm text-slate-600">
            {user.name} · {user.role}
          </span>
          <button
            onClick={logout}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Log out
          </button>
        </div>

        <button
          className="rounded-md p-2 text-slate-700 hover:bg-slate-100 sm:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
        >
          <span aria-hidden="true">☰</span>
        </button>
      </div>

      {open && (
        <div className="border-t border-slate-200 px-4 py-3 sm:hidden">
          <div className="flex flex-col gap-1">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} className={linkClass} end={link.end} onClick={() => setOpen(false)}>
                {link.label}
                {badgeFor(link) > 0 ? ` (${badgeFor(link)})` : ''}
              </NavLink>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
            <span className="text-sm text-slate-600">
              {user.name} · {user.role}
            </span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Log out
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
