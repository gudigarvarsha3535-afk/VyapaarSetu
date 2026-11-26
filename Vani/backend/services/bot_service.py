import logging
from typing import Dict, Any, Optional
from backend.models import BotMessageRequest, BotExecuteRequest, BotResponse, Product, Order
from backend.database import db
from backend.services.asr_service import asr_service
from backend.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class BotService:
    def __init__(self):
        self.conversation_state: Dict[str, Any] = {
            "pending_intent": None,
            "pending_product": None,
            "pending_unit": None,
            "awaiting": None
        }

    async def process_message(self, request: BotMessageRequest) -> BotResponse:
        """
        Coordinates voice transcription, camera/image attachments, LLM / fallback parsing,
        and backend execution.
        """
        transcribed_text = None
        user_text = request.text or ""

        # 1. Handle Voice Modality
        if request.inputType == "voice" or (request.audioBase64 and not user_text.strip()):
            asr_res = await asr_service.transcribe_audio_base64(request.audioBase64 or "")
            if asr_res.get("is_empty_or_noise"):
                return BotResponse(
                    success=True,
                    intent="CHAT_REPLY",
                    replyKn="ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಮತ್ತೊಮ್ಮೆ ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
                    updatedEntity=None,
                    refreshRequired=False,
                    transcribedText=""
                )
            user_text = asr_res.get("text", "")
            transcribed_text = user_text

        # 2. Handle Image Attachment Modality
        image_attached = bool(request.imageBase64 and request.imageBase64.strip())
        if image_attached and not user_text.strip():
            user_text = "ಈ ವಸ್ತುವನ್ನು ಸ್ಟೋರ್ ಗೆ ಸೇರಿಸಿ (Add this product to store)"

        # Check empty text after handling modalities
        if not user_text.strip():
            return BotResponse(
                success=True,
                intent="CHAT_REPLY",
                replyKn="ದಯವಿಟ್ಟು ಒಂದು ಸಂದೇಶವನ್ನು ನಮೂದಿಸಿ ಅಥವಾ ಮೈಕ್ ಬಟನ್ ಒತ್ತಿ ಮಾತನಾಡಿ.",
                updatedEntity=None,
                refreshRequired=False,
                transcribedText=transcribed_text
            )

        # Multi-turn clarification slot continuation
        if self.conversation_state.get("awaiting") == "QUANTITY":
            lower_u = user_text.lower()
            is_new_cmd = any(w in lower_u for w in [
                "discount", "off", "offer", "rate", "bele", "price", "order", "ord", "sales", "vyapara",
                "report", "add", "delete", "remove", "mugidide", "khali", "kali", "kaali"
            ])
            if is_new_cmd:
                self.conversation_state = {"awaiting": None}
            else:
                try:
                    from backend.services.vector_catalog_service import normalize_numbers
                    n_text = normalize_numbers(lower_u)
                except Exception:
                    n_text = lower_u
                import re
                m_cnt = re.search(r'(\d+)', n_text)
                if m_cnt:
                    count = int(m_cnt.group(1))
                    prod_name = self.conversation_state.get("pending_product", "Product")
                    unit_label = self.conversation_state.get("pending_unit", "1 packet")
                    self.conversation_state = {"awaiting": None}
                    return self.execute_intent(
                        BotExecuteRequest(
                            intent="UPDATE_STOCK",
                            payload={"productName": prod_name, "inStock": True, "stockCount": count, "unit": unit_label},
                            replyKn=f"{prod_name} ಸ್ಟಾಕ್ ಅನ್ನು {count} {unit_label}ಗೆ ನವೀಕರಿಸಲಾಗಿದೆ."
                        ),
                        transcribed_text=transcribed_text
                    )

        # 3. LLM / Fallback Intent Classification
        bot_intent_data = await llm_service.get_intent_and_payload(user_text, image_attached=image_attached)
        intent = bot_intent_data.get("intent", "CHAT_REPLY")
        payload = bot_intent_data.get("payload", {})
        reply_kn = bot_intent_data.get("replyKn", "ಕಾರ್ಯ ನಿರ್ವಹಿಸಲಾಗಿದೆ.")

        if payload.get("type") == "CLARIFICATION" and payload.get("productName"):
            self.conversation_state = {
                "pending_intent": "UPDATE_STOCK",
                "pending_product": payload.get("productName"),
                "pending_unit": payload.get("unit", "1 packet"),
                "awaiting": "QUANTITY"
            }

        # 4. Execute Intent if Mutating
        if intent in ["ADD_PRODUCT", "UPDATE_PRICE", "UPDATE_STOCK", "UPDATE_ORDER_STATUS", "GET_SALES_REPORT"]:
            return self.execute_intent(
                BotExecuteRequest(
                    intent=intent,
                    payload=payload,
                    replyKn=reply_kn
                ),
                image_base64=request.imageBase64,
                transcribed_text=transcribed_text
            )

        # Non-mutating conversational reply
        return BotResponse(
            success=True,
            intent=intent,
            replyKn=reply_kn,
            updatedEntity=None,
            refreshRequired=False,
            transcribedText=transcribed_text
        )

    def execute_intent(self, exec_req: BotExecuteRequest, image_base64: Optional[str] = None, transcribed_text: Optional[str] = None) -> BotResponse:
        intent = exec_req.intent
        payload = exec_req.payload
        reply_kn = exec_req.replyKn

        if intent == "ADD_PRODUCT":
            name = payload.get("name") or "New Store Product"
            unit = payload.get("unit") or "1 unit"
            orig_price = float(payload.get("originalPrice", 100))
            disc_price = float(payload.get("discountPrice", orig_price))
            category = payload.get("category", "General")
            stock_count = int(payload.get("stockCount", 10))
            
            # Use uploaded image if available, else payload imageUrl or default grocery image
            image_url = image_base64 or payload.get("imageUrl") or "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=400&q=80"

            new_prod = db.create_product({
                "name": name,
                "category": category,
                "unit": unit,
                "originalPrice": orig_price,
                "discountPrice": disc_price,
                "inStock": stock_count > 0,
                "stockCount": stock_count,
                "lowStockThreshold": 5,
                "imageUrl": image_url
            })

            kn_reply = reply_kn or f"{new_prod.name} ({new_prod.unit}) ₹{new_prod.discountPrice:.0f} ಗೆ ಸ್ಟೋರ್‌ಗೆ ಸೇರಿಸಲಾಗಿದೆ!"
            return BotResponse(
                success=True,
                intent="ADD_PRODUCT",
                replyKn=kn_reply,
                updatedEntity=new_prod,
                refreshRequired=True,
                transcribedText=transcribed_text
            )

        elif intent == "UPDATE_PRICE":
            prod_name = payload.get("productName", "")
            disc_price = payload.get("discountPrice")
            orig_price = payload.get("originalPrice")

            prod = db.find_product_by_name(prod_name)
            if not prod:
                return BotResponse(
                    success=False,
                    intent="UPDATE_PRICE",
                    replyKn=f"ಕ್ಷಮಿಸಿ, '{prod_name}' ಉತ್ಪನ್ನವು ಸ್ಟೋರ್‌ನಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ.",
                    updatedEntity=None,
                    refreshRequired=False,
                    transcribedText=transcribed_text
                )

            updates: Dict[str, Any] = {}
            if disc_price is not None:
                updates["discountPrice"] = float(disc_price)
            if orig_price is not None:
                updates["originalPrice"] = float(orig_price)

            updated_prod = db.update_product(prod.id, updates)
            kn_reply = reply_kn or f"{updated_prod.name} ಬೆಲೆ ₹{updated_prod.discountPrice:.0f} ಗೆ ಬದಲಾಯಿಸಲಾಗಿದೆ."
            return BotResponse(
                success=True,
                intent="UPDATE_PRICE",
                replyKn=kn_reply,
                updatedEntity=updated_prod,
                refreshRequired=True,
                transcribedText=transcribed_text
            )

        elif intent == "UPDATE_STOCK":
            # Multi-item batch update
            items_list = payload.get("items")
            if items_list and isinstance(items_list, list):
                updated_entities = []
                for it in items_list:
                    pname = it.get("productName", "")
                    p_instock = it.get("inStock", True)
                    p_count = it.get("stockCount", 10)
                    p_unit = it.get("unit", "1 packet")
                    prod = db.find_product_by_name(pname)
                    if prod:
                        up = db.update_product(prod.id, {"inStock": p_instock, "stockCount": p_count})
                        updated_entities.append(up)
                    else:
                        new_p = db.create_product({
                            "name": pname,
                            "category": "General",
                            "unit": p_unit,
                            "originalPrice": 50,
                            "discountPrice": 50,
                            "inStock": p_instock,
                            "stockCount": p_count
                        })
                        updated_entities.append(new_p)
                return BotResponse(
                    success=True,
                    intent="UPDATE_STOCK",
                    replyKn=reply_kn,
                    updatedEntity=updated_entities,
                    refreshRequired=True,
                    transcribedText=transcribed_text
                )

            # Single-item update
            prod_name = payload.get("productName", "")
            in_stock = payload.get("inStock")
            stock_count = payload.get("stockCount")

            prod = db.find_product_by_name(prod_name)
            if not prod:
                # If positive arrival of a new item, add to store
                if stock_count is not None and stock_count > 0:
                    unit_val = payload.get("unit", "1 packet")
                    prod = db.create_product({
                        "name": prod_name,
                        "category": "General",
                        "unit": unit_val,
                        "originalPrice": 50,
                        "discountPrice": 50,
                        "inStock": True,
                        "stockCount": int(stock_count)
                    })
                    return BotResponse(
                        success=True,
                        intent="UPDATE_STOCK",
                        replyKn=reply_kn or f"{prod.name} ಸ್ಟಾಕ್ ಅನ್ನು {stock_count} ಗೆ ನವೀಕರಿಸಲಾಗಿದೆ.",
                        updatedEntity=prod,
                        refreshRequired=True,
                        transcribedText=transcribed_text
                    )
                return BotResponse(
                    success=False,
                    intent="UPDATE_STOCK",
                    replyKn=f"ಕ್ಷಮಿಸಿ, '{prod_name}' ಉತ್ಪನ್ನವು ಸ್ಟೋರ್‌ನಲ್ಲಿ ಕಂಡುಬಂದಿಲ್ಲ.",
                    updatedEntity=None,
                    refreshRequired=False,
                    transcribedText=transcribed_text
                )

            updates: Dict[str, Any] = {}
            if in_stock is not None:
                updates["inStock"] = bool(in_stock)
            if stock_count is not None:
                updates["stockCount"] = int(stock_count)
                if in_stock is None:
                    updates["inStock"] = int(stock_count) > 0

            # If marked out of stock and stockCount wasn't set, set to 0
            if in_stock is False and stock_count is None:
                updates["stockCount"] = 0

            updated_prod = db.update_product(prod.id, updates)
            if not updated_prod.inStock:
                kn_reply = reply_kn or f"{updated_prod.name} ಸ್ಟಾಕ್ ಮುಗಿದಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ."
            else:
                kn_reply = reply_kn or f"{updated_prod.name} ಸ್ಟಾಕ್ ಅನ್ನು {updated_prod.stockCount} ಗೆ ನವೀಕರಿಸಲಾಗಿದೆ."

            return BotResponse(
                success=True,
                intent="UPDATE_STOCK",
                replyKn=kn_reply,
                updatedEntity=updated_prod,
                refreshRequired=True,
                transcribedText=transcribed_text
            )

        elif intent == "UPDATE_ORDER_STATUS":
            order_id = payload.get("orderId", "")
            status = payload.get("status", "PACKED").upper()

            order = db.get_order(order_id)
            if not order:
                return BotResponse(
                    success=False,
                    intent="UPDATE_ORDER_STATUS",
                    replyKn=f"ಕ್ಷಮಿಸಿ, ಆರ್ಡರ್ #{order_id} ಕಂಡುಬಂದಿಲ್ಲ.",
                    updatedEntity=None,
                    refreshRequired=False,
                    transcribedText=transcribed_text
                )

            updated_order = db.update_order_status(order.id, status)
            kn_reply = reply_kn or f"Order #{updated_order.id} status ಅನ್ನು {status} ಗೆ ಬದಲಾಯಿಸಲಾಗಿದೆ."
            return BotResponse(
                success=True,
                intent="UPDATE_ORDER_STATUS",
                replyKn=kn_reply,
                updatedEntity=updated_order,
                refreshRequired=True,
                transcribedText=transcribed_text
            )

        elif intent == "GET_SALES_REPORT":
            report = db.get_sales_report()
            kn_reply = (
                f"ಇವತ್ತಿನ ಒಟ್ಟು ವ್ಯಾಪಾರ ₹{report['totalRevenue']:,.0f} ({report['totalOrders']} ಆರ್ಡರ್‌ಗಳು). "
                f"UPI: ₹{report['upiRevenue']:,.0f}, COD: ₹{report['codRevenue']:,.0f}. "
                f"ಕಡಿಮೆ ಸ್ಟಾಕ್ ಇರುವ ಸರಕುಗಳು: {report['lowStockCount']}."
            )
            return BotResponse(
                success=True,
                intent="GET_SALES_REPORT",
                replyKn=kn_reply,
                updatedEntity=report,
                refreshRequired=False,
                transcribedText=transcribed_text
            )

        # Fallback
        return BotResponse(
            success=False,
            intent="UNKNOWN",
            replyKn="ಸೂಕ್ತವಾದ ಆದೇಶ ಸಿಗಲಿಲ್ಲ.",
            updatedEntity=None,
            refreshRequired=False,
            transcribedText=transcribed_text
        )

bot_service = BotService()
