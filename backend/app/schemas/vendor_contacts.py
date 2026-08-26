import uuid
from datetime import datetime

from pydantic import Field

from app.models import VendorSpecialty
from app.schemas.base import CamelModel


class VendorContactCreate(CamelModel):
    name: str = Field(min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    specialty: VendorSpecialty
    phone_number: str = Field(min_length=4, max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    # Null = plant-wide contact, callable for any machine.
    machine_id: uuid.UUID | None = None


class VendorContactUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    company: str | None = Field(default=None, max_length=255)
    specialty: VendorSpecialty | None = None
    phone_number: str | None = Field(default=None, min_length=4, max_length=20)
    whatsapp_number: str | None = Field(default=None, max_length=20)
    notes: str | None = None
    machine_id: uuid.UUID | None = None


class VendorContactPublic(CamelModel):
    id: uuid.UUID
    name: str
    company: str | None
    specialty: VendorSpecialty
    phone_number: str
    whatsapp_number: str | None
    notes: str | None
    machine_id: uuid.UUID | None
    created_at: datetime
