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

    def transcribe(self, language: str, audio_text: str) -> NatlasResult:
        if self.mode == "http":
            if not self.asr_url or not self.api_key:
                raise RuntimeError("N-ATLAS ASR configuration is incomplete")
            start = time.perf_counter()
            response = httpx.post(self.asr_url, json={"language": language, "audio": audio_text}, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
            response.raise_for_status()
            payload = response.json()
            return NatlasResult(payload["text"], "http", payload.get("model", "N-ATLAS-ASR"), int((time.perf_counter()-start)*1000))
        return NatlasResult(audio_text, "mock", "mock-asr-not-n-atlas", 1)

    def generate(self, language: str, prompt: str) -> NatlasResult:
        if self.mode == "http":
            if not self.llm_url or not self.api_key:
                raise RuntimeError("N-ATLAS LLM configuration is incomplete")
            start = time.perf_counter()
            response = httpx.post(self.llm_url, json={"language": language, "prompt": prompt}, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30)
            response.raise_for_status()
            payload = response.json()
            return NatlasResult(payload["text"], "http", payload.get("model", "N-ATLAS-LLM"), int((time.perf_counter()-start)*1000))
        return NatlasResult("Ka fara da duba alamun amfanin gona a hankali, sannan ka tuntubi jami'in noma idan matsalar tana yaduwa. Wannan amsar gwaji ce ta mock mode, ba sakamakon N-ATLAS ba.", "mock", "mock-llm-not-n-atlas", 1)
