// Unset in local dev: requests go through the relative /api and /uploads
// paths that vite.config.ts's dev-server proxy forwards to VITE_BACKEND_URL,
// stripping /api before hitting the backend's actual (unprefixed) routes.
// There's no such proxy in a production build (e.g. Vercel) -- set
// VITE_API_BASE_URL to the deployed backend's real origin (no trailing
// slash, no /api suffix: the backend mounts its routes at the root, see
// backend/app/main.py) so requests go straight there instead.
const API_ORIGIN = import.meta.env.VITE_API_BASE_URL as string | undefined
const API_BASE = API_ORIGIN ? API_ORIGIN : '/api'

// For asset paths returned directly by the API (currently just photoUrl,
// e.g. "/uploads/xxx.jpg") rather than routed through apiFetch below --
// these need the same origin, but never an /api prefix, matching the
// backend's separate (non-/api) static-files mount.
export function resolveAssetUrl(path: string): string {
  return API_ORIGIN ? `${API_ORIGIN}${path}` : path
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
