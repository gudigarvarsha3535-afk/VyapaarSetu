Project Contract: Kannada Conversational Commerce Platform

Golden Rule: All 4 team members (Frontend, Backend, Chatbot, QA/Testing) must follow these exact field names, routes, and JSON payloads. Do not rename keys without updating this file and notifying the team.

1. Environment & Base URLs

Frontend Dev Server: http://localhost:5173

Backend API Base URL: http://localhost:8000/api

Local Ollama LLM URL: http://localhost:11434/api/chat (Model: gemma3:4b or qwen2.5:7b)

SraVaani 1.0 ASR Endpoint: http://localhost:8001/transcribe (Handled by Chatbot service)

2. Core Data Models (Shared JSON Schemas)

2.1 Shop Settings (ShopConfig)

Controls storefront branding and whether the Delivery & Logistics sidebar tab is visible.

{
  "shopSlug": "ramesh-kirana",
  "shopName": "Ramesh Kirana & General Stores",
  "ownerPhone": "9876543210",
  "deliveryEnabled": true,
  "deliveryFee": 30,
  "freeDeliveryAbove": 500,
  "serviceablePincodes": ["590001", "590006", "590010"]
}


2.2 Product (Product)

Used across Buyer Storefront, Seller Dashboard Home, Pricing & Discounts, Inventory Control, and Chatbot.

{
  "id": "prod_101",
  "name": "Nandini Pure Ghee",
  "category": "Dairy & Staples",
  "unit": "500 ml",
  "originalPrice": 320,
  "discountPrice": 295,
  "discountPercent": 8,
  "inStock": true,
  "stockCount": 14,
  "lowStockThreshold": 5,
  "imageUrl": "data:image/jpeg;base64,...",
  "updatedAt": "2026-11-25T14:00:00Z"
}


Note: discountPercent is auto-calculated as Math.round(((originalPrice - discountPrice) / originalPrice) * 100). If discountPrice === originalPrice, discountPercent is 0.

2.3 Order (Order)

Note: Delivery only (no shop pickup). Customer must verify Mobile OTP before creating an order.

{
  "id": "ORD-101",
  "customerPhone": "9123456789",
  "customerName": "Kiran Patil",
  "deliveryAddress": "House 42, 3rd Cross, Tilakwadi, Belagavi - 590006",
  "items": [
    {
      "productId": "prod_101",
      "name": "Nandini Pure Ghee",
      "unit": "500 ml",
      "quantity": 2,
      "priceAtOrder": 295
    }
  ],
  "subtotal": 590,
  "deliveryFee": 0,
  "totalAmount": 590,
  "paymentMethod": "UPI",
  "status": "NEW",
  "deliveryPartner": "Self-Delivery",
  "createdAt": "2026-11-25T14:15:00Z"
}


Allowed paymentMethod values: "UPI" | "COD"

Allowed status values: "NEW" | "PACKED" | "OUT_FOR_DELIVERY" | "DELIVERED" | "CANCELLED"

3. Backend REST API Endpoints (Member 2)

3.1 Authentication

POST /api/auth/customer/send-otp

Request: { "phone": "9123456789" }

Response: { "success": true, "message": "OTP sent (Use 1234 for demo)" }

POST /api/auth/customer/verify-otp

Request: { "phone": "9123456789", "otp": "1234" }

Response: { "success": true, "token": "cust_token_9123456789", "phone": "9123456789" }

POST /api/auth/seller/login

Request: { "phone": "9876543210", "password": "demo123" }

Response: { "success": true, "token": "seller_token_001", "shop": { ...ShopConfig } }

3.2 Products & Inventory

GET /api/products

Query Params (optional): ?search=ghee&sort=price_asc|price_desc|discount_desc|stock&discountedOnly=true

Response: { "products": [ ...Product ] }

POST /api/products (Create product manually or via bot)

Request: Product (without id and updatedAt)

Response: { "success": true, "product": { ...Product } }

PATCH /api/products/:id (Quick Stock Toggle, Price Update, Discount Update)

Request (partial): { "inStock": false } OR { "discountPrice": 280, "stockCount": 20 }

Response: { "success": true, "product": { ...Product } }

DELETE /api/products/:id

Response: { "success": true, "deletedId": "prod_101" }

3.3 Orders & Delivery

GET /api/orders

Response: { "orders": [ ...Order ] }

POST /api/orders (Customer Checkout after OTP verification)

Request: { "customerPhone": "...", "customerName": "...", "deliveryAddress": "...", "items": [...], "paymentMethod": "UPI" }

Response: { "success": true, "order": { ...Order } }

PATCH /api/orders/:id/status (Seller Order Management & Delivery)

Request: { "status": "PACKED", "deliveryPartner": "Raju Rider" }

Response: { "success": true, "order": { ...Order } }

3.4 Sales & Reports

GET /api/reports/summary

Response:

{
  "totalRevenue": 12450,
  "totalOrders": 28,
  "upiRevenue": 8200,
  "codRevenue": 4250,
  "lowStockCount": 3,
  "topSellingProducts": [
    { "name": "Nandini Pure Ghee", "unitsSold": 18, "revenue": 5310 }
  ]
}


4. Chatbot Service Contract (Member 3 -> Member 2 & Member 1)

4.1 Frontend Chat Widget -> Chatbot Service

POST /api/bot/message

{
  "inputType": "voice",
  "text": "Bellulli rate 80 maadi",
  "audioBase64": null,
  "imageBase64": null,
  "activeTab": "HOME"
}


Note: If inputType === "voice", Chatbot Service first sends audioBase64 to SraVaani 1.0 to obtain Kannada text, then passes that text to Local Ollama LLM.

4.2 Chatbot Service -> Backend Execution (POST /api/bot/execute)

The Local LLM must output strict JSON matching one of these 5 Intents:

Intent 1: ADD_PRODUCT (Triggered with Camera Photo + Voice/Text)

{
  "intent": "ADD_PRODUCT",
  "payload": {
    "name": "Mysore Pak",
    "category": "Sweets",
    "unit": "500 g",
    "originalPrice": 250,
    "discountPrice": 220,
    "stockCount": 10,
    "imageUrl": "data:image/jpeg;base64,..."
  },
  "replyKn": "Mysore Pak (500 g) ₹220 ge store ge add aagide!"
}


Intent 2: UPDATE_PRICE

{
  "intent": "UPDATE_PRICE",
  "payload": {
    "productName": "Tomato",
    "originalPrice": 40,
    "discountPrice": 35
  },
  "replyKn": "Tomato bele ₹35 ge update aagide."
}


Intent 3: UPDATE_STOCK

{
  "intent": "UPDATE_STOCK",
  "payload": {
    "productName": "Akki",
    "inStock": false,
    "stockCount": 0
  },
  "replyKn": "Akki stock mugidide endu mark maadide."
}


Intent 4: UPDATE_ORDER_STATUS

{
  "intent": "UPDATE_ORDER_STATUS",
  "payload": {
    "orderId": "ORD-101",
    "status": "OUT_FOR_DELIVERY"
  },
  "replyKn": "Order #ORD-101 delivery ge kaliside."
}


Intent 5: GET_SALES_REPORT

{
  "intent": "GET_SALES_REPORT",
  "payload": {},
  "replyKn": "Ivattina ottu vyapara ₹12,450 (28 orders) aagide."
}


4.3 Response Returned to Frontend Chat Widget

{
  "success": true,
  "intent": "UPDATE_PRICE",
  "replyKn": "Tomato bele ₹35 ge update aagide.",
  "updatedEntity": { "...Product" },
  "refreshRequired": true
}


When refreshRequired === true, Frontend immediately re-fetches /api/products or /api/orders and flashes a highlight on updatedEntity.id.

5. Frontend UI Rules (Member 1)

Root Route (/): Opens Buyer Storefront directly (no login wall). Top-right has Cart button and subtle "Shop Owner Login" button.

Checkout Gate: Clicking Proceed to Order opens the Mobile + 4-Digit OTP Modal (1234 always valid in demo). Delivery address + UPI/COD only (no shop pickup).

Seller Dashboard (/seller):

Opens Home tab by default: Product card grid + Search bar + Sort dropdown + 1-tap inStock toggle switch on every card.

Card hierarchy: Bold discountPrice, crossed-out originalPrice, green discountPercent% OFF badge, and unit pill (1 kg, 500 ml).

Left Sidebar: Home, Pricing & Discounts, Inventory Control, Order Management, Delivery & Logistics (render ONLY if shop.deliveryEnabled === true), and Sales & Reports.

Bottom-Right Chat Widget: Includes Camera/Gallery upload, Hold-to-Talk Mic, Text input, and 3 Kannada quick-chips. When expanded, add pb-80 (bottom padding) to the main dashboard container so bottom cards are never covered.

6. Integration Checkpoints (Member 4 QA Lead)

Checkpoint 1: Frontend connects to Backend REST APIs (Customer places OTP order -> Seller sees order in Order Management & toggles stock on Home).

Checkpoint 2: Chatbot (SraVaani 1.0 + Local Ollama) sends JSON intents to POST /api/bot/execute -> Dashboard & Storefront update live.

Demo Freeze: 90 minutes before pitching—no new features, only bug fixes and rehearsal.
