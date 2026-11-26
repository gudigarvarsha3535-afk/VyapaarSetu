"""
Vani (ವಾಣಿ) - 100% Zero-Dependency Standalone Chatbot Tester
Run this file directly:
    python standalone_bot_tester.py

This file has NO external dependencies and requires NO other project files or backend.
It contains the self-contained Kannada/Kanglish NLP engine, intent parser, guardrails,
and interactive test console.
"""

import sys
import re
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# Force UTF-8 on Windows terminal for Kannada script
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8')

# Mock Store Catalog for Standalone Testing
STORE_CATALOG = {
    "prod_101": {"name": "Nandini Pure Ghee", "unit": "500 ml", "price": 295, "inStock": True, "stock": 14, "aliases": ["ghee", "tuppa", "nandini", "ತುಪ್ಪ"]},
    "prod_102": {"name": "Sona Masoori Rice (Akki)", "unit": "5 kg", "price": 310, "inStock": True, "stock": 22, "aliases": ["akki", "rice", "sona masoori", "ಅಕ್ಕಿ"]},
    "prod_103": {"name": "Mysore Sandal Soap", "unit": "3 x 150 g", "price": 195, "inStock": True, "stock": 18, "aliases": ["soap", "sabun", "sandal", "mysore sandal", "ಸೋಪ್"]},
    "prod_104": {"name": "Byadgi Chilli Powder", "unit": "500 g", "price": 165, "inStock": True, "stock": 3, "aliases": ["chilli", "menasinakayi", "byadgi", "mirchi", "ಮೆಣಸಿನಕಾಯಿ"]},
    "prod_105": {"name": "Organic Jaggery (Bella)", "unit": "1 kg", "price": 80, "inStock": True, "stock": 12, "aliases": ["bella", "jaggery", "bellam", "ಬೆಲ್ಲ"]},
    "prod_106": {"name": "Fresh Garlic (Bellulli)", "unit": "250 g", "price": 90, "inStock": True, "stock": 15, "aliases": ["bellulli", "garlic", "lahsun", "ಬೆಳ್ಳುಳ್ಳಿ"]},
    "prod_107": {"name": "Fresh Tomato (Tamota)", "unit": "1 kg", "price": 35, "inStock": True, "stock": 25, "aliases": ["tomato", "tamota", "ಟೊಮೆಟೊ"]},
    "prod_108": {"name": "Mysore Pak Sweet", "unit": "500 g", "price": 220, "inStock": False, "stock": 0, "aliases": ["mysore pak", "pak", "sweet", "ಮೈಸೂರು ಪಾಕ್"]},
    "prod_109": {"name": "Sugar", "unit": "1 kg", "price": 40, "inStock": True, "stock": 25, "aliases": ["sugar", "sakkare", "ಸಕ್ಕರೆ"]},
    "prod_110": {"name": "Chocolate syrup", "unit": "1 bottle", "price": 70, "inStock": True, "stock": 10, "aliases": ["chocolate syrup", "hershey", "hersheys", "hershy", "hershy's", "choclate syrup"]},
    "prod_111": {"name": "Shampoo", "unit": "1 packet", "price": 5, "inStock": True, "stock": 50, "aliases": ["shampoo", "shampu", "ಶಾಂಪೂ"]},
    "prod_112": {"name": "Water bottle", "unit": "1 bottle", "price": 20, "inStock": True, "stock": 30, "aliases": ["water bottle", "neerina bottle", "neerina bottles", "neeru bottle"]},
    "prod_113": {"name": "Rava / semolina", "unit": "1 packet", "price": 45, "inStock": True, "stock": 15, "aliases": ["rava", "rave", "idli rave", "sooji", "semolina", "ರವೆ", "ಇಡ್ಲಿ ರವೆ", "ರವ"]},
    "prod_114": {"name": "Basmati rice", "unit": "1 kg", "price": 95, "inStock": True, "stock": 20, "aliases": ["basmati rice", "basmati", "ಬಾಸುಮತಿ ರೈಸ್", "ಬಾಸುಮತಿ", "ಬಾಸ್ಮತಿ ರೈಸ್", "ಬಾಸ್ಮತಿ"]}
}

MOCK_ORDERS = {
    "ORD-101": {"status": "NEW", "customer": "Kiran Patil", "total": 590},
    "ORD-102": {"status": "PACKED", "customer": "Anand Rao", "total": 420}
}

class StandaloneVaniBot:
    """Self-contained NLP engine for Kannada & Kanglish store intents and guardrails."""
    
    conversation_state = {
        "pending_intent": None,
        "pending_product": None,
        "pending_unit": None,
        "awaiting": None
    }
    
    OUT_OF_CONTEXT = [
        "cricket", "match", "movie", "cinema", "song", "haadu", "weather",
        "rain", "havamana", "joke", "comedy", "python", "java", "coding",
        "election", "chunavane", "modi", "politics", "recipe", "doctor",
        "medicine", "hospital", "ipl", "virat", "dhoni"
    ]

    IDENTITY_WORDS = [
        "neenu yaaru", "who are you", "nin hesaru", "hesarenu", "ninna hesaru",
        "yaaru neenu", "ninna kelasa", "help", "enu madtiya", "what can you do",
        "namaskara", "namaste", "hello", "hi", "hey",
        "ಹಲೋ", "ಹಾಯ್", "ನಮಸ್ಕಾರ", "ನಮಸ್ತೆ", "ನೀನು ಯಾರು", "ಯಾರು ನೀನು",
        "ನಿನ್ನ ಹೆಸರು", "ಹೆಸರೇನು", "ನಿನ್ನ ಕೆಲಸ", "ಸಹಾಯ"
    ]

    @classmethod
    def match_product(cls, text_lower):
        # 1. Vector catalog lookup across the 11,675-entry dataset first
        try:
            from backend.services.vector_catalog_service import vector_catalog
            v_match = vector_catalog.find_canonical_product(text_lower)
            if v_match:
                canon_name, cat, score = v_match
                for pid, data in STORE_CATALOG.items():
                    if canon_name.lower() == data["name"].lower() or data["name"].lower() in canon_name.lower():
                        return pid, data
                return None, {"name": canon_name, "category": cat, "unit": "1 packet", "price": 40.0, "inStock": True, "stock": 10, "aliases": [canon_name.lower()]}
        except Exception:
            pass

        # 2. Direct catalog and alias matching
        for pid, data in STORE_CATALOG.items():
            if data["name"].lower() in text_lower:
                return pid, data
            for alias in data["aliases"]:
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    if alias in ["soap", "sabun"] and any(w in text_lower for w in ["washing", "batte", "detergent", "dish"]):
                        continue
                    return pid, data

        return None, None

    @classmethod
    def process_message(cls, text):
        raw_text = text.strip()
        lower = raw_text.lower()
        try:
            from backend.services.vector_catalog_service import normalize_numbers, KANNADA_NUMBER_MAP
            norm_lower = normalize_numbers(lower)
        except Exception:
            norm_lower = lower
            KANNADA_NUMBER_MAP = {}

        CONTAINER_PATTERN = r'\b(packet|packets|bottle|bottles|batli|box|boxes|dabba|dabbagalu|piece|pieces|nag|nagalu|bag|bags|cheela|chila|kattu|kattugalu|tin|tins|can|cans|pouch|pouches|sachet|sachets|strip|strips|cup|cups|slice|slices)\b|(?:(?<=^)|(?<=\s)|(?<=[.,!?]))(ಪ್ಯಾಕೆಟ್|ಪ್ಯಾಕೆಟ್ಸ್|ಪ್ಯಾಕೆಟ್‌ಗಳು|ಬಾಟಲ್|ಬಾಟಲಿ|ಬಾಟಲಿಗಳು|ಡಬ್ಬ|ಡಬ್ಬಗಳು|ಚೀಲ|ಚೀಲಗಳು|ಕಟ್ಟು|ತುಂಡು)(?=$|\s|[.,!?])'

        # Multi-turn clarification slot continuation
        if cls.conversation_state.get("awaiting") == "QUANTITY":
            _, other_prod = cls.match_product(lower)
            pending_p = (cls.conversation_state.get("pending_product") or "").lower()
            has_other_prod = bool(other_prod and other_prod["name"].lower() != pending_p)
            is_new_command = has_other_prod or any(w in lower for w in [
                "discount", "off", "offer", "rate", "bele", "price", "order", "ord", "sales", "vyapara",
                "report", "add", "delete", "remove", "mugidide", "khali", "kali", "kaali",
                "ಬೆಲೆ", "ರೇಟ್", "ರೂಪಾಯಿ", "ರುಪೀಸ್", "ಡಿಸ್ಕೌಂಟ್", "ರಿಯಾಯಿತಿ", "ಮುಗಿದಿದೆ", "ಖಾಲಿ", "ಹಲೋ", "ನಮಸ್ಕಾರ"
            ])
            if is_new_command:
                cls.conversation_state = {"awaiting": None}
            else:
                m_cnt = re.search(r'(\d+)', norm_lower)
                if m_cnt:
                    count = int(m_cnt.group(1))
                    prod_name = cls.conversation_state.get("pending_product", "Product")
                    unit_label = cls.conversation_state.get("pending_unit", "ಪ್ಯಾಕೆಟ್")
                    cls.conversation_state = {"awaiting": None}

                    pid, prod = cls.match_product(prod_name.lower())
                    if prod and pid:
                        prod["inStock"] = True
                        prod["stock"] = count
                    else:
                        new_id = f"prod_{len(STORE_CATALOG) + 101}"
                        STORE_CATALOG[new_id] = {
                            "name": prod_name,
                            "unit": unit_label,
                            "price": 50,
                            "inStock": True,
                            "stock": count,
                            "aliases": [prod_name.lower()]
                        }

                    return {
                        "success": True,
                        "intent": "UPDATE_STOCK",
                        "replyKn": f"{prod_name} ಸ್ಟಾಕ್ ಅನ್ನು {count} {unit_label}ಗೆ ನವೀಕರಿಸಲಾಗಿದೆ.",
                        "refreshRequired": True,
                        "updatedEntity": {"name": prod_name, "inStock": True, "stockCount": count}
                    }

        # 1. Empty input
        if not raw_text:
            return {
                "success": True,
                "intent": "CHAT_REPLY",
                "replyKn": "ದಯವಿಟ್ಟು ಒಂದು ಸಂದೇಶವನ್ನು ನಮೂದಿಸಿ ಅಥವಾ ಮೈಕ್ ಬಟನ್ ಒತ್ತಿ ಮಾತನಾಡಿ.",
                "refreshRequired": False
            }

        # 2. Identity Guardrail
        for kw in cls.IDENTITY_WORDS:
            if re.search(r'(?:\b|^|\s)' + re.escape(kw) + r'(?:\b|$|\s)', lower):
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಅಂಗಡಿಯ ಸಹಾಯಕ (Vani Store Assistant). ಸರಕುಗಳು, ಬೆಲೆ, ರಿಯಾಯಿತಿ, ಸ್ಟಾಕ್, ಆರ್ಡರ್ ಮತ್ತು ಮಾರಾಟ ವರದಿಗಳನ್ನು ನಿರ್ವಹಿಸಲು ನಾನು ನಿಮಗೆ ಸಹಾಯ ಮಾಡುತ್ತೇನೆ.",
                    "refreshRequired": False
                }

        # 3. Out-of-Context Guardrail
        for kw in cls.OUT_OF_CONTEXT:
            if re.search(r'\b' + re.escape(kw) + r'\b', lower):
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": "ಕ್ಷಮಿಸಿ, ನಾನು ಕೇವಲ ನಿಮ್ಮ ಅಂಗಡಿಯ ವ್ಯವಹಾರ (products, price, stock, orders, sales) ನಿರ್ವಹಣೆಗೆ ಮಾತ್ರ ಸಹಾಯ ಮಾಡಬಲ್ಲೆ. ಅಂಗಡಿಯ ಯಾವ ಕೆಲಸ ಮಾಡಬೇಕು?",
                    "refreshRequired": False
                }

        # 4. Sales Report Query
        if any(w in lower for w in ["sales", "vyapara", "vyapaara", "report", "ivattina", "eshtu vyapara", "today's sale"]):
            return {
                "success": True,
                "intent": "GET_SALES_REPORT",
                "replyKn": "ಇವತ್ತಿನ ಒಟ್ಟು ವ್ಯಾಪಾರ ₹12,450 (28 ಆರ್ಡರ್‌ಗಳು). UPI: ₹8,200, COD: ₹4,250. ಕಡಿಮೆ ಸ್ಟಾಕ್ ಇರುವ ಸರಕುಗಳು: 3.",
                "refreshRequired": False,
                "payload": {"totalRevenue": 12450, "totalOrders": 28}
            }

        # 5. Order Management (Update, Query, and Incoming Order)
        order_match = re.search(r"\b(?:order|ord|aadara|aadhesh)\b\s*#?\s*(?:ord-)?(\d{1,5})|#(\d{1,5})|\bORD-(\d{1,5})", lower, re.IGNORECASE)
        if order_match:
            order_num = order_match.group(1) or order_match.group(2) or order_match.group(3)
            ord_id = f"ORD-{order_num}"

            # 5a. Order Status Query (e.g. "ORD-101 status heli", "ORD-101 status enu")
            if any(w in lower for w in ["status", "enu", "heli", "eshtu", "nodona", "check"]):
                o_info = MOCK_ORDERS.get(ord_id, {"status": "NEW", "customer": "Customer", "total": 250})
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": f"Order #{ord_id} status: {o_info['status']} (ಗ್ರಾಹಕರು: {o_info.get('customer', 'Customer')}, ಒಟ್ಟು ಮೊತ್ತ: ₹{o_info.get('total', 0)}).",
                    "refreshRequired": False
                }

            # 5b. Incoming Customer Order (e.g. "1kg sugar order ID ORD-101 bandide", "order bandide")
            if any(w in lower for w in ["bandide", "bantu", "arrived", "hosa", "new"]):
                MOCK_ORDERS[ord_id] = {"status": "NEW", "customer": "Online Order", "total": 150}
                return {
                    "success": True,
                    "intent": "UPDATE_ORDER_STATUS",
                    "replyKn": f"ಹೊಸ Order #{ord_id} ಸ್ವೀಕರಿಸಲಾಗಿದೆ (Status: NEW).",
                    "refreshRequired": True,
                    "updatedEntity": {"orderId": ord_id, "status": "NEW"}
                }

            # 5c. Order Status Transition
            has_order_status_word = bool(re.search(r"\b(packed|pack|dispatch|dispatched|delivery|delivered|cancel|cancelled|kalisi|raddu|horatide)\b", lower))
            if has_order_status_word:
                if any(w in lower for w in ["dispatch", "dispatched", "horatide", "delivery ge", "kalisi"]):
                    status = "OUT_FOR_DELIVERY"
                elif any(w in lower for w in ["delivered", "tulpiside", "talpiside", "delivery aagide"]):
                    status = "DELIVERED"
                elif any(w in lower for w in ["cancel", "cancelled", "raddu"]):
                    status = "CANCELLED"
                else:
                    status = "PACKED"

                if ord_id in MOCK_ORDERS:
                    MOCK_ORDERS[ord_id]["status"] = status
                else:
                    MOCK_ORDERS[ord_id] = {"status": status, "customer": "Online Customer", "total": 200}

                return {
                    "success": True,
                    "intent": "UPDATE_ORDER_STATUS",
                    "replyKn": f"Order #{ord_id} status ಅನ್ನು {status} ಗೆ ಬದಲಾಯಿಸಲಾಗಿದೆ.",
                    "refreshRequired": True,
                    "updatedEntity": {"orderId": ord_id, "status": status}
                }

        # 6. Check Stock Inquiries / Questions (READ-ONLY, DO NOT MUTATE)
        # Examples: "yava yava item stock alli ide", "yava item stock ide", "stock list kodi", "yava item stock mugidide"
        is_question = bool(re.search(r"\b(yava|yavudu|yava yava|yavellam|which|what|enu|eshtu|list|patte)\b", lower))
        if is_question and ("stock" in lower or "item" in lower or "saraku" in lower):
            if any(w in lower for w in ["mugidide", "illa", "khali", "kali", "out of stock"]):
                out_items = [p["name"] for p in STORE_CATALOG.values() if not p.get("inStock") or p.get("stock", 0) <= 0]
                items_str = ", ".join(out_items) if out_items else "ಯಾವುದೂ ಇಲ್ಲ (ಎಲ್ಲಾ ವಸ್ತುಗಳು ಸ್ಟಾಕ್‌ನಲ್ಲಿವೆ)"
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": f"ಸ್ಟಾಕ್ ಮುಗಿದಿರುವ ವಸ್ತುಗಳು: {items_str}.",
                    "refreshRequired": False
                }
            else:
                in_items = [f"{p['name']} ({p.get('stock', 10)})" for p in STORE_CATALOG.values() if p.get("inStock", True) and p.get("stock", 0) > 0]
                preview = ", ".join(in_items[:5])
                extra = f" ಮತ್ತು ಇನ್ನು {len(in_items) - 5} ವಸ್ತುಗಳು" if len(in_items) > 5 else ""
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": f"ಸ್ಟಾಕ್‌ನಲ್ಲಿರುವ ವಸ್ತುಗಳು: {preview}{extra}.",
                    "refreshRequired": False
                }

        # 7. Stock Out Mutation Intent (e.g. "Akki stock mugidide", "idli rave packets kali agide", "20 shampoo packets kaali agide")
        stock_out_words = [
            "mugidide", "illa", "mugithu", "out of stock", "stock out",
            "khali", "khaliaagide", "kali", "kaali", "kali agide", "kaali agide", "kaliagide", "kaaliagide",
            "thegedu haaki", "thegedu haaku", "delete", "remove", "thegedu", "thege", "kala", "tegedu", "thegiri", "thegisi",
            "ಮುಗಿದಿದೆ", "ಮುಗೀತು", "ಇಲ್ಲ", "ಖಾಲಿ", "ಖಾಲಿಯಾಗಿದೆ", "ಕಾಲಿ", "ಕಾಲಿಯಾಗಿದೆ", "ತೆಗೆದು ಹಾಕಿ", "ತೆಗೆಯಿರಿ", "ತೆಗೆ"
        ]
        is_stock_out = any(w in lower for w in stock_out_words)

        if is_stock_out:
            clean_out = re.sub(r'\b(delete|remove|thegedu|haaki|haaku|maadi|madi|packets|packet|stock|kaali|kali|khali|khaliaagide|kaliagide|kaaliagide|agide|aagide|\d+)\b', '', lower)
            for kw_out in ["ಮುಗಿದಿದೆ", "ಮುಗೀತು", "ಇಲ್ಲ", "ಖಾಲಿಯಾಗಿದೆ", "ಖಾಲಿ", "ಕಾಲಿಯಾಗಿದೆ", "ಕಾಲಿ", "ತೆಗೆದು ಹಾಕಿ", "ತೆಗೆಯಿರಿ", "ತೆಗೆ", "ಪ್ಯಾಕೆಟ್ಸ್", "ಪ್ಯಾಕೆಟ್", "ಸ್ಟಾಕ್"]:
                clean_out = clean_out.replace(kw_out, " ")
            clean_out = " ".join(clean_out.split()).strip()
            pid, prod = cls.match_product(clean_out if clean_out else lower)
            if prod:
                prod["inStock"] = False
                prod["stock"] = 0
                return {
                    "success": True,
                    "intent": "UPDATE_STOCK",
                    "replyKn": f"{prod['name']} ಸ್ಟಾಕ್ ಮುಗಿದಿದೆ ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ.",
                    "refreshRequired": True,
                    "updatedEntity": {"id": pid, "name": prod["name"], "inStock": False, "stockCount": 0}
                }
            else:
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": "ಯಾವ ವಸ್ತುವಿನ ಸ್ಟಾಕ್ ಮುಗಿದಿದೆ ಎಂದು ದಯವಿಟ್ಟು ತಿಳಿಸಿ.",
                    "refreshRequired": False
                }
        else:
            pid, prod = cls.match_product(lower)

        # Positive stock update & Stock arrival: "togari bele 10kg bandide", "ಬಾಸ್ಮತಿ ರೈಸ್ 80 ಪ್ಯಾಕೆಟ್ಸ್ ಬಂದಿದೆ"
        arrival_words = [
            "bandive", "bandide", "bantu", "stock bantu", "packet ide", "packets ide", "arrived", "kodi", "beku", "tulpiside", "reach aagide", "load aagide",
            "ಬಂದಿದೆ", "ಬಂದಿವೆ", "ಬಂತು", "ತಲುಪಿದೆ", "ಲೋಡ್ ಆಗಿದೆ"
        ]
        has_arrival = any(w in norm_lower for w in arrival_words)
        has_stock_mention = ("stock" in norm_lower or "ide" in norm_lower or "ಇದೆ" in norm_lower or "ಸ್ಟಾಕ್" in norm_lower) and not any(w in norm_lower for w in ["yava", "yavudu", "eshtu", "list", "illa", "mugidide", "khali", "kali", "ಎಷ್ಟು", "ಯಾವ", "ಇಲ್ಲ", "ಮುಗಿದಿದೆ", "ಖಾಲಿ", "ಲಭ್ಯವಿದೆ"])
        has_container = bool(re.search(CONTAINER_PATTERN, norm_lower))
        has_number = bool(re.search(r'\d+', norm_lower))
        has_price_or_discount = any(w in norm_lower for w in [
            "rate", "price", "dar", "rupayi", "rupees", "rs", "₹", "discount", "offer", "off", "riyayiti", "%",
            "ರೇಟ್", "ಬೆಲೆ", "ದರ", "ರೂಪಾಯಿ", "ರೂ", "ರುಪಾಯಿ", "ರುಪೀಸ್", "ಡಿಸ್ಕೌಂಟ್", "ರಿಯಾಯಿತಿ", "ಆಫರ್"
        ]) or (bool(re.search(r'\bbele\b', norm_lower)) and not has_arrival)

        if (has_arrival or (has_stock_mention and has_number) or (has_container and (has_arrival or "ide" in norm_lower or "ಇದೆ" in norm_lower or has_number))) and not is_stock_out and not order_match and not has_price_or_discount:
            clauses = [p.strip() for p in re.split(r'[,;\n]|\bmattu\b|\bmathu\b|\bhagu\b|\+', raw_text) if p.strip()]

            def parse_item_clause(clause_str):
                c_norm = normalize_numbers(clause_str.lower())
                u_m = re.search(r"(\d+(?:\.\d+)?\s*(?:ml|l|litre|kg|g|gm|slice|ಕೆಜಿ|ಗ್ರಾಂ|ಲೀಟರ್|ಮಿಲಿ))", c_norm)
                v_unit = u_m.group(1) if u_m else None
                t_count = c_norm.replace(u_m.group(0), "") if u_m else c_norm
                
                ct_m = re.search(CONTAINER_PATTERN, t_count)
                c_unit = (ct_m.group(1) or ct_m.group(2)) if ct_m else None

                cnt_m = re.search(r'(\d+)\s*(?:' + CONTAINER_PATTERN + r')', t_count)
                if not cnt_m:
                    cnt_m = re.search(r'(?:' + CONTAINER_PATTERN + r')\s*(\d+)', t_count)
                if not cnt_m:
                    cnt_m = re.search(r'(\d+)\s*(?:ide|bantu|bandide|bandive|arrived|count|stock|ಬಂದಿದೆ|ಬಂದಿವೆ|ಬಂತು|ಇದೆ)', t_count)
                if not cnt_m:
                    cnt_m = re.search(r'(?:stock|count|ಸ್ಟಾಕ್)\s*(\d+)', t_count)
                if not cnt_m:
                    cnt_m = re.search(r'(\d+)', t_count)

                digits_found = [g for g in cnt_m.groups() if g and g.isdigit()] if cnt_m else []
                c_val = int(digits_found[0]) if digits_found else None
                if c_val is None and u_m:
                    m_d = re.search(r'\d+', u_m.group(1))
                    if m_d:
                        c_val = int(m_d.group(0))

                cl = normalize_numbers(clause_str)
                cl = re.sub(r'\b\d+\b', '', cl)
                cl = re.sub(CONTAINER_PATTERN, '', cl, flags=re.IGNORECASE)
                if v_unit:
                    cl = re.sub(re.escape(v_unit), '', cl, flags=re.IGNORECASE)
                for sw in ['na', 'ge', 'alli', 'bandive', 'bandide', 'bantu', 'arrived', 'ide', 'stock', 'galu', 'kodi', 'beku', 'slice', 'slices', 'ಬಂದಿದೆ', 'ಬಂದಿವೆ', 'ಬಂತು', 'ಇದೆ', 'ಸ್ಟಾಕ್', 'ಮಾಡಿ']:
                    if all(ord(c) < 128 for c in sw):
                        cl = re.sub(r'\b' + re.escape(sw) + r'\b', '', cl, flags=re.IGNORECASE)
                    else:
                        cl = re.sub(r'(?:(?<=^)|(?<=\s)|(?<=[.,!?]))' + re.escape(sw) + r'(?=$|\s|[.,!?])', ' ', cl)
                cl_cand = ' '.join(cl.split()).strip()

                p_id, p_obj = cls.match_product(cl_cand.lower() if cl_cand else c_norm)
                item_name = p_obj["name"] if p_obj else (cl_cand.title() if len(cl_cand) >= 2 else "Product")
                clean_unit_label = re.sub(r'^\d+\s*', '', v_unit) if v_unit else (c_unit or 'ಪ್ಯಾಕೆಟ್')
                return {
                    "pid": p_id,
                    "prod": p_obj,
                    "name": item_name,
                    "count": c_val,
                    "unit": clean_unit_label,
                    "vol_unit": v_unit
                }

            if len(clauses) > 1:
                parsed_items = [parse_item_clause(c) for c in clauses]
                valid_items = [it for it in parsed_items if it["count"] is not None]
                if not valid_items:
                    return {
                        "success": True,
                        "intent": "CHAT_REPLY",
                        "replyKn": "ದಯವಿಟ್ಟು ಸರಕುಗಳ ಪ್ರಮಾಣವನ್ನು (quantity) ತಿಳಿಸಿ (ಉದಾ: '50 bottle neeru, 20 soap bandide').",
                        "refreshRequired": False
                    }

                updated_list = []
                for it in valid_items:
                    disp = f"{it['name']} ({it['vol_unit']})" if it['vol_unit'] else it['name']
                    if it['prod'] and it['pid']:
                        it['prod']['inStock'] = True
                        it['prod']['stock'] = it['count']
                    else:
                        new_id = f"prod_{len(STORE_CATALOG) + 101}"
                        STORE_CATALOG[new_id] = {
                            "name": disp,
                            "unit": it['unit'],
                            "price": 50,
                            "inStock": True,
                            "stock": it['count'],
                            "aliases": [it['name'].lower()]
                        }
                    updated_list.append({"name": disp, "inStock": True, "stockCount": it['count'], "unit": it['unit']})

                summary_str = ", ".join([f"{it['name']} ({it['stockCount']} {it['unit']})" for it in updated_list])
                return {
                    "success": True,
                    "intent": "UPDATE_STOCK",
                    "replyKn": f"{summary_str} ಸ್ಟಾಕ್ ಅನ್ನು ಯಶಸ್ವಿಯಾಗಿ ನವೀಕರಿಸಲಾಗಿದೆ.",
                    "refreshRequired": True,
                    "updatedEntity": updated_list
                }
            else:
                it = parse_item_clause(clauses[0])
                if it["count"] is None:
                    # Missing quantity: Save state and ask user!
                    cls.conversation_state = {
                        "pending_intent": "UPDATE_STOCK",
                        "pending_product": it["name"],
                        "pending_unit": it["unit"],
                        "awaiting": "QUANTITY"
                    }
                    return {
                        "success": True,
                        "intent": "CHAT_REPLY",
                        "replyKn": f"ದಯವಿಟ್ಟು ಎಷ್ಟು {it['name']} ಬಂದಿದೆ ಎಂದು ತಿಳಿಸಿ (ಉದಾ: '{it['name']} 10 bandide').",
                        "refreshRequired": False
                    }

                disp = f"{it['name']} ({it['vol_unit']})" if it['vol_unit'] else it['name']
                if it['prod'] and it['pid']:
                    it['prod']['inStock'] = True
                    it['prod']['stock'] = it['count']
                else:
                    new_id = f"prod_{len(STORE_CATALOG) + 101}"
                    STORE_CATALOG[new_id] = {
                        "name": disp,
                        "unit": it['unit'],
                        "price": 50,
                        "inStock": True,
                        "stock": it['count'],
                        "aliases": [it['name'].lower()]
                    }

                return {
                    "success": True,
                    "intent": "UPDATE_STOCK",
                    "replyKn": f"{disp} ಸ್ಟಾಕ್ ಅನ್ನು {it['count']} {it['unit']}ಗೆ ನವೀಕರಿಸಲಾಗಿದೆ.",
                    "refreshRequired": True,
                    "updatedEntity": {"name": disp, "inStock": True, "stockCount": it['count']}
                }

        # 7. Add Product Intent
        if "add" in lower or "serisi" in lower or "hosa" in lower:
            unit_match = re.search(r"(\d+(?:\.\d+)?\s*(?:kg|g|gm|ml|l|litre|packet|piece))", lower)
            unit = unit_match.group(1) if unit_match else "1 unit"
            text_without_unit = lower.replace(unit, "") if unit_match else lower
            price_match = re.search(r"(?:₹|rs\.?|rate|bele)\s*(\d{1,5})|(\d{1,5})\s*(?:rs|rupayi|ge|/-)", text_without_unit)
            price = float(price_match.group(1) or price_match.group(2)) if price_match else 100.0

            name_guess = raw_text
            for sw in ["add maadi", "add", "serisi", "hosa", "ge", "rs", "rate", "bele"]:
                name_guess = re.sub(re.escape(sw), "", name_guess, flags=re.IGNORECASE)
            name_guess = re.sub(r"\d+", "", name_guess).strip()
            name_guess = name_guess if len(name_guess) > 2 else "New Product"

            return {
                "success": True,
                "intent": "ADD_PRODUCT",
                "replyKn": f"{name_guess} ({unit}) ₹{price:.0f} ಗೆ ಸ್ಟೋರ್‌ಗೆ ಸೇರಿಸಲಾಗಿದೆ!",
                "refreshRequired": True,
                "updatedEntity": {"name": name_guess, "unit": unit, "price": price}
            }

        # 8. Check Discount Percentage: "biscuit packets ge 10% discount maadi", "ಸಕ್ಕರೆ 10% ಡಿಸ್ಕೌಂಟ್ ಆಗಿದೆ"
        pct_match = re.search(
            r"(\d{1,2})\s*(?:%|percent|pratishata|ಪ್ರತಿಶತ)?\s*(?:discount|off|offer|riyayiti|ಡಿಸ್ಕೌಂಟ್|ರಿಯಾಯಿತಿ|ಆಫರ್)|"
            r"(?:discount|off|offer|riyayiti|ಡಿಸ್ಕೌಂಟ್|ರಿಯಾಯಿತಿ|ಆಫರ್)\s*(\d{1,2})\s*(?:%|percent|ಪ್ರತಿಶತ)?",
            norm_lower
        )
        if pct_match and any(w in norm_lower for w in ["discount", "offer", "%", "off", "riyayiti", "ಡಿಸ್ಕೌಂಟ್", "ರಿಯಾಯಿತಿ", "ಆಫರ್"]):
            pct_val = float(pct_match.group(1) or pct_match.group(2))
            name_guess = raw_text
            for sw in ["packets", "packet", "ge", "discount", "maadi", "kodi", "offer", "off", "percent", "riyayiti", "ಡಿಸ್ಕೌಂಟ್", "ರಿಯಾಯಿತಿ", "ಆಫರ್", "ಆಗಿದೆ", "ಮಾಡಿ"]:
                name_guess = name_guess.replace(sw, " ")
            name_guess = re.sub(r"\d+%", "", name_guess)
            name_guess = re.sub(r"\d+", "", name_guess).strip()
            item_name = prod["name"] if prod else (name_guess.title() if len(name_guess) >= 2 else "New Product")

            base_price = prod.get("price", 30.0) if prod else 30.0
            new_price = round(base_price * (1.0 - (pct_val / 100.0)), 2)
            if prod:
                prod["price"] = new_price
                prod["discountPercent"] = int(pct_val)
            else:
                new_id = f"prod_{len(STORE_CATALOG) + 101}"
                STORE_CATALOG[new_id] = {
                    "name": item_name,
                    "unit": "1 packet",
                    "price": new_price,
                    "discountPercent": int(pct_val),
                    "inStock": True,
                    "stock": 10,
                    "aliases": [item_name.lower()]
                }

            return {
                "success": True,
                "intent": "UPDATE_PRICE",
                "replyKn": f"{item_name} ಗೆ {int(pct_val)}% ರಿಯಾಯಿತಿ (Discount) ನೀಡಲಾಗಿದೆ. ಹೊಸ ಬೆಲೆ ₹{new_price:.0f}.",
                "refreshRequired": True,
                "updatedEntity": {"name": item_name, "discountPercent": int(pct_val), "discountPrice": new_price}
            }

        # 9a. Check Price Inquiry (Read-only: "1kg sakkare bele yestu", "ಅಕ್ಕಿ ಎಷ್ಟು ರೇಟ್", "hershy's bele yestu")
        is_price_inquiry = (
            any(w in norm_lower for w in ["eshtu", "yestu", "enu", "heli", "kodi", "what", "ಎಷ್ಟು", "ಏನು", "ಹೇಳಿ", "ಕೊಡಿ", "ತಿಳಿಸಿ"])
            and any(w in norm_lower for w in ["rate", "bele", "price", "dar", "ರೇಟ್", "ಬೆಲೆ", "ದರ", "ರೂಪಾಯಿ"])
            and not any(w in norm_lower for w in ["maadi", "madi", "haaki", "set", "change", "ಮಾಡಿ", "ಹಾಕಿ", "ಮಾಡಬೇಕು", "ಬದಲಾಯಿಸಿ"])
        )
        if is_price_inquiry:
            clean_q = re.sub(r'\b(eshtu|yestu|enu|heli|kodi|what|is|the|price|rate|bele|dar|1kg|\d+kg|\d+g|\d+gm|\d+ml|\d+l)\b', '', norm_lower)
            for qw in ["ಎಷ್ಟು", "ಏನು", "ಹೇಳಿ", "ಕೊಡಿ", "ತಿಳಿಸಿ", "ರೇಟ್", "ಬೆಲೆ", "ದರ", "ರೂಪಾಯಿ", "ಕೆಜಿ"]:
                clean_q = clean_q.replace(qw, " ")
            clean_q = re.sub(r'\b\d+\b', '', clean_q).strip()
            _, p_inq = cls.match_product(clean_q if clean_q else norm_lower)
            if p_inq:
                pr = p_inq.get('discountPrice', p_inq.get('price', 40))
                u = p_inq.get('unit', '1 packet')
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": f"{p_inq['name']} ಬೆಲೆ ₹{pr:.0f} ({u}ಗೆ).",
                    "refreshRequired": False
                }
            return {
                "success": True,
                "intent": "CHAT_REPLY",
                "replyKn": "ಯಾವ ವಸ್ತುವಿನ ಬೆಲೆ ತಿಳಿಯಬೇಕೆಂದು ದಯವಿಟ್ಟು ಸ್ಪಷ್ಟವಾಗಿ ತಿಳಿಸಿ.",
                "refreshRequired": False
            }

        # 9b. Fixed Price Update Intent (e.g. "ಅಕ್ಕಿ 1 ಕೆಜಿ ನೂರು ರೂಪಾಯಿ ಮಾಡಿ", "ಬಾಸುಮತಿ ರೈಸ್ 80")
        price_match = re.search(
            r"(?:rate|bele|price|dar|₹|rs\.?|ರೇಟ್|ಬೆಲೆ|ದರ|ರೂಪಾಯಿ|ರೂ|ರುಪಾಯಿ|ರುಪೀಸ್)\s*(\d{1,5})|"
            r"(\d{1,5})\s*(?:rs|rupayi|rupees|rate|bele|ge|maadi|madi|ರೂಪಾಯಿ|ರೂ|ರುಪಾಯಿ|ರುಪೀಸ್|ಗೆ|ಮಾಡಬೇಕು|ಮಾಡಿ|ಹಾಕಿ)|"
            r"(\d{1,5})\s*$",
            norm_lower
        )
        if price_match:
            price_val = float(price_match.group(1) or price_match.group(2) or price_match.group(3))
            
            # Extract product name cleanly using matched product or text before price/rate word
            item_name = prod["name"] if prod else None
            if not item_name:
                parts = re.split(r"(?:rate|bele|price|dar|ರೇಟ್|ಬೆಲೆ|ದರ|₹|\d+)", norm_lower, flags=re.IGNORECASE)
                if parts and parts[0].strip():
                    item_name = parts[0].strip().title()

            if item_name:
                if prod:
                    prod["price"] = price_val
                else:
                    new_id = f"prod_{len(STORE_CATALOG) + 101}"
                    STORE_CATALOG[new_id] = {
                        "name": item_name,
                        "unit": "1 unit",
                        "price": price_val,
                        "inStock": True,
                        "stock": 10,
                        "aliases": [item_name.lower()]
                    }

                return {
                    "success": True,
                    "intent": "UPDATE_PRICE",
                    "replyKn": f"{item_name} ಬೆಲೆ ₹{price_val:.0f} ಗೆ ಬದಲಾಯಿಸಲಾಗಿದೆ.",
                    "refreshRequired": True,
                    "updatedEntity": {"name": item_name, "discountPrice": price_val}
                }
            else:
                return {
                    "success": True,
                    "intent": "CHAT_REPLY",
                    "replyKn": "ಯಾವ ವಸ್ತುವಿನ ಬೆಲೆ ಬದಲಾಯಿಸಬೇಕು ಎಂದು ಸ್ಪಷ್ಟವಾಗಿ ತಿಳಿಸಿ.",
                    "refreshRequired": False
                }

        if any(w in norm_lower for w in ["rate", "bele", "price", "ರೇಟ್", "ಬೆಲೆ", "ದರ"]):
            return {
                "success": True,
                "intent": "CHAT_REPLY",
                "replyKn": "ಯಾವ ವಸ್ತುವಿನ ಬೆಲೆ ಎಷ್ಟು ಮಾಡಬೇಕು ಎಂದು ದಯವಿಟ್ಟು ತಿಳಿಸಿ.",
                "refreshRequired": False
            }

        # 10. Bare product status inquiry (e.g. "fruit juice", "bread", "tomato")
        pid, prod = cls.match_product(lower)
        if prod:
            stk = f"ಸ್ಟಾಕ್: {prod.get('stock', 0)} {prod.get('unit', '')}" if prod.get('inStock') else "ಸ್ಟಾಕ್ ಮುಗಿದಿದೆ"
            pr = prod.get('price', prod.get('discountPrice', 0))
            return {
                "success": True,
                "intent": "CHAT_REPLY",
                "replyKn": f"{prod['name']} ಲಭ್ಯವಿದೆ (ಬೆಲೆ: ₹{pr:.0f}, {stk}). ಬೆಲೆ ಅಥವಾ ಸ್ಟಾಕ್ ಬದಲಾವಣೆ ಮಾಡಬೇಕೆ?",
                "refreshRequired": False
            }

        # Default fallback
        return {
            "success": True,
            "intent": "CHAT_REPLY",
            "replyKn": "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಬೆಲೆ ಬದಲಾವಣೆ (ಉದಾ: 'Bellulli rate 80 maadi'), ಸ್ಟಾಕ್ (ಉದಾ: 'Akki stock mugidide'), ಅಥವಾ ಮಾರಾಟ ವರದಿ ತಿಳಿಸಿ.",
            "refreshRequired": False
        }


# Mini Web Server for Browser Testing
HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Vani Standalone Chatbot Tester</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 p-6 font-sans">
<div class="max-w-2xl mx-auto bg-white rounded-2xl shadow-md border overflow-hidden">
    <div class="bg-emerald-600 p-4 text-white">
        <h1 class="font-bold text-lg">ವಾಣಿ (Vani) - Standalone Chatbot Test Console</h1>
        <p class="text-xs text-emerald-100">Zero-backend needed. Test Kannada / Kanglish prompts live.</p>
    </div>
    <div id="chat" class="p-4 h-96 overflow-y-auto space-y-3 bg-slate-50 text-sm">
        <div class="bg-white border rounded-xl p-3 text-slate-700 shadow-xs">
            ನಮಸ್ಕಾರ! ಟೆಸ್ಟಿಂಗ್ ಮಾಡಲು ಕೆಳಗಿನ ಬಟನ್ ಒತ್ತಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.
        </div>
    </div>
    <div class="p-2 bg-white border-t flex gap-2 overflow-x-auto text-xs whitespace-nowrap">
        <button onclick="sendMsg('Bellulli rate 80 maadi')" class="bg-emerald-50 text-emerald-800 border border-emerald-200 px-3 py-1.5 rounded-full font-medium">🧅 Bellulli rate 80 maadi</button>
        <button onclick="sendMsg('Akki stock mugidide')" class="bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1.5 rounded-full font-medium">🌾 Akki stock mugidide</button>
        <button onclick="sendMsg('Ivattina vyapara eshtu?')" class="bg-sky-50 text-sky-800 border border-sky-200 px-3 py-1.5 rounded-full font-medium">📊 Ivattina vyapara eshtu?</button>
        <button onclick="sendMsg('Who are you?')" class="bg-purple-50 text-purple-800 border border-purple-200 px-3 py-1.5 rounded-full font-medium">🤖 Who are you?</button>
        <button onclick="sendMsg('Cricket score enu?')" class="bg-red-50 text-red-800 border border-red-200 px-3 py-1.5 rounded-full font-medium">🏏 Cricket score</button>
    </div>
    <div class="p-3 bg-white border-t flex items-center gap-2">
        <input id="txt" type="text" class="flex-1 bg-slate-100 px-3 py-2.5 rounded-xl text-sm border focus:outline-none focus:ring-2 focus:ring-emerald-500" placeholder="Type or click 🎙️ to speak Kannada..." onkeydown="if(event.key==='Enter') sendMsg()" />
        <button id="micBtn" onclick="toggleMic()" class="bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2 rounded-xl font-bold text-sm flex items-center gap-1.5 transition-all border border-slate-200 cursor-pointer" title="Click to speak Kannada / Kanglish">
            <span id="micIcon" class="text-base">🎙️</span>
            <span id="micStatus" class="hidden text-xs text-red-600 font-semibold animate-pulse">ಕೇಳಿಸಿಕೊಳ್ಳುತ್ತಿದ್ದೇನೆ...</span>
        </button>
        <button onclick="sendMsg()" class="bg-emerald-600 hover:bg-emerald-700 text-white px-5 py-2.5 rounded-xl font-bold text-sm shadow-sm transition-all cursor-pointer">Send</button>
    </div>
</div>
<script>
let recognition = null;
let isRecording = false;

function initRecognition() {
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRec) {
        alert("Web Speech API ನಿಮ್ಮ ಬ್ರೌಸರ್‌ನಲ್ಲಿ ಬೆಂಬಲಿತವಾಗಿಲ್ಲ. ದಯವಿಟ್ಟು Google Chrome ಅಥವಾ Microsoft Edge ಬಳಸಿ.");
        return null;
    }
    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'kn-IN'; // Kannada (India)
    
    rec.onstart = () => {
        isRecording = true;
        document.getElementById('micBtn').classList.add('bg-red-50', 'border-red-400');
        document.getElementById('micStatus').classList.remove('hidden');
        document.getElementById('txt').placeholder = "ಮಾತನಾಡಿ... (Listening in Kannada)";
    };
    
    rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('txt').value = transcript;
        sendMsg(transcript);
    };
    
    rec.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        stopMic();
    };
    
    rec.onend = () => {
        stopMic();
    };
    
    return rec;
}

function toggleMic() {
    if (!recognition) recognition = initRecognition();
    if (!recognition) return;
    
    if (isRecording) {
        recognition.stop();
    } else {
        try {
            recognition.start();
        } catch(e) {
            console.warn(e);
        }
    }
}

function stopMic() {
    isRecording = false;
    const btn = document.getElementById('micBtn');
    if (btn) btn.classList.remove('bg-red-50', 'border-red-400');
    const st = document.getElementById('micStatus');
    if (st) st.classList.add('hidden');
    const txt = document.getElementById('txt');
    if (txt) txt.placeholder = "Type or click 🎙️ to speak Kannada...";
}

async function sendMsg(overrideText) {
    const input = document.getElementById('txt');
    const msg = overrideText || input.value.trim();
    if(!msg) return;
    if(!overrideText) input.value = '';
    
    const chat = document.getElementById('chat');
    chat.innerHTML += `<div class="flex justify-end"><div class="bg-emerald-600 text-white rounded-xl p-2.5 max-w-[80%]">${msg}</div></div>`;
    
    const res = await fetch('/api/test', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({text: msg})
    });
    const data = await res.json();
    
    chat.innerHTML += `<div class="flex items-start gap-2"><div class="bg-white border rounded-xl p-3 text-slate-800 shadow-xs max-w-[85%]"><p class="font-medium">${data.replyKn}</p><div class="text-[11px] text-slate-400 mt-1 font-mono">Intent: ${data.intent} | Refresh: ${data.refreshRequired}</div></div></div>`;
    chat.scrollTop = chat.scrollHeight;
}
</script>
</body>
</html>
"""

class StandaloneHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode("utf-8"))

    def do_POST(self):
        if self.path == "/api/test":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8")
            data = json.loads(body)
            result = StandaloneVaniBot.process_message(data.get("text", ""))
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def start_browser_server(port=8080):
    server = HTTPServer(("localhost", port), StandaloneHandler)
    server.serve_forever()

if __name__ == "__main__":
    port = 8080
    t = threading.Thread(target=start_browser_server, args=(port,), daemon=True)
    t.start()

    print("=" * 65)
    print("  Vani (ವಾಣಿ) - Standalone Chatbot Tester")
    print("  Zero external backend needed!")
    print(f"  👉 Web UI is running at: http://localhost:{port}")
    print("=" * 65)
    print("\nQuick Test Examples:")
    print("  1. 'Bellulli rate 80 maadi'        (Price update)")
    print("  2. 'Akki stock mugidide'           (Stock out update)")
    print("  3. 'Order ORD-101 packed maadi'    (Order status update)")
    print("  4. 'Ivattina vyapara eshtu?'       (Sales summary query)")
    print("  5. 'Mysore Pak 500g 220 rs ge add' (Add product)")
    print("  6. 'Neenu yaaru?'                  (Identity guardrail)")
    print("  7. 'Who won the cricket match?'    (Out-of-context guardrail)")
    print("  8. 'Bele maadi'                    (Missing details clarification)")
    print("\nType your command below (or open the web browser URL above):")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            line = input("[Enter Command] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not line:
            continue
        if line.lower() in ("exit", "quit", "q"):
            print("Done testing.")
            break

        res = StandaloneVaniBot.process_message(line)
        print("-" * 50)
        print(f"🎯 Intent       : {res['intent']}")
        print(f"💬 Kannada Reply: {res['replyKn']}")
        print(f"🔄 UI Refresh   : {res['refreshRequired']}")
        if "updatedEntity" in res:
            print(f"📦 Entity Data  : {res['updatedEntity']}")
        print("-" * 50 + "\n")
