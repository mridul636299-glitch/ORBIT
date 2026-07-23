"""
Chat with the AI receptionist right in your terminal — no WhatsApp Business
API setup needed. This is the fastest way to see if the idea actually works
before you go through Meta's approval process.

Run: python seed_data.py   (once)
     python test_local.py
"""
from database import SessionLocal, init_db
from models import Business, Customer
import ai_engine

init_db()
db = SessionLocal()

business = db.query(Business).filter(Business.whatsapp_phone_number_id == "DEMO_NUMBER_ID").first()
if not business:
    print("Pehle 'python seed_data.py' chalayein demo business banane ke liye.")
    raise SystemExit(1)

customer = (
    db.query(Customer)
    .filter(Customer.business_id == business.id, Customer.phone_number == "TEST_USER")
    .first()
)
if not customer:
    customer = Customer(business_id=business.id, phone_number="TEST_USER", name="Test User")
    db.add(customer)
    db.commit()
    db.refresh(customer)

print(f"Chatting with {business.name}'s AI receptionist. Type 'exit' to quit.\n")
try:
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        reply = ai_engine.get_ai_response(db, business, customer, user_input)
        print(f"AI: {reply}\n")
finally:
    db.close()
