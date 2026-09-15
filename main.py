from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine, SessionLocal
from app.routers import auth_routes, pricing, chat, camera, listings, profile, orders
from app.seed_data import run_all_seeds

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Rangrez API",
    description=(
        "Backend for Rangrez — AI-Driven Market Linkage & Smart Cataloging for "
        "Marginalized Artisans (Smart India Hackathon 2026)."
    ),
    version="1.0.0",
)

# Wide-open CORS is fine for a hackathon demo where the frontend is a static HTML
# file opened from anywhere; tighten this to your deployed frontend origin for
# anything beyond the demo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(pricing.router)
app.include_router(chat.router)
app.include_router(camera.router)
app.include_router(listings.router)
app.include_router(profile.router)
app.include_router(orders.router)


@app.on_event("startup")
def seed_on_startup():
    db = SessionLocal()
    try:
        run_all_seeds(db)
    finally:
        db.close()


@app.get("/")
def root():
    return {
        "service": "Rangrez API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
