"""Vani bot running on a real VyaparSetu shop.

Reuses Vani's ASR + LLM/fallback intent parsing, then executes the intent
through the VyaparSetu API with the seller's own token.

VyaparSetu data model (products): name, description, price, image_url, is_active.
There is no stock-count column and no orders API yet, so:
  * UPDATE_STOCK "out of stock"  -> product hidden from the store (is_active = false)
  * UPDATE_STOCK "in stock"      -> product shown again (is_active = true)
  * UPDATE_ORDER_STATUS          -> polite "not available yet" reply, nothing changed
  * GET_SALES_REPORT             -> real figures: no orders yet, plus product counts
"""
import hashlib
import logging
import re
import time
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz

from backend.models import BotMessageRequest, BotResponse
from backend.services.asr_service import asr_service
from backend.services.llm_service import llm_service
from backend.services.vector_catalog_service import vector_catalog
from backend.vyaparsetu.client import VyaparSetuClient, VyaparSetuError, vyaparsetu_client

logger = logging.getLogger(__name__)

MATCH_THRESHOLD = 75
STATE_TTL_SECONDS = 15 * 60
MAX_NAME = 120


def _reply(intent: str, text: str, success: bool = True, entity: Any = None,
           refresh: bool = False, transcribed: Optional[str] = None) -> BotResponse:
    return BotResponse(success=success, intent=intent, replyKn=text, updatedEntity=entity,
                       refreshRequired=refresh, transcribedText=transcribed)


def _money(value: Any) -> str:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "₹0"
    return f"₹{n:,.0f}" if n.is_integer() else f"₹{n:,.2f}"


def _name_candidates(product_name: str, user_text: str) -> List[str]:
    """Vani's canonical name, the alias in brackets and the user's own words."""
    cands: List[str] = []
    if product_name:
        cands.append(product_name)
        cands.extend(p.strip() for p in re.split(r"[()/,]", product_name) if p.strip())
    words = [w for w in re.findall(r"[\wಀ-೿]+", user_text or "") if len(w) >= 3 and not w.isdigit()]
    cands.extend(words)
    seen, out = set(), []
    for c in cands:
        key = c.lower()
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


STOP_WORDS = {"rate", "bele", "price", "maadi", "madi", "stock", "mugidide", "khali", "kaali", "add", "beku",
              "ide", "illa", "rupayi", "rupees", "rs", "kg", "gram", "ml", "litre", "packet", "order", "discount"}


UNIT_RE = re.compile(r"^\d+(?:\.\d+)?(kg|g|gm|gram|grams|ml|l|ltr|litre|liter|pc|pcs)?$", re.I)


@lru_cache(maxsize=512)
def _canonical(text: str) -> str:
    """Vani's catalogue name for a product phrase ('Tuppa' -> 'Ghee'), '' if unknown."""
    if not text or not text.strip():
        return ""
    try:
        hit = vector_catalog.find_canonical_product(text)
    except Exception:  # catalogue problems must never break the shop actions
        return ""
    return str(hit[0]).lower() if hit else ""


def _words(text: str) -> List[str]:
    out = []
    for w in re.findall(r"[\wಀ-೿]+", (text or "").lower()):
        if len(w) >= 3 and w not in STOP_WORDS and not UNIT_RE.match(w):
            out.append(w)
    return out


def _match_score(product: Dict[str, Any], product_name: str, user_text: str, mention_canons: List[str]) -> int:
    pname = str(product.get("name") or "")
    p_canon = _canonical(pname)
    # 1. Same catalogue item ('Tuppa' and 'Ghee 500ml' are both Ghee)
    if p_canon and p_canon in mention_canons:
        return 100
    # 2. Catalogue items that share a word ('Nandini Pure Ghee' and 'Ghee')
    if p_canon:
        p_cwords = set(_words(p_canon))
        for c in mention_canons:
            if p_cwords & set(_words(c)):
                return 95
    # 3. A word of the product name said by the seller (tolerates small spelling slips)
    p_words = _words(pname)
    said = _words(product_name) + _words(user_text)
    best_word = 0
    for pw in p_words:
        for sw in said:
            if len(sw) >= 4 or len(pw) <= 4:
                best_word = max(best_word, fuzz.ratio(pw, sw))
    if best_word >= 85:
        return 90
    # 4. Whole-phrase fuzzy match as the last resort
    cands = [c for c in _name_candidates(product_name, user_text) if c.lower() not in STOP_WORDS]
    hay = (pname + " " + str(product.get("description") or "")).lower()
    best = 0
    for c in cands:
        cl = c.lower()
        best = max(best, fuzz.token_set_ratio(cl, pname.lower()), fuzz.partial_ratio(cl, hay) if len(cl) >= 4 else 0)
    return min(int(best), 89)


def find_product(products: List[Dict[str, Any]], product_name: str, user_text: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Best match among the seller's products.
    Returns (match, close_alternatives). match is None if not confident."""
    if not products:
        return None, []
    mention_canons = [c for c in {_canonical(product_name), _canonical(user_text)} if c]
    if product_name:
        mention_canons.append(product_name.lower())
    scored = [(_match_score(p, product_name, user_text, mention_canons), p) for p in products]
    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top = scored[0]
    if top_score < MATCH_THRESHOLD:
        return None, [p for s, p in scored[:3] if s >= 50]
    ties = [p for s, p in scored if s == top_score]
    if len(ties) > 1:
        return None, ties[:3]
    return top, []


# ---- local corrections on top of Vani's parser ------------------------------------------
# Vani's offline parser was built for its demo shop; these rules fix the commands it
# misreads for a real shop (delete, Kannada-script add, stock back in, order commands).
ORDER_RE = re.compile(r"\border(s)?\b|ಆರ್ಡರ್|\baardar\b", re.I)
DELETE_RE = re.compile(r"\b(delete|remove|tegedu|tegedi|tegi|tegeyiri|alisi|alisu)\b|ತೆಗೆ|ಅಳಿಸ", re.I)
ADD_RE = re.compile(r"\b(add|serisi|sersi|serisu|haaki|haki)\b|ಸೇರಿಸ|ಹಾಕಿ", re.I)
STOCK_IN_RE = re.compile(r"bandide|ಬಂದಿದೆ|back in stock|in stock|\bavailable\b|\blabhya\b|ಲಭ್ಯ", re.I)
# Product photos are uploaded by the seller page to VyaparSetu storage first; Vani only
# receives the resulting public URL and only accepts URLs from the product-images bucket.
PHOTO_URL_RE = re.compile(r"^https?://[^\s\"'<>]+/storage/v1/object/public/product-images/[0-9a-zA-Z-]+/[0-9a-zA-Z-]+\.(jpg|jpeg|png|webp)$")
YES_RE = re.compile(r"^\s*(haudu|houdu|hau|yes|ok|okay|sari|confirm|delete)\b|^\s*(ಹೌದು|ಸರಿ)", re.I)
NO_RE = re.compile(r"^\s*(illa|beda|no|cancel)\b|^\s*(ಇಲ್ಲ|ಬೇಡ)", re.I)
UNIT_IN_TEXT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(kg|kgs|g|gm|gram|grams|ml|l|ltr|litre|liter|ಕೆಜಿ|ಗ್ರಾಂ|ಮಿಲಿ|ಲೀಟರ್)(?![\wಀ-೿])", re.I)
ADD_FILLER = {"add", "serisi", "sersi", "serisu", "haaki", "haki", "maadi", "madi", "rupayi", "rupees", "rs", "beku",
              "ರೂಪಾಯಿ", "ರೂ", "ಸೇರಿಸಿ", "ಸೇರಿಸು", "ಹಾಕಿ", "ಮಾಡಿ", "ಬೇಕು"}


def _parse_add(user_text: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """'ಸಕ್ಕರೆ 1kg 45 ರೂಪಾಯಿ ಸೇರಿಸಿ' -> {name, unit, originalPrice}. None if no price is said."""
    unit_m = UNIT_IN_TEXT_RE.search(user_text)
    rest = UNIT_IN_TEXT_RE.sub(" ", user_text)
    numbers = re.findall(r"\d+(?:\.\d+)?", rest)
    if not numbers:
        return None
    name = str(payload.get("productName") or payload.get("name") or "").strip()
    if not name:
        words = [w for w in re.findall(r"[^\s\d₹.,!?]+", rest) if w.lower() not in ADD_FILLER]
        name = " ".join(words).strip()
    if not name:
        return None
    unit = (unit_m.group(1) + unit_m.group(2)) if unit_m else ""
    return {"name": name, "unit": unit, "originalPrice": float(numbers[-1])}


def correct_intent(user_text: str, intent: str, payload: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    text = user_text or ""
    if intent != "GET_SALES_REPORT" and ORDER_RE.search(text):
        return "UPDATE_ORDER_STATUS", payload
    if DELETE_RE.search(text):
        return "DELETE_PRODUCT", {"productName": payload.get("productName") or payload.get("name") or ""}
    if intent != "ADD_PRODUCT" and ADD_RE.search(text):
        add = _parse_add(text, payload)
        if add:
            return "ADD_PRODUCT", add
    if STOCK_IN_RE.search(text) and "?" not in text:
        if intent == "CHAT_REPLY" or (intent == "UPDATE_STOCK" and payload.get("inStock") is None):
            return "UPDATE_STOCK", {"productName": payload.get("productName") or "", "inStock": True}
    if intent == "CHAT_REPLY" and payload.get("type") == "PRODUCT_QUERY" and payload.get("productName"):
        return "PRODUCT_QUERY", payload
    return intent, payload


class VyaparSetuBot:
    def __init__(self, client: VyaparSetuClient = vyaparsetu_client):
        self.client = client
        self._state: Dict[str, Dict[str, Any]] = {}  # per seller, keyed by a hash of the user id

    # ---- per-seller conversation memory -------------------------------------------
    def _key(self, user_id: str) -> str:
        return hashlib.sha256(user_id.encode("utf-8")).hexdigest()

    def _get_state(self, user_id: str) -> Dict[str, Any]:
        st = self._state.get(self._key(user_id))
        if not st or time.time() - st.get("at", 0) > STATE_TTL_SECONDS:
            return {}
        return st

    def _set_state(self, user_id: str, state: Optional[Dict[str, Any]]) -> None:
        key = self._key(user_id)
        if state:
            state["at"] = time.time()
            self._state[key] = state
        else:
            self._state.pop(key, None)

    # ---- main entry ------------------------------------------------------------------
    async def handle(self, request: BotMessageRequest, token: str, seller: Dict[str, Any]) -> BotResponse:
        user_id = str(seller.get("id"))
        transcribed: Optional[str] = None
        user_text = (request.text or "").strip()

        if request.inputType == "voice" or (request.audioBase64 and not user_text):
            asr = await asr_service.transcribe_audio_base64(request.audioBase64 or "")
            if asr.get("is_empty_or_noise") or not (asr.get("text") or "").strip():
                return _reply("CHAT_REPLY", "ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.", transcribed="")
            user_text = asr["text"].strip()
            transcribed = user_text

        photo = (request.imageUrl or "").strip()
        if photo and not PHOTO_URL_RE.match(photo):
            return _reply("CHAT_REPLY", "ಈ ಫೋಟೋ ಸ್ವೀಕರಿಸಲಾಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು 📷 ಬಟನ್ ಬಳಸಿ ಮತ್ತೆ ಫೋಟೋ ಸೇರಿಸಿ.", success=False, transcribed=transcribed)
        if not photo and request.imageBase64 and request.imageBase64.strip():
            return _reply("CHAT_REPLY", "ಫೋಟೋ ಸೇರಿಸಲು ಚಾಟ್‌ನ 📷 ಬಟನ್ ಬಳಸಿ, ನಂತರ ಸರಕಿನ ಹೆಸರು ಹೇಳಿ.", transcribed=transcribed)

        state = self._get_state(user_id)
        if photo and not user_text:
            self._set_state(user_id, {"awaiting": "PHOTO", "url": photo})
            return _reply("CHAT_REPLY", "📷 ಫೋಟೋ ಸಿಕ್ಕಿತು! ಇದು ಯಾವ ಸರಕಿನದು? ಸರಕಿನ ಹೆಸರು ಹೇಳಿ (ಉದಾ: \"Tuppa\"), "
                          "ಅಥವಾ ಹೊಸ ಸರಕಾಗಿ ಸೇರಿಸಲು: \"Tuppa 500ml 295 add maadi\".", transcribed=transcribed)

        if not user_text:
            return _reply("CHAT_REPLY", "ದಯವಿಟ್ಟು ಒಂದು ಸಂದೇಶವನ್ನು ಟೈಪ್ ಮಾಡಿ.", transcribed=transcribed)

        # Follow-up to a question we asked earlier (e.g. the price of a new product)
        if state.get("awaiting") == "PRICE":
            m = re.search(r"(\d+(?:\.\d+)?)", user_text)
            if m:
                self._set_state(user_id, None)
                return await self._add_product(token, {"name": state["name"], "unit": state.get("unit"), "imageUrl": state.get("photo")},
                                               float(m.group(1)), transcribed)
        if state.get("awaiting") == "PHOTO" and not photo:
            if NO_RE.search(user_text):
                self._set_state(user_id, None)
                return _reply("CHAT_REPLY", "ಸರಿ, ಫೋಟೋ ಬಳಸಲಾಗಿಲ್ಲ.", success=False, transcribed=transcribed)
            photo = state.get("url") or ""
        if state.get("awaiting") == "DELETE":
            self._set_state(user_id, None)
            if YES_RE.search(user_text):
                try:
                    await self.client.delete_product(token, state["id"])
                except VyaparSetuError as err:
                    if err.status == 404:
                        return _reply("DELETE_PRODUCT", f"\"{state['name']}\" ಈಗಾಗಲೇ ಅಂಗಡಿಯಲ್ಲಿ ಇಲ್ಲ.", success=False, transcribed=transcribed)
                    return _reply("DELETE_PRODUCT", f"ಕ್ಷಮಿಸಿ, ಅಳಿಸಲಾಗಲಿಲ್ಲ: {err.message}", success=False, transcribed=transcribed)
                return _reply("DELETE_PRODUCT", f"\"{state['name']}\" ನಿಮ್ಮ ಅಂಗಡಿಯಿಂದ ಅಳಿಸಲಾಗಿದೆ.",
                              entity={"id": state["id"], "name": state["name"], "deleted": True}, refresh=True, transcribed=transcribed)
            if NO_RE.search(user_text):
                return _reply("DELETE_PRODUCT", f"ಸರಿ, \"{state['name']}\" ಅಳಿಸಲಾಗಿಲ್ಲ.", success=False, transcribed=transcribed)
            # anything else: forget the pending delete and handle the new message normally

        parsed = await llm_service.get_intent_and_payload(user_text, image_attached=False)
        intent = parsed.get("intent", "CHAT_REPLY")
        payload = parsed.get("payload") or {}
        reply_kn = parsed.get("replyKn") or "ನಾನು ನಿಮ್ಮ ಅಂಗಡಿಯ ಸಹಾಯಕಿ ವಾಣಿ. ಸರಕು, ಬೆಲೆ, ಸ್ಟಾಕ್ ಮತ್ತು ವರದಿಗಳಲ್ಲಿ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ."
        self._set_state(user_id, None)
        intent, payload = correct_intent(user_text, intent, payload)

        try:
            if photo:
                if intent == "ADD_PRODUCT":
                    payload = {**payload, "imageUrl": photo}
                else:
                    return await self._set_photo(token, user_id, photo, payload, user_text, transcribed)

            if intent == "DELETE_PRODUCT":
                product, problem = await self._resolve(token, str(payload.get("productName") or ""), user_text)
                if problem:
                    return _reply("DELETE_PRODUCT", problem, success=False, transcribed=transcribed)
                self._set_state(user_id, {"awaiting": "DELETE", "id": product["id"], "name": product["name"]})
                return _reply("DELETE_PRODUCT",
                              f"\"{product['name']}\" ({_money(product.get('price'))}) ಅನ್ನು ಶಾಶ್ವತವಾಗಿ ಅಳಿಸಬೇಕೆ? "
                              f"ಖಚಿತಪಡಿಸಲು \"ಹೌದು\" ಎನ್ನಿ, ಬೇಡವಾದರೆ \"ಬೇಡ\". (ಕೇವಲ ಮರೆಮಾಡಲು: \"{product['name']} stock illa\")",
                              success=True, entity=product, transcribed=transcribed)

            if intent == "PRODUCT_QUERY":
                product, problem = await self._resolve(token, str(payload.get("productName") or ""), user_text)
                if problem:
                    return _reply("CHAT_REPLY", problem, success=False, transcribed=transcribed)
                status = "ಅಂಗಡಿಯಲ್ಲಿ ಲಭ್ಯ" if product.get("is_active") else "ಸ್ಟಾಕ್ ಇಲ್ಲ — ಅಂಗಡಿಯಿಂದ ಮರೆಮಾಡಲಾಗಿದೆ"
                return _reply("CHAT_REPLY", f"{product['name']}: {_money(product.get('price'))}, {status}.",
                              entity=product, transcribed=transcribed)

            if intent == "ADD_PRODUCT":
                price = payload.get("discountPrice") or payload.get("originalPrice")
                # The parser invents a demo price (100) and unit ("1 unit") when the seller
                # said none; only trust a price if a number was actually said.
                if not re.findall(r"\d+(?:\.\d+)?", UNIT_IN_TEXT_RE.sub(" ", user_text)):
                    price = None
                if str(payload.get("unit") or "").strip().lower() == "1 unit":
                    payload = {**payload, "unit": ""}
                name = str(payload.get("name") or "").strip()
                if not name:
                    return _reply("CHAT_REPLY", "ಯಾವ ಸರಕನ್ನು ಸೇರಿಸಬೇಕು? ಹೆಸರು ಮತ್ತು ಬೆಲೆ ಹೇಳಿ, ಉದಾ: \"Tuppa 500ml 295 add maadi\".", transcribed=transcribed)
                if price in (None, "", 0):
                    self._set_state(user_id, {"awaiting": "PRICE", "name": name, "unit": payload.get("unit"), "photo": payload.get("imageUrl")})
                    return _reply("CHAT_REPLY", f"{name} ಬೆಲೆ ಎಷ್ಟು? (ಉದಾ: 120)", transcribed=transcribed)
                return await self._add_product(token, payload, float(price), transcribed)

            if intent == "UPDATE_PRICE":
                return await self._update_price(token, payload, user_text, transcribed)

            if intent == "UPDATE_STOCK":
                return await self._update_stock(token, payload, user_text, transcribed)

            if intent == "UPDATE_ORDER_STATUS":
                return _reply("UPDATE_ORDER_STATUS",
                              "ಗ್ರಾಹಕರ ಆರ್ಡರ್ ವ್ಯವಸ್ಥೆ (ಆರ್ಡರ್ ತೆಗೆದುಕೊಳ್ಳುವುದು, ಸ್ವೀಕರಿಸುವುದು, ಕಳುಹಿಸುವುದು) VyaparSetu ನಲ್ಲಿ ಇನ್ನೂ ಆರಂಭವಾಗಿಲ್ಲ. "
                              "ಯಾವುದೇ ಆರ್ಡರ್ ಬದಲಾಯಿಸಲಾಗಿಲ್ಲ. (Orders are not available in VyaparSetu yet.)",
                              success=False, transcribed=transcribed)

            if intent == "GET_SALES_REPORT":
                products = await self.client.list_products(token)
                active = sum(1 for p in products if p.get("is_active"))
                hidden = len(products) - active
                report = {"totalRevenue": 0, "totalOrders": 0, "products": len(products), "activeProducts": active, "hiddenProducts": hidden}
                return _reply("GET_SALES_REPORT",
                              f"ಇವತ್ತಿನ ವ್ಯಾಪಾರ ₹0 (0 ಆರ್ಡರ್‌ಗಳು) — ಆರ್ಡರ್ ವ್ಯವಸ್ಥೆ ಇನ್ನೂ ಆರಂಭವಾಗಿಲ್ಲ. "
                              f"ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿ {active} ಸರಕುಗಳು ಲಭ್ಯ, {hidden} ಮರೆಮಾಡಲಾಗಿದೆ.",
                              entity=report, transcribed=transcribed)
        except VyaparSetuError as err:
            logger.warning("VyaparSetu API error %s: %s", err.status, err.message)
            if err.status in (401, 403):
                return _reply(intent, "ನಿಮ್ಮ ಲಾಗಿನ್ ಅವಧಿ ಮುಗಿದಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಲಾಗಿನ್ ಆಗಿ.", success=False, transcribed=transcribed)
            return _reply(intent, f"ಕ್ಷಮಿಸಿ, ಕಾರ್ಯ ಪೂರ್ಣಗೊಳ್ಳಲಿಲ್ಲ: {err.message}", success=False, transcribed=transcribed)

        # Identity, out-of-scope, clarification: Vani's own safe reply, nothing changed
        return _reply(intent if intent in ("CHAT_REPLY", "UNKNOWN") else "CHAT_REPLY", reply_kn, transcribed=transcribed)

    # ---- actions -----------------------------------------------------------------------
    async def _add_product(self, token: str, payload: Dict[str, Any], price: float, transcribed: Optional[str]) -> BotResponse:
        name = str(payload.get("name") or "").strip()[:MAX_NAME]
        unit = str(payload.get("unit") or "").strip()
        products = await self.client.list_products(token)
        existing, _ = find_product(products, name, "")
        if existing and fuzz.token_set_ratio(name.lower(), str(existing.get("name", "")).lower()) >= 95:
            return _reply("ADD_PRODUCT", f"\"{existing['name']}\" ಈಗಾಗಲೇ ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿದೆ ({_money(existing.get('price'))}). ಬೆಲೆ ಬದಲಾಯಿಸಲು \"{name} rate {int(price)} maadi\" ಎಂದು ಹೇಳಿ.",
                          success=False, entity=existing, transcribed=transcribed)
        product = await self.client.create_product(token, {
            "name": name,
            "price": price,
            "description": unit or None,
            **({"image_url": payload["imageUrl"]} if payload.get("imageUrl") else {}),
            "is_active": True,
        })
        unit_txt = f" ({unit})" if unit else ""
        if payload.get("imageUrl"):
            unit_txt += " 📷"
        return _reply("ADD_PRODUCT", f"{product['name']}{unit_txt} {_money(product['price'])} ಗೆ ನಿಮ್ಮ ಅಂಗಡಿಗೆ ಸೇರಿಸಲಾಗಿದೆ!",
                      entity=product, refresh=True, transcribed=transcribed)

    async def _set_photo(self, token: str, user_id: str, photo: str, payload: Dict[str, Any], user_text: str,
                         transcribed: Optional[str]) -> BotResponse:
        """Attach an uploaded photo to the product the seller named."""
        product, problem = await self._resolve(token, str(payload.get("productName") or payload.get("name") or ""), user_text)
        if problem:
            # keep the photo so the seller can just say the product name again
            self._set_state(user_id, {"awaiting": "PHOTO", "url": photo})
            return _reply("CHAT_REPLY", problem + " ಸರಕಿನ ಹೆಸರನ್ನು ಮತ್ತೆ ಹೇಳಿ, ಅಥವಾ \"ಬೇಡ\" ಎನ್ನಿ.", success=False, transcribed=transcribed)
        updated = await self.client.update_product(token, product["id"], {"image_url": photo})
        return _reply("UPDATE_PHOTO", f"📷 {updated['name']} ಗೆ ಹೊಸ ಫೋಟೋ ಸೇರಿಸಲಾಗಿದೆ.",
                      entity=updated, refresh=True, transcribed=transcribed)

    async def _resolve(self, token: str, product_name: str, user_text: str):
        products = await self.client.list_products(token)
        if not products:
            return None, "ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿ ಇನ್ನೂ ಯಾವುದೇ ಸರಕುಗಳಿಲ್ಲ. ಮೊದಲು ಸರಕು ಸೇರಿಸಿ, ಉದಾ: \"Tuppa 500ml 295 add maadi\"."
        match, alts = find_product(products, product_name, user_text)
        if match:
            return match, None
        if alts:
            names = ", ".join(f"\"{a['name']}\"" for a in alts)
            return None, f"ಯಾವ ಸರಕು ಎಂದು ಖಚಿತವಾಗಲಿಲ್ಲ. ಇವುಗಳಲ್ಲಿ ಯಾವುದು? {names}"
        label = product_name or user_text
        return None, f"ಕ್ಷಮಿಸಿ, '{label}' ನಿಮ್ಮ ಅಂಗಡಿಯಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ."

    async def _update_price(self, token: str, payload: Dict[str, Any], user_text: str, transcribed: Optional[str]) -> BotResponse:
        percent = payload.get("discountPercent")
        new_price = payload.get("discountPrice") if payload.get("discountPrice") is not None else payload.get("originalPrice")
        if percent is None and new_price is None:
            return _reply("UPDATE_PRICE", "ಹೊಸ ಬೆಲೆ ಎಷ್ಟು? ಉದಾ: \"Bellulli rate 80 maadi\".", success=False, transcribed=transcribed)
        product, problem = await self._resolve(token, str(payload.get("productName") or ""), user_text)
        if problem:
            return _reply("UPDATE_PRICE", problem, success=False, transcribed=transcribed)

        if percent is not None:
            # Percentage discount: ALWAYS computed from this seller's current price.
            # (Vani's parser fills discountPrice from its own demo catalogue, which is
            # unrelated to the seller's shop, so that value is ignored here.)
            try:
                pct = float(percent)
            except (TypeError, ValueError):
                pct = -1
            if not 0 < pct < 100:
                return _reply("UPDATE_PRICE", "ರಿಯಾಯಿತಿ ಶೇಕಡಾ 1 ರಿಂದ 99 ರ ನಡುವೆ ಇರಬೇಕು.", success=False, transcribed=transcribed)
            current = float(product.get("price") or 0)
            if current <= 0:
                return _reply("UPDATE_PRICE", f"{product['name']} ಗೆ ಈಗ ಬೆಲೆ ಇಲ್ಲ. ಮೊದಲು ಬೆಲೆ ಹೊಂದಿಸಿ.", success=False, transcribed=transcribed)
            discounted = round(current * (1 - pct / 100), 2)
            updated = await self.client.update_product(token, product["id"], {"price": discounted})
            return _reply("UPDATE_PRICE",
                          f"{updated['name']} ಮೇಲೆ {pct:g}% ರಿಯಾಯಿತಿ: {_money(current)} → {_money(updated['price'])}.",
                          entity=updated, refresh=True, transcribed=transcribed)

        updated = await self.client.update_product(token, product["id"], {"price": float(new_price)})
        return _reply("UPDATE_PRICE", f"{updated['name']} ಬೆಲೆ {_money(updated['price'])} ಗೆ ಬದಲಾಯಿಸಲಾಗಿದೆ.",
                      entity=updated, refresh=True, transcribed=transcribed)

    async def _update_stock(self, token: str, payload: Dict[str, Any], user_text: str, transcribed: Optional[str]) -> BotResponse:
        items = payload.get("items") if isinstance(payload.get("items"), list) else [payload]
        done: List[Dict[str, Any]] = []
        problems: List[str] = []
        for it in items:
            in_stock = it.get("inStock")
            if in_stock is None and it.get("stockCount") is not None:
                in_stock = int(it.get("stockCount") or 0) > 0
            if in_stock is None:
                problems.append("ಸ್ಟಾಕ್ ಇದೆಯೇ ಅಥವಾ ಮುಗಿದಿದೆಯೇ ಎಂದು ತಿಳಿಸಿ.")
                continue
            product, problem = await self._resolve(token, str(it.get("productName") or ""), user_text if len(items) == 1 else "")
            if problem:
                problems.append(problem)
                continue
            updated = await self.client.update_product(token, product["id"], {"is_active": bool(in_stock)})
            done.append(updated)

        if not done:
            return _reply("UPDATE_STOCK", " ".join(problems) or "ಯಾವುದೇ ಬದಲಾವಣೆ ಮಾಡಲಾಗಿಲ್ಲ.", success=False, transcribed=transcribed)
        parts = []
        for p in done:
            parts.append(f"{p['name']}: " + ("ಅಂಗಡಿಯಲ್ಲಿ ಮತ್ತೆ ಲಭ್ಯ" if p.get("is_active") else "ಸ್ಟಾಕ್ ಮುಗಿದಿದೆ — ಅಂಗಡಿಯಿಂದ ಮರೆಮಾಡಲಾಗಿದೆ"))
        note = " (ಸ್ಟಾಕ್ ಸಂಖ್ಯೆ ಇನ್ನೂ ಉಳಿಸಲಾಗುವುದಿಲ್ಲ.)"
        extra = (" " + " ".join(problems)) if problems else ""
        return _reply("UPDATE_STOCK", "; ".join(parts) + "." + note + extra,
                      entity=done if len(done) > 1 else done[0], refresh=True, transcribed=transcribed)


vyaparsetu_bot = VyaparSetuBot()
