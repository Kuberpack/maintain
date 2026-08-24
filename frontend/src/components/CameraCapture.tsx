import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { hi } from '../lib/i18n'

interface CameraCaptureProps {
  photo: File | null
  onPhotoChange: (file: File | null) => void
  label?: string
  required?: boolean
  large?: boolean
}

export function CameraCapture({
  photo,
  onPhotoChange,
  label,
  required = false,
  large = false,
}: CameraCaptureProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  useEffect(() => {
    if (!photo) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(photo)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [photo])

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    onPhotoChange(e.target.files?.[0] ?? null)
  }

  function handleRetake() {
    onPhotoChange(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  const caption = label ?? hi.photo

  if (photo && previewUrl) {
    return (
      <div className="flex flex-col gap-2">
        <img
          src={previewUrl}
          alt="Captured proof"
          className={large ? 'h-48 w-full rounded-lg border border-slate-200 object-cover' : 'h-24 w-24 rounded-md border border-slate-200 object-cover'}
        />
        <button
          type="button"
          onClick={handleRetake}
          className="min-h-12 rounded-md border border-slate-300 px-4 py-2 text-base font-medium text-slate-700 hover:bg-slate-50"
        >
          {hi.retake}
        </button>
      </div>
    )
  }

  return (
    <label className="inline-flex min-h-16 cursor-pointer items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 bg-white px-4 py-3 text-base font-medium text-slate-800 hover:bg-slate-50">
      <span aria-hidden="true">📷</span>
      {caption}
      {required ? <span className="text-red-600">*</span> : null}
      <input ref={inputRef} type="file" accept="image/*" capture="environment" onChange={handleFileChange} className="hidden" />
    </label>
  )
}
