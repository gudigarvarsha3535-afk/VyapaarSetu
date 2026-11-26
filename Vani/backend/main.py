import shutil
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional, Dict, Any

from backend.config import settings
from backend.models import (
    ProductCreate, ProductUpdate, OrderCreateRequest, OrderStatusUpdate,
    CustomerSendOtpRequest, CustomerVerifyOtpRequest, SellerLoginRequest,
    BotMessageRequest, BotExecuteRequest, BotResponse
)
from backend.database import db
from backend.services.bot_service import bot_service
from backend.services.asr_service import asr_service
from backend.services.audio_service import audio_service

app = FastAPI(
    title="Vani - Kannada Conversational Commerce Platform",
    description="Backend REST API & Embedded Kannada Chatbot Service",
    version="1.0.0"
)

# CORS: only the local frontends by default (VyaparSetu dev server on 5173 and
# Vani's own pages on 8000). Override with VANI_CORS_ORIGINS="https://a.com,https://b.com".
import os as _os
_cors_origins = [o.strip() for o in _os.getenv(
    "VANI_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
).split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# VyaparSetu integration: Vani acting on the logged-in seller's real shop
from backend.vyaparsetu.routes import router as vyaparsetu_router
app.include_router(vyaparsetu_router)

# ----------------- 1. Authentication Endpoints ----------------- #

@app.post("/api/auth/customer/send-otp")
async def customer_send_otp(req: CustomerSendOtpRequest):
    phone = req.phone.strip()
    if not phone or len(phone) < 10:
        raise HTTPException(status_code=400, detail="Invalid phone number.")
    return {
        "success": True,
        "message": "OTP sent (Use 1234 for demo)",
        "phone": phone
    }

@app.post("/api/auth/customer/verify-otp")
async def customer_verify_otp(req: CustomerVerifyOtpRequest):
    phone = req.phone.strip()
    otp = req.otp.strip()
    if otp != "1234":
        raise HTTPException(status_code=400, detail="Invalid OTP. Please enter 1234 for demo.")
    return {
        "success": True,
        "token": f"cust_token_{phone}",
        "phone": phone
    }

@app.post("/api/auth/seller/login")
async def seller_login(req: SellerLoginRequest):
    # Demo credentials
    if req.phone == "9876543210" and req.password == "demo123":
        return {
            "success": True,
            "token": "seller_token_001",
            "shop": db.get_shop_config()
        }
    raise HTTPException(status_code=401, detail="Invalid seller credentials. Use 9876543210 / demo123.")

# ----------------- 2. Shop Configuration ----------------- #

@app.get("/api/shop/config")
async def get_shop_config():
    return db.get_shop_config()

@app.patch("/api/shop/config")
async def update_shop_config(updates: Dict[str, Any]):
    updated = db.update_shop_config(updates)
    return {"success": True, "shop": updated}

# ----------------- 3. Products & Inventory ----------------- #

@app.get("/api/products")
async def get_products(
    search: Optional[str] = None,
    sort: Optional[str] = None,
    discountedOnly: bool = False
):
    products = db.get_products(search=search, sort=sort, discounted_only=discountedOnly)
    return {"products": products}

@app.get("/api/products/{prod_id}")
async def get_product_by_id(prod_id: str):
    product = db.get_product(prod_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/api/products")
async def create_product(req: ProductCreate):
    product = db.create_product(req.model_dump())
    return {"success": True, "product": product}

@app.patch("/api/products/{prod_id}")
async def update_product(prod_id: str, updates: ProductUpdate):
    product = db.update_product(prod_id, updates.model_dump(exclude_unset=True))
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "product": product}

@app.delete("/api/products/{prod_id}")
async def delete_product(prod_id: str):
    deleted = db.delete_product(prod_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "deletedId": prod_id}

# ----------------- 4. Orders & Delivery ----------------- #

@app.get("/api/orders")
async def get_orders():
    return {"orders": db.get_orders()}

@app.get("/api/orders/{order_id}")
async def get_order_by_id(order_id: str):
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@app.post("/api/orders")
async def create_order(req: OrderCreateRequest):
    if not req.items:
        raise HTTPException(status_code=400, detail="Cannot place empty order.")
    
    # Check address and PIN code
    address = req.deliveryAddress.strip()
    if not address:
        raise HTTPException(status_code=400, detail="Delivery address is required.")

    # Validate serviceable PIN codes
    shop_cfg = db.get_shop_config()
    matched_pin = None
    for pin in shop_cfg.serviceablePincodes:
        if pin in address:
            matched_pin = pin
            break
            
    if not matched_pin:
        pincodes_str = ", ".join(shop_cfg.serviceablePincodes)
        raise HTTPException(
            status_code=400,
            detail=f"Delivery not available in your area. Serviceable PIN codes: {pincodes_str}"
        )

    # Check stock availability
    for it in req.items:
        p = db.get_product(it.productId)
        if not p or not p.inStock or p.stockCount < it.quantity:
            item_name = p.name if p else it.name
            raise HTTPException(
                status_code=400,
                detail=f"Sorry, '{item_name}' is out of stock or insufficient quantity available."
            )

    order = db.create_order(
        customer_phone=req.customerPhone,
        customer_name=req.customerName,
        delivery_address=req.deliveryAddress,
        items=req.items,
        payment_method=req.paymentMethod
    )
    return {"success": True, "order": order}

@app.patch("/api/orders/{order_id}/status")
async def update_order_status(order_id: str, req: OrderStatusUpdate):
    order = db.update_order_status(order_id, req.status, req.deliveryPartner)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"success": True, "order": order}

# ----------------- 5. Sales & Reports ----------------- #

@app.get("/api/reports/summary")
async def get_sales_summary():
    return db.get_sales_report()

# ----------------- 6. Chatbot Widget Endpoints ----------------- #

@app.post("/api/bot/message", response_model=BotResponse)
async def bot_message(req: BotMessageRequest):
    return await bot_service.process_message(req)

@app.post("/api/bot/execute", response_model=BotResponse)
async def bot_execute(req: BotExecuteRequest):
    return bot_service.execute_intent(req)

@app.post("/api/bot/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Direct ASR endpoint for SraVaani 1.0."""
    try:
        content = await file.read()
        wav = audio_service.convert_to_16k_mono_wav(content)
        # Check duration
        duration, is_noise = audio_service.check_audio_duration_and_energy(wav)
        if is_noise:
            return {"text": "", "confidence": 0.0, "is_empty_or_noise": True}
        # Transcribe
        import base64
        b64 = base64.b64encode(wav).decode("utf-8")
        return await asr_service.transcribe_audio_base64(b64)
    except Exception as e:
        return {"text": "", "confidence": 0.0, "error": str(e), "is_empty_or_noise": True}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "ffmpeg_path": settings.FFMPEG_PATH,
        "ffmpeg_available": Path(settings.FFMPEG_PATH).exists() or bool(shutil.which("ffmpeg")),
        "database": {
            "products_count": len(db.products),
            "orders_count": len(db.orders)
        }
    }

# ----------------- 7. Static Frontend Hosting ----------------- #

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    async def serve_storefront():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/seller")
    async def serve_seller_dashboard():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/test-bot")
    async def serve_test_bot():
        return FileResponse(str(frontend_dir / "test_bot.html"))
