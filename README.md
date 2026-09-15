# Rangrez Backend

FastAPI backend for **Rangrez** (SIH 2026 — AI-Driven Market Linkage & Smart
Cataloging for Marginalized Artisans), built to power every screen in the
`app-portal-section` of the provided frontend: Login, AI Chat, Listings, Camera
Studio, Profile, and Dynamic Pricing.

## Quick start

```bash
cd rangrez-backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# then open .env and paste your Anthropic API key in ANTHROPIC_API_KEY

uvicorn app.main:app --reload --port 8000
```

The API is now at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`. A demo artisan ("Sumitra Devi", phone
`9876543210`, matching the frontend's Profile view) and her three demo listings
are seeded automatically on first startup, along with the three pricing regions
(Kutch, Varanasi, Imphal) shown in the Dynamic Pricing view.

**Without an `ANTHROPIC_API_KEY`**, the chat and auto-cataloger endpoints still
work — they fall back to a simple rule-based responder so you can develop and
demo the rest of the app before wiring up the key.

## Wiring it into the frontend

The frontend currently has no backend calls at all (`handleAuthLogin`,
`sendPortalMessage`, `handlePortalPhotoUpload`, `updatePortalPrice` are all
client-side mocks). Point them at these endpoints:

| Frontend action | Endpoint |
|---|---|
| `handleAuthLogin` (OTP submit) | `POST /api/auth/request-otp` then `POST /api/auth/verify-otp` |
| Portal load / profile card | `GET /api/auth/me`, `GET /api/profile/dashboard` |
| `sendPortalMessage` (AI Chat) | `POST /api/chat/message` |
| Voice description → listing | `POST /api/chat/generate-catalog` |
| `handlePortalPhotoUpload` (Camera Studio) | `POST /api/camera/enhance` (multipart file upload) |
| Listings view | `GET /api/listings`, `POST /api/listings`, `PATCH/DELETE /api/listings/{id}` |
| GeM / ONDC / Institutional badges | `POST /api/listings/{id}/sync` |
| `updatePortalPrice` (Dynamic Pricing) | `GET /api/pricing/regions`, `POST /api/pricing/calculate` |

All endpoints except `request-otp`, `verify-otp`, `pricing/regions`, and the
public `listings/marketplace` feed require `Authorization: Bearer <token>` from
`verify-otp`'s response.

## Feature-by-feature notes

### Auth (`app/routers/auth_routes.py`)
Phone + OTP flow. There's no SMS gateway wired up, so `request-otp` generates a
4-digit code, stores it, and — only because `MOCK_SMS_MODE=true` — returns it
directly in the response as `demo_otp` for the demo/judges to see. Flip
`MOCK_SMS_MODE=false` (and plug in a real gateway like MSG91/Twilio) for
anything beyond the hackathon. Successful verification issues a JWT valid for
7 days.

### AI Chat & Multilingual Auto-Cataloger (`app/routers/chat.py`, `app/services/ai_service.py`)
Calls Claude to (a) classify + reply to free-form artisan messages in whichever
language they wrote in, and (b) turn a spoken/typed raw description into an
English + native-language product title, description, category, and tags —
exactly what the "Multilingual Auto-Cataloger" card on the landing page
promises. If the chat detects a pricing question and the artisan mentioned a
rupee figure, it automatically runs that figure through the pricing engine
using the artisan's own region.

### Dynamic Pricing Engine (`app/services/pricing_engine.py`)
This is the documented USP. Formula and rationale are in the module docstring;
regional multipliers live in the `pricing_regions` table (seeded from
`app/seed_data.py`) so a teammate can add a new artisan cluster with one row
instead of a code change. Note: because prices are now computed live rather
than hardcoded, numbers for *new* listings will differ slightly from the three
demo listings seeded from the original mockup — that's intentional; it shows
judges a real engine rather than static numbers.

### AI Image Studio / Camera Studio (`app/routers/camera.py`, `app/services/image_service.py`)
Pillow-based enhancement pipeline: EXIF-rotation fix, per-channel auto white
balance, brightness/contrast/saturation correction, unsharp mask, then
composited onto a clean square studio backdrop — the "Before → After" the
landing page shows. It's intentionally lightweight (no GPU/model download) so
it runs anywhere for the demo; swap in a proper matting model (e.g. `rembg`)
behind the same `enhance_product_photo()` function later without touching the
API.

### Listings (`app/routers/listings.py`)
Standard CRUD scoped to the logged-in artisan, plus a public `/marketplace`
feed (anything synced to at least one channel) for the B2B Buyer / GeM Officer
roles to browse, and a `/sync` endpoint that flips the GeM/ONDC/Institutional
badges shown in the frontend's Listings view. In production, `/sync` is where
you'd call the actual GeM and ONDC seller-onboarding APIs.

### Profile & Financials (`app/routers/profile.py`)
`GET /api/profile/dashboard` returns the three stat cards on the Profile view:
30-day payouts, order count, and middlemen deduction — which is hardcoded to
0% because Rangrez's whole model is disintermediation (see `Order.middlemen_deduction`
if you want to model partial commissions for a different marketplace channel later).

### Orders (`app/routers/orders.py`)
Minimal order-placement endpoint so B2B/GeM/Institutional buyers can actually
generate the order count and payout figures the Profile view displays, rather
than those numbers being permanently zero on a fresh database.

## Project layout

```
app/
  main.py            FastAPI app, CORS, router wiring, startup seeding
  config.py           env-driven settings
  database.py          SQLAlchemy engine/session (SQLite by default)
  models.py            User, Product, Order, OTP, PricingRegion
  schemas.py            Pydantic request/response models
  auth.py               OTP + JWT helpers, get_current_user dependency
  seed_data.py           demo artisan/listings + pricing region seeds
  routers/
    auth_routes.py, chat.py, camera.py, listings.py, pricing.py, profile.py, orders.py
  services/
    ai_service.py        Claude wrapper (+ offline fallback)
    image_service.py      Pillow enhancement pipeline
    pricing_engine.py     the dynamic pricing formula
  uploads/                raw + enhanced product photos land here
```

## Swapping the database for the demo day

SQLite (`rangrez.db`, created automatically) is fine for a single-machine demo.
To point at Postgres for a shared/deployed demo, just set `DATABASE_URL` in
`.env` to a Postgres URL and add `psycopg2-binary` to `requirements.txt` — no
code changes needed since everything goes through SQLAlchemy.
