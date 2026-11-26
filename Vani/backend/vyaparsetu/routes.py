"""HTTP routes used by the VyaparSetu seller pages.

POST /api/vyaparsetu/bot/message
  Header: Authorization: Bearer <VyaparSetu seller access token>
  Body:   BotMessageRequest (text / audioBase64)
The token is verified with the VyaparSetu backend (/api/auth/me, role must be
'seller') before anything runs, and is never logged or stored.
"""
from fastapi import APIRouter, Header, HTTPException

from backend.models import BotMessageRequest, BotResponse
from backend.vyaparsetu.bot import vyaparsetu_bot
from backend.vyaparsetu.client import VyaparSetuError

router = APIRouter(prefix="/api/vyaparsetu", tags=["vyaparsetu"])

MAX_TEXT = 1000
MAX_AUDIO_B64 = 8 * 1024 * 1024  # ~6 MB of audio


@router.post("/bot/message", response_model=BotResponse)
async def vyaparsetu_bot_message(req: BotMessageRequest, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer ") or len(authorization) < 20:
        raise HTTPException(status_code=401, detail="Seller login required")
    token = authorization[len("Bearer "):].strip()

    if req.text and len(req.text) > MAX_TEXT:
        raise HTTPException(status_code=413, detail="Message is too long")
    if req.imageUrl and len(req.imageUrl) > 500:
        raise HTTPException(status_code=413, detail="Photo link is too long")
    if req.audioBase64 and len(req.audioBase64) > MAX_AUDIO_B64:
        raise HTTPException(status_code=413, detail="Voice message is too long")

    try:
        seller = await vyaparsetu_bot.client.me(token)
    except VyaparSetuError as err:
        if err.status in (401, 403):
            raise HTTPException(status_code=401, detail="Seller login required")
        raise HTTPException(status_code=502, detail="VyaparSetu backend is not reachable")
    except Exception:
        raise HTTPException(status_code=502, detail="VyaparSetu backend is not reachable")

    if seller.get("role") != "seller":
        raise HTTPException(status_code=403, detail="Only approved sellers can use Vani")

    return await vyaparsetu_bot.handle(req, token, seller)
