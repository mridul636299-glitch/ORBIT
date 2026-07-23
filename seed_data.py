"""
Seeds one demo business (a dental clinic) with a few services, so you can try
the AI receptionist immediately without setting up real WhatsApp credentials.
Run: python seed_data.py
"""
from database import SessionLocal, init_db
from models import Business, Service

DEMO_PHONE_NUMBER_ID = "DEMO_NUMBER_ID"

init_db()
db = SessionLocal()

existing = db.query(Business).filter(Business.whatsapp_phone_number_id == DEMO_PHONE_NUMBER_ID).first()
if existing:
    print(f"Demo business already exists (id={existing.id}). Nothing to do.")
else:
    business = Business(
        name="Smile Care Dental Clinic",
        whatsapp_phone_number_id=DEMO_PHONE_NUMBER_ID,
        business_type="clinic",
        reply_language="hinglish",
        open_time="10:00",
        close_time="18:00",
        working_days="Mon,Tue,Wed,Thu,Fri,Sat",
        slot_duration_minutes=30,
    )
    db.add(business)
    db.commit()
    db.refresh(business)

    services = [
        Service(business_id=business.id, name="Dental Checkup", price=300, duration_minutes=20),
        Service(business_id=business.id, name="Teeth Cleaning", price=800, duration_minutes=30),
        Service(business_id=business.id, name="Root Canal", price=4500, duration_minutes=60),
    ]
    db.add_all(services)
    db.commit()
    print(f"Seeded business id={business.id} ({business.name}) with {len(services)} services.")

db.close()
