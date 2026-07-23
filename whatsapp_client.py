"""
Thin wrapper around Meta's WhatsApp Cloud API — sending messages and parsing
incoming webhook payloads.
"""
import httpx

from config import settings


def _graph_url() -> str:
    return f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


def send_whatsapp_message(to_number: str, text: str) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(_graph_url(), headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def extract_incoming_message(payload: dict):
    """
    Parse a Meta webhook payload.
    Returns (from_number, text, profile_name), or (None, None, None) for
    anything that isn't an incoming text message (e.g. delivery/read receipts).
    """
    try:
        change = payload["entry"][0]["changes"][0]["value"]
        if "messages" not in change:
            return None, None, None
        message = change["messages"][0]
        if message.get("type") != "text":
            return None, None, None
        from_number = message["from"]
        text = message["text"]["body"]
        profile_name = change.get("contacts", [{}])[0].get("profile", {}).get("name", "")
        return from_number, text, profile_name
    except (KeyError, IndexError):
        return None, None, None
