import type { ReactNode } from 'react'

export function Page({ children, width = 'max-w-6xl' }: { children: ReactNode; width?: string }) {
  return <main className={`mx-auto w-full ${width} px-4 pt-5 pb-6 sm:px-6 lg:pt-7`}>{children}</main>
}

export function PageHeader({
  eyebrow,
  title,
  subtitle,
  actions,
}: {
  eyebrow?: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <header className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        {eyebrow ? (
          <p className="mb-1 text-xs font-bold tracking-[0.16em] text-brand uppercase">{eyebrow}</p>
        ) : null}
        <h1 className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{title}</h1>
        {subtitle ? <p className="mt-1 max-w-2xl text-sm text-stone-600 sm:text-base">{subtitle}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  )
}

const TONE: Record<string, string> = {
  neutral: 'text-ink',
  bad: 'text-red-700',
  warn: 'text-amber-700',
  good: 'text-green-700',
  info: 'text-indigo-700',
  brand: 'text-brand',
}

const DOT: Record<string, string> = {
  neutral: 'bg-stone-400',
  bad: 'bg-red-600',
  warn: 'bg-amber-500',
  good: 'bg-green-600',
  info: 'bg-indigo-500',
  brand: 'bg-brand',
}

export function KpiCard({
  label,
  value,
  tone = 'neutral',
  hint,
}: {
  label: string
  value: string | number
  tone?: keyof typeof TONE
  hint?: string
}) {
  return (
    <div className="rounded-2xl border border-line bg-white px-4 py-3 shadow-sm">
      <div className="flex items-center gap-2">
        <span className={`h-2 w-2 rounded-full ${DOT[tone]}`} aria-hidden="true" />
        <p className="text-xs font-bold tracking-wide text-stone-500 uppercase">{label}</p>
      </div>
      <p className={`mt-2 text-3xl font-bold tracking-tight tabular-nums ${TONE[tone]}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-stone-500">{hint}</p> : null}
    </div>
  )
}

export function LoadingState({ label }: { label: string }) {
  return (
    <Page>
      <div className="flex items-center gap-3 rounded-2xl border border-line bg-white px-4 py-6 text-stone-500 shadow-sm">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent" aria-hidden="true" />
        <p className="text-base">{label}</p>
      </div>
    </Page>
  )
}

export function ErrorState({ message }: { message: string }) {
  return (
    <Page>
      <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-4 text-base text-red-700">{message}</p>
    </Page>
  )
}

export function EmptyState({ title, body }: { title: string; body?: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-white px-4 py-8 text-center">
      <p className="text-lg font-semibold text-ink">{title}</p>
      {body ? <p className="mt-1 text-sm text-stone-500">{body}</p> : null}
    </div>
  )
}
