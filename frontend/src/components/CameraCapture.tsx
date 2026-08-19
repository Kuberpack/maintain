import { useEffect, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'

interface CameraCaptureProps {
  photo: File | null
  onPhotoChange: (file: File | null) => void
}

/** Camera-only photo capture, no gallery picker: `capture="environment"`
 * asks mobile browsers to open the camera directly rather than a file
 * chooser, so a proof-of-completion photo can't just be an old one picked
 * from the gallery. Standalone and reusable -- doesn't know about
 * task_instances or mark-done; the caller wires that up. */
export function CameraCapture({ photo, onPhotoChange }: CameraCaptureProps) {
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

  if (photo && previewUrl) {
    return (
      <div className="flex items-center gap-2">
        <img src={previewUrl} alt="Captured proof of completion" className="h-10 w-10 rounded-md border border-slate-200 object-cover" />
        <button
          type="button"
          onClick={handleRetake}
          className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Retake photo
        </button>
      </div>
    )
  }

  return (
    <label className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
      <span aria-hidden="true">📷</span>
      Take photo
      <input ref={inputRef} type="file" accept="image/*" capture="environment" onChange={handleFileChange} className="hidden" />
    </label>
  )
}
