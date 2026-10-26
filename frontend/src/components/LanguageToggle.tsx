import type { Locale } from '../lib/i18n'

export function LanguageToggle({
  locale,
  setLocale,
  en,
  hi,
}: {
  locale: Locale
  setLocale: (locale: Locale) => void
  en: string
  hi: string
}) {
  return (
    <div className="flex rounded-full border border-line bg-white p-0.5 text-sm font-semibold">
      <button
        type="button"
        onClick={() => setLocale('en')}
        className={`min-h-10 min-w-11 rounded-full px-3 ${locale === 'en' ? 'bg-brand text-white' : 'text-stone-600'}`}
        aria-pressed={locale === 'en'}
      >
        {en}
      </button>
      <button
        type="button"
        onClick={() => setLocale('hi')}
        className={`min-h-10 min-w-11 rounded-full px-3 ${locale === 'hi' ? 'bg-brand text-white' : 'text-stone-600'}`}
        aria-pressed={locale === 'hi'}
      >
        {hi}
      </button>
    </div>
  )
}
