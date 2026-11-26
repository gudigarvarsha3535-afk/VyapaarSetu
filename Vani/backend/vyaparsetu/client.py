"""Small async client for the VyaparSetu backend (Node/Express).

Every call forwards the seller's own bearer token. No Supabase keys or
service-role credentials are used or stored here.
"""
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

VYAPARSETU_API_BASE = os.getenv("VYAPARSETU_API_BASE", "http://localhost:5000").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("VYAPARSETU_TIMEOUT_SECONDS", "10"))


class VyaparSetuError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class VyaparSetuClient:
    def __init__(self, base_url: str = VYAPARSETU_API_BASE, transport: Optional[httpx.AsyncBaseTransport] = None):
        self.base_url = base_url
        self._transport = transport  # tests inject a mock transport

    async def _request(self, method: str, path: str, token: str, json: Optional[Dict[str, Any]] = None) -> Tuple[int, Any]:
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        async with httpx.AsyncClient(base_url=self.base_url, timeout=TIMEOUT_SECONDS, transport=self._transport) as client:
            resp = await client.request(method, path, headers=headers, json=json)
        try:
            body = resp.json()
        except ValueError:
            body = None
        return resp.status_code, body

    async def me(self, token: str) -> Dict[str, Any]:
        status, body = await self._request("GET", "/api/auth/me", token)
        if status != 200 or not body or not body.get("success"):
            raise VyaparSetuError(status, (body or {}).get("message", "Not authenticated"))
        return body["data"]

    async def list_products(self, token: str) -> List[Dict[str, Any]]:
        status, body = await self._request("GET", "/api/seller/products", token)
        if status != 200 or not body or not body.get("success"):
            raise VyaparSetuError(status, (body or {}).get("message", "Could not load products"))
        return body.get("products") or []

    async def create_product(self, token: str, data: Dict[str, Any]) -> Dict[str, Any]:
        status, body = await self._request("POST", "/api/seller/products", token, json=data)
        if status != 201 or not body or not body.get("success"):
            raise VyaparSetuError(status, (body or {}).get("message", "Could not add the product"))
        return body["product"]

    async def update_product(self, token: str, product_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        status, body = await self._request("PATCH", f"/api/seller/products/{product_id}", token, json=data)
        if status != 200 or not body or not body.get("success"):
            raise VyaparSetuError(status, (body or {}).get("message", "Could not update the product"))
        return body["product"]

    async def delete_product(self, token: str, product_id: str) -> Dict[str, Any]:
        status, body = await self._request("DELETE", f"/api/seller/products/{product_id}", token)
        if status != 200 or not body or not body.get("success"):
            raise VyaparSetuError(status, (body or {}).get("message", "Could not delete the product"))
        return body.get("product") or {"id": product_id}


vyaparsetu_client = VyaparSetuClient()
