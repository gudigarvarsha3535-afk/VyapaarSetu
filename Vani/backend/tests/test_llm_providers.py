import pytest
import asyncio
from backend.services.llm_service import (
    LLMService, clean_and_parse_json, DeterministicFallbackParser
)

def test_clean_and_parse_json():
    # Valid raw JSON
    raw = '{"intent": "UPDATE_PRICE", "payload": {"productName": "Tomato", "discountPrice": 35}, "replyKn": "Tomato updated"}'
    parsed = clean_and_parse_json(raw)
    assert parsed is not None
    assert parsed["intent"] == "UPDATE_PRICE"

    # JSON inside markdown fences
    fenced = f"```json\n{raw}\n```"
    parsed_fenced = clean_and_parse_json(fenced)
    assert parsed_fenced is not None
    assert parsed_fenced["intent"] == "UPDATE_PRICE"

    # Malformed non-JSON
    assert clean_and_parse_json("Here is some text without JSON") is None
    assert clean_and_parse_json("") is None

def test_deterministic_fallback_parser():
    # Price
    res_price = DeterministicFallbackParser.parse("Tomato bele 35 maadi")
    assert res_price["intent"] == "UPDATE_PRICE"
    assert res_price["payload"]["discountPrice"] == 35.0

    # Stock
    res_stock = DeterministicFallbackParser.parse("Akki stock mugidide")
    assert res_stock["intent"] == "UPDATE_STOCK"
    assert res_stock["payload"]["inStock"] is False

    # Order
    res_order = DeterministicFallbackParser.parse("Order ORD-101 delivery ge kalisi")
    assert res_order["intent"] == "UPDATE_ORDER_STATUS"
    assert res_order["payload"]["status"] == "OUT_FOR_DELIVERY"
    assert res_order["payload"]["orderId"] == "ORD-101"

    # Sales
    res_sales = DeterministicFallbackParser.parse("Sales report kodi")
    assert res_sales["intent"] == "GET_SALES_REPORT"

    # Identity
    res_id = DeterministicFallbackParser.parse("Who are you?")
    assert res_id["intent"] == "CHAT_REPLY"

    # Out of context
    res_ooc = DeterministicFallbackParser.parse("Tell me a funny cricket joke")
    assert res_ooc["intent"] == "CHAT_REPLY"
    assert res_ooc["payload"]["type"] == "OUT_OF_CONTEXT"

@pytest.mark.asyncio
async def test_llm_service_offline_recovery():
    service = LLMService()
    # Force self-hosted to offline port to simulate offline Ollama server
    service.provider_name = "self_hosted"
    service.self_hosted_provider.base_url = "http://127.0.0.1:59999/api/chat"

    # The service must not crash; it should automatically recover using DeterministicFallbackParser!
    result = await service.get_intent_and_payload("Bellulli rate 80 maadi")
    assert result is not None
    assert result["intent"] == "UPDATE_PRICE"
    assert result["payload"]["discountPrice"] == 80.0
