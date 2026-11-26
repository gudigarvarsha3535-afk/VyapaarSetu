import base64
import os
import subprocess
import tempfile
import wave
import logging
from typing import Tuple, Optional
from backend.config import settings

logger = logging.getLogger(__name__)

class AudioConversionError(Exception):
    pass

class AudioService:
    def __init__(self, ffmpeg_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or settings.FFMPEG_PATH

    def decode_base64_audio(self, audio_base64: str) -> bytes:
        """Decodes base64 string, stripping data URI prefix if present."""
        if not audio_base64 or not audio_base64.strip():
            raise AudioConversionError("Audio base64 string is empty.")
        
        # Strip data URL prefix like 'data:audio/webm;base64,'
        if "," in audio_base64:
            audio_base64 = audio_base64.split(",", 1)[1]
            
        try:
            return base64.b64decode(audio_base64.strip())
        except Exception as e:
            raise AudioConversionError(f"Failed to decode base64 audio: {str(e)}")

    def convert_to_16k_mono_wav(self, audio_bytes: bytes) -> bytes:
        """
        Converts WebM, OGG, MP4, AAC or WAV bytes to 16kHz mono 16-bit PCM WAV using ffmpeg.
        """
        if not audio_bytes or len(audio_bytes) < 10:
            raise AudioConversionError("Audio data too short or empty.")

        with tempfile.NamedTemporaryFile(suffix=".input", delete=False) as in_file:
            in_file.write(audio_bytes)
            in_file_path = in_file.name

        out_file_path = in_file_path + ".wav"

        try:
            # Run ffmpeg to convert to 16000 Hz, 1 channel (mono), pcm_s16le
            cmd = [
                self.ffmpeg_path,
                "-y",  # Overwrite output
                "-i", in_file_path,
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                "-f", "wav",
                out_file_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=15
            )

            if result.returncode != 0:
                err_msg = result.stderr.decode("utf-8", errors="ignore")
                logger.warning(f"ffmpeg conversion failed: {err_msg}")
                # Fallback check: is input already a WAV?
                try:
                    with wave.open(in_file_path, "rb") as wf:
                        if wf.getnchannels() in (1, 2) and wf.getframerate() > 0:
                            return audio_bytes
                except Exception:
                    pass
                raise AudioConversionError(f"ffmpeg conversion failed: {err_msg[:200]}")

            with open(out_file_path, "rb") as f:
                converted_bytes = f.read()

            return converted_bytes

        except subprocess.TimeoutExpired:
            raise AudioConversionError("ffmpeg conversion timed out.")
        except FileNotFoundError:
            # Fallback if ffmpeg executable is missing on machine
            logger.error(f"ffmpeg binary not found at '{self.ffmpeg_path}'.")
            # If already a valid WAV, return as is
            try:
                with wave.open(in_file_path, "rb") as wf:
                    return audio_bytes
            except Exception:
                raise AudioConversionError("ffmpeg binary not found and input is not standard WAV.")
        finally:
            for p in (in_file_path, out_file_path):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass

    def check_audio_duration_and_energy(self, wav_bytes: bytes) -> Tuple[float, bool]:
        """
        Returns (duration_seconds, is_silent_or_noisy).
        """
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_bytes)
                tmp_path = tmp.name

            with wave.open(tmp_path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate) if rate > 0 else 0.0

            os.remove(tmp_path)
            
            # Less than 0.3 seconds is empty or click noise
            is_noise = duration < 0.3
            return duration, is_noise
        except Exception:
            return 0.0, True

audio_service = AudioService()
