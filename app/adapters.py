import os
import time
from dataclasses import dataclass
import httpx

@dataclass
class NatlasResult:
    text: str
    mode: str
    model: str
    latency_ms: int

class NatlasAdapter:
    def __init__(self) -> None:
        self.mode = os.getenv("NATLAS_MODE", "mock")
        self.asr_url = os.getenv("NATLAS_ASR_URL", "")
        self.llm_url = os.getenv("NATLAS_LLM_URL", "")
        self.api_key = os.getenv("NATLAS_API_KEY", "")
        self.asr_file_field = os.getenv("NATLAS_ASR_FILE_FIELD", "audio")
        self.asr_response_field = os.getenv("NATLAS_ASR_RESPONSE_FIELD", "text")
        self.llm_response_field = os.getenv("NATLAS_LLM_RESPONSE_FIELD", "text")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    @staticmethod
    def _payload_text(payload: dict, preferred: str) -> str:
        value = payload.get(preferred)
        if isinstance(value, str) and value.strip():
            return value
        for key in ("text", "transcript", "generated_text", "response", "output"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value
        raise RuntimeError(f"N-ATLAS response did not contain a text field; expected {preferred!r}")

    def transcribe_audio(self, language: str, audio: bytes, filename: str = "voice.ogg", content_type: str = "audio/ogg") -> NatlasResult:
        if self.mode != "http":
            return NatlasResult("", "mock", "mock-asr-not-n-atlas", 1)
        if not self.asr_url or not self.api_key:
            raise RuntimeError("N-ATLAS ASR configuration is incomplete")
        start = time.perf_counter()
        files = {self.asr_file_field: (filename, audio, content_type)}
        response = httpx.post(self.asr_url, params={"language": language}, files=files, headers=self._headers(), timeout=60)
        response.raise_for_status()
        payload = response.json()
        return NatlasResult(self._payload_text(payload, self.asr_response_field), "http", payload.get("model", "N-ATLAS-ASR"), int((time.perf_counter()-start)*1000))

    def transcribe(self, language: str, audio_text: str) -> NatlasResult:
        if self.mode == "http":
            if not self.asr_url or not self.api_key:
                raise RuntimeError("N-ATLAS ASR configuration is incomplete")
            start = time.perf_counter()
            response = httpx.post(self.asr_url, json={"language": language, "audio": audio_text}, headers=self._headers(), timeout=30)
            response.raise_for_status()
            payload = response.json()
            return NatlasResult(self._payload_text(payload, self.asr_response_field), "http", payload.get("model", "N-ATLAS-ASR"), int((time.perf_counter()-start)*1000))
        return NatlasResult(audio_text, "mock", "mock-asr-not-n-atlas", 1)

    def generate(self, language: str, prompt: str) -> NatlasResult:
        if self.mode == "http":
            if not self.llm_url or not self.api_key:
                raise RuntimeError("N-ATLAS LLM configuration is incomplete")
            start = time.perf_counter()
            response = httpx.post(self.llm_url, json={"language": language, "prompt": prompt}, headers={**self._headers(), "Content-Type": "application/json"}, timeout=60)
            response.raise_for_status()
            payload = response.json()
            return NatlasResult(self._payload_text(payload, self.llm_response_field), "http", payload.get("model", "N-ATLAS-LLM"), int((time.perf_counter()-start)*1000))
        return NatlasResult("Ka fara da duba alamun amfanin gona a hankali, sannan ka tuntubi jami'in noma idan matsalar tana yaduwa. Wannan amsar gwaji ce ta mock mode, ba sakamakon N-ATLAS ba.", "mock", "mock-llm-not-n-atlas", 1)
