import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { useAsync } from '../lib/useAsync'
import { listTaskInstances } from '../api/taskInstances'
import { daysUntilDue } from '../lib/status'
import { useLocale } from '../locale/localeContext'
import type { UserRole } from '../api/types'

interface NavItem {
  to: string
  labelKey: 'today' | 'machines' | 'review' | 'overdue' | 'summary' | 'reports' | 'users' | 'profile'
  end: boolean
  roles?: readonly UserRole[]
  badge?: 'review' | 'today'
}

const LINKS: NavItem[] = [
  { to: '/today', labelKey: 'today', end: false, badge: 'today' },
  { to: '/', labelKey: 'machines', end: true, roles: ['admin', 'supervisor', 'management'] },
  { to: '/review', labelKey: 'review', end: false, roles: ['admin', 'supervisor'], badge: 'review' },
  { to: '/overdue', labelKey: 'overdue', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/summary', labelKey: 'summary', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/reports', labelKey: 'reports', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/users', labelKey: 'users', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/profile', labelKey: 'profile', end: false },
]

function linkClass({ isActive }: { isActive: boolean }): string {
  return `block rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
  }`
}

export function NavBar() {
  const { user, logout } = useAuth()
  const { t, locale, setLocale } = useLocale()
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
                {t[link.labelKey]}
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
          <LanguageToggle locale={locale} setLocale={setLocale} en={t.languageEn} hi={t.languageHi} />
          <button
            onClick={logout}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {t.logout}
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
                {t[link.labelKey]}
                {badgeFor(link) > 0 ? ` (${badgeFor(link)})` : ''}
              </NavLink>
            ))}
          </div>
          <div className="mt-3 flex items-center justify-between border-t border-slate-200 pt-3">
            <LanguageToggle locale={locale} setLocale={setLocale} en={t.languageEn} hi={t.languageHi} />
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              {t.logout}
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}

function LanguageToggle({
  locale,
  setLocale,
  en,
  hi,
}: {
  locale: 'en' | 'hi'
  setLocale: (locale: 'en' | 'hi') => void
  en: string
  hi: string
}) {
  return (
    <div className="flex rounded-md border border-slate-300 text-xs font-medium">
      <button
        type="button"
        onClick={() => setLocale('en')}
        className={`px-2 py-1 ${locale === 'en' ? 'bg-slate-900 text-white' : 'text-slate-700'}`}
      >
        {en}
      </button>
      <button
        type="button"
        onClick={() => setLocale('hi')}
        className={`px-2 py-1 ${locale === 'hi' ? 'bg-slate-900 text-white' : 'text-slate-700'}`}
      >
        {hi}
      </button>
    </div>
  )
}
