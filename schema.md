# Schema — Machine Maintenance & Cleaning Tracker

Draft only — subject to change once Phase 1 begins.

## `users`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| name | text | |
| role | enum | operator / supervisor / management |
| email | text | for alerts |
| whatsapp_number | text | for alerts |
| created_at | timestamptz | |

## `machines`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| name | text | e.g. "Corrugator 1" |
| type | text | e.g. corrugator, printer, folder-gluer, laminator, die-cutter |
| location | text | plant/section |
| created_at | timestamptz | |

## `task_types`
Defines the recurring task templates per machine.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| category | enum | cleaning / oiling / part_replacement / repair / preventive |
| description | text | e.g. "Daily Preventive Maintenance" |
| default_interval_days | int | null for repair (event-driven, not scheduled) |

## `checklist_items`
Inspection points on a preventive (or other) task type. Completing a `task_instance` of that type requires a result for every item.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| task_type_id | uuid, FK → task_types.id | |
| section | text | grouping, e.g. "Single Facer" |
| sort_order | int | display order |
| description | text | inspection point |
| requires_value | bool | if true, a numeric reading is required |
| value_unit | text | e.g. bar, °C; null when not measured |

## `checklist_item_results`
Per-run status for one inspection point.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| task_instance_id | uuid, FK → task_instances.id | |
| checklist_item_id | uuid, FK → checklist_items.id | |
| item_status | enum | ok / attention / critical / planned (GREEN/YELLOW/RED/BLUE) |
| numeric_value | float | optional reading |
| notes | text | |

Unique on `(task_instance_id, checklist_item_id)`.

## `task_instances`
Each scheduled/actual occurrence of a task — this is the log + schedule combined.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| task_type_id | uuid, FK → task_types.id | |
| due_date | date | computed from last completion + interval, or manually set |
| status | enum | pending / done / overdue |
| completed_at | timestamptz | null until done |
| completed_by | uuid, FK → users.id | null until done |
| notes | text | free-text notes on completion |
| rescheduled_by | uuid, FK → users.id | null unless supervisor manually overrode |
| photo_url | text | optional, for proof-of-completion (open question) |

## `part_replacements`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| part_name | text | |
| replaced_at | date | |
| replaced_by | uuid, FK → users.id | |
| notes | text | reason/condition of old part |

## `repair_logs`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| reported_at | timestamptz | |
| reported_by | uuid, FK → users.id | |
| issue_description | text | |
| downtime_minutes | int | |
| resolved_at | timestamptz | null until resolved |
| resolved_by | uuid, FK → users.id | |
| resolution_notes | text | |

## Relationships
- `machines` 1—N `task_types` 1—N `task_instances`
- `task_types` 1—N `checklist_items`
- `task_instances` 1—N `checklist_item_results`
- `machines` 1—N `part_replacements`
- `machines` 1—N `repair_logs`
- `users` 1—N `task_instances` (as completer/rescheduler), `part_replacements`, `repair_logs`
