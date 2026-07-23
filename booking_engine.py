"""
Pure scheduling logic: what slots are open on a given day, and booking them.
No WhatsApp or AI code here on purpose — keep this testable in isolation.
"""
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models import Appointment, Business


def get_available_slots(db: Session, business: Business, target_date: datetime, limit: int = 6):
    """Return open slot datetimes for a business on a given date (skips past slots)."""
    working_days = [d.strip() for d in business.working_days.split(",")]
    day_name = target_date.strftime("%a")
    if day_name not in working_days:
        return []

    open_h, open_m = map(int, business.open_time.split(":"))
    close_h, close_m = map(int, business.close_time.split(":"))

    slot = target_date.replace(hour=open_h, minute=open_m, second=0, microsecond=0)
    day_close = target_date.replace(hour=close_h, minute=close_m, second=0, microsecond=0)

    booked = (
        db.query(Appointment)
        .filter(
            Appointment.business_id == business.id,
            Appointment.status == "confirmed",
            Appointment.scheduled_at >= slot,
            Appointment.scheduled_at < day_close,
        )
        .all()
    )
    booked_times = {a.scheduled_at for a in booked}

    step = timedelta(minutes=business.slot_duration_minutes)
    now = datetime.now()
    slots = []
    while slot < day_close and len(slots) < limit:
        if slot not in booked_times and slot > now:
            slots.append(slot)
        slot += step
    return slots


def book_slot(db: Session, business: Business, customer_id: int, service_id: int | None, scheduled_at: datetime):
    """Book a slot if it's free. Returns (True, Appointment) or (False, reason_str)."""
    clash = (
        db.query(Appointment)
        .filter(
            Appointment.business_id == business.id,
            Appointment.status == "confirmed",
            Appointment.scheduled_at == scheduled_at,
        )
        .first()
    )
    if clash:
        return False, "Yeh slot already book ho chuka hai. Kripya doosra time chunein."

    appt = Appointment(
        business_id=business.id,
        customer_id=customer_id,
        service_id=service_id,
        scheduled_at=scheduled_at,
        status="confirmed",
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return True, appt


def cancel_appointment(db: Session, business_id: int, appointment_id: int):
    appt = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.business_id == business_id)
        .first()
    )
    if not appt:
        return False, "Appointment nahi mila."
    appt.status = "cancelled"
    db.commit()
    return True, appt
