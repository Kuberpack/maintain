from app.data.checklists.common import PmTemplate, from_sections

DAILY: list[tuple[str, list[str]]] = [
    (
        "Safety and housekeeping",
        [
            "Check walkways, covers, and fall hazards around tanks",
            "Confirm PPE and chemical handling area is in order",
            "Check for unusual odour or overflow",
        ],
    ),
    (
        "Process",
        [
            "Check pump operation and unusual noise",
            "Check for leaks at pipes, valves, and tanks",
            "Check aeration / mixing if in service",
            "Record visual sludge / foam / colour condition",
            "Check chemical dosing pumps if in use",
        ],
    ),
    (
        "Utilities",
        [
            "Check blower / compressor operation",
            "Check electrical panel indicators",
            "Check level sensors and alarms",
        ],
    ),
]

WEEKLY: list[tuple[str, list[str]]] = [
    (
        "Weekly Preventive Maintenance",
        [
            "Lubricate pump and blower bearings as specified",
            "Inspect couplings and mounts",
            "Check for leaks at flanges and unions",
            "Clean screens / strainers",
            "Inspect electrical-panel filters",
            "Test high-level and overflow alarms",
            "Test emergency stops where fitted",
        ],
    ),
]

MONTHLY: list[tuple[str, list[str]]] = [
    (
        "Mechanical",
        [
            "Check pump vibration and seal condition",
            "Check gearbox oil level on mixers/blowers",
            "Inspect valves for sticking",
            "Check foundation/anchor bolts",
        ],
    ),
    (
        "Electrical and statutory",
        [
            "Inspect electrical terminals; isolate equipment before intervention",
            "Check earthing connections",
            "Inspect cables and conduit",
            "Review statutory / lab sampling schedule",
        ],
    ),
]

QUARTERLY: list[tuple[str, list[str]]] = [
    (
        "Quarterly Preventive Maintenance",
        [
            "Inspect tanks, weirs, and media condition",
            "Service blowers / pumps per OEM hours",
            "Inspect chemical storage and dosing lines",
            "Review recurring process upsets",
            "Electrical-panel inspection by qualified personnel",
        ],
    ),
]

HALF_YEARLY: list[tuple[str, list[str]]] = [
    (
        "Half-Yearly Preventive Maintenance",
        [
            "Inspect/replace gearbox oil according to OEM hours/condition",
            "Inspect critical pump bearings",
            "Desludge / clean tanks as required by process",
            "Back up PLC/HMI parameters where supported",
            "Verify safety interlocks and alarms",
        ],
    ),
]

ANNUAL: list[tuple[str, list[str]]] = [
    (
        "Annual Shutdown Inspection",
        [
            "Pumps",
            "Blowers / compressors",
            "Tanks and civil structure",
            "Piping and valves",
            "Aeration / mixing",
            "Chemical dosing",
            "Electrical panels",
            "Instrumentation",
            "Safety systems",
        ],
    ),
]

TEMPLATES: list[PmTemplate] = [
    {"description": "Daily Preventive Maintenance", "default_interval_days": 1, "items": from_sections(DAILY)},
    {"description": "Weekly Preventive Maintenance", "default_interval_days": 7, "items": from_sections(WEEKLY)},
    {"description": "Monthly Preventive Maintenance", "default_interval_days": 30, "items": from_sections(MONTHLY)},
    {"description": "Quarterly Preventive Maintenance", "default_interval_days": 90, "items": from_sections(QUARTERLY)},
    {
        "description": "Half-Yearly Preventive Maintenance",
        "default_interval_days": 180,
        "items": from_sections(HALF_YEARLY),
    },
    {"description": "Annual Shutdown Maintenance", "default_interval_days": 365, "items": from_sections(ANNUAL)},
]
