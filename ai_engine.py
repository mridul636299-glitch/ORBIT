"""
The brain of the receptionist. Builds a system prompt from the business's own
config (services/pricing/hours), gives Claude two tools (check availability,
book appointment), and loops until Claude has a final text reply ready to send.
"""
from datetime import datetime

import anthropic
from sqlalchemy.orm import Session

import booking_engine
from config import settings
from models import Business, Customer, Message, Service

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

TOOLS = [
    {
        "name": "check_availability",
        "description": "Check open appointment slots for a given date (YYYY-MM-DD). Always use this before booking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "book_appointment",
        "description": (
            "Book an appointment for the customer at a specific date & time. "
            "Only call this after the customer has clearly confirmed one specific "
            "slot that was already shown to them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "datetime": {"type": "string", "description": "ISO datetime, e.g. 2026-07-25T11:00:00"},
                "service_name": {"type": "string", "description": "Name of the service being booked, if known"},
            },
            "required": ["datetime"],
        },
    },
]

LANGUAGE_INSTRUCTIONS = {
    "hinglish": "Hinglish mein (Hindi-English mix, Roman script) jawaab do — jaise log WhatsApp par naturally likhte hain.",
    "english": "Reply in simple, friendly English.",
    "hindi": "Hindi mein (Devanagari script) jawaab do.",
}

MAX_TOOL_LOOPS = 3


def _build_system_prompt(business: Business, services: list[Service]) -> str:
    service_lines = "\n".join(
        f"- {s.name}: \u20b9{s.price:.0f} ({s.duration_minutes} min)" for s in services
    ) or "- (Abhi koi service configure nahi hui hai)"

    language_instruction = LANGUAGE_INSTRUCTIONS.get(business.reply_language, LANGUAGE_INSTRUCTIONS["hinglish"])

    return f"""Tum "{business.name}" ke liye AI receptionist ho, WhatsApp par customers se baat karte ho.

Business type: {business.business_type}
Working days: {business.working_days}
Timing: {business.open_time} - {business.close_time}

Services & pricing:
{service_lines}

Tumhara kaam:
1. Customer ke sawalon ka jawaab do — pricing, timing, services ke baare mein — seedha aur helpful.
2. Agar customer appointment book karna chahta hai, pehle check_availability tool se open slots dikhao, phir customer ke ek specific slot confirm karne ke baad hi book_appointment tool call karo.
3. Khud se koi slot book mat karo jab tak customer ne clearly ek time confirm na kiya ho.
4. {language_instruction}
5. Chhote, WhatsApp-style messages likho — lambi paragraphs mat likho.
6. Agar koi medical/professional advice wala sawaal ho jo tumhare scope se bahar hai, clearly bolo ki business isse directly baat karke confirm karega.

Aaj ki date: {datetime.now().strftime('%Y-%m-%d, %A')}
"""


def get_ai_response(db: Session, business: Business, customer: Customer, user_message: str) -> str:
    """Main entry point: given a new incoming WhatsApp message, return the reply text."""
    db.add(Message(customer_id=customer.id, role="user", content=user_message))
    db.commit()

    services = db.query(Service).filter(Service.business_id == business.id).all()
    system_prompt = _build_system_prompt(business, services)

    history = (
        db.query(Message)
        .filter(Message.customer_id == customer.id)
        .order_by(Message.timestamp.desc())
        .limit(12)
        .all()
    )
    history.reverse()
    messages = [{"role": m.role, "content": m.content} for m in history]

    reply_text = _run_conversation_turn(db, business, customer, system_prompt, messages)

    db.add(Message(customer_id=customer.id, role="assistant", content=reply_text))
    db.commit()
    return reply_text


def _run_conversation_turn(db, business, customer, system_prompt, messages, depth=0):
    if depth > MAX_TOOL_LOOPS:
        return "Sorry, thoda technical issue aa gaya hai. Kripya thodi der mein try karein."

    response = client.messages.create(
        model=settings.CLAUDE_MODEL,
        max_tokens=500,
        system=system_prompt,
        tools=TOOLS,
        messages=messages,
    )

    if response.stop_reason == "tool_use":
        tool_use_block = next(b for b in response.content if b.type == "tool_use")
        tool_result = _execute_tool(db, business, customer, tool_use_block.name, tool_use_block.input)

        messages = messages + [
            {"role": "assistant", "content": response.content},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_block.id,
                        "content": tool_result,
                    }
                ],
            },
        ]
        return _run_conversation_turn(db, business, customer, system_prompt, messages, depth + 1)

    text_blocks = [b.text for b in response.content if b.type == "text"]
    return "\n".join(text_blocks).strip() or "Aap kaise madad chahte hain?"


def _execute_tool(db: Session, business: Business, customer: Customer, name: str, tool_input: dict) -> str:
    if name == "check_availability":
        try:
            target_date = datetime.strptime(tool_input["date"], "%Y-%m-%d")
        except (ValueError, KeyError):
            return "Invalid date format."
        slots = booking_engine.get_available_slots(db, business, target_date)
        if not slots:
            return "Is din koi slot available nahi hai."
        return "Available slots: " + ", ".join(s.strftime("%H:%M") for s in slots)

    if name == "book_appointment":
        try:
            when = datetime.fromisoformat(tool_input["datetime"])
        except (ValueError, KeyError):
            return "Invalid datetime format."
        service = None
        if tool_input.get("service_name"):
            service = (
                db.query(Service)
                .filter(
                    Service.business_id == business.id,
                    Service.name.ilike(f"%{tool_input['service_name']}%"),
                )
                .first()
            )
        success, result = booking_engine.book_slot(
            db, business, customer.id, service.id if service else None, when
        )
        if success:
            return f"Appointment confirmed for {when.strftime('%d %b, %H:%M')}."
        return result

    return "Unknown tool."
