import hashlib
import hmac
import os
from dataclasses import dataclass

import httpx

@dataclass
class WhatsAppMessage:
    message_id: str
    sender: str
    media_id: str | None
    mime_type: str | None
    text: str | None

class WhatsAppAdapter:
    def __init__(self) -> None:
        self.token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
        self.verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
        self.app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
        self.graph_version = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")

    @property
    def configured(self) -> bool:
        return bool(self.token and self.phone_number_id and self.verify_token)

    def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if not self.app_secret:
            return False
        if not signature or not signature.startswith("sha256="):
            return False
        expected = hmac.new(self.app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature.removeprefix("sha256="), expected)

    def parse_messages(self, payload: dict) -> list[WhatsAppMessage]:
        messages: list[WhatsAppMessage] = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                for message in value.get("messages", []):
                    audio = message.get("audio") or {}
                    messages.append(WhatsAppMessage(
                        message_id=message.get("id", ""),
                        sender=message.get("from", ""),
                        media_id=audio.get("id"),
                        mime_type=audio.get("mime_type"),
                        text=message.get("text", {}).get("body"),
                    ))
        return messages

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def download_media(self, media_id: str) -> tuple[bytes, str, str]:
        if not self.token:
            raise RuntimeError("WhatsApp access token is not configured")
        base = f"https://graph.facebook.com/{self.graph_version}"
        metadata = httpx.get(f"{base}/{media_id}", headers=self._headers(), timeout=30)
        metadata.raise_for_status()
        info = metadata.json()
        media_url = info.get("url")
        if not media_url:
            raise RuntimeError("WhatsApp media response did not include a download URL")
        media = httpx.get(media_url, headers=self._headers(), timeout=60)
        media.raise_for_status()
        return media.content, info.get("mime_type", "audio/ogg"), media_id

    def send_text(self, recipient: str, body: str) -> dict:
        if not self.token or not self.phone_number_id:
            raise RuntimeError("WhatsApp sending configuration is incomplete")
        url = f"https://graph.facebook.com/{self.graph_version}/{self.phone_number_id}/messages"
        response = httpx.post(url, headers={**self._headers(), "Content-Type": "application/json"}, json={"messaging_product": "whatsapp", "to": recipient, "type": "text", "text": {"body": body}}, timeout=30)
        response.raise_for_status()
        return response.json()
