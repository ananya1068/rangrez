from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import PricingRegion, User
from app.schemas import PricingRegionOut, PriceCalculateIn, PriceCalculateOut
from app.services.pricing_engine import calculate_price, RegionNotFoundError

router = APIRouter(prefix="/api/pricing", tags=["pricing"])


@router.get("/regions", response_model=List[PricingRegionOut])
def list_regions(db: Session = Depends(get_db)):
    return db.query(PricingRegion).all()


@router.post("/calculate", response_model=PriceCalculateOut)
def calculate(payload: PriceCalculateIn, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        result = calculate_price(
            db,
            region_key=payload.region_key,
            material_labor_cost=payload.material_labor_cost,
            has_gi_tag=payload.has_gi_tag,
            export_ready=payload.export_ready,
        )
    except RegionNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PriceCalculateOut(**result.__dict__)
