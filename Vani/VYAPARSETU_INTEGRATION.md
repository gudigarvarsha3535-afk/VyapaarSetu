# Vani inside VyaparSetu

Vani (the Kannada store chatbot) runs as its own service and works on the
**logged-in seller's real VyaparSetu shop**.

```
Seller page (localhost:5173)  --text-->  Vani (localhost:8000)  --seller token-->  VyaparSetu backend (localhost:5000)  -->  Supabase
                                         understands Kannada/Kanglish               checks login + seller role, RLS applies
```

- Vani's intent understanding (Gemini / self-hosted LLM, plus the offline
  fallback parser) is unchanged.
- Only the execution layer is new: `backend/vyaparsetu/` calls the VyaparSetu
  API with the seller's own token. Vani never holds Supabase keys.
- Vani's original demo (`/`, `/seller`, in-memory data) still works as before.

## Run (three terminals)

1. VyaparSetu backend — `C:\Users\HP\Desktop\kannada-ecommerce-backend`
   ```powershell
   npm run dev
   ```
2. VyaparSetu frontend — `...\kannada-ecommerce-backend\stitch_vyaparsetu_local_commerce_platform`
   ```powershell
   npm run dev
   ```
3. Vani — `C:\Users\HP\Downloads\Vani`
   ```powershell
   .\.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
   Do **not** use `python start.py` together with VyaparSetu: it also starts a
   frontend on port 5173, which VyaparSetu's frontend already uses.

First-time setup (already done on this computer):
```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
```

## What Vani can do on a VyaparSetu shop

| Say (example) | Result |
|---|---|
| `Tuppa 500ml 295 add maadi` | Adds "Ghee" (500ml) at ₹295 to your shop |
| `Bellulli rate 80 maadi` | Changes the price of your garlic product |
| `Akki stock mugidide` | Marks rice out of stock (hidden from the store) |
| `Akki stock bandide` / in stock | Shows it in the store again |
| `Ivattina vyapara eshtu?` | Today's sales (₹0 until orders exist) + product counts |
| `Order 5 packed maadi` | Explains orders are not available yet — nothing changes |

Product names are matched fuzzily (English, Kannada, Kanglish). If Vani is not
sure which product you mean, it asks instead of guessing. If a new product has
no price, it asks for the price.

## Settings (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `VYAPARSETU_API_BASE` | `http://localhost:5000` | VyaparSetu backend address |
| `VANI_CORS_ORIGINS` | localhost 5173 / 8000 | Websites allowed to call Vani |
| `LLM_PROVIDER`, `LLM_API_KEY`, ... | see `.env.example` | Optional LLM; without it the offline parser is used |

## Not available yet

- **Voice**: needs `ffmpeg` and the ARTPARK SraVaani speech server (port 8001).
  Neither is installed on this computer, so the chat window is text-only.
- **Photo upload**: VyaparSetu has no image storage yet; add products by text.
- **Stock counts / orders**: VyaparSetu has no stock-count column or orders API
  yet, so "out of stock" hides the product and order commands change nothing.

## Tests

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
```
41 tests: Vani's original 31 + 10 for the VyaparSetu connector (fake VyaparSetu
API and offline parser — no real data or external services are used).
