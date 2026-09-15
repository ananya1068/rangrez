"""
Location-driven dynamic pricing engine — the core USP of Rangrez.

Formula (documented so it's easy to defend in front of judges):

    base_price = material_labor_cost
                 x regional_demand_multiplier   (varies by artisan cluster: export
                                                  pull, institutional buying, etc.)
                 x gi_premium                    (1.15x if the craft carries a GI tag)
                 x export_readiness_bonus        (1.08x if the listing is export-ready,
                                                  i.e. has passed the AI Image Studio)

    price_low  = base_price x 0.94
    price_high = base_price x 1.12

    middlemen_cut_recovered = base_price x 0.29
        (the average commission a haat/mela middleman would have taken — shown to the
        artisan as money now landing directly in their account instead)

Regional multipliers are stored in the `pricing_regions` table (see seed_data.py) so
they can be tuned per-cluster without touching code — a judge or teammate can add a
new artisan cluster by inserting one row.
"""

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.models import PricingRegion

GI_PREMIUM = 1.15
EXPORT_READY_BONUS = 1.08
MIDDLEMEN_CUT_RATIO = 0.29
PRICE_BAND_LOW_RATIO = 0.94
PRICE_BAND_HIGH_RATIO = 1.12


@dataclass
class PriceResult:
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


class RegionNotFoundError(Exception):
    pass


def get_region(db: Session, region_key: str) -> PricingRegion:
    region = db.query(PricingRegion).filter(PricingRegion.key == region_key).first()
    if not region:
        raise RegionNotFoundError(f"Unknown pricing region '{region_key}'")
    return region


def calculate_price(
    db: Session,
    region_key: str,
    material_labor_cost: float,
    has_gi_tag: bool = False,
    export_ready: bool = False,
) -> PriceResult:
    region = get_region(db, region_key)

    gi_factor = GI_PREMIUM if has_gi_tag else 1.0
    export_factor = EXPORT_READY_BONUS if export_ready else 1.0

    base_price = (
        material_labor_cost
        * region.demand_multiplier
        * region.logistics_factor
        * gi_factor
        * export_factor
    )

    price_low = round(base_price * PRICE_BAND_LOW_RATIO, -1)  # round to nearest 10
    price_high = round(base_price * PRICE_BAND_HIGH_RATIO, -1)
    middlemen_cut = round(base_price * MIDDLEMEN_CUT_RATIO, -1)

    return PriceResult(
        region_key=region.key,
        region_display_name=region.display_name,
        material_labor_cost=material_labor_cost,
        demand_multiplier=region.demand_multiplier,
        demand_label=region.demand_label,
        base_price=round(base_price, 2),
        price_low=price_low,
        price_high=price_high,
        middlemen_cut_recovered=middlemen_cut,
        breakdown={
            "material_labor_cost": material_labor_cost,
            "regional_demand_multiplier": region.demand_multiplier,
            "logistics_factor": region.logistics_factor,
            "gi_premium_applied": gi_factor,
            "export_readiness_bonus_applied": export_factor,
        },
    )
