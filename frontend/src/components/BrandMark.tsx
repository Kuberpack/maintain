type Size = 'sm' | 'md' | 'lg'

const IMG: Record<Size, string> = {
  sm: 'h-8 w-6',
  md: 'h-10 w-8',
  lg: 'h-16 w-12',
}

const WORD: Record<Size, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-3xl',
}

/**
 * Official mark from https://www.kuberpack.com/kuber-logo-mark.png
 * (the same file the company site uses in the header). The words beside
 * it are set in type, matching the site, so they can be swapped if a
 * horizontal logo file is provided later.
 */
export function BrandMark({
  size = 'md',
  light = false,
  subtitle,
}: {
  size?: Size
  light?: boolean
  subtitle?: string
}) {
  return (
    <span className="inline-flex min-w-0 items-center gap-2.5">
      <img
        src="/brand/kuber-logo-mark.png"
        alt=""
        width={94}
        height={120}
        className={`${IMG[size]} shrink-0 rounded-md bg-[#1a1612] object-contain`}
      />
      <span className="flex min-w-0 flex-col leading-none">
        <span className={`font-black tracking-tight ${WORD[size]} ${light ? 'text-white' : 'text-ink'}`}>KUBER</span>
        <span
          className={`mt-1 font-bold tracking-[0.16em] text-brand ${size === 'lg' ? 'text-xs' : 'text-[9px]'}`}
        >
          PAPER & PACK
        </span>
        {subtitle ? (
          <span className={`mt-1 hidden truncate text-xs font-medium sm:block ${light ? 'text-stone-400' : 'text-stone-500'}`}>
            {subtitle}
          </span>
        ) : null}
      </span>
    </span>
  )
}
