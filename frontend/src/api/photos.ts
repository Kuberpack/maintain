import { apiFetch, fetchAuthenticatedBlob } from './client'

export interface UploadedPhoto {
  url: string
}

export function uploadPhoto(file: File): Promise<UploadedPhoto> {
  const formData = new FormData()
  formData.append('file', file)
  return apiFetch<UploadedPhoto>('/photos', { method: 'POST', body: formData })
}

export function photoFilename(photoUrl: string): string {
  return photoUrl.split('/').pop() ?? ''
}

export function fetchPhotoBlob(photoUrl: string): Promise<Blob> {
  return fetchAuthenticatedBlob(`/photos/files/${photoFilename(photoUrl)}`)
}
