import os

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import User, Product
from app.services.image_service import save_upload, enhance_product_photo

router = APIRouter(prefix="/api/camera", tags=["camera"])

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/enhance")
async def enhance_photo(
    file: UploadFile = File(...),
    product_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Please upload a JPG, PNG, or WEBP photo.")

    raw_bytes = await file.read()
    raw_path = save_upload(raw_bytes, file.filename)
    enhanced_path = enhance_product_photo(raw_path)

    if product_id:
        product = (
            db.query(Product)
            .filter(Product.id == product_id, Product.owner_id == current_user.id)
            .first()
        )
        if not product:
            raise HTTPException(status_code=404, detail="Listing not found.")
        product.raw_image_path = os.path.basename(raw_path)
        product.enhanced_image_path = os.path.basename(enhanced_path)
        db.commit()

    return {
        "raw_image_url": f"/api/camera/file/{os.path.basename(raw_path)}",
        "enhanced_image_url": f"/api/camera/file/{os.path.basename(enhanced_path)}",
    }


@router.get("/file/{filename}")
def get_file(filename: str):
    path = os.path.join(settings.UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(path)
