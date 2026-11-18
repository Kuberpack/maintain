export type UserRole = 'operator' | 'supervisor' | 'management' | 'admin'
export type TaskCategory = 'cleaning' | 'oiling' | 'part_replacement' | 'repair' | 'preventive'
export type TaskStatus = 'pending' | 'done' | 'overdue'
export type ReviewStatus = 'none' | 'awaiting_review' | 'approved' | 'rejected'
export type ExceptionLevel = 'none' | 'attention' | 'critical'

export interface User {
  id: string
  name: string
  role: UserRole
  email: string | null
  phoneNumber: string | null
  whatsappNumber: string | null
  createdAt: string
  createdById: string | null
  canAssignOperators: boolean
}

export type UserAuditAction = 'created' | 'deleted'

export interface UserAuditEvent {
  id: string
  action: UserAuditAction
  actorId: string | null
  actorName: string
  actorRole: UserRole
  targetUserId: string | null
  targetName: string
  targetRole: UserRole
  at: string
}

export type MachineKind = 'production' | 'utility'

export interface Machine {
  id: string
  name: string
  type: string
  location: string | null
  operatorId: string | null
  operator: { id: string; name: string } | null
  supervisorId: string | null
  supervisor: { id: string; name: string } | null
  groupName: string | null
  kind: MachineKind
  createdAt: string
}

export interface TaskType {
  id: string
  machineId: string
  category: TaskCategory
  description: string
  descriptionHi: string | null
  defaultIntervalDays: number | null
}

export interface TaskInstance {
  id: string
  taskTypeId: string
  dueDate: string
  status: TaskStatus
  completedAt: string | null
  completedBy: string | null
  notes: string | null
  rescheduledBy: string | null
  photoUrl: string | null
  exceptionPhotoUrl: string | null
  startedAt: string | null
  durationSeconds: number | null
  isFastSubmit: boolean
  reviewStatus: ReviewStatus
  reviewedBy: string | null
  reviewedAt: string | null
  reviewNotes: string | null
  exceptionLevel: ExceptionLevel
}

export interface TaskInstanceMarkDoneResponse {
  completed: TaskInstance
  next: TaskInstance | null
}

export type ChecklistItemStatus = 'ok' | 'attention' | 'critical' | 'planned'

export interface ChecklistItem {
  id: string
  taskTypeId: string
  section: string
  sectionHi: string | null
  sortOrder: number
  description: string
  descriptionHi: string | null
  requiresValue: boolean
  valueUnit: string | null
  minValue: number | null
  maxValue: number | null
}

export interface ChecklistItemResult {
  id: string
  taskInstanceId: string
  checklistItemId: string
  itemStatus: ChecklistItemStatus
  numericValue: number | null
  notes: string | null
}

export interface ChecklistItemResultInput {
  checklistItemId: string
  itemStatus: ChecklistItemStatus
  numericValue?: number | null
  notes?: string | null
}

export interface RepairLog {
  id: string
  machineId: string
  reportedAt: string
  reportedBy: string | null
  issueDescription: string
  impact: string | null
  downtimeMinutes: number | null
  resolvedAt: string | null
  resolvedBy: string | null
  resolutionNotes: string | null
}

export type RemovedPartCondition = 'worn' | 'damaged' | 'broken' | 'reusable'
export type RemovedPartStatus =
  | 'pending_decision'
  | 'in_maintenance_store'
  | 'sent_for_repair'
  | 'returned_to_stock'
  | 'scrapped'
  | 'sold'
  | 'returned_to_vendor'

export interface RemovedPartEvent {
  id: string
  status: RemovedPartStatus
  actorId: string | null
  actorName: string
  at: string
  notes: string | null
  photoUrl: string | null
  location: string | null
  vendor: string | null
  sentOn: string | null
  sparePartId: string | null
  sparePartName: string | null
  quantity: number | null
  scrapOn: string | null
  scrapQty: number | null
  scrapUnit: string | null
  scrapBuyer: string | null
  saleBuyer: string | null
  saleAmount: number | null
  saleOn: string | null
  warrantyNote: string | null
}

export interface RemovedPart {
  id: string
  partReplacementId: string
  machineId: string
  machineName: string
  partName: string
  fittedPartName: string
  replacedAt: string
  removedByName: string | null
  condition: RemovedPartCondition
  status: RemovedPartStatus
  quantity: number
  location: string | null
  notes: string | null
  vendor: string | null
  sentOn: string | null
  scrapOn: string | null
  scrapQty: number | null
  scrapUnit: string | null
  scrapBuyer: string | null
  saleBuyer: string | null
  saleAmount: number | null
  saleOn: string | null
  warrantyNote: string | null
  refurbSpareName: string | null
  creditedSparePartId: string | null
  creditedQty: number | null
  ageDays: number
  createdAt: string
  events: RemovedPartEvent[]
}

export interface RemovedPartsReport {
  byStatus: { status: RemovedPartStatus; count: number }[]
  pending: number
  pendingOlderThanDays: number
  staleDays: number
  months: {
    month: string
    scrapCount: number
    scrap: { unit: string; qty: number }[]
    resaleCount: number
    resaleAmount: number
  }[]
  machines: { machineId: string; machineName: string; replacements: number }[]
}

export interface PartReplacement {
  id: string
  machineId: string
  partName: string
  replacedAt: string
  replacedBy: string | null
  notes: string | null
  sparePartId: string | null
  quantityUsed: number | null
  removedPart: RemovedPart | null
}

export interface SparePart {
  id: string
  name: string
  itemGroup: string
  category: string
  qtyOnHand: number
  unit: string | null
  minQty: number | null
  machineId: string | null
  machineName: string | null
  lowStock: boolean
}

export interface HandoverNote {
  id: string
  machineId: string
  note: string
  createdBy: string | null
  createdAt: string
}

export type VendorSpecialty = 'mechanical' | 'electrical' | 'hydraulics' | 'oem' | 'other'

export interface VendorContact {
  id: string
  name: string
  company: string | null
  specialty: VendorSpecialty
  phoneNumber: string
  whatsappNumber: string | null
  notes: string | null
  machineId: string | null
  createdAt: string
}

export type OutputUnit = 'kg' | 'pcs'

export interface ShiftLog {
  id: string
  machineId: string
  logDate: string
  startTime: string | null
  endTime: string | null
  outputQty: number | null
  outputUnit: OutputUnit
  jobChangeCount: number | null
  wastageBoardline: number | null
  wastageMachine: number | null
  delayReason: string | null
  delayMinutes: number | null
  createdBy: string | null
  createdAt: string
  updatedAt: string
  runningMinutes: number | null
}

export interface PublicConfig {
  alertUpcomingDays: number
  alertOverdueEscalateDays: number
  alertUnreviewedHours: number
}

export interface WeeklyReport {
  weekStart: string
  weekEnd: string
  approved: number
  overdue: number
  rejected: number
  awaitingReview: number
  critical: number
  rows: Array<{
    machine: string
    task: string
    dueDate: string
    reviewStatus: string
    status: string
    exceptionLevel: string
  }>
}

export interface TokenResponse {
  accessToken: string
  tokenType: string
  user: User
}
