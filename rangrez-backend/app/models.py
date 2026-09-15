import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Enum, Boolean, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class UserRole(str, enum.Enum):
    MASTER_ARTISAN = "Master Artisan"
    B2B_BUYER = "B2B Buyer"
    GEM_OFFICER = "GeM Officer"


class SyncChannel(str, enum.Enum):
    GEM = "GeM"
    ONDC = "ONDC"
    INSTITUTIONAL = "Institutional"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_id)
    phone = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, default="")
    role = Column(Enum(UserRole), default=UserRole.MASTER_ARTISAN)
    region = Column(String, default="Kutch, Gujarat")
    craft_category = Column(String, default="")
    gi_tag_number = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="owner", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="buyer", cascade="all, delete-orphan")


class OTP(Base):
    __tablename__ = "otps"

    id = Column(String, primary_key=True, default=gen_id)
    phone = Column(String, index=True, nullable=False)
    code = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    consumed = Column(Boolean, default=False)


class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_id)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    title_translated = Column(String, default="")
    description = Column(Text, default="")
    description_translated = Column(Text, default="")
    source_language = Column(String, default="hi")

    craft_category = Column(String, default="")
    material_labor_cost = Column(Float, default=0.0)
    price = Column(Float, default=0.0)
    price_low = Column(Float, default=0.0)
    price_high = Column(Float, default=0.0)

    region = Column(String, default="Kutch, Gujarat")
    raw_image_path = Column(String, default="")
    enhanced_image_path = Column(String, default="")

    gem_active = Column(Boolean, default=False)
    ondc_active = Column(Boolean, default=False)
    institutional_active = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="products")
    orders = relationship("Order", back_populates="product", cascade="all, delete-orphan")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, default=gen_id)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    buyer_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel = Column(Enum(SyncChannel), default=SyncChannel.GEM)
    quantity = Column(Integer, default=1)
    total_amount = Column(Float, default=0.0)
    middlemen_deduction = Column(Float, default=0.0)  # always 0 on Rangrez, kept explicit for the dashboard stat
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("Product", back_populates="orders")
    buyer = relationship("User", back_populates="orders")


class PricingRegion(Base):
    """
    Seeded regional pricing clusters, matching the three demo clusters in the
    frontend's Dynamic Pricing view (Kutch, Varanasi, Imphal) plus room to add more.
    """
    __tablename__ = "pricing_regions"

    id = Column(String, primary_key=True, default=gen_id)
    key = Column(String, unique=True, nullable=False)  # e.g. "kutch"
    display_name = Column(String, nullable=False)
    demand_multiplier = Column(Float, nullable=False)
    demand_label = Column(String, default="")
    logistics_factor = Column(Float, default=1.0)
    gi_premium = Column(Float, default=1.0)
    notes = Column(String, default="")
