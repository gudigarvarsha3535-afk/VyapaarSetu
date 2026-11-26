import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_database():
    db.reset()

def test_chatbot_intent_update_price():
    # Kanglish price update: "Bellulli rate 80 maadi"
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Bellulli rate 80 maadi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "UPDATE_PRICE"
    assert data["refreshRequired"] is True
    assert data["updatedEntity"]["discountPrice"] == 80
    assert "prod_106" in data["updatedEntity"]["id"]

def test_chatbot_intent_update_stock():
    # Kanglish stock update: "Akki stock mugidide"
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Akki stock mugidide"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "UPDATE_STOCK"
    assert data["refreshRequired"] is True
    assert data["updatedEntity"]["inStock"] is False
    assert data["updatedEntity"]["stockCount"] == 0

def test_chatbot_intent_update_order_status():
    # Order status update: "Order ORD-101 packed maadi"
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Order ORD-101 packed maadi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "UPDATE_ORDER_STATUS"
    assert data["refreshRequired"] is True
    assert data["updatedEntity"]["status"] == "PACKED"

def test_chatbot_intent_sales_report():
    # Sales report query: "Ivattina vyapara eshtu?"
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Ivattina vyapara eshtu?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "GET_SALES_REPORT"
    assert "ವ್ಯಾಪಾರ" in data["replyKn"] or "ಮಾರಾಟ" in data["replyKn"]
    assert data["refreshRequired"] is False  # Read-only query doesn't require entity reload

def test_chatbot_intent_add_product_with_image():
    # Add product with camera image base64
    fake_img = "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
    res = client.post("/api/bot/message", json={
        "inputType": "image",
        "text": "Mysore Pak 500g 220 rs ge add maadi",
        "imageBase64": fake_img
    })
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["intent"] == "ADD_PRODUCT"
    assert data["refreshRequired"] is True
    assert data["updatedEntity"]["discountPrice"] == 220
    assert data["updatedEntity"]["imageUrl"] == fake_img

def test_chatbot_identity_guardrail():
    # "Neenu yaaru?" -> should return identity, non-mutating
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Neenu yaaru? Ninna kelasa enu?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "CHAT_REPLY"
    assert data["refreshRequired"] is False
    assert data["updatedEntity"] is None
    assert "ಸಹಾಯಕ" in data["replyKn"] or "Vani" in data["replyKn"]

def test_chatbot_out_of_context_guardrail():
    # Cricket / sports query -> polite refusal, non-mutating
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Who won the cricket match yesterday? What is python coding?"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "CHAT_REPLY"
    assert data["refreshRequired"] is False
    assert data["updatedEntity"] is None
    assert "ಅಂಗಡಿಯ" in data["replyKn"] or "ಕ್ಷಮಿಸಿ" in data["replyKn"]

def test_chatbot_missing_details_clarification():
    # Ambiguous command: "Bele maadi" without product or price
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "Bele maadi"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "CHAT_REPLY"
    assert data["refreshRequired"] is False
    assert data["updatedEntity"] is None
    assert "ತಿಳಿಸಿ" in data["replyKn"] or "ಯಾವ" in data["replyKn"]

def test_chatbot_empty_or_noisy_text():
    # Empty string
    res = client.post("/api/bot/message", json={
        "inputType": "text",
        "text": "   "
    })
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "CHAT_REPLY"
    assert data["refreshRequired"] is False
    assert "ನಮೂದಿಸಿ" in data["replyKn"] or "ಮಾತನಾಡಿ" in data["replyKn"]
