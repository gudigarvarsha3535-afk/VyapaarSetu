from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone

class ShopConfig(BaseModel):
    shopSlug: str = "ramesh-kirana"
    shopName: str = "Ramesh Kirana & General Stores"
    ownerPhone: str = "9876543210"
    deliveryEnabled: bool = True
    deliveryFee: int = 30
    freeDeliveryAbove: int = 500
    serviceablePincodes: List[str] = ["590001", "590006", "590010"]

class Product(BaseModel):
    id: str
    name: str
    category: str
    unit: str
    originalPrice: float
    discountPrice: float
    discountPercent: int = 0
    inStock: bool = True
    stockCount: int = 10
    lowStockThreshold: int = 5
    imageUrl: Optional[str] = None
    updatedAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def calculate_discount_percent(cls, values):
        if isinstance(values, dict):
            orig = values.get("originalPrice", 0)
            disc = values.get("discountPrice", orig)
            if orig and orig > 0:
                if disc < orig:
                    values["discountPercent"] = round(((orig - disc) / orig) * 100)
                else:
                    values["discountPercent"] = 0
            else:
                values["discountPercent"] = 0
            if "updatedAt" not in values or not values["updatedAt"]:
                values["updatedAt"] = datetime.now(timezone.utc).isoformat()
        return values

class ProductCreate(BaseModel):
    name: str
    category: str = "General"
    unit: str = "1 unit"
    originalPrice: float
    discountPrice: Optional[float] = None
    inStock: bool = True
    stockCount: int = 10
    lowStockThreshold: int = 5
    imageUrl: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    originalPrice: Optional[float] = None
    discountPrice: Optional[float] = None
    inStock: Optional[bool] = None
    stockCount: Optional[int] = None
    lowStockThreshold: Optional[int] = None
    imageUrl: Optional[str] = None

class OrderItem(BaseModel):
    productId: str
    name: str
    unit: str
    quantity: int
    priceAtOrder: float

class Order(BaseModel):
    id: str
    customerPhone: str
    customerName: str
    deliveryAddress: str
    items: List[OrderItem]
    subtotal: float
    deliveryFee: float
    totalAmount: float
    paymentMethod: Literal["UPI", "COD"]
    status: Literal["NEW", "PACKED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"] = "NEW"
    deliveryPartner: str = "Self-Delivery"
    createdAt: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class OrderCreateRequest(BaseModel):
    customerPhone: str
    customerName: str
    deliveryAddress: str
    items: List[OrderItem]
    paymentMethod: Literal["UPI", "COD"] = "UPI"

class OrderStatusUpdate(BaseModel):
    status: Literal["NEW", "PACKED", "OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"]
    deliveryPartner: Optional[str] = None

class CustomerSendOtpRequest(BaseModel):
    phone: str

class CustomerVerifyOtpRequest(BaseModel):
    phone: str
    otp: str

class SellerLoginRequest(BaseModel):
    phone: str
    password: str

class BotMessageRequest(BaseModel):
    inputType: Literal["voice", "text", "image"] = "text"
    text: Optional[str] = None
    audioBase64: Optional[str] = None
    imageBase64: Optional[str] = None
    imageUrl: Optional[str] = None  # VyaparSetu: public URL of a photo already uploaded to product storage
    activeTab: Optional[str] = "HOME"

class BotExecuteRequest(BaseModel):
    intent: str
    payload: Dict[str, Any] = {}
    replyKn: str

class BotResponse(BaseModel):
    success: bool
    intent: str
    replyKn: str
    updatedEntity: Optional[Any] = None
    refreshRequired: bool = False
    transcribedText: Optional[str] = None
