import { API } from './api.js';
import { ChatWidget } from './chat_widget.js';

class VaniApp {
    constructor() {
        this.currentRoute = window.location.pathname.startsWith('/seller') ? '/seller' : '/';
        this.shopConfig = null;
        this.products = [];
        this.orders = [];
        this.cart = []; // [{ product, quantity }]
        this.sellerLoggedIn = Boolean(localStorage.getItem('vani_seller_token'));
        this.activeSellerTab = 'home';
        this.selectedCategory = 'all';
        this.searchQuery = '';
        this.sortBy = '';
        this.chatWidget = null;
        this.customerPhone = null;
        this.customerToken = null;

        this.init();
    }

    async init() {
        try {
            this.shopConfig = await API.getShopConfig();
        } catch (e) {
            console.warn("Using fallback shop config:", e);
            this.shopConfig = {
                shopSlug: "ramesh-kirana",
                shopName: "Ramesh Kirana & General Stores",
                ownerPhone: "9876543210",
                deliveryEnabled: true,
                deliveryFee: 30,
                freeDeliveryAbove: 500,
                serviceablePincodes: ["590001", "590006", "590010"]
            };
        }

        this.setupNavigation();
        await this.loadProducts();
        
        if (this.currentRoute === '/seller') {
            await this.loadOrders();
        }

        this.render();
    }

    setupNavigation() {
        // Handle browser popstate
        window.addEventListener('popstate', () => {
            this.currentRoute = window.location.pathname.startsWith('/seller') ? '/seller' : '/';
            this.render();
        });
    }

    navigate(route) {
        this.currentRoute = route;
        window.history.pushState({}, '', route);
        this.render();
    }

    async loadProducts() {
        try {
            const res = await API.getProducts({
                search: this.searchQuery,
                sort: this.sortBy
            });
            this.products = res.products || [];
        } catch (e) {
            console.error("Failed to load products:", e);
        }
    }

    async loadOrders() {
        try {
            const res = await API.getOrders();
            this.orders = res.orders || [];
        } catch (e) {
            console.error("Failed to load orders:", e);
        }
    }

    // Flash highlight on updated entity (product or order)
    flashHighlight(entityId) {
        if (!entityId) return;
        setTimeout(() => {
            const el = document.getElementById(`card-${entityId}`) || document.getElementById(`row-${entityId}`);
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                el.classList.add('flash-highlight');
                setTimeout(() => el.classList.remove('flash-highlight'), 3000);
            }
        }, 150);
    }

    // Cart operations
    addToCart(product) {
        if (!product.inStock || product.stockCount <= 0) return;
        const existing = this.cart.find(item => item.product.id === product.id);
        if (existing) {
            if (existing.quantity < product.stockCount) {
                existing.quantity += 1;
            } else {
                alert(`Only ${product.stockCount} units available in stock.`);
            }
        } else {
            this.cart.push({ product, quantity: 1 });
        }
        this.renderCartBadges();
        this.renderCartDrawer();
    }

    updateCartQuantity(productId, delta) {
        const item = this.cart.find(it => it.product.id === productId);
        if (!item) return;

        item.quantity += delta;
        if (item.quantity <= 0) {
            this.cart = this.cart.filter(it => it.product.id !== productId);
        } else if (item.quantity > item.product.stockCount) {
            item.quantity = item.product.stockCount;
            alert(`Only ${item.product.stockCount} units available in stock.`);
        }
        this.renderCartBadges();
        this.renderCartDrawer();
    }

    getCartSubtotal() {
        return this.cart.reduce((sum, item) => sum + (item.product.discountPrice * item.quantity), 0);
    }

    getCartDeliveryFee() {
        const subtotal = this.getCartSubtotal();
        if (subtotal === 0) return 0;
        return subtotal >= this.shopConfig.freeDeliveryAbove ? 0 : this.shopConfig.deliveryFee;
    }

    getCartTotal() {
        return this.getCartSubtotal() + this.getCartDeliveryFee();
    }

    renderCartBadges() {
        const count = this.cart.reduce((sum, it) => sum + it.quantity, 0);
        document.querySelectorAll('.cart-count-badge').forEach(el => {
            el.textContent = count;
            el.classList.toggle('hidden', count === 0);
        });
    }

    render() {
        const appContainer = document.getElementById('app');
        if (!appContainer) return;

        if (this.currentRoute === '/seller') {
            if (!this.sellerLoggedIn) {
                this.renderSellerLogin(appContainer);
            } else {
                this.renderSellerDashboard(appContainer);
            }
        } else {
            this.renderStorefront(appContainer);
        }

        this.renderCartBadges();
    }

    // ----------------- BUYER STOREFRONT ----------------- //

    renderStorefront(container) {
        const shop = this.shopConfig;
        const categories = ["all", "Dairy & Staples", "Grains & Rice", "Fresh Vegetables", "Spices & Masala", "Sweets & Snacks", "Beverages", "Personal Care"];

        const filteredProducts = this.products.filter(p => {
            if (this.selectedCategory !== 'all' && p.category !== this.selectedCategory) return false;
            if (this.searchQuery) {
                const q = this.searchQuery.toLowerCase();
                return p.name.toLowerCase().includes(q) || p.unit.toLowerCase().includes(q);
            }
            return true;
        });

        container.innerHTML = `
            <!-- Top Navigation Bar -->
            <header class="bg-white border-b border-slate-200 sticky top-0 z-40 shadow-sm">
                <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between gap-4">
                    <!-- Brand -->
                    <div class="flex items-center gap-3 cursor-pointer" id="store-brand-btn">
                        <div class="w-10 h-10 rounded-xl bg-emerald-600 flex items-center justify-center text-white font-bold text-lg shadow-sm">
                            ವಾ
                        </div>
                        <div>
                            <h1 class="font-bold text-slate-900 text-base sm:text-lg leading-tight font-kannada">
                                ${shop.shopName}
                            </h1>
                            <p class="text-xs text-emerald-700 font-medium flex items-center gap-1">
                                <span class="w-2 h-2 rounded-full bg-emerald-500"></span>
                                Belagavi • ಮನೆ ಬಾಗಿಲಿಗೆ ಡೆಲಿವರಿ (Home Delivery Only)
                            </p>
                        </div>
                    </div>

                    <!-- Actions -->
                    <div class="flex items-center gap-2 sm:gap-4">
                        <!-- Seller Portal Login Link -->
                        <button id="open-seller-btn" class="text-xs font-semibold text-slate-500 hover:text-emerald-700 hover:bg-slate-100 px-3 py-2 rounded-lg transition border border-slate-200">
                            Shop Owner Login
                        </button>

                        <!-- Cart Button -->
                        <button id="cart-drawer-toggle-btn" class="relative bg-emerald-600 hover:bg-emerald-700 text-white px-3.5 py-2 rounded-xl flex items-center gap-2 font-semibold text-sm shadow-sm transition">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>
                            <span class="hidden sm:inline">ಬುಟ್ಟಿ (Cart)</span>
                            <span class="cart-count-badge bg-amber-400 text-slate-900 text-xs font-bold rounded-full h-5 w-5 flex items-center justify-center shadow-sm">
                                0
                            </span>
                        </button>
                    </div>
                </div>
            </header>

            <!-- Storefront Main Content -->
            <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                <!-- Delivery Banner -->
                <div class="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-2xl p-4 mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div class="flex items-center gap-3">
                        <div class="p-2.5 bg-emerald-600 text-white rounded-xl">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0"></path></svg>
                        </div>
                        <div>
                            <h2 class="font-bold text-slate-800 text-sm sm:text-base font-kannada">ಮನೆ ಬಾಗಿಲಿಗೆ ಉಚಿತ ಡೆಲಿವರಿ!</h2>
                            <p class="text-xs text-slate-600">
                                ₹${shop.freeDeliveryAbove}+ ಆರ್ಡರ್‌ಗೆ ಉಚಿತ ಡೆಲಿವರಿ. Serviceable PIN Codes: <span class="font-mono font-semibold text-emerald-800">${shop.serviceablePincodes.join(', ')}</span>
                            </p>
                        </div>
                    </div>
                    <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                        📦 Delivery Only (No Pickup)
                    </span>
                </div>

                <!-- Search & Filter Controls -->
                <div class="flex flex-col sm:flex-row gap-3 items-center justify-between mb-6">
                    <!-- Search input -->
                    <div class="relative w-full sm:w-80">
                        <input type="text" id="store-search-input" value="${this.searchQuery}" placeholder="ಹುಡುಕಿ / Search products..." class="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:border-emerald-500 bg-white text-sm" />
                        <svg class="w-5 h-5 text-slate-400 absolute left-3 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                    </div>

                    <!-- Sort Select -->
                    <div class="w-full sm:w-auto flex items-center gap-2">
                        <label class="text-xs text-slate-500 font-medium whitespace-nowrap">ವಿಂಗಡಿಸಿ (Sort):</label>
                        <select id="store-sort-select" class="bg-white border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-500 text-slate-700">
                            <option value="" ${this.sortBy === '' ? 'selected' : ''}>Default</option>
                            <option value="price_asc" ${this.sortBy === 'price_asc' ? 'selected' : ''}>Price: Low to High</option>
                            <option value="price_desc" ${this.sortBy === 'price_desc' ? 'selected' : ''}>Price: High to Low</option>
                            <option value="discount_desc" ${this.sortBy === 'discount_desc' ? 'selected' : ''}>Discount %</option>
                            <option value="stock" ${this.sortBy === 'stock' ? 'selected' : ''}>In Stock First</option>
                        </select>
                    </div>
                </div>

                <!-- Category Pills -->
                <div class="flex gap-2 overflow-x-auto pb-3 mb-6 scrollbar-none">
                    ${categories.map(cat => `
                        <button class="category-pill px-3.5 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition ${this.selectedCategory === cat ? 'bg-emerald-600 text-white shadow-sm' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'}" data-category="${cat}">
                            ${cat === 'all' ? 'ಎಲ್ಲವೂ (All)' : cat}
                        </button>
                    `).join('')}
                </div>

                <!-- Products Grid -->
                <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                    ${filteredProducts.length === 0 ? `
                        <div class="col-span-full py-16 text-center">
                            <svg class="w-12 h-12 text-slate-300 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"></path></svg>
                            <p class="text-slate-500 font-medium">ಯಾವುದೇ ವಸ್ತುಗಳು ಸಿಗಲಿಲ್ಲ / No products found.</p>
                        </div>
                    ` : filteredProducts.map(p => this.renderProductCardBuyer(p)).join('')}
                </div>
            </main>

            <!-- Cart Drawer Container -->
            <div id="cart-drawer-container"></div>

            <!-- OTP Checkout Modal Container -->
            <div id="otp-modal-container"></div>
        `;

        this.bindStorefrontEvents();
    }

    renderProductCardBuyer(p) {
        const inCartItem = this.cart.find(it => it.product.id === p.id);
        const qty = inCartItem ? inCartItem.quantity : 0;
        const isOutOfStock = !p.inStock || p.stockCount <= 0;

        return `
            <div id="card-${p.id}" class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col relative group">
                
                <!-- Image & Badges -->
                <div class="relative w-full h-36 bg-slate-100 overflow-hidden">
                    <img src="${p.imageUrl || 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=400&q=80'}" alt="${p.name}" class="w-full h-full object-cover group-hover:scale-105 transition duration-300" />
                    
                    <!-- Discount % Badge -->
                    ${p.discountPercent > 0 ? `
                        <span class="absolute top-2 left-2 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full shadow-sm">
                            ${p.discountPercent}% OFF
                        </span>
                    ` : ''}

                    <!-- Unit Pill -->
                    <span class="absolute bottom-2 left-2 bg-black/60 backdrop-blur-sm text-white text-[11px] font-medium px-2 py-0.5 rounded-md">
                        ${p.unit}
                    </span>

                    <!-- Out of stock overlay -->
                    ${isOutOfStock ? `
                        <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-[2px] flex items-center justify-center p-2 text-center">
                            <span class="bg-red-600 text-white text-xs font-bold px-2.5 py-1 rounded-lg shadow-md font-kannada">
                                ಖಾಲಿಯಾಗಿದೆ / Out of Stock
                            </span>
                        </div>
                    ` : ''}
                </div>

                <!-- Info -->
                <div class="p-3.5 flex-1 flex flex-col justify-between">
                    <div>
                        <span class="text-[10px] font-semibold uppercase tracking-wider text-slate-400 block mb-0.5">${p.category}</span>
                        <h3 class="font-bold text-slate-800 text-sm leading-snug line-clamp-2 font-kannada mb-2">${p.name}</h3>
                    </div>

                    <!-- Price & Actions -->
                    <div>
                        <div class="flex items-baseline gap-1.5 mb-3">
                            <span class="text-base font-extrabold text-slate-900">₹${p.discountPrice}</span>
                            ${p.originalPrice > p.discountPrice ? `
                                <span class="text-xs text-slate-400 line-through">₹${p.originalPrice}</span>
                            ` : ''}
                        </div>

                        ${isOutOfStock ? `
                            <button disabled class="w-full py-2 rounded-xl bg-slate-100 text-slate-400 text-xs font-bold cursor-not-allowed">
                                Unavailable
                            </button>
                        ` : qty > 0 ? `
                            <div class="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-xl p-1">
                                <button class="w-7 h-7 bg-white text-emerald-700 hover:bg-emerald-600 hover:text-white rounded-lg font-bold flex items-center justify-center shadow-xs transition btn-cart-minus" data-id="${p.id}">-</button>
                                <span class="text-sm font-bold text-emerald-900">${qty}</span>
                                <button class="w-7 h-7 bg-emerald-600 text-white hover:bg-emerald-700 rounded-lg font-bold flex items-center justify-center shadow-xs transition btn-cart-plus" data-id="${p.id}">+</button>
                            </div>
                        ` : `
                            <button class="w-full py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center gap-1.5 shadow-sm transition btn-add-cart" data-id="${p.id}">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                                ಸೇರಿಸಿ (Add)
                            </button>
                        `}
                    </div>
                </div>
            </div>
        `;
    }

    bindStorefrontEvents() {
        // Open Seller Login
        document.getElementById('open-seller-btn')?.addEventListener('click', () => {
            this.navigate('/seller');
        });

        // Search
        const searchInput = document.getElementById('store-search-input');
        searchInput?.addEventListener('input', (e) => {
            this.searchQuery = e.target.value;
            this.loadProducts().then(() => this.render());
        });

        // Sort
        const sortSelect = document.getElementById('store-sort-select');
        sortSelect?.addEventListener('change', (e) => {
            this.sortBy = e.target.value;
            this.loadProducts().then(() => this.render());
        });

        // Categories
        document.querySelectorAll('.category-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                this.selectedCategory = btn.getAttribute('data-category');
                this.render();
            });
        });

        // Add to Cart Buttons
        document.querySelectorAll('.btn-add-cart').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.getAttribute('data-id');
                const prod = this.products.find(p => p.id === pid);
                if (prod) this.addToCart(prod);
                this.render();
            });
        });

        document.querySelectorAll('.btn-cart-plus').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.getAttribute('data-id');
                this.updateCartQuantity(pid, 1);
                this.render();
            });
        });

        document.querySelectorAll('.btn-cart-minus').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.getAttribute('data-id');
                this.updateCartQuantity(pid, -1);
                this.render();
            });
        });

        // Cart Drawer Toggle
        document.getElementById('cart-drawer-toggle-btn')?.addEventListener('click', () => {
            this.openCartDrawer();
        });
    }

    // ----------------- CART & OTP CHECKOUT ----------------- //

    openCartDrawer() {
        const container = document.getElementById('cart-drawer-container');
        if (!container) return;

        const subtotal = this.getCartSubtotal();
        const deliveryFee = this.getCartDeliveryFee();
        const total = this.getCartTotal();
        const isFreeDelivery = subtotal >= this.shopConfig.freeDeliveryAbove;

        container.innerHTML = `
            <div id="cart-drawer-backdrop" class="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex justify-end">
                <div class="w-full max-w-md bg-white h-full shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-200">
                    
                    <!-- Header -->
                    <div class="p-4 border-b border-slate-200 flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <h2 class="font-bold text-slate-800 text-lg font-kannada">ನಿಮ್ಮ ಬುಟ್ಟಿ (Your Cart)</h2>
                            <span class="bg-emerald-100 text-emerald-800 text-xs font-bold px-2 py-0.5 rounded-full">${this.cart.length} items</span>
                        </div>
                        <button id="close-cart-btn" class="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                        </button>
                    </div>

                    <!-- Items List -->
                    <div class="flex-1 overflow-y-auto p-4 space-y-3">
                        ${this.cart.length === 0 ? `
                            <div class="text-center py-20 text-slate-400">
                                <svg class="w-16 h-16 mx-auto mb-3 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"></path></svg>
                                <p class="font-medium text-slate-500">ಬುಟ್ಟಿ ಖಾಲಿಯಾಗಿದೆ / Cart is empty</p>
                            </div>
                        ` : this.cart.map(item => `
                            <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-200">
                                <div class="flex items-center gap-3">
                                    <img src="${item.product.imageUrl || ''}" class="w-12 h-12 rounded-lg object-cover border border-slate-200" />
                                    <div>
                                        <h4 class="font-bold text-slate-800 text-sm font-kannada leading-tight">${item.product.name}</h4>
                                        <p class="text-xs text-slate-500 font-medium">${item.product.unit} • ₹${item.product.discountPrice}</p>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2">
                                    <button class="w-6 h-6 bg-white border border-slate-300 text-slate-700 rounded font-bold flex items-center justify-center hover:bg-slate-100 cart-drawer-minus" data-id="${item.product.id}">-</button>
                                    <span class="text-sm font-bold w-4 text-center">${item.quantity}</span>
                                    <button class="w-6 h-6 bg-white border border-slate-300 text-slate-700 rounded font-bold flex items-center justify-center hover:bg-slate-100 cart-drawer-plus" data-id="${item.product.id}">+</button>
                                </div>
                            </div>
                        `).join('')}
                    </div>

                    <!-- Bill Summary & Checkout -->
                    ${this.cart.length > 0 ? `
                        <div class="p-4 bg-slate-50 border-t border-slate-200 space-y-3">
                            <div class="space-y-1.5 text-xs text-slate-600">
                                <div class="flex justify-between">
                                    <span>Subtotal</span>
                                    <span class="font-semibold text-slate-800">₹${subtotal}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span>Delivery Fee (Home Delivery Only)</span>
                                    <span class="font-semibold ${isFreeDelivery ? 'text-emerald-700' : 'text-slate-800'}">
                                        ${isFreeDelivery ? 'ಉಚಿತ (FREE)' : `₹${deliveryFee}`}
                                    </span>
                                </div>
                                <div class="border-t border-slate-200 pt-2 flex justify-between text-sm font-extrabold text-slate-900">
                                    <span>ಒಟ್ಟು ಮೊತ್ತ (Total)</span>
                                    <span class="text-emerald-700 text-base">₹${total}</span>
                                </div>
                            </div>

                            <button id="proceed-checkout-btn" class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm rounded-xl shadow-md transition flex items-center justify-center gap-2">
                                <span>ಆರ್ಡರ್ ಮುಂದುವರಿಸಿ (Proceed to Order)</span>
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                            </button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        document.getElementById('close-cart-btn')?.addEventListener('click', () => {
            container.innerHTML = '';
        });

        document.querySelectorAll('.cart-drawer-plus').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.getAttribute('data-id');
                this.updateCartQuantity(pid, 1);
                this.openCartDrawer();
                this.render();
            });
        });

        document.querySelectorAll('.cart-drawer-minus').forEach(btn => {
            btn.addEventListener('click', () => {
                const pid = btn.getAttribute('data-id');
                this.updateCartQuantity(pid, -1);
                this.openCartDrawer();
                this.render();
            });
        });

        document.getElementById('proceed-checkout-btn')?.addEventListener('click', () => {
            container.innerHTML = '';
            this.openOtpModal();
        });
    }

    openOtpModal() {
        const modalContainer = document.getElementById('otp-modal-container');
        if (!modalContainer) return;

        let step = 'PHONE'; // PHONE -> OTP -> ADDRESS -> CONFIRMED
        let phone = this.customerPhone || '9123456789';
        let otp = '1234';
        let address = 'House 42, 3rd Cross, Tilakwadi, Belagavi - 590006';
        let customerName = 'Kiran Patil';
        let paymentMethod = 'UPI';

        const renderModal = () => {
            modalContainer.innerHTML = `
                <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
                    <div class="bg-white rounded-2xl max-w-md w-full shadow-2xl border border-slate-200 overflow-hidden animate-in zoom-in-95 duration-150">
                        
                        <!-- Header -->
                        <div class="bg-gradient-to-r from-emerald-600 to-teal-700 text-white p-4 flex items-center justify-between">
                            <h3 class="font-bold text-base font-kannada">
                                ${step === 'CONFIRMED' ? 'ಆರ್ಡರ್ ಯಶಸ್ವಿಯಾಗಿದೆ!' : 'ಗ್ರಾಹಕರ ವಿವರ (Customer Checkout)'}
                            </h3>
                            ${step !== 'CONFIRMED' ? `
                                <button id="close-otp-modal" class="text-white/80 hover:text-white">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                                </button>
                            ` : ''}
                        </div>

                        <!-- Content Body -->
                        <div class="p-6">
                            ${step === 'PHONE' ? `
                                <div class="space-y-4">
                                    <div>
                                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ಮೊಬೈಲ್ ಸಂಖ್ಯೆ (Mobile Number)</label>
                                        <input type="tel" id="checkout-phone" value="${phone}" maxlength="10" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:border-emerald-600 text-base font-mono" placeholder="10-digit mobile number" />
                                    </div>
                                    <p class="text-xs text-slate-500">ಡೆಮೊ ಪರಿಶೀಲನೆಗಾಗಿ ಯಾವುದೇ 10-ಅಂಕಿಯ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ.</p>
                                    <button id="send-otp-btn" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition text-sm">
                                        OTP ಕಳುಹಿಸಿ (Send OTP)
                                    </button>
                                </div>
                            ` : step === 'OTP' ? `
                                <div class="space-y-4">
                                    <div class="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800">
                                        OTP sent to <span class="font-bold">${phone}</span> (Demo mode: Use <span class="font-bold text-emerald-900 underline">1234</span>)
                                    </div>
                                    <div>
                                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">4-Digit OTP</label>
                                        <input type="text" id="checkout-otp" value="1234" maxlength="4" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 focus:outline-none focus:border-emerald-600 text-center tracking-widest text-lg font-bold font-mono" />
                                    </div>
                                    <button id="verify-otp-btn" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition text-sm">
                                        ಪರಿಶೀಲಿಸಿ (Verify OTP)
                                    </button>
                                </div>
                            ` : step === 'ADDRESS' ? `
                                <div class="space-y-3.5">
                                    <div>
                                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ನಿಮ್ಮ ಹೆಸರು (Full Name)</label>
                                        <input type="text" id="checkout-name" value="${customerName}" class="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:border-emerald-600" />
                                    </div>
                                    <div>
                                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ಡೆಲಿವರಿ ವಿಳಾಸ (Delivery Address with PIN)</label>
                                        <textarea id="checkout-address" rows="2" class="w-full px-3 py-2 rounded-xl border border-slate-300 text-sm focus:outline-none focus:border-emerald-600">${address}</textarea>
                                        <p class="text-[11px] text-slate-500 mt-1">Serviceable PIN codes: 590001, 590006, 590010</p>
                                    </div>
                                    <div>
                                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ಪಾವತಿ ವಿಧಾನ (Payment Method)</label>
                                        <div class="grid grid-cols-2 gap-2 text-xs font-bold">
                                            <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer ${paymentMethod === 'UPI' ? 'border-emerald-600 bg-emerald-50 text-emerald-900' : 'border-slate-200'}">
                                                <input type="radio" name="paymethod" value="UPI" ${paymentMethod === 'UPI' ? 'checked' : ''} />
                                                <span>UPI Payment</span>
                                            </label>
                                            <label class="flex items-center gap-2 p-2.5 rounded-xl border cursor-pointer ${paymentMethod === 'COD' ? 'border-emerald-600 bg-emerald-50 text-emerald-900' : 'border-slate-200'}">
                                                <input type="radio" name="paymethod" value="COD" ${paymentMethod === 'COD' ? 'checked' : ''} />
                                                <span>Cash on Delivery</span>
                                            </label>
                                        </div>
                                    </div>
                                    <div class="p-2.5 bg-slate-50 rounded-xl flex justify-between items-center text-xs font-bold">
                                        <span>Total to Pay:</span>
                                        <span class="text-emerald-700 text-sm">₹${this.getCartTotal()}</span>
                                    </div>
                                    <button id="confirm-order-btn" class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition text-sm shadow-md">
                                        ಆರ್ಡರ್ ದೃಢೀಕರಿಸಿ (Confirm & Place Order)
                                    </button>
                                </div>
                            ` : `
                                <!-- ORDER CONFIRMED -->
                                <div class="text-center py-4 space-y-3">
                                    <div class="w-16 h-16 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center mx-auto shadow-inner">
                                        <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path></svg>
                                    </div>
                                    <h4 class="font-bold text-slate-800 text-lg font-kannada">ಆರ್ಡರ್ ಸ್ವೀಕರಿಸಲಾಗಿದೆ!</h4>
                                    <p class="text-xs text-slate-600">ನಿಮ್ಮ ಆರ್ಡರ್ ಅಂಗಡಿ ಮಾಲೀಕರಿಗೆ ತಲುಪಿದೆ. ಶೀಘ್ರದಲ್ಲೇ ಮನೆ ಬಾಗಿಲಿಗೆ ತಲುಪಿಸಲಾಗುವುದು.</p>
                                    <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl text-left text-xs space-y-1">
                                        <p><span class="font-bold">Phone:</span> ${phone}</p>
                                        <p><span class="font-bold">Address:</span> ${address}</p>
                                        <p><span class="font-bold">Total:</span> ₹${this.getCartTotal()}</p>
                                    </div>
                                    <button id="done-order-btn" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition text-sm">
                                        ಮತ್ತಷ್ಟು ಶಾಪಿಂಗ್ ಮಾಡಿ (Continue Shopping)
                                    </button>
                                </div>
                            `}
                        </div>
                    </div>
                </div>
            `;

            document.getElementById('close-otp-modal')?.addEventListener('click', () => {
                modalContainer.innerHTML = '';
            });

            document.getElementById('send-otp-btn')?.addEventListener('click', async () => {
                const p = document.getElementById('checkout-phone').value.trim();
                if (p.length < 10) return alert("Please enter a valid 10-digit mobile number.");
                phone = p;
                await API.sendCustomerOtp(phone);
                step = 'OTP';
                renderModal();
            });

            document.getElementById('verify-otp-btn')?.addEventListener('click', async () => {
                const o = document.getElementById('checkout-otp').value.trim();
                try {
                    const res = await API.verifyCustomerOtp(phone, o);
                    this.customerPhone = phone;
                    this.customerToken = res.token;
                    step = 'ADDRESS';
                    renderModal();
                } catch (err) {
                    alert(err.message || "Invalid OTP");
                }
            });

            document.querySelectorAll('input[name="paymethod"]').forEach(radio => {
                radio.addEventListener('change', (e) => {
                    paymentMethod = e.target.value;
                    renderModal();
                });
            });

            document.getElementById('confirm-order-btn')?.addEventListener('click', async () => {
                customerName = document.getElementById('checkout-name')?.value || customerName;
                address = document.getElementById('checkout-address')?.value || address;

                const items = this.cart.map(it => ({
                    productId: it.product.id,
                    name: it.product.name,
                    unit: it.product.unit,
                    quantity: it.quantity,
                    priceAtOrder: it.product.discountPrice
                }));

                try {
                    await API.createOrder({
                        customerPhone: phone,
                        customerName: customerName,
                        deliveryAddress: address,
                        items: items,
                        paymentMethod: paymentMethod
                    });
                    this.cart = [];
                    step = 'CONFIRMED';
                    renderModal();
                } catch (err) {
                    alert(err.message || "Failed to place order.");
                }
            });

            document.getElementById('done-order-btn')?.addEventListener('click', () => {
                modalContainer.innerHTML = '';
                this.loadProducts().then(() => this.render());
            });
        };

        renderModal();
    }

    // ----------------- SELLER DASHBOARD ----------------- //

    renderSellerLogin(container) {
        container.innerHTML = `
            <div class="min-h-screen bg-slate-100 flex items-center justify-center p-4">
                <div class="bg-white rounded-3xl shadow-xl max-w-md w-full p-8 border border-slate-200">
                    <div class="text-center mb-6">
                        <div class="w-14 h-14 rounded-2xl bg-emerald-600 text-white font-bold text-2xl flex items-center justify-center mx-auto mb-3 shadow-md">
                            ವಾ
                        </div>
                        <h2 class="text-xl font-extrabold text-slate-800 font-kannada">ಅಂಗಡಿ ಮಾಲೀಕರ ಲಾಗಿನ್</h2>
                        <p class="text-xs text-slate-500 mt-1">Vani Seller Dashboard Access</p>
                    </div>

                    <form id="seller-login-form" class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ಮೊಬೈಲ್ ಸಂಖ್ಯೆ (Phone)</label>
                            <input type="tel" id="seller-phone" value="9876543210" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm font-mono focus:border-emerald-600 focus:outline-none" />
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 uppercase mb-1">ಪಾಸ್‌ವರ್ಡ್ (Password)</label>
                            <input type="password" id="seller-pass" value="demo123" class="w-full px-3.5 py-2.5 rounded-xl border border-slate-300 text-sm focus:border-emerald-600 focus:outline-none" />
                        </div>

                        <div class="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-800">
                            Demo Credentials: Phone: <span class="font-bold">9876543210</span>, Password: <span class="font-bold">demo123</span>
                        </div>

                        <button type="submit" class="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl transition text-sm shadow-md">
                            ಲಾಗಿನ್ ಮಾಡಿ (Login to Dashboard)
                        </button>
                    </form>

                    <div class="mt-6 text-center">
                        <button id="back-to-store-btn" class="text-xs text-slate-500 hover:text-emerald-700 underline font-medium">
                            ← Return to Buyer Storefront
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.getElementById('seller-login-form')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const phone = document.getElementById('seller-phone').value;
            const pass = document.getElementById('seller-pass').value;
            try {
                const res = await API.sellerLogin(phone, pass);
                localStorage.setItem('vani_seller_token', res.token);
                this.sellerLoggedIn = true;
                await this.loadOrders();
                this.render();
            } catch (err) {
                alert(err.message || "Login failed");
            }
        });

        document.getElementById('back-to-store-btn')?.addEventListener('click', () => {
            this.navigate('/');
        });
    }

    renderSellerDashboard(container) {
        const tabs = [
            { id: 'home', label: 'Home', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
            { id: 'pricing', label: 'Pricing & Discounts', icon: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z' },
            { id: 'inventory', label: 'Inventory Control', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
            { id: 'orders', label: 'Order Management', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01' },
            { id: 'delivery', label: 'Delivery & Logistics', icon: 'M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0' },
            { id: 'reports', label: 'Sales & Reports', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' }
        ];

        container.innerHTML = `
            <div class="min-h-screen bg-slate-50 flex flex-col">
                
                <!-- Seller Top Navbar -->
                <header class="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
                    <div class="px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                        <div class="flex items-center gap-3">
                            <div class="w-9 h-9 rounded-xl bg-emerald-700 text-white flex items-center justify-center font-bold text-base shadow-sm">
                                ವಾ
                            </div>
                            <div>
                                <h2 class="font-bold text-slate-800 text-sm sm:text-base font-kannada leading-tight">
                                    ${this.shopConfig.shopName}
                                </h2>
                                <p class="text-xs text-slate-400">Seller Dashboard • Belagavi</p>
                            </div>
                        </div>

                        <div class="flex items-center gap-2 sm:gap-3">
                            <!-- Switch to Buyer Storefront Button -->
                            <button id="view-storefront-btn" class="text-xs font-semibold text-slate-600 hover:text-emerald-700 hover:bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200 transition flex items-center gap-1.5">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                                <span class="hidden sm:inline">View Storefront</span>
                            </button>

                            <!-- Logout -->
                            <button id="seller-logout-btn" class="text-xs font-semibold text-red-600 hover:bg-red-50 px-3 py-1.5 rounded-lg border border-red-200 transition">
                                Logout
                            </button>
                        </div>
                    </div>
                </header>

                <!-- Dashboard Layout: Sidebar + Main Content -->
                <div class="flex-1 flex overflow-hidden">
                    
                    <!-- Left Sidebar -->
                    <aside class="w-64 bg-white border-r border-slate-200 flex flex-col justify-between p-4 hidden md:flex shrink-0">
                        <nav class="space-y-1.5">
                            ${tabs.map(t => `
                                <button class="seller-tab-btn w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-semibold text-xs tracking-wide transition ${this.activeSellerTab === t.id ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}" data-tab="${t.id}">
                                    <svg class="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${t.icon}"></path></svg>
                                    <span>${t.label}</span>
                                </button>
                            `).join('')}
                        </nav>

                        <!-- Store Quick Status Card -->
                        <div class="p-3 bg-slate-50 border border-slate-200 rounded-2xl text-xs space-y-1.5">
                            <div class="flex justify-between items-center text-slate-500">
                                <span>Total Products:</span>
                                <span class="font-bold text-slate-800">${this.products.length}</span>
                            </div>
                            <div class="flex justify-between items-center text-slate-500">
                                <span>Pending Orders:</span>
                                <span class="font-bold text-emerald-700">${this.orders.filter(o => o.status === 'NEW' || o.status === 'PACKED').length}</span>
                            </div>
                        </div>
                    </aside>

                    <!-- Main Dashboard Content (with container id for pb-80 clearance padding) -->
                    <main id="seller-dashboard-content" class="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 transition-all duration-300">
                        ${this.renderActiveSellerTabContent()}
                    </main>
                </div>

                <!-- EMBEDDED CHATBOT WIDGET MOUNT POINT -->
                <div id="chat-widget-container"></div>
            </div>
        `;

        this.bindSellerEvents();

        // Instantiate Embedded Chatbot Widget
        this.chatWidget = new ChatWidget({
            containerId: 'chat-widget-container',
            onEntityUpdated: async (intent, entity, entityId) => {
                await this.loadProducts();
                await this.loadOrders();
                this.render();
                this.flashHighlight(entityId);
            }
        });
    }

    renderActiveSellerTabContent() {
        if (this.activeSellerTab === 'home') return this.renderTabHome();
        if (this.activeSellerTab === 'pricing') return this.renderTabPricing();
        if (this.activeSellerTab === 'inventory') return this.renderTabInventory();
        if (this.activeSellerTab === 'orders') return this.renderTabOrders();
        if (this.activeSellerTab === 'delivery') return this.renderTabDelivery();
        if (this.activeSellerTab === 'reports') return this.renderTabReports();
        return '';
    }

    // 1. Tab: Home
    renderTabHome() {
        return `
            <div>
                <!-- Top Toolbar -->
                <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
                    <div>
                        <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಸರಕುಗಳ ನಿರ್ವಹಣೆ (Products Catalog)</h2>
                        <p class="text-xs text-slate-500">1-Tap In-Stock Toggle, Search & Sort</p>
                    </div>

                    <!-- Search & Sort -->
                    <div class="flex items-center gap-3 w-full sm:w-auto">
                        <input type="text" id="seller-search" value="${this.searchQuery}" placeholder="Search products..." class="bg-white border border-slate-300 px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-emerald-600 w-full sm:w-56" />
                        <select id="seller-sort" class="bg-white border border-slate-300 px-3 py-2 rounded-xl text-xs focus:outline-none focus:border-emerald-600">
                            <option value="">Sort: Default</option>
                            <option value="price_asc" ${this.sortBy === 'price_asc' ? 'selected' : ''}>Price: Low to High</option>
                            <option value="price_desc" ${this.sortBy === 'price_desc' ? 'selected' : ''}>Price: High to Low</option>
                            <option value="discount_desc" ${this.sortBy === 'discount_desc' ? 'selected' : ''}>Discount %</option>
                            <option value="stock" ${this.sortBy === 'stock' ? 'selected' : ''}>Stock Level</option>
                        </select>
                    </div>
                </div>

                <!-- Product Grid -->
                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                    ${this.products.map(p => `
                        <div id="card-${p.id}" class="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
                            <div>
                                <div class="relative h-32 rounded-xl bg-slate-100 overflow-hidden mb-3">
                                    <img src="${p.imageUrl || ''}" class="w-full h-full object-cover" />
                                    ${p.discountPercent > 0 ? `
                                        <span class="absolute top-2 left-2 bg-emerald-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                                            ${p.discountPercent}% OFF
                                        </span>
                                    ` : ''}
                                    <span class="absolute bottom-2 left-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded-md">
                                        ${p.unit}
                                    </span>
                                </div>
                                <h4 class="font-bold text-slate-800 text-sm font-kannada leading-tight line-clamp-1">${p.name}</h4>
                                <span class="text-[11px] text-slate-400 uppercase tracking-wider block mb-2">${p.category}</span>
                                
                                <div class="flex items-baseline gap-2 mb-3">
                                    <span class="text-base font-extrabold text-slate-900">₹${p.discountPrice}</span>
                                    ${p.originalPrice > p.discountPrice ? `
                                        <span class="text-xs text-slate-400 line-through">₹${p.originalPrice}</span>
                                    ` : ''}
                                </div>
                            </div>

                            <!-- 1-Tap inStock Toggle Switch -->
                            <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
                                <span class="text-xs font-semibold ${p.inStock ? 'text-emerald-700' : 'text-red-500'}">
                                    ${p.inStock ? `In Stock (${p.stockCount})` : 'Out of Stock'}
                                </span>
                                
                                <label class="relative inline-flex items-center cursor-pointer">
                                    <input type="checkbox" class="sr-only peer stock-toggle-input" data-id="${p.id}" ${p.inStock ? 'checked' : ''} />
                                    <div class="w-9 h-5 bg-slate-300 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-600"></div>
                                </label>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 2. Tab: Pricing & Discounts
    renderTabPricing() {
        return `
            <div class="max-w-5xl">
                <div class="mb-6">
                    <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಬೆಲೆ ಮತ್ತು ರಿಯಾಯಿತಿ (Pricing & Discounts)</h2>
                    <p class="text-xs text-slate-500">Live discountPercent auto-calculation: round(((orig - disc) / orig) * 100)</p>
                </div>

                <div class="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
                    <div class="overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                                <tr>
                                    <th class="p-3.5">Product</th>
                                    <th class="p-3.5">Unit</th>
                                    <th class="p-3.5">Original Price (₹)</th>
                                    <th class="p-3.5">Discount Price (₹)</th>
                                    <th class="p-3.5">Discount %</th>
                                    <th class="p-3.5 text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-100">
                                ${this.products.map(p => `
                                    <tr id="row-${p.id}" class="hover:bg-slate-50/80 transition">
                                        <td class="p-3.5 font-bold text-slate-800 font-kannada flex items-center gap-2">
                                            <img src="${p.imageUrl || ''}" class="w-8 h-8 rounded object-cover" />
                                            <span>${p.name}</span>
                                        </td>
                                        <td class="p-3.5 text-slate-500 font-mono">${p.unit}</td>
                                        <td class="p-3.5">
                                            <input type="number" id="orig-price-${p.id}" value="${p.originalPrice}" class="w-20 px-2 py-1 rounded border border-slate-300 font-mono" />
                                        </td>
                                        <td class="p-3.5">
                                            <input type="number" id="disc-price-${p.id}" value="${p.discountPrice}" class="w-20 px-2 py-1 rounded border border-slate-300 font-mono" />
                                        </td>
                                        <td class="p-3.5">
                                            <span class="inline-block px-2 py-0.5 rounded-full text-[11px] font-bold ${p.discountPercent > 0 ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-500'}">
                                                ${p.discountPercent}% OFF
                                            </span>
                                        </td>
                                        <td class="p-3.5 text-right">
                                            <button class="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-bold text-xs save-price-btn" data-id="${p.id}">
                                                Save
                                            </button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }

    // 3. Tab: Inventory Control
    renderTabInventory() {
        return `
            <div class="max-w-5xl">
                <div class="mb-6">
                    <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಸ್ಟಾಕ್ ನಿಯಂತ್ರಣ (Inventory Control)</h2>
                    <p class="text-xs text-slate-500">Monitor stock levels, set thresholds, and mark availability</p>
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                    ${this.products.map(p => {
                        const isLowStock = p.stockCount <= p.lowStockThreshold;
                        return `
                            <div id="card-${p.id}" class="bg-white rounded-2xl border ${isLowStock ? 'border-amber-300 ring-2 ring-amber-100' : 'border-slate-200'} p-4 shadow-xs">
                                <div class="flex items-center justify-between mb-2">
                                    <span class="text-xs font-semibold uppercase text-slate-400">${p.category}</span>
                                    ${isLowStock ? `
                                        <span class="bg-amber-100 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded-full">
                                            Low Stock Alert
                                        </span>
                                    ` : ''}
                                </div>
                                <h4 class="font-bold text-slate-800 text-sm font-kannada mb-3">${p.name}</h4>
                                
                                <div class="space-y-2 text-xs">
                                    <div class="flex items-center justify-between">
                                        <label class="text-slate-500">Stock Count:</label>
                                        <input type="number" id="stock-count-${p.id}" value="${p.stockCount}" class="w-20 px-2 py-1 rounded border border-slate-300 font-mono text-center" />
                                    </div>
                                    <div class="flex items-center justify-between">
                                        <label class="text-slate-500">Threshold:</label>
                                        <span class="font-mono text-slate-700">${p.lowStockThreshold} units</span>
                                    </div>
                                </div>

                                <button class="w-full mt-4 py-1.5 bg-slate-800 hover:bg-slate-900 text-white rounded-xl text-xs font-bold save-stock-btn" data-id="${p.id}">
                                    Update Stock
                                </button>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    // 4. Tab: Order Management
    renderTabOrders() {
        const statusColors = {
            'NEW': 'bg-sky-100 text-sky-800 border-sky-300',
            'PACKED': 'bg-amber-100 text-amber-800 border-amber-300',
            'OUT_FOR_DELIVERY': 'bg-purple-100 text-purple-800 border-purple-300',
            'DELIVERED': 'bg-emerald-100 text-emerald-800 border-emerald-300',
            'CANCELLED': 'bg-red-100 text-red-800 border-red-300'
        };

        return `
            <div class="max-w-5xl">
                <div class="mb-6">
                    <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಆರ್ಡರ್ ನಿರ್ವಹಣೆ (Order Management)</h2>
                    <p class="text-xs text-slate-500">Status transitions: NEW -> PACKED -> OUT_FOR_DELIVERY -> DELIVERED -> CANCELLED</p>
                </div>

                <div class="space-y-4">
                    ${this.orders.length === 0 ? `
                        <p class="text-slate-400 py-10 text-center text-sm font-medium">No orders yet.</p>
                    ` : this.orders.map(o => `
                        <div id="card-${o.id}" class="bg-white rounded-2xl border border-slate-200 p-4 shadow-xs space-y-3">
                            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                                <div class="flex items-center gap-3">
                                    <span class="font-mono font-extrabold text-sm text-slate-900">#${o.id}</span>
                                    <span class="text-xs text-slate-400 font-medium">${new Date(o.createdAt).toLocaleString()}</span>
                                    <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${statusColors[o.status] || 'bg-slate-100 text-slate-700'}">
                                        ${o.status}
                                    </span>
                                </div>
                                <div class="flex items-center gap-2">
                                    <span class="text-xs font-bold text-slate-500">Status:</span>
                                    <select class="order-status-select bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-bold focus:outline-none" data-id="${o.id}">
                                        <option value="NEW" ${o.status === 'NEW' ? 'selected' : ''}>NEW</option>
                                        <option value="PACKED" ${o.status === 'PACKED' ? 'selected' : ''}>PACKED</option>
                                        <option value="OUT_FOR_DELIVERY" ${o.status === 'OUT_FOR_DELIVERY' ? 'selected' : ''}>OUT_FOR_DELIVERY</option>
                                        <option value="DELIVERED" ${o.status === 'DELIVERED' ? 'selected' : ''}>DELIVERED</option>
                                        <option value="CANCELLED" ${o.status === 'CANCELLED' ? 'selected' : ''}>CANCELLED</option>
                                    </select>
                                </div>
                            </div>

                            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                                <div>
                                    <span class="text-slate-400 block font-semibold">Customer:</span>
                                    <span class="font-bold text-slate-800">${o.customerName}</span>
                                    <span class="text-slate-500 block">${o.customerPhone}</span>
                                </div>
                                <div>
                                    <span class="text-slate-400 block font-semibold">Delivery Address:</span>
                                    <span class="text-slate-700">${o.deliveryAddress}</span>
                                </div>
                                <div>
                                    <span class="text-slate-400 block font-semibold">Payment & Total:</span>
                                    <span class="font-bold text-emerald-800 text-sm">₹${o.totalAmount}</span>
                                    <span class="text-slate-500 block">Method: ${o.paymentMethod}</span>
                                </div>
                            </div>

                            <!-- Items in order -->
                            <div class="bg-slate-50 rounded-xl p-2.5 text-xs text-slate-700 flex flex-wrap gap-3">
                                ${o.items.map(it => `
                                    <span class="bg-white px-2 py-1 rounded-md border border-slate-200 font-medium">
                                        ${it.name} (${it.unit}) × <strong>${it.quantity}</strong>
                                    </span>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // 5. Tab: Delivery & Logistics
    renderTabDelivery() {
        const shop = this.shopConfig;
        return `
            <div class="max-w-4xl">
                <div class="mb-6">
                    <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಡೆಲಿವರಿ ಮತ್ತು ಲಾಜಿಸ್ಟಿಕ್ಸ್ (Delivery & Logistics)</h2>
                    <p class="text-xs text-slate-500">Every shopkeeper must deliver orders; manage fees and serviceable areas.</p>
                </div>

                <div class="bg-white rounded-2xl border border-slate-200 p-6 space-y-6 shadow-xs">
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Standard Delivery Fee (₹)</label>
                            <input type="number" id="delivery-fee-input" value="${shop.deliveryFee}" class="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-mono" />
                        </div>
                        <div>
                            <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Free Delivery Above (₹)</label>
                            <input type="number" id="free-delivery-input" value="${shop.freeDeliveryAbove}" class="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-mono" />
                        </div>
                    </div>

                    <div>
                        <label class="block text-xs font-bold text-slate-700 uppercase mb-1">Serviceable PIN Codes (Comma Separated)</label>
                        <input type="text" id="pincodes-input" value="${shop.serviceablePincodes.join(', ')}" class="w-full px-3 py-2 border border-slate-300 rounded-xl text-sm font-mono" />
                    </div>

                    <div class="pt-4 border-t border-slate-100 flex justify-end">
                        <button id="save-logistics-btn" class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-sm transition">
                            Save Logistics Settings
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // 6. Tab: Sales & Reports
    renderTabReports() {
        // Calculate report metrics
        const totalRevenue = this.orders.filter(o => o.status !== 'CANCELLED').reduce((sum, o) => sum + o.totalAmount, 0);
        const totalOrders = this.orders.filter(o => o.status !== 'CANCELLED').length;
        const upiRevenue = this.orders.filter(o => o.paymentMethod === 'UPI' && o.status !== 'CANCELLED').reduce((sum, o) => sum + o.totalAmount, 0);
        const codRevenue = this.orders.filter(o => o.paymentMethod === 'COD' && o.status !== 'CANCELLED').reduce((sum, o) => sum + o.totalAmount, 0);
        const lowStockCount = this.products.filter(p => p.stockCount <= p.lowStockThreshold).length;

        return `
            <div class="max-w-5xl">
                <div class="mb-6">
                    <h2 class="text-xl font-extrabold text-slate-900 font-kannada">ಮಾರಾಟ ವರದಿ (Sales & Reports)</h2>
                    <p class="text-xs text-slate-500">Live summary of revenue, payment breakdown, and low stock</p>
                </div>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                        <span class="text-xs text-slate-400 font-semibold block">Total Revenue</span>
                        <span class="text-xl font-extrabold text-emerald-700 mt-1 block">₹${totalRevenue.toLocaleString()}</span>
                    </div>
                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                        <span class="text-xs text-slate-400 font-semibold block">Total Orders</span>
                        <span class="text-xl font-extrabold text-slate-800 mt-1 block">${totalOrders}</span>
                    </div>
                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                        <span class="text-xs text-slate-400 font-semibold block">UPI Revenue</span>
                        <span class="text-xl font-extrabold text-purple-700 mt-1 block">₹${upiRevenue.toLocaleString()}</span>
                    </div>
                    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-xs">
                        <span class="text-xs text-slate-400 font-semibold block">Low Stock Alert</span>
                        <span class="text-xl font-extrabold text-amber-600 mt-1 block">${lowStockCount} items</span>
                    </div>
                </div>
            </div>
        `;
    }

    bindSellerEvents() {
        // Tab switching
        document.querySelectorAll('.seller-tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.activeSellerTab = btn.getAttribute('data-tab');
                this.render();
            });
        });

        // View Storefront
        document.getElementById('view-storefront-btn')?.addEventListener('click', () => {
            this.navigate('/');
        });

        // Logout
        document.getElementById('seller-logout-btn')?.addEventListener('click', () => {
            localStorage.removeItem('vani_seller_token');
            this.sellerLoggedIn = false;
            this.render();
        });

        // 1-Tap Stock Toggle
        document.querySelectorAll('.stock-toggle-input').forEach(chk => {
            chk.addEventListener('change', async (e) => {
                const pid = e.target.getAttribute('data-id');
                const inStock = e.target.checked;
                await API.updateProduct(pid, { inStock, stockCount: inStock ? 10 : 0 });
                await this.loadProducts();
                this.render();
                this.flashHighlight(pid);
            });
        });

        // Save Price Button
        document.querySelectorAll('.save-price-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.getAttribute('data-id');
                const orig = parseFloat(document.getElementById(`orig-price-${pid}`).value);
                const disc = parseFloat(document.getElementById(`disc-price-${pid}`).value);
                await API.updateProduct(pid, { originalPrice: orig, discountPrice: disc });
                await this.loadProducts();
                this.render();
                this.flashHighlight(pid);
            });
        });

        // Save Stock Button
        document.querySelectorAll('.save-stock-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.getAttribute('data-id');
                const count = parseInt(document.getElementById(`stock-count-${pid}`).value);
                await API.updateProduct(pid, { stockCount: count, inStock: count > 0 });
                await this.loadProducts();
                this.render();
                this.flashHighlight(pid);
            });
        });

        // Order Status Select
        document.querySelectorAll('.order-status-select').forEach(sel => {
            sel.addEventListener('change', async (e) => {
                const oid = e.target.getAttribute('data-id');
                const status = e.target.value;
                await API.updateOrderStatus(oid, status);
                await this.loadOrders();
                this.render();
                this.flashHighlight(oid);
            });
        });

        // Save Logistics
        document.getElementById('save-logistics-btn')?.addEventListener('click', async () => {
            const fee = parseInt(document.getElementById('delivery-fee-input').value);
            const freeAbove = parseInt(document.getElementById('free-delivery-input').value);
            const pins = document.getElementById('pincodes-input').value.split(',').map(s => s.trim()).filter(Boolean);
            await API.updateShopConfig({ deliveryFee: fee, freeDeliveryAbove: freeAbove, serviceablePincodes: pins });
            this.shopConfig = await API.getShopConfig();
            alert("Logistics settings saved successfully!");
            this.render();
        });
    }
}

// Instantiate App
window.addEventListener('DOMContentLoaded', () => {
    new VaniApp();
});
