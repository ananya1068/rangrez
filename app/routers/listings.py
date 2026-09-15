from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Product
from app.schemas import ProductOut, ProductCreateIn, ProductUpdateIn, SyncChannelIn
from app.services.pricing_engine import calculate_price, RegionNotFoundError

router = APIRouter(prefix="/api/listings", tags=["listings"])


def _region_to_key(region_display: str) -> str:
    region_display = (region_display or "").lower()
    if "kutch" in region_display:
        return "kutch"
    if "varanasi" in region_display:
        return "varanasi"
    if "imphal" in region_display or "manipur" in region_display:
        return "imphal"
    return "kutch"


@router.get("", response_model=List[ProductOut])
def list_my_listings(
    all_active_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Product).filter(Product.owner_id == current_user.id)
    listings = q.order_by(Product.created_at.desc()).all()
    if all_active_only:
        listings = [p for p in listings if p.gem_active or p.ondc_active or p.institutional_active]
    return listings


@router.get("/marketplace", response_model=List[ProductOut])
def marketplace_feed(db: Session = Depends(get_db)):
    """Public feed of everything synced to at least one channel — what a B2B buyer or GeM officer would browse."""
    return (
        db.query(Product)
        .filter((Product.gem_active == True) | (Product.ondc_active == True) | (Product.institutional_active == True))  # noqa: E712
        .order_by(Product.created_at.desc())
        .all()
    )


@router.post("", response_model=ProductOut)
def create_listing(
    payload: ProductCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = Product(
        owner_id=current_user.id,
        title=payload.title,
        description=payload.description,
        craft_category=payload.craft_category,
        material_labor_cost=payload.material_labor_cost,
        source_language=payload.source_language,
        region=current_user.region,
    )

    if payload.auto_price and payload.material_labor_cost > 0:
        region_key = payload.region_key or _region_to_key(current_user.region)
        try:
            price = calculate_price(
                db,
                region_key=region_key,
                material_labor_cost=payload.material_labor_cost,
                has_gi_tag=payload.has_gi_tag,
                export_ready=payload.export_ready,
            )
            product.price = (price.price_low + price.price_high) / 2
            product.price_low = price.price_low
            product.price_high = price.price_high
        except RegionNotFoundError:
            pass

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{listing_id}", response_model=ProductOut)
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == listing_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return product


@router.patch("/{listing_id}", response_model=ProductOut)
def update_listing(
    listing_id: str,
    payload: ProductUpdateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == listing_id, Product.owner_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{listing_id}")
def delete_listing(
    listing_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(Product.id == listing_id, Product.owner_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found.")
    db.delete(product)
    db.commit()
    return {"deleted": True}


@router.post("/{listing_id}/sync", response_model=ProductOut)
def toggle_sync_channel(
    listing_id: str,
    payload: SyncChannelIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Flip a listing's GeM / ONDC / Institutional sync status. In production this
    would call the actual GeM/ONDC seller APIs; here it models the state transition
    so the rest of the app (badges in the frontend) has something real to reflect."""
    product = (
        db.query(Product)
        .filter(Product.id == listing_id, Product.owner_id == current_user.id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found.")

    channel = payload.channel.strip().lower()
    if channel == "gem":
        product.gem_active = payload.active
    elif channel == "ondc":
        product.ondc_active = payload.active
    elif channel == "institutional":
        product.institutional_active = payload.active
    else:
        raise HTTPException(status_code=400, detail="channel must be one of: GeM, ONDC, Institutional")

    db.commit()
    db.refresh(product)
    return product
