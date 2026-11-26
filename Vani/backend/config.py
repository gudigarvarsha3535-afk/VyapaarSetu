import os
import shutil
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

def detect_ffmpeg_path() -> str:
    """Find a functional ffmpeg binary on the system or return 'ffmpeg'."""
    custom = os.getenv("FFMPEG_PATH")
    if custom and Path(custom).exists():
        return custom
    
    in_path = shutil.which("ffmpeg")
    if in_path:
        return in_path

    # Check common Windows paths
    candidates = [
        r"C:\Program Files\KeyShot12\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        r"C:\Users\Asus\AppData\Local\Programs\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return "ffmpeg"

class Settings:
    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "5173"))
    
    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()  # "gemini" or "self_hosted"
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", os.getenv("GEMINI_API_KEY", ""))
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/api/chat")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash" if os.getenv("LLM_PROVIDER") != "self_hosted" else "gemma3:4b")
    LLM_TIMEOUT_SECONDS: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "10"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    
    # Audio & ASR Settings
    FFMPEG_PATH: str = detect_ffmpeg_path()
    SRAVAANI_ENDPOINT: str = os.getenv("SRAVAANI_ENDPOINT", "http://localhost:8001/transcribe")
    USE_LOCAL_SRAVAANI_IF_AVAILABLE: bool = os.getenv("USE_LOCAL_SRAVAANI", "true").lower() == "true"

settings = Settings()
