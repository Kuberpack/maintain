// Browser always uses same-origin /api and /uploads.
// Local `vite`: vite.config.ts proxies /api to the backend.
// Vercel: vercel.json rewrites those paths to Railway so the phone never
// talks to *.up.railway.app (blocked on some company WiFi; *.vercel.app is not).
const API_BASE = '/api'

export function resolveAssetUrl(path: string): string {
  return path
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

export async function fetchAuthenticatedBlob(path: string): Promise<Blob> {
  const token = localStorage.getItem('authToken')
  const response = await fetch(`${API_BASE}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new ApiError(`Request to ${path} failed (${response.status})`, response.status)
  }
  return response.blob()
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('authToken')
  // FormData bodies (photo upload) need the browser to set its own
  // multipart Content-Type with boundary -- forcing application/json here
  // would silently break the upload.
  const isFormData = init?.body instanceof FormData
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init?.headers,
    },
  })

  if (!response.ok) {
    let detail = `Request to ${path} failed (${response.status})`
    try {
      const body: unknown = await response.json()
      if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
        detail = body.detail
      }
    } catch {
      // response body wasn't JSON -- keep the generic message
    }
    throw new ApiError(detail, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}
