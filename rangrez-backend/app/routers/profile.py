from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from app.auth import get_current_user
from app.database import get_db
from app.models import User, Product, Order
from app.schemas import DashboardOut

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    monthly_payouts = (
        db.query(func.coalesce(func.sum(Order.total_amount), 0.0))
        .join(Product, Order.product_id == Product.id)
        .filter(Product.owner_id == current_user.id, Order.created_at >= thirty_days_ago)
        .scalar()
    )

    order_count = (
        db.query(func.count(Order.id))
        .join(Product, Order.product_id == Product.id)
        .filter(Product.owner_id == current_user.id)
        .scalar()
    )

    active_listings = (
        db.query(func.count(Product.id))
        .filter(
            Product.owner_id == current_user.id,
            (Product.gem_active == True) | (Product.ondc_active == True) | (Product.institutional_active == True),  # noqa: E712
        )
        .scalar()
    )

    return DashboardOut(
        monthly_payouts=float(monthly_payouts or 0),
        order_count=int(order_count or 0),
        middlemen_deduction_pct=0.0,
        active_listings=int(active_listings or 0),
    )
