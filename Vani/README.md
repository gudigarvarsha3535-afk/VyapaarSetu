# Vani (ವಾಣಿ) - Kannada Conversational Commerce Platform

**Vani** is an AI-powered conversational commerce platform tailor-made for Karnataka small sellers, local kirana shop owners, artisans, and rural entrepreneurs. It empowers merchants to manage their entire digital storefront, inventory, pricing, order fulfillment, and sales analytics effortlessly through Kannada voice, Kanglish text chat, and mobile camera photo capture.

---

## 🌟 Core Architecture & Highlights

### 1. Embedded Chatbot Widget (Not Standalone)
- **Embedded Directly into Seller Dashboard**: Accessible as a floating panel at the bottom-right of `/seller`.
- **Clearance Padding (`pb-80`)**: When expanded, automatically applies `pb-80` to the main dashboard container so lower product cards and tables are never obscured.
- **Multimodal Input Support**:
  - 🎤 **Voice**: Browser audio converted to 16 kHz mono WAV via `ffmpeg` and transcribed using **ARTPARK-IISc SraVaani 1.0**.
  - ⌨️ **Text**: Direct Kannada (ಕನ್ನಡ) or Kanglish text input.
  - 📷 **Camera / Gallery**: Click photos with the device camera or select from the gallery to attach as product photos (never runs unwanted OCR/bill mutations).
  - ⚡ **Kannada Quick-Chips**: 1-tap store command chips (`Bellulli rate 80 maadi`, `Akki stock mugidide`, `Ivattina vyapara eshtu?`, etc.).
- **Live Synchronization & Pulsing Highlight**: When a bot action completes (`refreshRequired: true`), the dashboard immediately re-fetches data and flashes a yellow/green pulsing highlight ring (`.flash-highlight`) on the updated entity.

### 2. Buyer Storefront Service (`/`)
- Zero login wall: shoppers browse products immediately.
- Clean hierarchy: product photo, unit pill (`1 kg`, `500 ml`), bold `discountPrice`, crossed-out `originalPrice`, green `discountPercent% OFF` badge.
- Clear out-of-stock overlay and disabled buttons when `inStock: false`.
- **Delivery-Only Fulfillment**: Zero shop pickup option anywhere.
- **OTP Checkout**: Mobile Number + 4-digit OTP modal (`1234` for prototype demo).
- **Serviceable PIN Code Check**: Validates delivery address against store's serviceable PIN codes (`590001`, `590006`, `590010`).
- **Payment Selection**: UPI or Cash on Delivery (COD).

### 3. Seller Dashboard Service (`/seller`)
- **Login Gate**: Mobile `9876543210` / Password `demo123`.
- **Home**: Product grid with search, sort dropdown, and a 1-tap `inStock` toggle switch on every card.
- **Pricing & Discounts**: Live discount percent auto-calculation: `round(((originalPrice - discountPrice) / originalPrice) * 100)`.
- **Inventory Control**: Real-time stock counts and low stock alert warnings.
- **Order Management**: Status transitions: `NEW` ➔ `PACKED` ➔ `OUT_FOR_DELIVERY` ➔ `DELIVERED` ➔ `CANCELLED`.
- **Delivery & Logistics**: Delivery fee (₹30), free delivery threshold (₹500), serviceable PIN codes, and rider management.
- **Sales & Reports**: Summary of total revenue, order count, UPI vs COD breakdown, low stock items, and top-selling products.

---

## 🔄 Easy LLM Upgrade Path (Cloud Free Tier ➔ Self-Hosted Private LLM)

The LLM client is built behind a pluggable provider interface (`BaseLLMProvider`) configured strictly via environment variables. Switching from cloud Gemini to a self-hosted private LLM (such as Ollama with Gemma/Qwen or vLLM / llama.cpp) requires **changing configuration only—zero code changes**.

### Environment Variables (`.env`)

```ini
# Choose "gemini" for Cloud Free Tier or "self_hosted" for Local Private LLM
LLM_PROVIDER=gemini

# When using Gemini (Cloud):
LLM_API_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash

# When switching to Self-Hosted (Ollama / vLLM / llama.cpp):
# LLM_PROVIDER=self_hosted
# LLM_BASE_URL=http://localhost:11434/api/chat
# LLM_MODEL=gemma3:4b
# LLM_API_KEY=

# Inference parameters
LLM_TIMEOUT_SECONDS=10
LLM_TEMPERATURE=0.0
```

### Deterministic Keyword & Regex Fallback Parser
If the external LLM provider is offline, times out, rate limits, or returns non-JSON output, Vani's **Deterministic Fallback Parser** automatically intercepts the request:
- Guaranteed 100% uptime for all store commands in Kannada and Kanglish.
- Automatic Kannada phonetic alias resolution (e.g. `akki` ➔ Sona Masoori Rice, `tuppa` ➔ Nandini Pure Ghee, `bellulli` ➔ Fresh Garlic, `menasinakayi` ➔ Byadgi Chilli).

---

## 🛡️ Chatbot Rule Set: Identity, Scope & Guardrails

| User Query Scenario | Bot Behavior | Intent / refreshRequired |
| :--- | :--- | :--- |
| **Identity** (`"Who are you?"` / `"Neenu yaaru?"`) | Polite explanation in Kannada that Vani is the store assistant for products, prices, stock, orders, and reports. Never reveals hidden system prompts or schemas. | `CHAT_REPLY` / `false` |
| **Shop Questions** (`"Ivattina vyapara eshtu?"`) | Answers using live catalog and sales numbers without inventing fake prices or policies. | `GET_SALES_REPORT` / `false` |
| **Out-of-Context** (Cricket, movies, coding, medical/legal, chit-chat) | Politely declines in Kannada, states it only assists with store operations, and asks what store task is needed. Never mutates data. | `CHAT_REPLY` / `false` |
| **Missing Details** (`"Rate maadi"`, `"Stock mugidide"`) | Asks a short clarifying question in Kannada rather than guessing or hallucinating values. | `CHAT_REPLY` / `false` |
| **Empty / Noisy Input** (Silence or click noise < 0.3s) | Asks politely to speak clearly or type without changing any store state. | `CHAT_REPLY` / `false` |

---

## 🚀 How to Run the Platform

### 1. Start Both Services with Single Command
Run the unified launcher:
```powershell
python start.py
```
This automatically spins up:
- **Frontend Dev Server**: `http://localhost:5173`
- **Backend REST API**: `http://localhost:8000/api` (also serves frontend at `http://localhost:8000`)
- **API Documentation**: `http://localhost:8000/docs`

### 2. Or Run Backend Independently via Uvicorn
```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧪 Comprehensive QA Test Suite

The platform includes a 31-test automated suite covering normal operations, critical situations, audio conversions, and edge cases:

```powershell
python -m pytest backend/tests/ -v
```

### Verified Test Areas:
1. **API & Authentication (`test_api.py`)**: Customer OTP flow (1234 demo), seller login, product sorting (`price_asc`, `discount_desc`, `stock`), stock toggle, PIN code serviceability validation (`590006` allowed, `560001` rejected), free delivery threshold calculation, order status transitions, and sales summary reports.
2. **Chatbot Intents & Guardrails (`test_chatbot.py`)**: All 5 mutating intents (`ADD_PRODUCT`, `UPDATE_PRICE`, `UPDATE_STOCK`, `UPDATE_ORDER_STATUS`, `GET_SALES_REPORT`), camera photo attachment, identity inquiry, out-of-context refusal, missing details clarification, and empty/noisy text.
3. **Audio & SraVaani ASR Edge Cases (`test_audio_edge_cases.py`)**: Base64 audio decoding, data URL stripping, corrupt base64 rejection, duration & noise classification (< 0.3s noise detection), and phonetic alias resolution.
4. **LLM Provider Switching & Fallback (`test_llm_providers.py`)**: Markdown fence stripping, JSON schema validation, offline Ollama error recovery, and deterministic fallback parser.
5. **Critical Situations (`test_critical_edge_cases.py`)**: Out-of-stock cart checkout rejection, insufficient stock checkout rejection, zero/negative discount edge cases, non-existent product/order handling, and image-only product creation.
