"""
Sends WhatsApp reminders for appointments coming up soon.
Run this as a separate scheduled job (cron/Task Scheduler/hosting provider's
cron add-on) every ~15 minutes: `python reminder_scheduler.py`
"""
from datetime import datetime, timedelta

from database import SessionLocal
from models import Appointment, Business, Customer
import whatsapp_client


def send_due_reminders(hours_before: int = 2, window_minutes: int = 15):
    db = SessionLocal()
    try:
        window_start = datetime.now() + timedelta(hours=hours_before)
        window_end = window_start + timedelta(minutes=window_minutes)

        due = (
            db.query(Appointment)
            .filter(
                Appointment.status == "confirmed",
                Appointment.reminder_sent.is_(False),
                Appointment.scheduled_at >= window_start,
                Appointment.scheduled_at < window_end,
            )
            .all()
        )

        for appt in due:
            customer = db.query(Customer).filter(Customer.id == appt.customer_id).first()
            business = db.query(Business).filter(Business.id == appt.business_id).first()
            if not customer or not business:
                continue
            text = (
                f"Reminder: Aapka appointment {business.name} mein "
                f"{appt.scheduled_at.strftime('%d %b, %H:%M')} par hai. "
                f"Reschedule karna ho toh yahin message kar dein."
            )
            whatsapp_client.send_whatsapp_message(customer.phone_number, text)
            appt.reminder_sent = True

        db.commit()
        return len(due)
    finally:
        db.close()


if __name__ == "__main__":
    count = send_due_reminders()
    print(f"Sent {count} reminder(s).")
