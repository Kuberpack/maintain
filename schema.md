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
| created_by_id | uuid, FK → users.id, nullable | which supervisor/admin added this person. SET NULL on creator delete. |
| can_assign_operators | boolean, default false | at most one supervisor. That person assigns operators plant-wide. Other supervisors only see units dedicated to them. |

## `machines`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| name | text | e.g. "Corrugator 1" |
| type | text | e.g. corrugator, printer, folder-gluer, laminator, die-cutter |
| location | text | plant/section |
| operator_id | uuid, FK → users.id, nullable | dedicated operator for this unit. One person may own several rows. SET NULL on user delete. |
| supervisor_id | uuid, FK → users.id, nullable | dedicated supervisor for this unit (reassignable). Null on plant equipment with no dedicated supervisor. SET NULL on user delete. |
| group_name | text, nullable | display group, e.g. "Fully Automatic Corrugation Machine" |
| kind | text | `production` or `utility` |
| created_at | timestamptz | |

## `task_types`
Defines the recurring task templates per machine.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| category | enum | cleaning / oiling / part_replacement / repair / preventive |
| description | text | e.g. "Daily Preventive Maintenance" |
| description_hi | text | optional Hindi label; UI falls back to description |
| default_interval_days | int | null for repair (event-driven, not scheduled) |

## `checklist_items`
Inspection points on a preventive (or other) task type. Completing a `task_instance` of that type requires a result for every item.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| task_type_id | uuid, FK → task_types.id | |
| section | text | grouping, e.g. "Single Facer" |
| section_hi | text | optional Hindi section label |
| sort_order | int | display order |
| description | text | inspection point |
| description_hi | text | optional Hindi inspection text |
| requires_value | bool | if true, a numeric reading is required |
| value_unit | text | e.g. bar, °C; null when not measured |
| min_value | float | optional expected minimum; out of range becomes Attention |
| max_value | float | optional expected maximum |

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
| completed_at | timestamptz | operator submit time (null until submitted) |
| completed_by | uuid, FK → users.id | null until submitted |
| notes | text | free-text notes on completion |
| rescheduled_by | uuid, FK → users.id | null unless supervisor manually overrode |
| photo_url | text | required proof photo on submit |
| exception_photo_url | text | required extra photo if any item is attention/critical |
| started_at | timestamptz | when the operator opened the checklist |
| duration_seconds | int | submit minus started_at |
| is_fast_submit | bool | true if a large checklist was submitted in under 3 minutes |
| review_status | enum | none / awaiting_review / approved / rejected |
| reviewed_by | uuid, FK → users.id | supervisor who accepted or rejected |
| reviewed_at | timestamptz | |
| review_notes | text | reject reason, shown to the operator |
| exception_level | enum | none / attention / critical (worst item on the run) |

Work is not `done` until `review_status=approved`. The next recurring instance is created only then.

## `handover_notes`
Shift note on a machine so the next operator is not blind.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| note | text | |
| created_by | uuid, FK → users.id | |
| created_at | timestamptz | |

## `spare_parts`
Plant stores stock. One row per item. The sheet area (Bearing, Rewinding, …) is `category`. A blank item group is stored as `""` so the unique key still holds.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| name | text | trimmed item name |
| item_group | text | `""` when the sheet left the group blank |
| category | text | sheet / machine area |
| qty_on_hand | float | |
| unit | text, nullable | set when the sheet qty was `12 Mtr` or `2 pkt` |
| min_qty | float, nullable | optional reorder point; not on the stock sheet |
| machine_id | uuid, FK → machines.id, nullable | set when the area is obviously one machine. SET NULL if that machine is deleted |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Unique on `(category, name, item_group)`.

Low stock means on-hand is 0 or below, or `min_qty` is set and on-hand is at or below it.

## `part_replacements`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| part_name | text | |
| replaced_at | date | |
| replaced_by | uuid, FK → users.id | |
| notes | text | reason the new part was fitted |
| spare_part_id | uuid, FK → spare_parts.id, nullable | set only when this log took stock. RESTRICT: the spare row stays while a log points at it |
| quantity_used | int, nullable | how many were deducted. Null when the log did not use stock. Deleting the log puts this many back, and also reverses a refurbished credit on the removed part |

## `removed_parts`
The old part that came off when a replacement was logged. One row per replacement (rows logged before this table have none). Current status is the latest disposition. History is `removed_part_events`.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| part_replacement_id | uuid, FK → part_replacements.id, unique | CASCADE |
| machine_id | uuid, FK → machines.id | CASCADE. Copied so the list can filter without guessing |
| part_name | text | the part that came off. Defaults to the fitted part name |
| condition | enum | worn / damaged / broken / reusable |
| status | enum | pending_decision / in_maintenance_store / sent_for_repair / returned_to_stock / scrapped / sold / returned_to_vendor |
| quantity | int | how many came off. Default 1 |
| location | text, nullable | where it is now, e.g. maintenance store rack B |
| notes | text, nullable | latest note |
| vendor | text, nullable | repair vendor, or the vendor a warranty return went to |
| sent_on | date, nullable | sent for repair, or returned to the vendor |
| scrap_on | date, nullable | |
| scrap_qty | float, nullable | pieces or weight |
| scrap_unit | text, nullable | kg or pcs |
| scrap_buyer | text, nullable | |
| sale_buyer | text, nullable | |
| sale_amount | float, nullable | rupees |
| sale_on | date, nullable | |
| warranty_note | text, nullable | |
| stock_credited | bool | true while a refurbished quantity is sitting on a spare |
| credited_spare_part_id | uuid, FK → spare_parts.id, nullable | RESTRICT while set. Often a "Used Refurbish" item, not the new part that was fitted |
| credited_qty | int, nullable | pieces added back. Taken back out if the disposition changes or the replacement is undone |
| created_by | uuid, FK → users.id, nullable | SET NULL |
| created_at | timestamptz | |
| updated_at | timestamptz | |

Logging a replacement only accepts `pending_decision` or `in_maintenance_store`. Supervisor/admin record the later disposition. Operators do not open this list.

A part is stale when it is still `pending_decision` and `replaced_at` is at least 7 days ago (the page can use another threshold).

## `removed_part_events`
Append-only. One row per log and per disposition change: who, when, the status at that moment, notes, and an optional photo URL from the existing upload flow. Detail columns (vendor, scrap, sale, spare name) are copied onto the event so the trail still reads after the current row moves on. Events are not edited. Undoing the replacement deletes them with the removed part.

## `repair_logs`
| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | |
| reported_at | timestamptz | |
| reported_by | uuid, FK → users.id | |
| issue_description | text | |
| impact | text, nullable | what this stops if unfixed. Required on new reports; null only on rows logged before the column existed. |
| downtime_minutes | int | |
| resolved_at | timestamptz | null until resolved |
| resolved_by | uuid, FK → users.id | |
| resolution_notes | text | |

## `vendor_contacts`
Outside people to call when something is mechanically wrong. Readable by every role including operators; only supervisor/admin maintain it.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| name | text | |
| company | text, nullable | |
| specialty | enum | mechanical / electrical / hydraulics / oem / other |
| phone_number | text | |
| whatsapp_number | text, nullable | |
| notes | text, nullable | |
| machine_id | uuid, FK → machines.id, nullable | null = plant-wide, callable for any machine |
| created_at | timestamptz | |

## `user_audit_events`
Who let someone in and who removed them. Names and roles are text snapshots, not joins: a hard-deleted user has no row left to join to, and the trail has to outlive the account it records.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| action | enum | created / deleted |
| actor_id | uuid, FK → users.id, nullable | SET NULL |
| actor_name | text | snapshot |
| actor_role | enum | snapshot, reuses `user_role` |
| target_user_id | uuid, FK → users.id, nullable | SET NULL — goes null on the delete it records |
| target_name | text | snapshot |
| target_role | enum | snapshot, reuses `user_role` |
| at | timestamptz | |

## `shift_logs`
The paper "Machine Start & End Time" sheet: one row per machine per plant day. Production data, deliberately separate from the corrugator's "Shift parameter log" PM checklist (pressures/temperatures), which stays a `task_type` with `checklist_items`.

| column | type | notes |
|---|---|---|
| id | uuid, PK | |
| machine_id | uuid, FK → machines.id | CASCADE |
| log_date | date | local (Sonipat) calendar day |
| start_time | time, nullable | local wall clock, as written on the sheet |
| end_time | time, nullable | earlier than start means the shift ran past midnight |
| output_qty | float, nullable | |
| output_unit | enum | kg / pcs — kg for board line, pcs for converting |
| job_change_count | int, nullable | |
| wastage_boardline | float, nullable | same unit as output |
| wastage_machine | float, nullable | same unit as output |
| delay_reason | text, nullable | the sheet's "Reason of Delay" |
| delay_minutes | int, nullable | for totals |
| created_by | uuid, FK → users.id, nullable | |
| created_at | timestamptz | |
| updated_at | timestamptz | operators re-save the row through the shift |

Unique on `(machine_id, log_date)` — saving is an upsert, since a second save is a correction rather than a new record. `running_minutes` is derived from start/end (not stored) so the API and the insights view can't disagree about a past-midnight shift. Operators may only write today's row; correcting an earlier day is supervisor/admin.

## Relationships
- `machines` 1—N `task_types` 1—N `task_instances`
- `task_types` 1—N `checklist_items`
- `task_instances` 1—N `checklist_item_results`
- `machines` 1—N `part_replacements` 1—1 `removed_parts` 1—N `removed_part_events`
- `machines` 1—N `spare_parts` (optional link)
- `spare_parts` 1—N `part_replacements` (optional; only rows that deducted stock)
- `spare_parts` 1—N `removed_parts` (optional; only while a refurbished quantity is credited)
- `machines` 1—N `repair_logs`
- `machines` 1—N `handover_notes`
- `machines` 1—N `shift_logs` (at most one per `log_date`)
- `machines` 1—N `vendor_contacts` (plus plant-wide contacts with no machine)
- `users` 1—N `users` (`created_by_id`), 1—N `user_audit_events` (as actor or target)
- `users` 1—N `task_instances` (as completer/rescheduler/reviewer), `part_replacements`, `repair_logs`, `handover_notes`
