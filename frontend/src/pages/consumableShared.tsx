import { NavLink } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'

export const fieldClass =
  'min-h-12 w-full rounded-xl border border-line bg-white px-3 text-base text-ink outline-none focus:border-brand'

export const buttonClass =
  'inline-flex min-h-12 items-center justify-center rounded-full bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-dark disabled:opacity-50'

export const quietButtonClass =
  'inline-flex min-h-12 items-center justify-center rounded-full border border-line bg-white px-4 text-sm font-semibold text-stone-800'

const BALANCE: Record<string, { label: string; className: string }> = {
  open: { label: 'Open', className: 'bg-amber-100 text-amber-900' },
  partial: { label: 'Part returned', className: 'bg-sky-100 text-sky-900' },
  balanced: { label: 'Balanced', className: 'bg-green-100 text-green-800' },
  leakage: { label: 'LEAKAGE', className: 'bg-red-100 text-red-800' },
}

export function BalanceChip({ status }: { status: string }) {
  const tone = BALANCE[status] ?? { label: status, className: 'bg-stone-100 text-stone-700' }
  return <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-bold tracking-wide ${tone.className}`}>{tone.label}</span>
}

export function ConsumableNav() {
  const { user } = useAuth()
  if (!user) return null
  const links: { to: string; label: string; end?: boolean }[] = [{ to: '/consumables', label: 'Slips', end: true }]
  if (user.role !== 'operator') links.push({ to: '/consumables/items', label: 'Items' })
  if (user.role === 'management' || user.role === 'admin') links.push({ to: '/consumables/reports', label: 'Reports' })
  return (
    <nav className="mb-4 flex gap-2 overflow-x-auto" aria-label="Store">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) =>
            `inline-flex min-h-10 shrink-0 items-center rounded-full px-4 text-sm font-semibold ${
              isActive ? 'bg-brand text-white' : 'border border-line bg-white text-stone-700'
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  )
}
