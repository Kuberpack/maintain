import type { RemovedPart, RemovedPartCondition, RemovedPartEvent, RemovedPartStatus } from '../api/types'

export const CONDITION_LABEL: Record<RemovedPartCondition, string> = {
  worn: 'Worn',
  damaged: 'Damaged',
  broken: 'Broken',
  reusable: 'Reusable',
}

export const STATUS_LABEL: Record<RemovedPartStatus, string> = {
  pending_decision: 'Pending decision',
  in_maintenance_store: 'In maintenance store',
  sent_for_repair: 'Sent for repair',
  returned_to_stock: 'Returned to stock',
  scrapped: 'Scrapped',
  sold: 'Sold',
  returned_to_vendor: 'Returned to vendor',
}

export const STATUS_ORDER: RemovedPartStatus[] = [
  'pending_decision',
  'in_maintenance_store',
  'sent_for_repair',
  'returned_to_stock',
  'scrapped',
  'sold',
  'returned_to_vendor',
]

export function isStalePending(part: Pick<RemovedPart, 'status' | 'ageDays'>, staleDays: number): boolean {
  return part.status === 'pending_decision' && part.ageDays >= staleDays
}

/** Plant wall time. Stored timestamps are UTC; the floor reads Sonipat. */
export function formatWhen(iso: string): string {
  const when = new Date(iso)
  if (Number.isNaN(when.getTime())) return iso
  return when.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function inr(amount: number): string {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 2,
  }).format(amount)
}

export function scrapText(scrap: { unit: string; qty: number }[]): string {
  if (scrap.length === 0) return '—'
  return scrap.map((row) => `${row.qty} ${row.unit}`).join(', ')
}

export function eventDetail(event: RemovedPartEvent): string {
  const bits: string[] = []
  if (event.location) bits.push(event.location)
  if (event.vendor) bits.push(event.vendor)
  if (event.sentOn) bits.push(event.sentOn)
  if (event.sparePartName) bits.push(`${event.quantity ?? ''} ${event.sparePartName}`.trim())
  if (event.scrapQty != null) bits.push(`${event.scrapQty} ${event.scrapUnit ?? ''}`.trim())
  if (event.scrapBuyer) bits.push(event.scrapBuyer)
  if (event.saleBuyer) bits.push(event.saleBuyer)
  if (event.saleAmount != null) bits.push(inr(event.saleAmount))
  if (event.warrantyNote) bits.push(event.warrantyNote)
  if (event.notes) bits.push(event.notes)
  return bits.join(' · ')
}
