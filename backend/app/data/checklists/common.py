"""Checklist item specs used when seeding PM task types."""

from typing import NotRequired, TypedDict


class ChecklistItemSpec(TypedDict):
    section: str
    description: str
    requires_value: bool
    value_unit: str | None
    min_value: NotRequired[float | None]
    max_value: NotRequired[float | None]


class PmTemplate(TypedDict):
    description: str
    default_interval_days: int
    items: list[ChecklistItemSpec]


def from_sections(sections: list[tuple[str, list[str]]]) -> list[ChecklistItemSpec]:
    items: list[ChecklistItemSpec] = []
    for section, lines in sections:
        for line in lines:
            items.append(
                {
                    "section": section,
                    "description": line,
                    "requires_value": False,
                    "value_unit": None,
                }
            )
    return items


def from_readings(
    section: str,
    readings: list[tuple[str, str] | tuple[str, str, float | None, float | None]],
) -> list[ChecklistItemSpec]:
    items: list[ChecklistItemSpec] = []
    for row in readings:
        name = row[0]
        unit = row[1]
        spec: ChecklistItemSpec = {
            "section": section,
            "description": name,
            "requires_value": True,
            "value_unit": unit or None,
        }
        if len(row) >= 4:
            spec["min_value"] = row[2]
            spec["max_value"] = row[3]
        items.append(spec)
    return items
