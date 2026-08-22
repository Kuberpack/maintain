"""Checklist item specs used when seeding PM task types."""

from typing import TypedDict


class ChecklistItemSpec(TypedDict):
    section: str
    description: str
    requires_value: bool
    value_unit: str | None


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


def from_readings(section: str, readings: list[tuple[str, str]]) -> list[ChecklistItemSpec]:
    return [
        {
            "section": section,
            "description": name,
            "requires_value": True,
            "value_unit": unit,
        }
        for name, unit in readings
    ]
