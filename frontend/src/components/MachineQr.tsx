import { useEffect, useState } from 'react'
import { fetchAuthenticatedBlob } from '../api/client'

export function MachineQr({ machineId, machineName }: { machineId: string; machineName: string }) {
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let objectUrl: string | null = null
    const origin = window.location.origin
    fetchAuthenticatedBlob(`/machines/${machineId}/qr?origin=${encodeURIComponent(origin)}`)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob)
        setSrc(objectUrl)
      })
      .catch(() => setError('Could not load QR'))
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [machineId])

  function handlePrint() {
    if (!src) return
    const w = window.open('', '_blank')
    if (!w) return
    w.document.write(
      `<html><head><title>QR ${machineName}</title></head><body style="text-align:center;font-family:sans-serif">
       <h1>${machineName}</h1><img src="${src}" width="280" height="280"/>
       <p>Scan to open this machine in the maintenance app</p></body></html>`,
    )
    w.document.close()
    w.focus()
    w.print()
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>
  if (!src) return <p className="text-sm text-slate-500">QR…</p>

  return (
    <div className="flex flex-col items-start gap-2">
      <img src={src} alt={`QR for ${machineName}`} className="h-32 w-32 border border-slate-200 bg-white p-1" />
      <button
        type="button"
        onClick={handlePrint}
        className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        Print QR sticker
      </button>
    </div>
  )
}
