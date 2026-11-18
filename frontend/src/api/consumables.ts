import { apiFetch, fetchAuthenticatedBlob } from './client'

export interface ConsumableItem {
  id: string
  name: string
  itemGroup: string
  partyName: string | null
  partyAddress: string | null
  contactNo: string | null
  leadTimeDays: number | null
  minStock: number
  maxStock: number | null
  rate: number
  unit: string
  qtyOnHand: number
  lowStock: boolean
  tracksEmptyCore: boolean
  coresOutstanding: number
  standardQty: number | null
  standardPer: number | null
  standardBasis: string | null
  active: boolean
}

export interface ConsumableItemInput {
  name: string
  itemGroup?: string
  partyName?: string | null
  partyAddress?: string | null
  contactNo?: string | null
  leadTimeDays?: number | null
  minStock: number
  maxStock?: number | null
  rate: number
  unit: string
  qtyOnHand?: number
  tracksEmptyCore?: boolean
  standardQty?: number | null
  standardPer?: number | null
  standardBasis?: string | null
  active?: boolean
  clearStandard?: boolean
  clearMaxStock?: boolean
}

export interface StockCount {
  id: string
  itemId: string
  bookQty: number
  countedQty: number
  variance: number
  note: string | null
  countedByName: string
  countedOn: string
}

export interface MaterialReturn {
  id: string
  qty: number
  note: string | null
  returnedByName: string
  returnedOn: string
}

export interface SlipLine {
  id: string
  lineNo: number
  itemId: string
  itemName: string
  unit: string
  rate: number
  qtyIssued: number
  qtyUsed: number | null
  qtyReturned: number
  qtyCarried: number | null
  leakageQty: number | null
  leakageValue: number | null
  balanceStatus: 'open' | 'partial' | 'balanced' | 'leakage' | string
  leakageNote: string | null
  productionQty: number | null
  expectedQty: number | null
  variancePct: number | null
  standardQty: number | null
  standardPer: number | null
  standardBasis: string | null
  coreDue: boolean
  coreReturned: boolean
  closedAt: string | null
  returns: MaterialReturn[]
}

export interface StoreSlip {
  id: string
  financialYear: string
  slipNo: number
  slipNoLabel: string
  slipDate: string
  shift: string
  department: string
  machineId: string
  machineName: string
  issuedById: string | null
  issuedByName: string
  receivedById: string | null
  receivedByName: string
  hodName: string | null
  remark: string | null
  supervisorConfirmedAt: string | null
  supervisorConfirmedName: string | null
  supervisorNote: string | null
  status: 'open' | 'closed' | string
  stale: boolean
  hasLeakage: boolean
  needsSign: boolean
  leakageQty: number
  leakageValue: number
  lines: SlipLine[]
  createdAt: string
}

export interface SlipCreated {
  slip: StoreSlip
  coreWarnings: string[]
}

export interface ShiftInfo {
  id: string
  label: string
  starts: string
  ends: string
}

export interface ConsumablePolicy {
  corePolicy: 'warn' | 'block' | string
  shifts: ShiftInfo[]
}

export interface LeakageBucket {
  key: string
  label: string
  qty: number
  valueInr: number
  variancePct: number | null
}

export interface LeakageReport {
  month: string
  totalQty: number
  totalValueInr: number
  byItem: LeakageBucket[]
  byMachine: LeakageBucket[]
  byOperator: LeakageBucket[]
  byMonth: { month: string; qty: number; valueInr: number }[]
  topItems: LeakageBucket[]
  staleSlips: {
    id: string
    slipNoLabel: string
    financialYear: string
    slipDate: string
    shift: string
    department: string
    machineName: string
    receivedByName: string
    issuedByName: string
  }[]
}

export interface DailySheet {
  month: string
  daysInMonth: number
  rows: {
    itemId: string
    itemName: string
    itemGroup: string
    partyName: string | null
    partyAddress: string | null
    contactNo: string | null
    leadTimeDays: number | null
    minStock: number
    maxStock: number | null
    rate: number
    openingStock: number
    unit: string
    days: { day: number; inward: number; consumption: number }[]
    monthInward: number
    monthConsumption: number
    closingStock: number
  }[]
}

export function getConsumablePolicy(): Promise<ConsumablePolicy> {
  return apiFetch<ConsumablePolicy>('/consumables/policy')
}

export function listConsumableItems(params?: { search?: string; lowStock?: boolean }): Promise<ConsumableItem[]> {
  const query = new URLSearchParams()
  if (params?.search) query.set('search', params.search)
  if (params?.lowStock) query.set('lowStock', 'true')
  const suffix = query.toString() ? `?${query}` : ''
  return apiFetch<ConsumableItem[]>(`/consumables/items${suffix}`)
}

export function createConsumableItem(payload: ConsumableItemInput): Promise<ConsumableItem> {
  return apiFetch<ConsumableItem>('/consumables/items', { method: 'POST', body: JSON.stringify(payload) })
}

export function updateConsumableItem(id: string, payload: Partial<ConsumableItemInput>): Promise<ConsumableItem> {
  return apiFetch<ConsumableItem>(`/consumables/items/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
}

export function receiveInward(id: string, qty: number, note?: string): Promise<ConsumableItem> {
  return apiFetch<ConsumableItem>(`/consumables/items/${id}/inward`, {
    method: 'POST',
    body: JSON.stringify({ qty, note: note || null }),
  })
}

export function recordStockCount(id: string, countedQty: number, note?: string): Promise<StockCount> {
  return apiFetch<StockCount>(`/consumables/items/${id}/counts`, {
    method: 'POST',
    body: JSON.stringify({ countedQty, note: note || null }),
  })
}

export function listSlips(): Promise<StoreSlip[]> {
  return apiFetch<StoreSlip[]>('/consumables/slips')
}

export function getSlip(id: string): Promise<StoreSlip> {
  return apiFetch<StoreSlip>(`/consumables/slips/${id}`)
}

export function createSlip(payload: {
  slipDate: string
  shift: string
  department: string
  machineId: string
  receivedById: string
  hodName?: string | null
  remark?: string | null
  lines: { itemId: string; qty: number }[]
  overrideMissingCores?: boolean
}): Promise<SlipCreated> {
  return apiFetch<SlipCreated>('/consumables/slips', { method: 'POST', body: JSON.stringify(payload) })
}

export function returnMaterial(slipId: string, lineId: string, qty: number, note?: string): Promise<StoreSlip> {
  return apiFetch<StoreSlip>(`/consumables/slips/${slipId}/lines/${lineId}/returns`, {
    method: 'POST',
    body: JSON.stringify({ qty, note: note || null }),
  })
}

export function closeSlipLine(
  slipId: string,
  lineId: string,
  payload: { qtyUsed: number; qtyReturned: number; qtyCarried: number; productionQty?: number | null; leakageNote?: string | null },
): Promise<StoreSlip> {
  return apiFetch<StoreSlip>(`/consumables/slips/${slipId}/lines/${lineId}/close`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function returnCore(slipId: string, lineId: string): Promise<StoreSlip> {
  return apiFetch<StoreSlip>(`/consumables/slips/${slipId}/lines/${lineId}/core-return`, { method: 'POST' })
}

export function confirmSlip(
  slipId: string,
  payload: { note?: string | null; lineNotes?: { lineId: string; leakageNote: string }[] },
): Promise<StoreSlip> {
  return apiFetch<StoreSlip>(`/consumables/slips/${slipId}/confirm`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getLeakageReport(month: string): Promise<LeakageReport> {
  return apiFetch<LeakageReport>(`/consumables/reports/leakage?month=${month}`)
}

export function getDailySheet(month: string): Promise<DailySheet> {
  return apiFetch<DailySheet>(`/consumables/reports/daily?month=${month}`)
}

export async function downloadConsumableExport(month: string, kind: 'daily' | 'leakage', format: 'csv' | 'xlsx'): Promise<void> {
  const blob = await fetchAuthenticatedBlob(`/consumables/reports/export?month=${encodeURIComponent(month)}&kind=${kind}&format=${format}`)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `consumables-${kind}-${month}.${format}`
  link.click()
  URL.revokeObjectURL(url)
}
