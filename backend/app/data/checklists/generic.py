from app.data.checklists.common import PmTemplate, from_sections

DAILY: list[tuple[str, list[str]]] = [
    (
        "Safety and housekeeping",
        [
            "Test emergency stops",
            "Check guards and interlocks",
            "Clear scrap, dust, and slip hazards around the machine",
            "Confirm operator station is clear and lighting is adequate",
        ],
    ),
    (
        "Mechanical",
        [
            "Listen for abnormal noise or vibration",
            "Check belt/chain tracking and tension",
            "Inspect drive belts, chains, and couplings",
            "Check bearings for heat or play",
            "Lubricate designated daily points",
        ],
    ),
    (
        "Pneumatic / hydraulic",
        [
            "Check pneumatic pressure",
            "Check for air leaks at hoses, fittings, and cylinders",
            "Check hydraulic oil level if fitted",
            "Check for hydraulic leakage",
        ],
    ),
    (
        "Process and quality",
        [
            "Inspect feed/registration/alignment",
            "Check sensors and photocells",
            "Check glue/ink/adhesive application if used",
            "Wipe rolls, belts, and contact surfaces",
        ],
    ),
]

WEEKLY: list[tuple[str, list[str]]] = [
    (
        "Weekly Preventive Maintenance",
        [
            "Lubricate designated bearings according to OEM lubrication chart",
            "Inspect all chains and sprockets",
            "Check chain tension",
            "Inspect timing/drive belts",
            "Inspect couplings",
            "Check gearbox oil leakage",
            "Check pneumatic leakage",
            "Clean electrical-panel filters",
            "Inspect cooling fans",
            "Check motor temperature",
            "Check bearing temperature",
            "Test emergency stops",
            "Test guards and interlocks",
        ],
    ),
]

MONTHLY: list[tuple[str, list[str]]] = [
    (
        "Mechanical",
        [
            "Check bearing play",
            "Check gearbox oil level",
            "Check motor-to-gearbox coupling",
            "Check chain elongation",
            "Check sprocket wear",
            "Inspect all drive belts",
            "Check foundation/anchor bolts",
            "Check machine vibration",
            "Inspect pneumatic cylinders",
        ],
    ),
    (
        "Electrical",
        [
            "Inspect electrical terminals for signs of looseness or overheating; isolate equipment before intervention",
            "Check contactors",
            "Check relays",
            "Check VFD cooling if fitted",
            "Clean panel filters",
            "Inspect cables",
            "Check earthing connections",
            "Inspect sensors",
            "Check PLC alarms/history if fitted",
        ],
    ),
]

QUARTERLY: list[tuple[str, list[str]]] = [
    (
        "Quarterly Preventive Maintenance",
        [
            "Inspect complete drive train",
            "Check gearbox condition",
            "Inspect pneumatic FRL units",
            "Check machine calibration / registration",
            "Electrical-panel inspection by qualified personnel",
            "Motor vibration monitoring",
            "Critical bearing vibration monitoring",
            "Review recurring breakdowns",
        ],
    ),
]

HALF_YEARLY: list[tuple[str, list[str]]] = [
    (
        "Half-Yearly Preventive Maintenance",
        [
            "Inspect/replace gearbox oil according to OEM hours/condition",
            "Inspect critical bearings",
            "Check motor bearings",
            "Inspect all chains and sprockets",
            "Check electrical-panel components",
            "Back up HMI/PLC parameters where supported",
            "Verify machine safety interlocks",
        ],
    ),
]

ANNUAL: list[tuple[str, list[str]]] = [
    (
        "Annual Shutdown Inspection",
        [
            "Feed and delivery systems",
            "Drive train",
            "Motors",
            "Gearboxes",
            "Bearings",
            "Pneumatic system",
            "Hydraulic system if fitted",
            "Electrical panels",
            "PLC/HMI if fitted",
            "VFDs if fitted",
            "Sensors/encoders",
            "Safety guards",
            "Emergency-stop circuits",
            "Lubrication system",
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
