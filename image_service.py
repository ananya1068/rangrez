"""
AI Image Studio backend: takes a raw workshop photo and produces an
e-commerce-ready shot — auto white balance, contrast/brightness correction,
sharpening, and a clean padded frame on a neutral backdrop (matching the
"Before -> After" card on the landing page and the Camera Studio view).

This uses Pillow only (no heavyweight ML background-removal model) so it runs
anywhere without a GPU or extra downloads — appropriate for a hackathon demo.
Swap in a proper matting model (e.g. rembg) later without changing the API shape.
"""

import os
import uuid

from PIL import Image, ImageEnhance, ImageOps, ImageFilter

from app.config import settings

CANVAS_SIZE = (1000, 1000)
CANVAS_BG = (245, 241, 233)  # matches the frontend's --cream-card family


def _autowhitebalance(img: Image.Image) -> Image.Image:
    # Stretch each channel's histogram independently — a cheap, effective auto-WB.
    r, g, b = img.convert("RGB").split()
    r = ImageOps.autocontrast(r, cutoff=1)
    g = ImageOps.autocontrast(g, cutoff=1)
    b = ImageOps.autocontrast(b, cutoff=1)
    return Image.merge("RGB", (r, g, b))


def enhance_product_photo(input_path: str) -> str:
    """Reads the raw photo at input_path, enhances it, saves to a new file, returns its path."""
    img = Image.open(input_path)
    img = ImageOps.exif_transpose(img)  # fix phone-camera rotation
    img = img.convert("RGB")

    img = _autowhitebalance(img)
    img = ImageEnhance.Brightness(img).enhance(1.08)
    img = ImageEnhance.Contrast(img).enhance(1.12)
    img = ImageEnhance.Color(img).enhance(1.15)
    img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=110, threshold=3))

    # Compose onto a clean square studio backdrop, centered, so every listing photo
    # has consistent e-commerce framing regardless of the artisan's original photo shape.
    canvas = Image.new("RGB", CANVAS_SIZE, CANVAS_BG)
    img.thumbnail((CANVAS_SIZE[0] - 120, CANVAS_SIZE[1] - 120), Image.LANCZOS)
    offset = ((CANVAS_SIZE[0] - img.width) // 2, (CANVAS_SIZE[1] - img.height) // 2)
    canvas.paste(img, offset)

    out_name = f"enhanced_{uuid.uuid4().hex[:10]}.jpg"
    out_path = os.path.join(settings.UPLOAD_DIR, out_name)
    canvas.save(out_path, "JPEG", quality=92)
    return out_path


def save_upload(file_bytes: bytes, original_filename: str) -> str:
    ext = os.path.splitext(original_filename)[1].lower() or ".jpg"
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        ext = ".jpg"
    name = f"raw_{uuid.uuid4().hex[:10]}{ext}"
    path = os.path.join(settings.UPLOAD_DIR, name)
    with open(path, "wb") as f:
        f.write(file_bytes)
    return path
