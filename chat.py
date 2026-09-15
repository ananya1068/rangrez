import re

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    ChatMessageIn, ChatMessageOut, CatalogGenerateIn, CatalogGenerateOut, PriceCalculateOut,
)
from app.services import ai_service
from app.services.pricing_engine import calculate_price, RegionNotFoundError

router = APIRouter(prefix="/api/chat", tags=["chat"])

_NUMBER_RE = re.compile(r"(\d[\d,]*)")


@router.post("/message", response_model=ChatMessageOut)
def send_message(
    payload: ChatMessageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = ai_service.chat_reply(payload.message, payload.language_hint)

    suggested_price = None
    if result.get("detected_intent") == "pricing_question":
        # Best-effort: if the artisan mentioned a rupee figure, treat it as their
        # material/labor cost and price it against their profile's region.
        match = _NUMBER_RE.search(payload.message)
        if match:
            cost = float(match.group(1).replace(",", ""))
            region_key = _region_to_key(current_user.region)
            try:
                price = calculate_price(db, region_key=region_key, material_labor_cost=cost)
                suggested_price = PriceCalculateOut(**price.__dict__)
            except RegionNotFoundError:
                pass

    return ChatMessageOut(
        reply=result.get("reply", ""),
        reply_language=result.get("reply_language", "en"),
        detected_intent=result.get("detected_intent", "general"),
        suggested_price=suggested_price,
    )


@router.post("/generate-catalog", response_model=CatalogGenerateOut)
def generate_catalog(
    payload: CatalogGenerateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    listing = ai_service.generate_catalog_listing(payload.spoken_description, payload.language_hint)

    suggested_price = None
    if payload.material_labor_cost:
        region_key = payload.region_key or _region_to_key(current_user.region)
        try:
            price = calculate_price(
                db,
                region_key=region_key,
                material_labor_cost=payload.material_labor_cost,
                has_gi_tag=payload.has_gi_tag,
            )
            suggested_price = PriceCalculateOut(**price.__dict__)
        except RegionNotFoundError:
            pass

    return CatalogGenerateOut(
        title=listing.get("title_en", ""),
        title_translated=listing.get("title_native", ""),
        description=listing.get("description_en", ""),
        description_translated=listing.get("description_native", ""),
        detected_language=listing.get("detected_language", "hi"),
        craft_category=listing.get("craft_category", "General handicraft"),
        tags=listing.get("tags", []),
        suggested_price=suggested_price,
    )


def _region_to_key(region_display: str) -> str:
    region_display = (region_display or "").lower()
    if "kutch" in region_display:
        return "kutch"
    if "varanasi" in region_display:
        return "varanasi"
    if "imphal" in region_display or "manipur" in region_display:
        return "imphal"
    return "kutch"
