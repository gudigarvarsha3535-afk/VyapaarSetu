from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import copy
from backend.models import ShopConfig, Product, Order, OrderItem

class Database:
    def __init__(self):
        self.reset()

    def reset(self):
        self.shop_config: ShopConfig = ShopConfig(
            shopSlug="ramesh-kirana",
            shopName="Ramesh Kirana & General Stores",
            ownerPhone="9876543210",
            deliveryEnabled=True,
            deliveryFee=30,
            freeDeliveryAbove=500,
            serviceablePincodes=["590001", "590006", "590010"]
        )

        # Realistic Karnataka Seed Products
        self.products: Dict[str, Product] = {
            "prod_101": Product(
                id="prod_101",
                name="Nandini Pure Ghee",
                category="Dairy & Staples",
                unit="500 ml",
                originalPrice=320,
                discountPrice=295,
                inStock=True,
                stockCount=14,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1589927986089-35812388d1f4?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:00:00Z"
            ),
            "prod_102": Product(
                id="prod_102",
                name="Sona Masoori Rice (Akki)",
                category="Grains & Rice",
                unit="5 kg",
                originalPrice=340,
                discountPrice=310,
                inStock=True,
                stockCount=22,
                lowStockThreshold=8,
                imageUrl="https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:05:00Z"
            ),
            "prod_103": Product(
                id="prod_103",
                name="Mysore Sandal Soap",
                category="Personal Care",
                unit="3 x 150 g",
                originalPrice=210,
                discountPrice=195,
                inStock=True,
                stockCount=18,
                lowStockThreshold=6,
                imageUrl="https://images.unsplash.com/photo-1607006314177-38605337eb02?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:10:00Z"
            ),
            "prod_104": Product(
                id="prod_104",
                name="Byadgi Chilli Powder (Menasinakayi)",
                category="Spices & Masala",
                unit="500 g",
                originalPrice=180,
                discountPrice=165,
                inStock=True,
                stockCount=3,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1596040033229-a9821ebd058d?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:15:00Z"
            ),
            "prod_105": Product(
                id="prod_105",
                name="Organic Bellam (Jaggery / Bella)",
                category="Staples & Sweeteners",
                unit="1 kg",
                originalPrice=90,
                discountPrice=80,
                inStock=True,
                stockCount=12,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1615485290382-441e4d049cb5?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:20:00Z"
            ),
            "prod_106": Product(
                id="prod_106",
                name="Fresh Garlic (Bellulli)",
                category="Fresh Vegetables",
                unit="250 g",
                originalPrice=90,
                discountPrice=80,
                inStock=True,
                stockCount=15,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1615477032128-4447432eb846?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:25:00Z"
            ),
            "prod_107": Product(
                id="prod_107",
                name="Fresh Tomato (Tamota)",
                category="Fresh Vegetables",
                unit="1 kg",
                originalPrice=40,
                discountPrice=35,
                inStock=True,
                stockCount=25,
                lowStockThreshold=10,
                imageUrl="https://images.unsplash.com/photo-1592924357228-91a4daadcfea?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:30:00Z"
            ),
            "prod_108": Product(
                id="prod_108",
                name="Mysore Pak Traditional Sweet",
                category="Sweets & Snacks",
                unit="500 g",
                originalPrice=250,
                discountPrice=220,
                inStock=False,
                stockCount=0,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1599785209707-a456fc1337bb?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:35:00Z"
            ),
            "prod_109": Product(
                id="prod_109",
                name="Filter Coffee Powder (80:20 Blend)",
                category="Beverages",
                unit="250 g",
                originalPrice=160,
                discountPrice=150,
                inStock=True,
                stockCount=16,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1559056199-641a0ac8b55e?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:40:00Z"
            ),
            "prod_110": Product(
                id="prod_110",
                name="Aashirvaad Shudh Chakki Atta",
                category="Flour & Atta",
                unit="5 kg",
                originalPrice=285,
                discountPrice=260,
                inStock=True,
                stockCount=8,
                lowStockThreshold=5,
                imageUrl="https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=400&q=80",
                updatedAt="2026-11-25T14:45:00Z"
            )
        }

        # Seed Orders
        self.orders: Dict[str, Order] = {
            "ORD-101": Order(
                id="ORD-101",
                customerPhone="9123456789",
                customerName="Kiran Patil",
                deliveryAddress="House 42, 3rd Cross, Tilakwadi, Belagavi - 590006",
                items=[
                    OrderItem(
                        productId="prod_101",
                        name="Nandini Pure Ghee",
                        unit="500 ml",
                        quantity=2,
                        priceAtOrder=295
                    )
                ],
                subtotal=590,
                deliveryFee=0,
                totalAmount=590,
                paymentMethod="UPI",
                status="NEW",
                deliveryPartner="Self-Delivery",
                createdAt="2026-11-25T14:15:00Z"
            ),
            "ORD-102": Order(
                id="ORD-102",
                customerPhone="9845012345",
                customerName="Anand Rao",
                deliveryAddress="Flat 204, Green Palms, Camp, Belagavi - 590001",
                items=[
                    OrderItem(
                        productId="prod_102",
                        name="Sona Masoori Rice (Akki)",
                        unit="5 kg",
                        quantity=1,
                        priceAtOrder=310
                    ),
                    OrderItem(
                        productId="prod_106",
                        name="Fresh Garlic (Bellulli)",
                        unit="250 g",
                        quantity=1,
                        priceAtOrder=80
                    )
                ],
                subtotal=390,
                deliveryFee=30,
                totalAmount=420,
                paymentMethod="COD",
                status="PACKED",
                deliveryPartner="Raju Rider",
                createdAt="2026-11-25T13:30:00Z"
            ),
            "ORD-103": Order(
                id="ORD-103",
                customerPhone="9448123456",
                customerName="Geetha Kulkarni",
                deliveryAddress="No. 15, 2nd Main, RPD Cross, Belagavi - 590006",
                items=[
                    OrderItem(
                        productId="prod_109",
                        name="Filter Coffee Powder (80:20 Blend)",
                        unit="250 g",
                        quantity=2,
                        priceAtOrder=150
                    ),
                    OrderItem(
                        productId="prod_104",
                        name="Byadgi Chilli Powder (Menasinakayi)",
                        unit="500 g",
                        quantity=1,
                        priceAtOrder=165
                    )
                ],
                subtotal=465,
                deliveryFee=30,
                totalAmount=495,
                paymentMethod="UPI",
                status="OUT_FOR_DELIVERY",
                deliveryPartner="Basavaraj Express",
                createdAt="2026-11-25T12:00:00Z"
            ),
            "ORD-104": Order(
                id="ORD-104",
                customerPhone="9900554433",
                customerName="Prakash Hiremath",
                deliveryAddress="Plot 12, Hindwadi, Belagavi - 590001",
                items=[
                    OrderItem(
                        productId="prod_103",
                        name="Mysore Sandal Soap",
                        unit="3 x 150 g",
                        quantity=1,
                        priceAtOrder=195
                    )
                ],
                subtotal=195,
                deliveryFee=30,
                totalAmount=225,
                paymentMethod="UPI",
                status="DELIVERED",
                deliveryPartner="Self-Delivery",
                createdAt="2026-11-25T11:15:00Z"
            )
        }

        self.next_prod_id = 111
        self.next_order_id = 105

    # Shop Config
    def get_shop_config(self) -> ShopConfig:
        return self.shop_config

    def update_shop_config(self, updates: Dict[str, Any]) -> ShopConfig:
        for k, v in updates.items():
            if hasattr(self.shop_config, k):
                setattr(self.shop_config, k, v)
        return self.shop_config

    # Products
    def get_products(self, search: Optional[str] = None, sort: Optional[str] = None, discounted_only: bool = False) -> List[Product]:
        items = list(self.products.values())
        if search:
            s = search.lower().strip()
            items = [p for p in items if s in p.name.lower() or s in p.category.lower() or s in p.unit.lower()]
        
        if discounted_only:
            items = [p for p in items if p.discountPercent > 0]

        if sort == "price_asc":
            items.sort(key=lambda p: p.discountPrice)
        elif sort == "price_desc":
            items.sort(key=lambda p: p.discountPrice, reverse=True)
        elif sort == "discount_desc":
            items.sort(key=lambda p: p.discountPercent, reverse=True)
        elif sort == "stock":
            items.sort(key=lambda p: (not p.inStock, p.stockCount))

        return items

    def get_product(self, prod_id: str) -> Optional[Product]:
        return self.products.get(prod_id)

    def find_product_by_name(self, name_query: str) -> Optional[Product]:
        """Finds product using direct, partial, or alias matching."""
        q = name_query.lower().strip()
        # Direct contains
        for p in self.products.values():
            if q in p.name.lower() or p.name.lower() in q:
                return p
        
        # Canonical Kannada/Kanglish alias map
        alias_map = {
            "akki": "prod_102",
            "rice": "prod_102",
            "sona masoori": "prod_102",
            "ghee": "prod_101",
            "tuppa": "prod_101",
            "nandini": "prod_101",
            "soap": "prod_103",
            "sabun": "prod_103",
            "sandal": "prod_103",
            "mysore sandal": "prod_103",
            "menasinakayi": "prod_104",
            "chilli": "prod_104",
            "byadgi": "prod_104",
            "mirchi": "prod_104",
            "bella": "prod_105",
            "jaggery": "prod_105",
            "bellam": "prod_105",
            "bellulli": "prod_106",
            "garlic": "prod_106",
            "lahsun": "prod_106",
            "tomato": "prod_107",
            "tamota": "prod_107",
            "mysore pak": "prod_108",
            "pak": "prod_108",
            "sweet": "prod_108",
            "coffee": "prod_109",
            "kapi": "prod_109",
            "atta": "prod_110",
            "godhi": "prod_110",
            "flour": "prod_110"
        }
        for word in q.split():
            if word in alias_map and alias_map[word] in self.products:
                return self.products[alias_map[word]]

        return None

    def create_product(self, data: Dict[str, Any]) -> Product:
        pid = f"prod_{self.next_prod_id}"
        self.next_prod_id += 1
        data["id"] = pid
        if "category" not in data or not data["category"]:
            data["category"] = "General"
        if "discountPrice" not in data or data["discountPrice"] is None:
            data["discountPrice"] = data.get("originalPrice", 0)
        prod = Product(**data)
        self.products[pid] = prod
        return prod

    def update_product(self, prod_id: str, updates: Dict[str, Any]) -> Optional[Product]:
        prod = self.products.get(prod_id)
        if not prod:
            return None
        d = prod.model_dump()
        for k, v in updates.items():
            if v is not None:
                d[k] = v
        d["updatedAt"] = datetime.now(timezone.utc).isoformat()
        updated_prod = Product(**d)
        self.products[prod_id] = updated_prod
        return updated_prod

    def delete_product(self, prod_id: str) -> bool:
        if prod_id in self.products:
            del self.products[prod_id]
            return True
        return False

    # Orders
    def get_orders(self) -> List[Order]:
        orders = list(self.orders.values())
        orders.sort(key=lambda o: o.createdAt, reverse=True)
        return orders

    def get_order(self, order_id: str) -> Optional[Order]:
        # Support both 'ORD-101' and '101'
        if order_id in self.orders:
            return self.orders[order_id]
        alt = f"ORD-{order_id.replace('ORD-', '')}"
        return self.orders.get(alt)

    def create_order(self, customer_phone: str, customer_name: str, delivery_address: str, items: List[OrderItem], payment_method: str = "UPI") -> Order:
        oid = f"ORD-{self.next_order_id}"
        self.next_order_id += 1

        subtotal = sum(item.priceAtOrder * item.quantity for item in items)
        delivery_fee = 0 if subtotal >= self.shop_config.freeDeliveryAbove else self.shop_config.deliveryFee
        total_amount = subtotal + delivery_fee

        # Deduct stock
        for it in items:
            p = self.products.get(it.productId)
            if p:
                new_stock = max(0, p.stockCount - it.quantity)
                self.update_product(p.id, {"stockCount": new_stock, "inStock": new_stock > 0})

        order = Order(
            id=oid,
            customerPhone=customer_phone,
            customerName=customer_name,
            deliveryAddress=delivery_address,
            items=items,
            subtotal=subtotal,
            deliveryFee=delivery_fee,
            totalAmount=total_amount,
            paymentMethod=payment_method,
            status="NEW",
            deliveryPartner="Self-Delivery",
            createdAt=datetime.now(timezone.utc).isoformat()
        )
        self.orders[oid] = order
        return order

    def update_order_status(self, order_id: str, status: str, delivery_partner: Optional[str] = None) -> Optional[Order]:
        order = self.get_order(order_id)
        if not order:
            return None
        d = order.model_dump()
        d["status"] = status
        if delivery_partner:
            d["deliveryPartner"] = delivery_partner
        updated = Order(**d)
        self.orders[order.id] = updated
        return updated

    # Reports
    def get_sales_report(self) -> Dict[str, Any]:
        total_revenue = sum(o.totalAmount for o in self.orders.values() if o.status != "CANCELLED")
        total_orders = len([o for o in self.orders.values() if o.status != "CANCELLED"])
        upi_revenue = sum(o.totalAmount for o in self.orders.values() if o.paymentMethod == "UPI" and o.status != "CANCELLED")
        cod_revenue = sum(o.totalAmount for o in self.orders.values() if o.paymentMethod == "COD" and o.status != "CANCELLED")
        low_stock_count = len([p for p in self.products.values() if p.stockCount <= p.lowStockThreshold])

        # Aggregate product sales
        sold_stats: Dict[str, Dict[str, Any]] = {}
        for o in self.orders.values():
            if o.status == "CANCELLED":
                continue
            for it in o.items:
                if it.name not in sold_stats:
                    sold_stats[it.name] = {"name": it.name, "unitsSold": 0, "revenue": 0}
                sold_stats[it.name]["unitsSold"] += it.quantity
                sold_stats[it.name]["revenue"] += it.priceAtOrder * it.quantity

        top_selling = sorted(sold_stats.values(), key=lambda s: s["unitsSold"], reverse=True)[:5]

        return {
            "totalRevenue": round(total_revenue, 2),
            "totalOrders": total_orders,
            "upiRevenue": round(upi_revenue, 2),
            "codRevenue": round(cod_revenue, 2),
            "lowStockCount": low_stock_count,
            "topSellingProducts": top_selling
        }

db = Database()
