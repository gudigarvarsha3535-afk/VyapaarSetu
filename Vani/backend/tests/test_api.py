import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import db

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_database():
    db.reset()

def test_customer_otp_flow():
    # Send OTP
    res = client.post("/api/auth/customer/send-otp", json={"phone": "9123456789"})
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Verify with invalid OTP
    res_bad = client.post("/api/auth/customer/verify-otp", json={"phone": "9123456789", "otp": "9999"})
    assert res_bad.status_code == 400

    # Verify with valid demo OTP
    res_good = client.post("/api/auth/customer/verify-otp", json={"phone": "9123456789", "otp": "1234"})
    assert res_good.status_code == 200
    assert "token" in res_good.json()
    assert res_good.json()["phone"] == "9123456789"

def test_seller_login():
    # Valid credentials
    res = client.post("/api/auth/seller/login", json={"phone": "9876543210", "password": "demo123"})
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "token" in data
    assert data["shop"]["shopSlug"] == "ramesh-kirana"

    # Invalid credentials
    res_bad = client.post("/api/auth/seller/login", json={"phone": "9876543210", "password": "wrong"})
    assert res_bad.status_code == 401

def test_products_crud_and_sorting():
    # Get all products
    res = client.get("/api/products")
    assert res.status_code == 200
    products = res.json()["products"]
    assert len(products) >= 10

    # Test sorting price asc
    res_asc = client.get("/api/products?sort=price_asc")
    prods_asc = res_asc.json()["products"]
    prices = [p["discountPrice"] for p in prods_asc]
    assert prices == sorted(prices)

    # Test sorting discount desc
    res_disc = client.get("/api/products?sort=discount_desc")
    prods_disc = res_disc.json()["products"]
    discs = [p["discountPercent"] for p in prods_disc]
    assert discs == sorted(discs, reverse=True)

    # Test 1-tap stock toggle
    p1 = products[0]
    res_toggle = client.patch(f"/api/products/{p1['id']}", json={"inStock": False})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["product"]["inStock"] is False

    # Test price update and discount calculation
    res_price = client.patch(f"/api/products/{p1['id']}", json={"originalPrice": 200, "discountPrice": 150})
    assert res_price.status_code == 200
    updated = res_price.json()["product"]
    assert updated["originalPrice"] == 200
    assert updated["discountPrice"] == 150
    assert updated["discountPercent"] == 25  # (200 - 150) / 200 = 25%

def test_order_creation_delivery_validation():
    # Valid order with serviceable PIN code 590006
    valid_payload = {
        "customerPhone": "9123456789",
        "customerName": "Kiran Patil",
        "deliveryAddress": "House 42, Tilakwadi, Belagavi - 590006",
        "items": [
            {
                "productId": "prod_101",
                "name": "Nandini Pure Ghee",
                "unit": "500 ml",
                "quantity": 1,
                "priceAtOrder": 295
            }
        ],
        "paymentMethod": "UPI"
    }
    res = client.post("/api/orders", json=valid_payload)
    assert res.status_code == 200
    order = res.json()["order"]
    assert order["subtotal"] == 295
    assert order["deliveryFee"] == 30  # Subtotal < 500
    assert order["totalAmount"] == 325

    # Out of area PIN code rejection (e.g., 560001 Bengaluru)
    invalid_address_payload = valid_payload.copy()
    invalid_address_payload["deliveryAddress"] = "MG Road, Bengaluru - 560001"
    res_invalid = client.post("/api/orders", json=invalid_address_payload)
    assert res_invalid.status_code == 400
    assert "Delivery not available in your area" in res_invalid.json()["detail"]

    # Free delivery threshold test (>= 500)
    free_delivery_payload = {
        "customerPhone": "9123456789",
        "customerName": "Kiran Patil",
        "deliveryAddress": "Tilakwadi, Belagavi - 590006",
        "items": [
            {
                "productId": "prod_101",
                "name": "Nandini Pure Ghee",
                "unit": "500 ml",
                "quantity": 2,
                "priceAtOrder": 295
            }
        ],
        "paymentMethod": "UPI"
    }
    res_free = client.post("/api/orders", json=free_delivery_payload)
    assert res_free.status_code == 200
    order_free = res_free.json()["order"]
    assert order_free["subtotal"] == 590
    assert order_free["deliveryFee"] == 0
    assert order_free["totalAmount"] == 590

def test_order_status_transitions():
    res = client.patch("/api/orders/ORD-101/status", json={"status": "PACKED", "deliveryPartner": "Raju Rider"})
    assert res.status_code == 200
    order = res.json()["order"]
    assert order["status"] == "PACKED"
    assert order["deliveryPartner"] == "Raju Rider"

def test_sales_report_summary():
    res = client.get("/api/reports/summary")
    assert res.status_code == 200
    data = res.json()
    assert "totalRevenue" in data
    assert "totalOrders" in data
    assert "upiRevenue" in data
    assert "codRevenue" in data
    assert "topSellingProducts" in data
    assert data["totalRevenue"] > 0
