import { apiFetch, fetchAuthenticatedBlob } from './client'
import type { WeeklyReport } from './types'

export function getWeeklyReport(): Promise<WeeklyReport> {
  return apiFetch<WeeklyReport>('/reports/weekly')
}

export function downloadWeeklyPdf(): Promise<Blob> {
  return fetchAuthenticatedBlob('/reports/weekly.pdf')
}
