import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db
from backend.services.audio_service import audio_service, AudioConversionError
from backend.services.asr_service import asr_service
from backend.services.llm_service import llm_service
from backend.tests.test_audio_edge_cases import create_synthetic_wav
import base64

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_database():
    db.reset()

def test_edge_case_checkout_out_of_stock_item():
    # prod_108 is Mysore Pak which is out of stock (inStock: False, stockCount: 0)
    p = db.get_product("prod_108")
    assert p.inStock is False

    payload = {
        "customerPhone": "9123456789",
        "customerName": "Ramesh",
        "deliveryAddress": "Tilakwadi, Belagavi - 590006",
        "items": [
            {
                "productId": "prod_108",
                "name": p.name,
                "unit": p.unit,
                "quantity": 1,
                "priceAtOrder": p.discountPrice
            }
        ],
        "paymentMethod": "UPI"
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "out of stock" in res.json()["detail"].lower()

def test_edge_case_checkout_insufficient_stock():
    # prod_104 has stockCount: 3. Requesting 5 should fail.
    p = db.get_product("prod_104")
    assert p.stockCount == 3

    payload = {
        "customerPhone": "9123456789",
        "customerName": "Ramesh",
        "deliveryAddress": "Tilakwadi, Belagavi - 590006",
        "items": [
            {
                "productId": "prod_104",
                "name": p.name,
                "unit": p.unit,
                "quantity": 5,
                "priceAtOrder": p.discountPrice
            }
        ],
        "paymentMethod": "UPI"
    }
    res = client.post("/api/orders", json=payload)
    assert res.status_code == 400
    assert "insufficient quantity" in res.json()["detail"].lower()

def test_edge_case_discount_calculation_edge_cases():
    # If discountPrice equals originalPrice, discountPercent must be 0
    prod = db.create_product({
        "name": "Zero Discount Item",
        "originalPrice": 100,
        "discountPrice": 100,
        "unit": "1 kg"
    })
    assert prod.discountPercent == 0

    # If discountPrice > originalPrice, discountPercent must still be 0 (no negative discount)
    prod2 = db.create_product({
        "name": "Higher Price Item",
        "originalPrice": 100,
        "discountPrice": 120,
        "unit": "1 kg"
    })
    assert prod2.discountPercent == 0

def test_edge_case_unintended_ocr_camera_photo_only_attaches_image():
    # When an image is attached without text, it should create product with default name and attached image
    # without trying to parse random bills or run unintended OCR mutations
    fake_img = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    res = client.post("/api/bot/message", json={
        "inputType": "image",
        "text": "",
        "imageBase64": fake_img
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "ADD_PRODUCT"
    assert data["updatedEntity"]["imageUrl"] == fake_img

def test_edge_case_nonexistent_product_update():
    # Direct execute with non-existent product
    res_exec = client.post("/api/bot/execute", json={
        "intent": "UPDATE_PRICE",
        "payload": {"productName": "Avocado Oil Extra", "discountPrice": 500},
        "replyKn": ""
    })
    assert res_exec.status_code == 200
    data_exec = res_exec.json()
    assert data_exec["success"] is False
    assert data_exec["refreshRequired"] is False
    assert "ಕಂಡುಬಂದಿಲ್ಲ" in data_exec["replyKn"]

    # Via bot message (asks for clarification if unknown product)
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Avocado oil rate 500 maadi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["refreshRequired"] is False
    assert data["updatedEntity"] is None

def test_edge_case_nonexistent_order_update():
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Order ORD-9999 delivered aagide"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is False
    assert data["refreshRequired"] is False
    assert "ಕಂಡುಬಂದಿಲ್ಲ" in data["replyKn"]

@pytest.mark.asyncio
async def test_edge_case_audio_asr_with_synthetic_audio():
    # Valid synthetic WAV
    wav_bytes = create_synthetic_wav(duration_seconds=1.5)
    b64 = base64.b64encode(wav_bytes).decode("utf-8")
    
    res = await asr_service.transcribe_audio_base64(b64)
    assert "is_empty_or_noise" in res

@pytest.mark.asyncio
async def test_edge_case_llm_provider_switching():
    # Test setting provider to gemini
    llm_service.provider_name = "gemini"
    res1 = await llm_service.get_intent_and_payload("Bellulli rate 80 maadi")
    assert res1["intent"] == "UPDATE_PRICE"

    # Test setting provider to self_hosted
    llm_service.provider_name = "self_hosted"
    res2 = await llm_service.get_intent_and_payload("Akki stock mugidide")
    assert res2["intent"] == "UPDATE_STOCK"
