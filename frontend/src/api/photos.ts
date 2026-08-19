import { apiFetch } from './client'

export interface UploadedPhoto {
  url: string
}

export function uploadPhoto(file: File): Promise<UploadedPhoto> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<UploadedPhoto>('/photos', { method: 'POST', body: formData })
}
