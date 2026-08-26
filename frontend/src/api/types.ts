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

export interface PartReplacement {
  id: string
  machineId: string
  partName: string
  replacedAt: string
  replacedBy: string | null
  notes: string | null
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
