# WhatsApp AI Receptionist

Chhoti businesses (clinics, salons, coaching centers, gyms) ke liye AI receptionist jo unke WhatsApp Business number par customer queries handle karta hai — pricing/timing sawaal, appointment booking, aur reminders. Multi-tenant hai: ek hi backend se kitni bhi businesses onboard ki ja sakti hain.

Tested aur working: DB models, booking/clash logic, webhook payload parsing, admin API, aur reminder scheduler — sab automated tests se pass ho chuke hain (neeche "What's tested" dekhein).

## Architecture

```
main.py                → FastAPI app: WhatsApp webhook + admin API
ai_engine.py            → Claude ko system prompt + tools deta hai, reply banata hai
booking_engine.py        → Slot availability & booking logic (pure, no AI/WhatsApp dependency)
whatsapp_client.py        → WhatsApp Cloud API se message bhejna/webhook payload parse karna
models.py / database.py    → SQLAlchemy models (Business, Service, Customer, Message, Appointment) + DB setup
schemas.py                → Admin API ke request/response shapes (Pydantic)
reminder_scheduler.py      → Cron se chalane wali script — upcoming appointments ke reminders bhejti hai
seed_data.py                → Demo business + services banata hai testing ke liye
test_local.py                 → Terminal mein AI se chat karo, WhatsApp setup ke bina
```

## Quick test — WhatsApp setup ke bina (5 minute)

```bash
pip install -r requirements.txt
cp .env.example .env
# .env mein sirf ANTHROPIC_API_KEY fill karo abhi ke liye

python seed_data.py     # ek demo dental clinic + services seed karta hai
python test_local.py    # terminal mein AI receptionist se chat karo
```

Isse tumhe pata chal jayega ki conversation + booking flow actually kaam karta hai ya nahi, WhatsApp/Meta ke approval process mein padne se pehle.

## WhatsApp par live karna

1. [developers.facebook.com](https://developers.facebook.com) par ek app banao, WhatsApp product add karo. Isse `WHATSAPP_TOKEN` aur `WHATSAPP_PHONE_NUMBER_ID` milega.
2. `.env` mein `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, aur ek random `WHATSAPP_VERIFY_TOKEN` daalo.
3. Server chalao: `uvicorn main:app --reload`
4. Local testing ke liye `ngrok http 8000` se URL expose karo.
5. Meta dashboard mein webhook URL set karo: `https://<your-ngrok-url>/webhook`, verify token wahi daalo jo `.env` mein hai.
6. Apni pehli real business register karo (neeche curl example dekho).

### Business onboard karna (admin API)

Sab `/businesses` routes `X-Admin-Key` header maangte hain — value wahi honi chahiye jo `.env` ke `ADMIN_API_KEY` mein hai.

```bash
curl -X POST http://localhost:8000/businesses \
  -H "X-Admin-Key: <your ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Glow Salon",
        "whatsapp_phone_number_id": "<meta phone_number_id>",
        "business_type": "salon",
        "open_time": "10:00",
        "close_time": "20:00"
      }'

curl -X POST http://localhost:8000/businesses/1/services \
  -H "X-Admin-Key: <your ADMIN_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Haircut", "price": 300, "duration_minutes": 30}'
```

## Deploy

- `Dockerfile` included — Railway, Render, ya Fly.io par seedha deploy ho jayega.
- Production mein `DATABASE_URL` ko Postgres se replace karo (SQLite sirf demo/MVP ke liye theek hai).
- `reminder_scheduler.py` ko cron se har ~15 minute chalao (`python reminder_scheduler.py`) taaki appointment reminders time par jaayein.

## What's tested

Automated tests (imports, DB, booking clash/double-booking logic, webhook payload parsing including edge cases, full FastAPI request/response cycle including auth, aur reminder-window logic) sab pass ho chuke hain. **Jo test nahi ho saka:** actual Claude API call aur actual WhatsApp send — inke liye real API keys chahiye, jo isse sandbox mein available nahi hain. `test_local.py` chala ke apni key se yeh verify kar lena pehle live jaane se pehle.

## Isse bechne se pehle — jo abhi missing hai (brutal honesty)

1. **Koi dashboard UI nahi hai.** Business owner ko abhi admin API (curl/Postman) use karna padta hai apna config set karne ke liye. Non-technical customers ko onboard karne se pehle, ya kisi buyer ko pitch karne se pehle, yeh sabse pehli cheez hai jo add karni chahiye.
2. **Billing/subscription system nahi hai** — abhi sab free/manual hai.
3. **Single shared admin key** — multiple team members ke liye proper auth (per-user login) nahi hai.
4. **Synchronous webhook processing** — high volume par (ek business ke liye hi bahut saare simultaneous messages) ek background queue (e.g. Redis + worker) add karna padega.

Agla sabse high-leverage step: ek simple web dashboard jahan business owner khud apni services/pricing/timing set kar sake, sign up kar sake, aur apne appointments dekh sake — bina kisi curl command ke. Batao agar wahi banau next.
