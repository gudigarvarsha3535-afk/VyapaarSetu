/**
 * Vani - API Client
 * Automatically connects to backend REST endpoints.
 */

// Auto-detect base API URL: if served from port 5173, point to http://localhost:8000/api; if served from 8000, point to /api
const API_BASE = window.location.port === "5173" ? "http://localhost:8000/api" : "/api";

export const API = {
    // Shop Config
    async getShopConfig() {
        const res = await fetch(`${API_BASE}/shop/config`);
        return await res.json();
    },

    async updateShopConfig(updates) {
        const res = await fetch(`${API_BASE}/shop/config`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updates)
        });
        return await res.json();
    },

    // Auth
    async sendCustomerOtp(phone) {
        const res = await fetch(`${API_BASE}/auth/customer/send-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone })
        });
        return await res.json();
    },

    async verifyCustomerOtp(phone, otp) {
        const res = await fetch(`${API_BASE}/auth/customer/verify-otp`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, otp })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "OTP verification failed");
        }
        return await res.json();
    },

    async sellerLogin(phone, password) {
        const res = await fetch(`${API_BASE}/auth/seller/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ phone, password })
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Seller login failed");
        }
        return await res.json();
    },

    // Products
    async getProducts(params = {}) {
        const query = new URLSearchParams();
        if (params.search) query.append("search", params.search);
        if (params.sort) query.append("sort", params.sort);
        if (params.discountedOnly) query.append("discountedOnly", "true");

        const url = `${API_BASE}/products${query.toString() ? "?" + query.toString() : ""}`;
        const res = await fetch(url);
        return await res.json();
    },

    async createProduct(productData) {
        const res = await fetch(`${API_BASE}/products`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(productData)
        });
        return await res.json();
    },

    async updateProduct(id, updates) {
        const res = await fetch(`${API_BASE}/products/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(updates)
        });
        return await res.json();
    },

    async deleteProduct(id) {
        const res = await fetch(`${API_BASE}/products/${id}`, {
            method: "DELETE"
        });
        return await res.json();
    },

    // Orders
    async getOrders() {
        const res = await fetch(`${API_BASE}/orders`);
        return await res.json();
    },

    async createOrder(orderData) {
        const res = await fetch(`${API_BASE}/orders`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(orderData)
        });
        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Order creation failed");
        }
        return await res.json();
    },

    async updateOrderStatus(orderId, status, deliveryPartner = null) {
        const res = await fetch(`${API_BASE}/orders/${orderId}/status`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status, deliveryPartner })
        });
        return await res.json();
    },

    // Sales Reports
    async getSalesReport() {
        const res = await fetch(`${API_BASE}/reports/summary`);
        return await res.json();
    },

    // Bot message
    async sendBotMessage(payload) {
        const res = await fetch(`${API_BASE}/bot/message`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        return await res.json();
    }
};
