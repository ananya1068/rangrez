from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.models import UserRole


# ---------- Auth ----------

class RequestOTPIn(BaseModel):
    phone: str = Field(..., min_length=6, max_length=15)


class RequestOTPOut(BaseModel):
    phone: str
    otp_sent: bool
    # Only populated because there's no real SMS gateway wired up for the demo.
    demo_otp: Optional[str] = None
    expires_in_seconds: int = 300


class VerifyOTPIn(BaseModel):
    phone: str
    otp: str
    role: UserRole = UserRole.MASTER_ARTISAN
    name: Optional[str] = None
    region: Optional[str] = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    phone: str
    name: str
    role: UserRole
    region: str
    craft_category: str
    gi_tag_number: str

    class Config:
        from_attributes = True


TokenOut.model_rebuild()


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    region: Optional[str] = None
    craft_category: Optional[str] = None
    gi_tag_number: Optional[str] = None


# ---------- Pricing ----------

class PricingRegionOut(BaseModel):
    key: str
    display_name: str
    demand_multiplier: float
    demand_label: str
    logistics_factor: float
    gi_premium: float
    notes: str

    class Config:
        from_attributes = True


class PriceCalculateIn(BaseModel):
    region_key: str
    material_labor_cost: float = Field(..., gt=0)
    craft_category: Optional[str] = "General handicraft"
    has_gi_tag: bool = False
    export_ready: bool = False


class PriceCalculateOut(BaseModel):
    region_key: str
    region_display_name: str
    material_labor_cost: float
    demand_multiplier: float
    demand_label: str
    base_price: float
    price_low: float
    price_high: float
    middlemen_cut_recovered: float
    breakdown: dict


# ---------- Products / Listings ----------

class ProductOut(BaseModel):
    id: str
    title: str
    title_translated: str
    description: str
    description_translated: str
    craft_category: str
    price: float
    price_low: float
    price_high: float
    region: str
    raw_image_path: Optional[str] = None
    enhanced_image_path: Optional[str] = None
    gem_active: bool
    ondc_active: bool
    institutional_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreateIn(BaseModel):
    title: str
    description: str = ""
    craft_category: str = "General handicraft"
    material_labor_cost: float = 0.0
    region_key: Optional[str] = None
    source_language: str = "hi"
    auto_price: bool = True
    has_gi_tag: bool = False
    export_ready: bool = False


class ProductUpdateIn(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    price_low: Optional[float] = None
    price_high: Optional[float] = None


class SyncChannelIn(BaseModel):
    channel: str  # "GeM" | "ONDC" | "Institutional"
    active: bool


# ---------- Chat / AI cataloger ----------

class ChatMessageIn(BaseModel):
    message: str
    language_hint: Optional[str] = None  # e.g. "hi", "en" - if omitted, model detects it


class ChatMessageOut(BaseModel):
    reply: str
    reply_language: str
    detected_intent: str  # "pricing_question" | "catalog_request" | "general"
    suggested_price: Optional[PriceCalculateOut] = None


class CatalogGenerateIn(BaseModel):
    spoken_description: str
    language_hint: Optional[str] = None
    region_key: Optional[str] = None
    material_labor_cost: Optional[float] = None
    has_gi_tag: bool = False


class CatalogGenerateOut(BaseModel):
    title: str
    title_translated: str
    description: str
    description_translated: str
    detected_language: str
    craft_category: str
    tags: List[str]
    suggested_price: Optional[PriceCalculateOut] = None


# ---------- Orders / Dashboard ----------

class OrderOut(BaseModel):
    id: str
    product_id: str
    channel: str
    quantity: int
    total_amount: float
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardOut(BaseModel):
    monthly_payouts: float
    order_count: int
    middlemen_deduction_pct: float
    active_listings: int
