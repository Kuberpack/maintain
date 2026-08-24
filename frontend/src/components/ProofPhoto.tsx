import { useEffect, useState } from 'react'
import { fetchPhotoBlob } from '../api/photos'

export function ProofPhoto({
  url,
  alt,
  className,
  zoomable = false,
}: {
  url: string
  alt: string
  className?: string
  zoomable?: boolean
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    fetchPhotoBlob(url)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setSrc(null)
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [url])

  if (!src) {
    return <span className="text-sm text-slate-400">Photo…</span>
  }

  return (
    <>
      <button
        type="button"
        onClick={() => zoomable && setOpen(true)}
        className={zoomable ? 'block' : 'cursor-default'}
      >
        <img src={src} alt={alt} className={className ?? 'h-24 w-full rounded-md object-cover'} />
      </button>
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4"
          onClick={() => setOpen(false)}
          role="dialog"
          aria-modal="true"
        >
          <img src={src} alt={alt} className="max-h-full max-w-full rounded-md object-contain" />
        </div>
      )}
    </>
  )
}
