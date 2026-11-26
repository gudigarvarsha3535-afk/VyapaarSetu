# Frontend Contract: Kannada Conversational Commerce Platform

## 1. Routes & Navigation
- `/`: Buyer Storefront. Zero login wall.
  - Header: Store Logo, Store Name ("Ramesh Kirana & General Stores"), Search Bar, Cart Button (with item badge), "Shop Owner Login" button linking to `/seller`.
  - Product Grid: Displays product photo, unit pill (e.g. `1 kg`, `500 ml`), bold `discountPrice`, crossed-out `originalPrice`, green `discountPercent% OFF` badge, and stock status badge.
  - Stock State: When `inStock === false`, card displays prominent out-of-stock overlay ("ಖಾಲಿಯಾಗಿದೆ / Out of Stock") and "Add to Cart" is disabled.
  - Cart Modal & Checkout:
    - Lists selected items, quantities, unit prices, subtotal.
    - Delivery fee: ₹30 if subtotal < ₹500, else FREE (₹0).
    - Delivery-only fulfillment: NO shop pickup option anywhere.
    - "Proceed to Order" triggers Mobile + 4-Digit OTP modal (`1234` accepted for demo).
    - Upon OTP verification, asks for Delivery Address and PIN code.
    - PIN code is validated against `serviceablePincodes` (`590001`, `590006`, `590010`).
    - Payment Method: "UPI" or "COD".
    - "Confirm Order" calls `POST /api/orders` and shows success confirmation with order ID.

- `/seller`: Seller Dashboard.
  - Login modal if not authenticated (demo credentials: Phone `9876543210`, Password `demo123`).
  - Left Sidebar Tabs:
    1. **Home** (Default): Search & sort (price asc, price desc, discount %, stock), product card grid with 1-tap `inStock` toggle switch on every card.
    2. **Pricing & Discounts**: Edit `originalPrice` and `discountPrice` with instant `discountPercent` calculation.
    3. **Inventory Control**: Update `stockCount`, set low stock alert thresholds, toggle stock status.
    4. **Order Management**: Status transitions (`NEW` -> `PACKED` -> `OUT_FOR_DELIVERY` -> `DELIVERED` -> `CANCELLED`) and delivery rider assignment.
    5. **Delivery & Logistics**: Delivery fee configuration, free-delivery threshold, serviceable PIN codes, delivery partner fleet.
    6. **Sales & Reports**: Total revenue, total orders, UPI vs COD breakdown, top selling products.
  - Embedded Chatbot Widget:
    - Fixed at bottom-right / bottom panel.
    - Clearance padding: When widget is open, main dashboard container adds `pb-80` to prevent bottom product cards from being obscured.
    - Camera capture / Gallery upload for product image attachments.
    - Voice recording via Web Audio API + Hold-to-Talk Mic button.
    - Text chat input with Kannada placeholder.
    - 4 Kannada quick-action prompt chips.
    - Highlight animation: Flashes yellow/green highlight on cards when chatbot executes updates.
