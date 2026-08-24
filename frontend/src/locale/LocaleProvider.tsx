import { useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/useAuth'
import { messages, STORAGE_KEY } from '../lib/i18n'
import type { Locale } from '../lib/i18n'
import { LocaleContext } from './localeContext'

function readStored(): Locale | null {
  const value = localStorage.getItem(STORAGE_KEY)
  if (value === 'en' || value === 'hi') return value
  return null
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [locale, setLocaleState] = useState<Locale>(() => readStored() ?? 'en')

  useEffect(() => {
    const stored = readStored()
    if (stored) {
      setLocaleState(stored)
      return
    }
    if (user?.role === 'operator') setLocaleState('hi')
    else if (user) setLocaleState('en')
  }, [user?.id, user?.role])

  function setLocale(next: Locale) {
    localStorage.setItem(STORAGE_KEY, next)
    setLocaleState(next)
  }

  const value = useMemo(
    () => ({ locale, setLocale, t: messages[locale] }),
    [locale],
  )

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}
