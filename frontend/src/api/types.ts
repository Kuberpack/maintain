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
}

export interface Machine {
  id: string
  name: string
  type: string
  location: string | null
  createdAt: string
}

export interface TaskType {
  id: string
  machineId: string
  category: TaskCategory
  description: string
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
  sortOrder: number
  description: string
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
