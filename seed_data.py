from sqlalchemy.orm import Session

from app.models import PricingRegion, User, Product, UserRole

REGIONS = [
    dict(
        key="kutch",
        display_name="Kutch, Gujarat (Rural Craft Hub)",
        demand_multiplier=1.42,
        demand_label="Export Demand: High",
        logistics_factor=1.0,
        gi_premium=1.15,
        notes="Raw Silk: Base",
    ),
    dict(
        key="varanasi",
        display_name="Varanasi, UP (Heritage Cluster)",
        demand_multiplier=1.65,
        demand_label="High Institutional Inflow",
        logistics_factor=1.0,
        gi_premium=1.15,
        notes="Raw Zari: Medium",
    ),
    dict(
        key="imphal",
        display_name="Imphal, Manipur (Northeast Handloom)",
        demand_multiplier=1.30,
        demand_label="Rare GI Value",
        logistics_factor=1.0,
        gi_premium=1.15,
        notes="Organic Pigments",
    ),
]


def seed_regions(db: Session):
    for r in REGIONS:
        existing = db.query(PricingRegion).filter(PricingRegion.key == r["key"]).first()
        if not existing:
            db.add(PricingRegion(**r))
    db.commit()


def seed_demo_artisan_and_listings(db: Session):
    """
    Seeds the same demo artisan (Sumitra Devi) and three listings shown in the
    frontend's Profile and Listings views, so the UI has real backend data to
    render on first run instead of only its hardcoded mockup.
    """
    demo_phone = "9876543210"
    user = db.query(User).filter(User.phone == demo_phone).first()
    if not user:
        user = User(
            phone=demo_phone,
            name="Sumitra Devi",
            role=UserRole.MASTER_ARTISAN,
            region="Kutch, Gujarat",
            craft_category="Embroidered Textiles",
            gi_tag_number="GJ-4820",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    if db.query(Product).filter(Product.owner_id == user.id).count() == 0:
        demo_products = [
            dict(
                title="Kutchi Embroidered Silk Shawl",
                description="GI-Certified needlework on tussar silk.",
                craft_category="Embroidered Textile",
                material_labor_cost=820,
                price=1850, price_low=1750, price_high=1950,
                region="Kutch, Gujarat",
                gem_active=True, ondc_active=False, institutional_active=False,
            ),
            dict(
                title="Terracotta Clay Vessel",
                description="Hand-thrown red river clay with burnished glaze.",
                craft_category="Pottery",
                material_labor_cost=350,
                price=680, price_low=620, price_high=740,
                region="Kutch, Gujarat",
                gem_active=False, ondc_active=True, institutional_active=False,
            ),
            dict(
                title="Saharanpur Teak Wood Box",
                description="Hand-carved floral relief with brass filigree inlay.",
                craft_category="Wood Carving",
                material_labor_cost=1150,
                price=2450, price_low=2400, price_high=2800,
                region="Varanasi, UP",
                gem_active=False, ondc_active=False, institutional_active=True,
            ),
        ]
        for p in demo_products:
            db.add(Product(owner_id=user.id, **p))
        db.commit()


def run_all_seeds(db: Session):
    seed_regions(db)
    seed_demo_artisan_and_listings(db)
