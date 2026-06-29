from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings, _get_lan_ip
from backend.database.connection import init_db, get_db
from backend.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

app = FastAPI(
    title="运动姿态评估与纠错系统",
    description="Sports Posture Assessment and Correction System API",
    version="1.0.0"
)

_cors_origins = settings.CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from backend.routers import auth, assessment, fms, prescription, learning, checkin, coach, admin, prescription_v2
from backend.routers.multi_view_assessment import router as multi_view_router
app.include_router(auth.router)
app.include_router(fms.router)
app.include_router(assessment.router)
app.include_router(multi_view_router)
app.include_router(prescription.router)
app.include_router(learning.router)
app.include_router(checkin.router)
app.include_router(coach.router)
app.include_router(admin.router)
app.include_router(prescription_v2.router)

@app.on_event("startup")
def on_startup():
    init_db()
    from backend.database.seed import seed_action_library, seed_users
    db = next(get_db())
    try:
        seed_action_library(db)
        seed_users(db)
    finally:
        db.close()

    # 打印多机部署相关配置，便于调试
    lan_ip = _get_lan_ip()
    logger.info("=" * 60)
    logger.info("运动姿态评估与纠错系统 API v1.0.0")
    logger.info("监听地址: http://%s:%s", settings.HOST, settings.PORT)
    logger.info("本机局域网 IP: %s", lan_ip)
    logger.info("数据库: %s:%s/%s", settings.DB_HOST, settings.DB_PORT, settings.DB_NAME)
    logger.info("DeepSeek 模型: %s", settings.DEEPSEEK_MODEL)
    logger.info("CORS 允许来源 (%d 个):", len(_cors_origins))
    for origin in _cors_origins:
        logger.info("  - %s", origin)
    logger.info("=" * 60)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
