import type { DisplayStatus } from '../lib/status'

const STYLES: Record<DisplayStatus, { bg: string; text: string; label: string }> = {
  overdue: { bg: '#fee2e2', text: '#991b1b', label: 'लेट / Overdue' },
  upcoming: { bg: '#fef3c7', text: '#92400e', label: 'जल्दी / Due soon' },
  ok: { bg: '#dcfce7', text: '#166534', label: 'ठीक / OK' },
  done: { bg: '#e5e7eb', text: '#374151', label: 'हो गया / Done' },
  review: { bg: '#e0e7ff', text: '#3730a3', label: 'रिव्यू / Waiting' },
  rejected: { bg: '#ffedd5', text: '#9a3412', label: 'दोबारा / Redo' },
}

export function StatusBadge({ status }: { status: DisplayStatus }) {
  const style = STYLES[status]
  return (
    <span
      className="inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-sm font-medium"
      style={{ backgroundColor: style.bg, color: style.text }}
    >
      {style.label}
    </span>
  )
}
