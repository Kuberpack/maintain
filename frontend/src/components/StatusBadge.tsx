import type { DisplayStatus } from '../lib/status'

const STYLES: Record<DisplayStatus, { bg: string; text: string; label: string }> = {
  overdue: { bg: '#fee2e2', text: '#991b1b', label: 'Overdue' },
  upcoming: { bg: '#fef3c7', text: '#92400e', label: 'Due soon' },
  ok: { bg: '#dcfce7', text: '#166534', label: 'OK' },
  done: { bg: '#e5e7eb', text: '#374151', label: 'Done' },
}

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const style = STYLES[status]
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: style.bg, color: style.text }}
    >
      {style.label}
    </span>
  )
}
