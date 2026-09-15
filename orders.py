from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Product, Order, SyncChannel
from app.schemas import OrderOut
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/orders", tags=["orders"])


class OrderCreateIn(BaseModel):
    product_id: str
    channel: str = "GeM"
    quantity: int = Field(1, ge=1)


@router.post("", response_model=OrderOut)
def place_order(
    payload: OrderCreateIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.query(Product).filter(Product.id == payload.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Listing not found.")

    try:
        channel = SyncChannel(payload.channel)
    except ValueError:
        raise HTTPException(status_code=400, detail="channel must be one of: GeM, ONDC, Institutional")

    order = Order(
        product_id=product.id,
        buyer_id=current_user.id,
        channel=channel,
        quantity=payload.quantity,
        total_amount=round(product.price * payload.quantity, 2),
        middlemen_deduction=0.0,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def my_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Order).filter(Order.buyer_id == current_user.id).order_by(Order.created_at.desc()).all()
