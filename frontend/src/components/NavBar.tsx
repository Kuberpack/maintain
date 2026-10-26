import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { useAsync } from '../lib/useAsync'
import { listTaskInstances } from '../api/taskInstances'
import { daysUntilDue } from '../lib/status'
import { useLocale } from '../locale/localeContext'
import { BrandMark } from './BrandMark'
import { LanguageToggle } from './LanguageToggle'
import type { UserRole } from '../api/types'

interface NavItem {
  to: string
  labelKey:
    | 'home'
    | 'today'
    | 'machines'
    | 'review'
    | 'overdue'
    | 'summary'
    | 'reports'
    | 'users'
    | 'profile'
    | 'directory'
    | 'shift'
    | 'spares'
    | 'removedParts'
  end: boolean
  roles?: readonly UserRole[]
  badge?: 'review' | 'today'
}

const LINKS: NavItem[] = [
  { to: '/', labelKey: 'home', end: true, roles: ['admin', 'supervisor'] },
  { to: '/today', labelKey: 'today', end: false, badge: 'today' },
  { to: '/machines', labelKey: 'machines', end: true, roles: ['admin', 'supervisor', 'management'] },
  { to: '/spares', labelKey: 'spares', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/removed', labelKey: 'removedParts', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/review', labelKey: 'review', end: false, roles: ['admin', 'supervisor'], badge: 'review' },
  { to: '/shift', labelKey: 'shift', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/overdue', labelKey: 'overdue', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/summary', labelKey: 'summary', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/reports', labelKey: 'reports', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/users', labelKey: 'users', end: false, roles: ['admin', 'supervisor', 'management'] },
  { to: '/directory', labelKey: 'directory', end: false },
  { to: '/profile', labelKey: 'profile', end: false },
]

const DESKTOP_PRIMARY: Record<UserRole, string[]> = {
  operator: ['/today', '/directory', '/profile'],
  supervisor: ['/', '/today', '/review', '/overdue', '/machines', '/removed'],
  management: ['/summary', '/reports', '/overdue', '/machines', '/removed'],
  admin: ['/', '/today', '/review', '/machines', '/overdue'],
}

const MOBILE_TABS: Record<UserRole, string[]> = {
  operator: ['/today', '/directory', '/profile'],
  supervisor: ['/', '/review', '/overdue', '/machines'],
  management: ['/summary', '/reports', '/overdue', '/machines'],
  admin: ['/', '/review', '/today', '/machines'],
}

function isCurrent(link: NavItem, pathname: string): boolean {
  if (link.end) return pathname === link.to
  return pathname === link.to || pathname.startsWith(`${link.to}/`)
}

function roleLabel(role: UserRole, t: { roleOperator: string; roleSupervisor: string; roleManagement: string; roleAdmin: string }): string {
  if (role === 'operator') return t.roleOperator
  if (role === 'supervisor') return t.roleSupervisor
  if (role === 'management') return t.roleManagement
  return t.roleAdmin
}

export function NavBar() {
  const { user, logout } = useAuth()
  const { t, locale, setLocale } = useLocale()
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
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

  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname])

  if (!user) return null

  const reviewCount = reviewQueue.data?.length ?? 0
  const todayCount =
    todayWork.data?.filter((ti) => ti.status !== 'done' && ti.reviewStatus !== 'awaiting_review' && daysUntilDue(ti.dueDate) <= 0)
      .length ?? 0

  const links = LINKS.filter((link) => !link.roles || link.roles.includes(user.role))
  const ordered = (paths: string[]) =>
    paths.flatMap((path) => {
      const link = links.find((item) => item.to === path)
      return link ? [link] : []
    })
  const desktopPrimary = ordered(DESKTOP_PRIMARY[user.role])
  const desktopMore = links.filter((link) => !DESKTOP_PRIMARY[user.role].includes(link.to))
  const mobileTabs = ordered(MOBILE_TABS[user.role])
  const mobileMore = links.filter((link) => !MOBILE_TABS[user.role].includes(link.to))
  const moreActive = mobileMore.some((link) => isCurrent(link, location.pathname))

  function badgeFor(link: NavItem): number {
    if (link.badge === 'review') return reviewCount
    if (link.badge === 'today' && user?.role === 'operator') return todayCount
    return 0
  }

  return (
    <header className="app-nav sticky top-0 z-30 border-b border-line bg-white/95 backdrop-blur">
      {moreOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-20 hidden cursor-default lg:block"
          aria-label={t.close}
          onClick={() => setMoreOpen(false)}
        />
      ) : null}
      <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-2.5 sm:px-6">
        <NavLink to="/" className="min-w-0 shrink-0" aria-label="Kuber Pack">
          <BrandMark size="sm" subtitle={locale === 'hi' ? 'रखरखाव' : 'Maintenance'} />
        </NavLink>

        <nav className="ml-2 hidden min-w-0 flex-1 items-center gap-1 lg:flex" aria-label="Primary">
          {desktopPrimary.map((link) => (
            <DesktopLink key={link.to} link={link} label={t[link.labelKey]} count={badgeFor(link)} />
          ))}
          {desktopMore.length > 0 ? (
            <div className="relative">
              <button
                type="button"
                className={`inline-flex min-h-10 items-center gap-1 rounded-full px-3 text-sm font-semibold ${
                  desktopMore.some((link) => isCurrent(link, location.pathname))
                    ? 'bg-brand text-white'
                    : 'text-stone-700 hover:bg-paper'
                }`}
                aria-expanded={moreOpen}
                onClick={() => setMoreOpen((open) => !open)}
              >
                {t.more}
                <Caret />
              </button>
              {moreOpen ? (
                <div className="absolute top-12 left-0 z-40 w-56 rounded-2xl border border-line bg-white p-2 shadow-lg">
                  {desktopMore.map((link) => (
                    <NavLink
                      key={link.to}
                      to={link.to}
                      end={link.end}
                      className={({ isActive }) =>
                        `flex min-h-11 items-center justify-between rounded-xl px-3 text-sm font-semibold ${
                          isActive ? 'bg-brand text-white' : 'text-stone-800 hover:bg-paper'
                        }`
                      }
                    >
                      <span>{t[link.labelKey]}</span>
                      {badgeFor(link) > 0 ? <Count n={badgeFor(link)} /> : null}
                    </NavLink>
                  ))}
                </div>
              ) : null}
            </div>
          ) : null}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <span className="hidden max-w-48 truncate text-right text-sm text-stone-600 xl:block">
            <span className="font-semibold text-ink">{user.name}</span>
            <span className="text-stone-400"> · {roleLabel(user.role, t)}</span>
          </span>
          <LanguageToggle locale={locale} setLocale={setLocale} en={t.languageEn} hi={t.languageHi} />
          <button
            type="button"
            onClick={logout}
            aria-label={t.logout}
            className="inline-flex min-h-10 items-center rounded-full border border-line px-3 text-sm font-semibold text-stone-700 hover:bg-paper"
          >
            {t.logout}
          </button>
        </div>
      </div>

      <nav
        className="app-nav fixed inset-x-0 bottom-0 z-30 border-t border-line bg-white lg:hidden"
        style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
        aria-label="Primary"
      >
        <ul
          className="mx-auto grid max-w-lg"
          style={{ gridTemplateColumns: `repeat(${mobileTabs.length + (mobileMore.length > 0 ? 1 : 0)}, minmax(0, 1fr))` }}
        >
          {mobileTabs.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                end={link.end}
                className={({ isActive }) =>
                  `flex min-h-[4.5rem] w-full min-w-0 flex-col items-center justify-center gap-0.5 px-1 text-[11px] leading-tight font-semibold ${
                    isActive ? 'text-brand' : 'text-stone-500'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <span className="relative">
                      <NavIcon name={link.labelKey} active={isActive} />
                      {badgeFor(link) > 0 ? (
                        <span className="absolute -top-1.5 -right-2 grid min-w-4 place-items-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white">
                          {badgeFor(link)}
                        </span>
                      ) : null}
                    </span>
                    <span className="w-full text-center leading-tight">{t[link.labelKey]}</span>
                  </>
                )}
              </NavLink>
            </li>
          ))}
          {mobileMore.length > 0 ? (
            <li>
              <button
                type="button"
                onClick={() => setMoreOpen(true)}
                className={`flex min-h-[4.5rem] w-full min-w-0 flex-col items-center justify-center gap-0.5 px-1 text-[11px] leading-tight font-semibold ${
                  moreActive ? 'text-brand' : 'text-stone-500'
                }`}
                aria-expanded={moreOpen}
              >
                <NavIcon name="more" active={moreActive} />
                {t.more}
              </button>
            </li>
          ) : null}
        </ul>
      </nav>

      {moreOpen && mobileMore.length > 0 ? (
        <div className="fixed inset-0 z-40 lg:hidden" role="presentation">
          <button
            type="button"
            className="absolute inset-0 bg-ink/40"
            aria-label={t.close}
            onClick={() => setMoreOpen(false)}
          />
          <div
            role="dialog"
            aria-label={t.more}
            className="absolute inset-x-0 bottom-0 rounded-t-3xl bg-white px-4 pt-3 shadow-2xl"
            style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 1rem)' }}
          >
            <div className="mx-auto mb-3 h-1.5 w-10 rounded-full bg-stone-200" />
            <p className="mb-2 px-1 text-sm font-semibold text-stone-500">
              {user.name} · {roleLabel(user.role, t)}
            </p>
            <ul className="flex flex-col">
              {mobileMore.map((link) => (
                <li key={link.to}>
                  <NavLink
                    to={link.to}
                    end={link.end}
                    className={({ isActive }) =>
                      `flex min-h-14 items-center justify-between rounded-2xl px-3 text-base font-semibold ${
                        isActive ? 'bg-brand text-white' : 'text-ink'
                      }`
                    }
                  >
                    <span className="inline-flex items-center gap-3">
                      <NavIcon name={link.labelKey} />
                      {t[link.labelKey]}
                    </span>
                    {badgeFor(link) > 0 ? <Count n={badgeFor(link)} /> : null}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        </div>
      ) : null}
    </header>
  )
}

function DesktopLink({ link, label, count }: { link: NavItem; label: string; count: number }) {
  return (
    <NavLink
      to={link.to}
      end={link.end}
      className={({ isActive }) =>
        `inline-flex min-h-10 items-center gap-1.5 rounded-full px-3 text-sm font-semibold ${
          isActive ? 'bg-brand text-white' : 'text-stone-700 hover:bg-paper'
        }`
      }
    >
      {label}
      {count > 0 ? <Count n={count} /> : null}
    </NavLink>
  )
}

function Count({ n }: { n: number }) {
  return (
    <span className="inline-flex min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-xs font-bold text-white">
      {n}
    </span>
  )
}

function Caret() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" fill="none">
      <path d="M2.5 4.5 6 8l3.5-3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  )
}

function NavIcon({ name, active = false }: { name: string; active?: boolean }) {
  const stroke = active ? '#e0561b' : 'currentColor'
  const common = { width: 22, height: 22, viewBox: '0 0 24 24', fill: 'none', 'aria-hidden': true as const }
  if (name === 'home') {
    return (
      <svg {...common}>
        <path d="M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-9.5Z" stroke={stroke} strokeWidth="1.8" strokeLinejoin="round" />
      </svg>
    )
  }
  if (name === 'today') {
    return (
      <svg {...common}>
        <rect x="4" y="5" width="16" height="15" rx="2" stroke={stroke} strokeWidth="1.8" />
        <path d="M8 3.5V7M16 3.5V7M4 10h16" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'review') {
    return (
      <svg {...common}>
        <path d="M8 12.5 11 15.5 16.5 9" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <rect x="4" y="4" width="16" height="16" rx="3" stroke={stroke} strokeWidth="1.8" />
      </svg>
    )
  }
  if (name === 'overdue') {
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="8" stroke={stroke} strokeWidth="1.8" />
        <path d="M12 8v4.5L15 15" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'machines') {
    return (
      <svg {...common}>
        <rect x="3" y="7" width="18" height="11" rx="2" stroke={stroke} strokeWidth="1.8" />
        <path d="M8 7V5h8v2M8 12h.01M12 12h.01M16 12h.01" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'summary' || name === 'reports') {
    return (
      <svg {...common}>
        <path d="M5 19V10M10 19V5M15 19v-7M20 19V8" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'directory') {
    return (
      <svg {...common}>
        <path d="M8 4h8l3 3v13H8a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z" stroke={stroke} strokeWidth="1.8" />
        <path d="M9 12h6M9 16h4" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'profile' || name === 'users') {
    return (
      <svg {...common}>
        <circle cx="12" cy="9" r="3" stroke={stroke} strokeWidth="1.8" />
        <path d="M6 19c.8-2.5 3-4 6-4s5.2 1.5 6 4" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    )
  }
  if (name === 'more') {
    return (
      <svg {...common}>
        <circle cx="6" cy="12" r="1.4" fill={stroke} />
        <circle cx="12" cy="12" r="1.4" fill={stroke} />
        <circle cx="18" cy="12" r="1.4" fill={stroke} />
      </svg>
    )
  }
  if (name === 'removedParts') {
    return (
      <svg {...common}>
        <path d="M4 8h16v10a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8Z" stroke={stroke} strokeWidth="1.8" />
        <path d="M8 8V6a4 4 0 0 1 8 0v2M12 12v5M9.5 14.5 12 12l2.5 2.5" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    )
  }
  return (
    <svg {...common}>
      <circle cx="12" cy="12" r="7" stroke={stroke} strokeWidth="1.8" />
    </svg>
  )
}
