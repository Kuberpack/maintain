import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

const LINKS = [
  { to: '/', label: 'Machines', end: true },
  { to: '/overdue', label: 'Overdue', end: false },
  { to: '/summary', label: 'Summary', end: false },
  { to: '/users', label: 'Users', end: false, roles: ['supervisor', 'management'] as const },
]

function linkClass({ isActive }: { isActive: boolean }): string {
  return `block rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
  }`
}

export function NavBar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)

  if (!user) return null

  const links = LINKS.filter((link) => !('roles' in link) || (link.roles as readonly string[]).includes(user.role))

  return (
    <nav className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <div className="flex items-center gap-6">
          <span className="font-semibold text-slate-900">Kuberpack Maintenance</span>
          <div className="hidden gap-1 sm:flex">
            {links.map((link) => (
              <NavLink key={link.to} to={link.to} className={linkClass} end={link.end}>
                {link.label}
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
