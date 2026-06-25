from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.database.connection import init_db

app = FastAPI(
    title="运动姿态评估与纠错系统",
    description="Sports Posture Assessment and Correction System API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from backend.routers import auth, assessment, fms, prescription, training, learning, records, checkin, coach, admin
# fms router
# from backend.routers import fms
app.include_router(auth.router)
app.include_router(fms.router)
app.include_router(assessment.router)
app.include_router(prescription.router)
app.include_router(training.router)
app.include_router(learning.router)
app.include_router(records.router)
app.include_router(checkin.router)
app.include_router(coach.router)
app.include_router(admin.router)

@app.on_event("startup")
def on_startup():
    init_db()

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
