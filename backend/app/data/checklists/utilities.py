from app.data.checklists.common import PmTemplate, from_sections

DAILY: list[tuple[str, list[str]]] = [
    (
        "Safety and housekeeping",
        [
            "Check walkways, covers, and fall hazards around the equipment",
            "Confirm guards and covers are in place",
            "Look for oil, water, or fuel leaks on the floor",
            "Confirm the area is clear of scrap and rags",
        ],
    ),
    (
        "Operation",
        [
            "Listen for abnormal noise or vibration",
            "Check gauges / indicators if fitted",
            "Check for unusual heat on motors and bearings",
            "Confirm start/stop and emergency stop if fitted",
        ],
    ),
]

WEEKLY: list[tuple[str, list[str]]] = [
    (
        "Weekly Preventive Maintenance",
        [
            "Lubricate designated points",
            "Inspect belts, couplings, and mounts",
            "Check for leaks at hoses, flanges, and unions",
            "Clean filters / strainers if fitted",
            "Inspect electrical-panel filters and cooling",
            "Test emergency stops and alarms if fitted",
        ],
    ),
]

COMPRESSOR_DAILY: list[tuple[str, list[str]]] = [
    (
        "Compressor",
        [
            "Check oil level",
            "Drain condensate from receiver / traps",
            "Listen for abnormal noise or vibration",
            "Check for air leaks at hoses and fittings",
            "Check discharge pressure",
            "Check cooling airflow and cleanliness",
        ],
    ),
]

DG_DAILY: list[tuple[str, list[str]]] = [
    (
        "Diesel generator",
        [
            "Check fuel level",
            "Check engine oil level",
            "Check coolant level",
            "Look for fuel, oil, or coolant leaks",
            "Check battery terminals",
            "Confirm the area is clear and exhaust path is open",
        ],
    ),
]

TRANSFORMER_DAILY: list[tuple[str, list[str]]] = [
    (
        "Transformer",
        [
            "Visual check for oil leaks or seepage",
            "Check for unusual noise or smell",
            "Check conservator / oil level if visible",
            "Confirm cooling fans or radiators are clear",
            "Check the area is dry and locked as required",
        ],
    ),
]

BOILER_DAILY: list[tuple[str, list[str]]] = [
    (
        "Boiler",
        [
            "Check steam pressure",
            "Check water level",
            "Check for steam or water leaks",
            "Check feed pump operation",
            "Listen for abnormal noise",
            "Confirm safety valves and gauges are readable",
        ],
    ),
]

FORKLIFT_DAILY: list[tuple[str, list[str]]] = [
    (
        "Forklift / stacker",
        [
            "Check tyres / wheels",
            "Check forks / mast for damage",
            "Check hydraulic leaks",
            "Test brakes and horn",
            "Check battery / fuel as fitted",
            "Confirm lights and reverse alarm if fitted",
        ],
    ),
]

SCRAP_DAILY: list[tuple[str, list[str]]] = [
    (
        "Scrap machine",
        [
            "Clear scrap around infeed and discharge",
            "Listen for abnormal noise or vibration",
            "Check belts, chains, and guards",
            "Check for oil leaks",
            "Test emergency stop",
        ],
    ),
]


def _daily_weekly(daily: list[tuple[str, list[str]]]) -> list[PmTemplate]:
    return [
        {"description": "Daily Preventive Maintenance", "default_interval_days": 1, "items": from_sections(daily)},
        {"description": "Weekly Preventive Maintenance", "default_interval_days": 7, "items": from_sections(WEEKLY)},
    ]


TEMPLATES: list[PmTemplate] = _daily_weekly(DAILY)
COMPRESSOR: list[PmTemplate] = _daily_weekly(COMPRESSOR_DAILY)
GENERATOR: list[PmTemplate] = _daily_weekly(DG_DAILY)
TRANSFORMER: list[PmTemplate] = _daily_weekly(TRANSFORMER_DAILY)
BOILER: list[PmTemplate] = _daily_weekly(BOILER_DAILY)
FORKLIFT: list[PmTemplate] = _daily_weekly(FORKLIFT_DAILY)
SCRAP: list[PmTemplate] = _daily_weekly(SCRAP_DAILY)
