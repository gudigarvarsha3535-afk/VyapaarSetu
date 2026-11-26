"""Tests for Vani acting on a VyaparSetu shop.

The VyaparSetu backend is replaced by an in-memory fake (httpx.MockTransport),
and the LLM is forced to the offline deterministic parser, so these tests
never touch real data or external services.
"""
import json
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

import backend.main as main
from backend.services.llm_service import llm_service
from backend.vyaparsetu import bot as bot_module
from backend.vyaparsetu.client import VyaparSetuClient

SELLER_TOKEN = "token-seller-aaaaaaaaaaaa"
SELLER2_TOKEN = "token-seller-bbbbbbbbbbbb"
CUSTOMER_TOKEN = "token-customer-cccccccccc"


class FakeVyaparSetu:
    def __init__(self):
        self.users = {
            SELLER_TOKEN: {"id": "u-seller-1", "role": "seller", "full_name": "Asha", "shop": {"id": "shop-1"}},
            SELLER2_TOKEN: {"id": "u-seller-2", "role": "seller", "full_name": "Ravi", "shop": {"id": "shop-2"}},
            CUSTOMER_TOKEN: {"id": "u-cust", "role": "customer", "full_name": "C", "shop": None},
        }
        self.products = []
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        token = request.headers.get("authorization", "").replace("Bearer ", "")
        user = self.users.get(token)
        path, method = request.url.path, request.method
        self.calls.append((method, path))
        if not user:
            return httpx.Response(401, json={"success": False, "message": "Invalid or expired authentication token"})
        if path == "/api/auth/me":
            return httpx.Response(200, json={"success": True, "data": {**user, "email": "x@test.in"}})
        if user["role"] != "seller":
            return httpx.Response(403, json={"success": False, "message": "You do not have permission"})
        shop_id = user["shop"]["id"]
        if path == "/api/seller/products" and method == "GET":
            own = [p for p in self.products if p["shop_id"] == shop_id]
            return httpx.Response(200, json={"success": True, "count": len(own), "products": own})
        if path == "/api/seller/products" and method == "POST":
            body = json.loads(request.content)
            p = {"id": str(uuid.uuid4()), "shop_id": shop_id, "name": body["name"], "price": body["price"],
                 "description": body.get("description"), "image_url": body.get("image_url"), "is_active": body.get("is_active", True)}
            self.products.append(p)
            return httpx.Response(201, json={"success": True, "product": p})
        if path.startswith("/api/seller/products/") and method == "PATCH":
            pid = path.rsplit("/", 1)[1]
            p = next((x for x in self.products if x["id"] == pid and x["shop_id"] == shop_id), None)
            if not p:
                return httpx.Response(404, json={"success": False, "message": "Product not found"})
            p.update(json.loads(request.content))
            return httpx.Response(200, json={"success": True, "product": p})
        if path.startswith("/api/seller/products/") and method == "DELETE":
            pid = path.rsplit("/", 1)[1]
            p = next((x for x in self.products if x["id"] == pid and x["shop_id"] == shop_id), None)
            if not p:
                return httpx.Response(404, json={"success": False, "message": "Product not found"})
            self.products.remove(p)
            return httpx.Response(200, json={"success": True, "product": {"id": p["id"], "name": p["name"]}})
        return httpx.Response(404, json={"success": False})


@pytest.fixture()
def env(monkeypatch):
    fake = FakeVyaparSetu()
    client = VyaparSetuClient(base_url="http://vyaparsetu.test", transport=httpx.MockTransport(fake.handler))
    bot = bot_module.VyaparSetuBot(client=client)
    monkeypatch.setattr("backend.vyaparsetu.routes.vyaparsetu_bot", bot)
    monkeypatch.setattr(llm_service, "provider_name", "offline-for-tests")
    return TestClient(main.app), fake


def say(tc, text, token=SELLER_TOKEN):
    r = tc.post("/api/vyaparsetu/bot/message", json={"inputType": "text", "text": text},
                headers={"Authorization": f"Bearer {token}"})
    return r


def test_requires_seller_login(env):
    tc, fake = env
    assert tc.post("/api/vyaparsetu/bot/message", json={"text": "hi"}).status_code == 401
    assert say(tc, "hi", token="token-unknown-zzzzzzzzzz").status_code == 401
    assert say(tc, "hi", token=CUSTOMER_TOKEN).status_code == 403
    assert fake.products == []


def test_add_product_goes_to_the_sellers_own_shop(env):
    tc, fake = env
    r = say(tc, "Tuppa 500ml 295 rupayi add maadi").json()
    assert r["success"] and r["intent"] == "ADD_PRODUCT" and r["refreshRequired"]
    assert len(fake.products) == 1
    p = fake.products[0]
    assert p["shop_id"] == "shop-1" and p["price"] == 295 and p["description"] == "500ml"


def test_update_price_matches_kanglish_name(env):
    tc, fake = env
    fake.products.append({"id": str(uuid.uuid4()), "shop_id": "shop-1", "name": "Bellulli (Garlic) 1kg", "price": 120,
                          "description": None, "image_url": None, "is_active": True})
    r = say(tc, "Bellulli rate 80 maadi").json()
    assert r["success"] and r["intent"] == "UPDATE_PRICE"
    assert fake.products[0]["price"] == 80


def test_out_of_stock_hides_product_and_back_in_stock_shows_it(env):
    tc, fake = env
    fake.products.append({"id": str(uuid.uuid4()), "shop_id": "shop-1", "name": "Sona Masoori Akki 5kg", "price": 310,
                          "description": None, "image_url": None, "is_active": True})
    r = say(tc, "Akki stock mugidide").json()
    assert r["success"] and r["intent"] == "UPDATE_STOCK"
    assert fake.products[0]["is_active"] is False


def test_unknown_product_is_not_invented(env):
    tc, fake = env
    fake.products.append({"id": str(uuid.uuid4()), "shop_id": "shop-1", "name": "Mysore Sandal Soap", "price": 60,
                          "description": None, "image_url": None, "is_active": True})
    r = say(tc, "Bellulli rate 80 maadi").json()
    assert r["success"] is False
    assert fake.products[0]["price"] == 60
    assert not any(m == "POST" for m, _ in fake.calls)


def test_cannot_touch_another_sellers_products(env):
    tc, fake = env
    fake.products.append({"id": str(uuid.uuid4()), "shop_id": "shop-2", "name": "Bellulli 1kg", "price": 120,
                          "description": None, "image_url": None, "is_active": True})
    r = say(tc, "Bellulli rate 80 maadi", token=SELLER_TOKEN).json()
    assert r["success"] is False
    assert fake.products[0]["price"] == 120


def test_orders_are_not_faked_and_report_is_real_zero(env):
    tc, fake = env
    r = say(tc, "Order 5 packed maadi").json()
    assert r["success"] is False and r["intent"] == "UPDATE_ORDER_STATUS" and not r["refreshRequired"]
    r = say(tc, "Ivattina vyapara eshtu?").json()
    assert r["intent"] == "GET_SALES_REPORT" and r["updatedEntity"]["totalRevenue"] == 0


def test_identity_and_out_of_scope_change_nothing(env):
    tc, fake = env
    for text in ["Neenu yaaru?", "Who won the cricket match?"]:
        r = say(tc, text).json()
        assert r["refreshRequired"] is False
    assert fake.products == [] and not any(m in ("POST", "PATCH") for m, _ in fake.calls)


def test_photo_upload_is_refused_politely(env):
    tc, fake = env
    r = tc.post("/api/vyaparsetu/bot/message", json={"inputType": "image", "imageBase64": "aGVsbG8="},
                headers={"Authorization": f"Bearer {SELLER_TOKEN}"}).json()
    assert r["refreshRequired"] is False and fake.products == []


def test_backend_down_gives_502(monkeypatch):
    def broken(request):
        raise httpx.ConnectError("down")
    client = VyaparSetuClient(base_url="http://vyaparsetu.test", transport=httpx.MockTransport(broken))
    monkeypatch.setattr("backend.vyaparsetu.routes.vyaparsetu_bot", bot_module.VyaparSetuBot(client=client))
    r = TestClient(main.app).post("/api/vyaparsetu/bot/message", json={"text": "hi"},
                                  headers={"Authorization": f"Bearer {SELLER_TOKEN}"})
    assert r.status_code == 502


def test_percent_discount_uses_the_sellers_own_price(env):
    # Vani's parser derives discountPrice from its demo catalogue; the connector
    # must ignore that and compute from the seller's real price.
    tc, fake = env
    fake.products.append({"id": str(uuid.uuid4()), "shop_id": "shop-1", "name": "Nandini Ghee 500ml", "price": 280,
                          "description": None, "image_url": None, "is_active": True})
    r = say(tc, "Tuppa mele 10% discount kodi").json()
    assert r["success"] and r["intent"] == "UPDATE_PRICE"
    assert fake.products[0]["price"] == 252.0


def _product(fake, name, price, shop="shop-1", active=True):
    p = {"id": str(uuid.uuid4()), "shop_id": shop, "name": name, "price": price,
         "description": None, "image_url": None, "is_active": active}
    fake.products.append(p)
    return p


def test_delete_asks_first_then_deletes_on_yes(env):
    tc, fake = env
    _product(fake, "Nandini Pure Ghee 500ml", 280)
    _product(fake, "Sunflower Oil 1L", 145)
    r = say(tc, "Tuppa delete maadi").json()
    assert r["intent"] == "DELETE_PRODUCT" and not r["refreshRequired"]
    assert len(fake.products) == 2  # nothing deleted before the seller confirms
    r = say(tc, "ಹೌದು").json()
    assert r["success"] and r["refreshRequired"]
    assert [p["name"] for p in fake.products] == ["Sunflower Oil 1L"]


def test_delete_cancelled_keeps_product(env):
    tc, fake = env
    _product(fake, "Sakkare 1kg", 45)
    say(tc, "ಸಕ್ಕರೆ ತೆಗೆದುಹಾಕಿ")
    r = say(tc, "beda").json()
    assert r["success"] is False and not r["refreshRequired"]
    assert len(fake.products) == 1
    assert not any(m == "DELETE" for m, _ in fake.calls)


def test_add_in_kannada_script(env):
    tc, fake = env
    r = say(tc, "ಸಕ್ಕರೆ 1kg 45 ರೂಪಾಯಿ ಸೇರಿಸಿ").json()
    assert r["success"] and r["intent"] == "ADD_PRODUCT" and r["refreshRequired"]
    assert len(fake.products) == 1 and fake.products[0]["price"] == 45 and fake.products[0]["description"] == "1kg"


def test_stock_back_in_shows_product_again(env):
    tc, fake = env
    _product(fake, "Sona Masoori Akki 5kg", 310, active=False)
    r = say(tc, "Akki stock bandide").json()
    assert r["success"] and r["intent"] == "UPDATE_STOCK" and r["refreshRequired"]
    assert fake.products[0]["is_active"] is True


@pytest.mark.parametrize("text", ["Order tagoli", "Order accept maadi", "Order 5 dispatch maadi", "ಆರ್ಡರ್ ಕಳುಹಿಸಿ"])
def test_order_commands_say_not_available_and_change_nothing(env, text):
    tc, fake = env
    _product(fake, "Tuppa 500ml", 295)
    r = say(tc, text).json()
    assert r["intent"] == "UPDATE_ORDER_STATUS" and r["success"] is False and not r["refreshRequired"]
    assert not any(m in ("POST", "PATCH", "DELETE") for m, _ in fake.calls)


def test_price_update_picks_the_right_product_among_several(env):
    tc, fake = env
    ghee = _product(fake, "Nandini Pure Ghee 500ml", 280)
    _product(fake, "Sunflower Oil 1L", 145)
    _product(fake, "Sona Masoori Akki 5kg", 310)
    r = say(tc, "Tuppa rate 300 maadi").json()
    assert r["success"], r["replyKn"]
    assert ghee["price"] == 300 and [p["price"] for p in fake.products][1:] == [145, 310]


def test_product_question_answers_from_the_sellers_shop(env):
    tc, fake = env
    _product(fake, "Sona Masoori Akki 5kg", 310)
    r = say(tc, "Akki stock ide?").json()
    assert "₹310" in r["replyKn"] and not r["refreshRequired"]


def test_voice_message_changes_shop_and_asks_dashboard_to_refresh(env, monkeypatch):
    tc, fake = env
    _product(fake, "Bellulli (Garlic) 1kg", 120)

    async def fake_asr(audio_b64):
        return {"text": "Bellulli rate 90 maadi", "is_empty_or_noise": False}
    monkeypatch.setattr(bot_module.asr_service, "transcribe_audio_base64", fake_asr)
    r = tc.post("/api/vyaparsetu/bot/message", json={"inputType": "voice", "audioBase64": "UklGRg=="},
                headers={"Authorization": f"Bearer {SELLER_TOKEN}"}).json()
    assert r["transcribedText"] == "Bellulli rate 90 maadi"
    assert r["success"] and r["refreshRequired"] and fake.products[0]["price"] == 90


PHOTO = "https://abc.supabase.co/storage/v1/object/public/product-images/u-seller-1/2b7e1c9a-1111-4222-8333-444455556666.jpg"


def send(tc, body, token=SELLER_TOKEN):
    return tc.post("/api/vyaparsetu/bot/message", json=body, headers={"Authorization": f"Bearer {token}"}).json()


def test_photo_with_add_command_creates_product_with_photo(env):
    tc, fake = env
    r = send(tc, {"inputType": "text", "text": "Tuppa 500ml 295 add maadi", "imageUrl": PHOTO})
    assert r["success"] and r["intent"] == "ADD_PRODUCT" and r["refreshRequired"]
    assert fake.products[0]["image_url"] == PHOTO


def test_photo_alone_then_product_name_sets_photo(env):
    tc, fake = env
    ghee = _product(fake, "Nandini Pure Ghee 500ml", 280)
    r = send(tc, {"inputType": "image", "imageUrl": PHOTO})
    assert not r["refreshRequired"] and ghee["image_url"] is None
    r = say(tc, "Tuppa")
    r = r.json()
    assert r["success"] and r["intent"] == "UPDATE_PHOTO" and r["refreshRequired"]
    assert ghee["image_url"] == PHOTO and ghee["price"] == 280


def test_photo_add_without_price_keeps_photo_until_price_given(env):
    tc, fake = env
    send(tc, {"inputType": "text", "text": "Sakkare add maadi", "imageUrl": PHOTO})
    assert fake.products == []
    r = say(tc, "45").json()
    assert r["success"] and fake.products[0]["image_url"] == PHOTO


def test_foreign_or_unsafe_photo_links_are_refused(env):
    tc, fake = env
    p = _product(fake, "Tuppa 500ml", 295)
    for bad in ["https://evil.example/x.jpg", "javascript:alert(1)",
                "https://abc.supabase.co/storage/v1/object/public/other-bucket/a/b.jpg"]:
        r = send(tc, {"inputType": "text", "text": "Tuppa", "imageUrl": bad})
        assert r["success"] is False and not r["refreshRequired"]
    assert p["image_url"] is None
    assert not any(m in ("POST", "PATCH") for m, _ in fake.calls)


def test_add_without_price_asks_instead_of_using_demo_price(env):
    tc, fake = env
    r = say(tc, "Tuppa add maadi").json()
    assert fake.products == [] and not r["refreshRequired"]
    r = say(tc, "300").json()
    assert r["success"] and fake.products[0]["price"] == 300 and fake.products[0]["description"] is None
