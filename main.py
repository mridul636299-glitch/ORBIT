"""
FastAPI app: WhatsApp webhook (public) + admin API for onboarding businesses
(protected by an X-Admin-Key header).
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

import ai_engine
import whatsapp_client
from config import settings
from database import get_db, init_db
from models import Business, Customer, Service
from schemas import AppointmentOut, BusinessCreate, BusinessOut, ServiceCreate, ServiceOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)


@app.get("/")
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


def verify_admin(x_admin_key: str | None = Header(default=None)):
    if not settings.ADMIN_API_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_API_KEY not configured on server.")
    if x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


# ---------------------------------------------------------------------------
# WhatsApp webhook
# ---------------------------------------------------------------------------

@app.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    """Meta calls this once when you register the webhook URL."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    payload = await request.json()
    from_number, text, profile_name = whatsapp_client.extract_incoming_message(payload)

    if not from_number or not text:
        return {"status": "ignored"}  # delivery receipts, non-text messages, etc.

    try:
        phone_number_id = payload["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"]
    except (KeyError, IndexError):
        return {"status": "ignored"}

    business = db.query(Business).filter(Business.whatsapp_phone_number_id == phone_number_id).first()
    if not business:
        return {"status": "no business configured for this number"}

    customer = (
        db.query(Customer)
        .filter(Customer.business_id == business.id, Customer.phone_number == from_number)
        .first()
    )
    if not customer:
        customer = Customer(business_id=business.id, phone_number=from_number, name=profile_name or "")
        db.add(customer)
        db.commit()
        db.refresh(customer)

    reply = ai_engine.get_ai_response(db, business, customer, text)
    whatsapp_client.send_whatsapp_message(from_number, reply)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Admin API — onboarding businesses & services (needs X-Admin-Key header)
# ---------------------------------------------------------------------------

@app.post("/businesses", response_model=BusinessOut, dependencies=[Depends(verify_admin)])
def create_business(payload: BusinessCreate, db: Session = Depends(get_db)):
    business = Business(**payload.model_dump())
    db.add(business)
    db.commit()
    db.refresh(business)
    return business


@app.get("/businesses/{business_id}", response_model=BusinessOut, dependencies=[Depends(verify_admin)])
def get_business(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@app.post(
    "/businesses/{business_id}/services",
    response_model=ServiceOut,
    dependencies=[Depends(verify_admin)],
)
def add_service(business_id: int, payload: ServiceCreate, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    service = Service(business_id=business_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@app.get(
    "/businesses/{business_id}/appointments",
    response_model=list[AppointmentOut],
    dependencies=[Depends(verify_admin)],
)
def list_appointments(business_id: int, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business.appointments
