import { useState } from 'react'
import type { FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { useLocale } from '../locale/localeContext'
import { ApiError } from '../api/client'
import { BrandMark } from '../components/BrandMark'
import { LanguageToggle } from '../components/LanguageToggle'

type Mode = 'pin' | 'password'

export function LoginPage() {
  const { user, loginPin, loginPassword } = useAuth()
  const { t, locale, setLocale } = useLocale()
  const [mode, setMode] = useState<Mode>('pin')
  const [phoneNumber, setPhoneNumber] = useState('')
  const [pin, setPin] = useState('')
  const [showPin, setShowPin] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to={user.role === 'management' ? '/summary' : user.role === 'operator' ? '/today' : '/'} replace />
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      if (mode === 'pin') {
        await loginPin(phoneNumber, pin)
      } else {
        await loginPassword(email, password)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t.loginFailed)
    } finally {
      setSubmitting(false)
    }
  }

  const fieldClass =
    'min-h-14 w-full rounded-2xl border border-line bg-paper px-4 text-lg text-ink outline-none focus:border-brand focus:bg-white'

  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1.05fr)_minmax(22rem,0.95fr)]">
      <aside className="relative overflow-hidden bg-[#0A0A0C] px-5 pt-6 pb-6 text-white sm:px-10 lg:flex lg:flex-col lg:justify-between lg:px-14 lg:py-12">
        <div className="pointer-events-none absolute -top-24 -right-16 h-64 w-64 rounded-full bg-brand/30 blur-3xl" />
        <BrandMark size="md" light />
        <div className="relative mt-5 max-w-lg lg:mt-0">
          <p className="text-xs font-bold tracking-[0.22em] text-brand uppercase">Sonipat</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight lg:mt-3 lg:text-5xl">{t.loginTitle}</h1>
          <p className="mt-2 max-w-sm text-base leading-relaxed text-stone-300 lg:mt-3">{t.loginSubtitle}</p>
        </div>
        <p className="relative mt-8 hidden text-sm text-stone-500 lg:block">Kuber Paper & Pack Pvt. Ltd.</p>
      </aside>

      <main className="flex items-center justify-center bg-paper px-4 py-8 sm:px-8">
        <div className="w-full max-w-md">
          <div className="mb-5 flex justify-end">
            <LanguageToggle locale={locale} setLocale={setLocale} en={t.languageEn} hi={t.languageHi} />
          </div>

          <form
            onSubmit={handleSubmit}
            className="rounded-3xl border border-line bg-white p-5 shadow-sm sm:p-7"
          >
            <div className="mb-6 grid grid-cols-2 gap-1 rounded-2xl bg-paper p-1 text-sm font-semibold">
              <button
                type="button"
                onClick={() => setMode('pin')}
                className={`min-h-12 rounded-xl px-3 ${mode === 'pin' ? 'bg-white text-ink shadow-sm' : 'text-stone-500'}`}
              >
                {t.phonePin}
              </button>
              <button
                type="button"
                onClick={() => setMode('password')}
                className={`min-h-12 rounded-xl px-3 ${mode === 'password' ? 'bg-white text-ink shadow-sm' : 'text-stone-500'}`}
              >
                {t.emailPassword}
              </button>
            </div>

            <div className="flex flex-col gap-4">
              {mode === 'pin' ? (
                <>
                  <label className="flex flex-col gap-1.5 text-sm font-semibold text-stone-700">
                    {t.phone}
                    <input
                      type="tel"
                      inputMode="numeric"
                      autoComplete="username"
                      required
                      value={phoneNumber}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      className={fieldClass}
                    />
                  </label>
                  <label className="flex flex-col gap-1.5 text-sm font-semibold text-stone-700">
                    {t.pin}
                    <span className="relative">
                      <input
                        type={showPin ? 'text' : 'password'}
                        inputMode="numeric"
                        pattern="\d{4,6}"
                        autoComplete="current-password"
                        required
                        value={pin}
                        onChange={(e) => setPin(e.target.value)}
                        className={`${fieldClass} pr-16 tracking-[0.3em]`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPin((v) => !v)}
                        className="absolute top-1/2 right-3 min-h-10 -translate-y-1/2 px-2 text-sm font-semibold text-stone-500"
                      >
                        {showPin ? (locale === 'hi' ? 'छुपाएँ' : 'Hide') : locale === 'hi' ? 'दिखाएँ' : 'Show'}
                      </button>
                    </span>
                  </label>
                </>
              ) : (
                <>
                  <label className="flex flex-col gap-1.5 text-sm font-semibold text-stone-700">
                    {t.email}
                    <input
                      type="email"
                      autoComplete="username"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className={fieldClass}
                    />
                  </label>
                  <label className="flex flex-col gap-1.5 text-sm font-semibold text-stone-700">
                    {t.password}
                    <input
                      type="password"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className={fieldClass}
                    />
                  </label>
                </>
              )}

              {error ? (
                <p className="rounded-xl bg-red-50 px-3 py-2 text-sm font-medium text-red-700" role="alert">
                  {error}
                </p>
              ) : null}

              <button
                type="submit"
                disabled={submitting}
                className="mt-1 min-h-14 rounded-2xl bg-brand text-lg font-bold text-white hover:bg-brand-dark disabled:opacity-50"
              >
                {submitting ? t.saving : t.signIn}
              </button>
            </div>
          </form>
        </div>
      </main>
    </div>
  )
}
