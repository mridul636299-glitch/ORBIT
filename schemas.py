"""
Pydantic schemas for the admin API. Response schemas use from_attributes=True
so they can be built directly from SQLAlchemy model instances, and they only
expose the flat fields we want (never the raw ORM object with its relationships,
which would blow up JSON serialization).
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BusinessCreate(BaseModel):
    name: str
    whatsapp_phone_number_id: str
    business_type: str = "general"
    reply_language: str = "hinglish"
    open_time: str = "09:00"
    close_time: str = "19:00"
    working_days: str = "Mon,Tue,Wed,Thu,Fri,Sat"
    slot_duration_minutes: int = 30


class BusinessOut(BusinessCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ServiceCreate(BaseModel):
    name: str
    price: float
    duration_minutes: int = 30
    description: str = ""


class ServiceOut(ServiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
    business_id: int


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    customer_id: int
    service_id: int | None
    scheduled_at: datetime
    status: str
    reminder_sent: bool
