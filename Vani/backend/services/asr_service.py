import base64
import logging
import io
from typing import Dict, Any, Optional
import httpx
from backend.config import settings
from backend.services.audio_service import audio_service, AudioConversionError

logger = logging.getLogger(__name__)

class ASRService:
    def __init__(self):
        self.endpoint = settings.SRAVAANI_ENDPOINT
        self.local_model = None
        self._init_local_model()

    def _init_local_model(self):
        """Attempts to load local SraVaani PyTorch/HuggingFace model once at startup."""
        if not settings.USE_LOCAL_SRAVAANI_IF_AVAILABLE:
            return
        try:
            import os
            import torch
            from transformers import AutoModel
            device = "cuda" if torch.cuda.is_available() else "cpu"
            # Official model (gated on HuggingFace): accept its terms while logged in,
            # then put a read token in .env as HF_TOKEN.
            model_id = os.getenv("SRAVAANI_MODEL", "ARTPARK-IISc/SraVaani-1.0")
            hf_token = os.getenv("HF_TOKEN") or None
            print(f"[SraVaani] Loading {model_id} on {device} (first run downloads ~900 MB)...", flush=True)
            # The model card's usage: AutoModel + trust_remote_code, inference via model.transcribe(path)
            self.local_model = AutoModel.from_pretrained(model_id, trust_remote_code=True, token=hf_token).to(device).eval()
            self.device = device
            print("[SraVaani] ARTPARK-IISc SraVaani 1.0 loaded successfully. Voice input is ON.", flush=True)
        except Exception as e:
            msg = str(e)
            if "gated" in msg.lower() or "401" in msg or "403" in msg or "restricted" in msg.lower():
                reason = "access denied: accept the model terms on HuggingFace and set HF_TOKEN in .env"
            else:
                reason = msg.splitlines()[0][:200] if msg else type(e).__name__
            print(f"[SraVaani] NOT loaded ({reason}). Voice input is OFF; typing still works.", flush=True)
            self.local_model = None

    async def transcribe_audio_base64(self, audio_base64: str) -> Dict[str, Any]:
        """
        Receives audioBase64, converts via ffmpeg to 16kHz mono WAV,
        and transcribes using SraVaani 1.0.
        Returns: { 'text': str, 'confidence': float, 'is_empty_or_noise': bool }
        """
        if not audio_base64 or not audio_base64.strip():
            return {"text": "", "confidence": 0.0, "is_empty_or_noise": True, "error": "No audio provided"}

        try:
            raw_bytes = audio_service.decode_base64_audio(audio_base64)
            wav_bytes = audio_service.convert_to_16k_mono_wav(raw_bytes)
        except AudioConversionError as ace:
            logger.warning(f"Audio conversion error: {ace}")
            return {"text": "", "confidence": 0.0, "is_empty_or_noise": True, "error": str(ace)}
        except Exception as e:
            logger.error(f"Unexpected audio decoding error: {e}")
            return {"text": "", "confidence": 0.0, "is_empty_or_noise": True, "error": str(e)}

        duration, is_noise = audio_service.check_audio_duration_and_energy(wav_bytes)
        if is_noise or duration < 0.3:
            return {"text": "", "confidence": 0.0, "is_empty_or_noise": True, "duration": duration}

        # 1. Try local SraVaani model if loaded
        if self.local_model is not None:
            try:
                import os
                import tempfile
                import torch
                # SraVaani transcribes from a file path: write the 16 kHz mono WAV to a temp file
                fd, wav_path = tempfile.mkstemp(suffix=".wav")
                try:
                    with os.fdopen(fd, "wb") as fh:
                        fh.write(wav_bytes)
                    with torch.no_grad():
                        hyps = self.local_model.transcribe(wav_path, return_hypotheses=True)
                finally:
                    try:
                        os.remove(wav_path)
                    except OSError:
                        pass
                # Result may be a list (or nested list) of Hypothesis objects or strings
                first = hyps
                while isinstance(first, (list, tuple)) and first:
                    first = first[0]
                text = (getattr(first, "text", first) if first is not None else "") or ""
                text = str(text).strip()
                return {"text": text, "confidence": 0.95, "is_empty_or_noise": len(text) == 0}
            except Exception as e:
                logger.error(f"Local SraVaani inference error: {e}")

        # 2. Try SraVaani HTTP endpoint
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    self.endpoint,
                    files={"audio": ("audio.wav", wav_bytes, "audio/wav")}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = data.get("text", "").strip()
                    return {"text": text, "confidence": data.get("confidence", 0.9), "is_empty_or_noise": len(text) == 0}
        except Exception:
            # Endpoint offline or not running
            pass

        # 3. Fallback: speech_recognition library if available
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(wav_bytes)) as source:
                audio_data = r.record(source)
                # Try Kannada (kn-IN)
                text = r.recognize_google(audio_data, language="kn-IN")
                return {"text": text.strip(), "confidence": 0.85, "is_empty_or_noise": len(text.strip()) == 0}
        except Exception:
            pass

        # 4. Graceful handling when no speech engine can identify content
        return {
            "text": "",
            "confidence": 0.0,
            "is_empty_or_noise": True,
            "note": "Audio processed but no intelligible speech detected"
        }

asr_service = ASRService()
