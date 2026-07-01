from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings, _get_lan_ip
from backend.database.connection import init_db, get_db
from backend.logger import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)

# ── 禁用 Ultralytics 在线同步，避免每次启动检查更新 ──
import os
os.environ.setdefault("ULTRALYTICS_SETTINGS", "")
try:
    from ultralytics import settings as ultralytics_settings
    ultralytics_settings.update({"sync": False, "hub": False})
except Exception:
    pass

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

from backend.middleware.rate_limit import auth_rate_limit_middleware
app.middleware("http")(auth_rate_limit_middleware)

from backend.routers import auth, assessment, fms, prescription, learning, checkin, coach, admin, prescription_v2, coach_actions
from backend.routers.multi_view_assessment import router as multi_view_router
app.include_router(auth.router)
app.include_router(fms.router)
app.include_router(assessment.router)
app.include_router(multi_view_router)
app.include_router(prescription.router)
app.include_router(learning.router)
app.include_router(checkin.router)
app.include_router(coach.router)
app.include_router(coach_actions.router)
app.include_router(admin.router)
app.include_router(prescription_v2.router)

# ── 静态文件挂载：教练上传的动作媒体 ──
from fastapi.staticfiles import StaticFiles
UPLOADS_ACTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads", "actions")
os.makedirs(UPLOADS_ACTIONS_DIR, exist_ok=True)
app.mount("/media/uploads/actions", StaticFiles(directory=UPLOADS_ACTIONS_DIR), name="action_uploads")

@app.on_event("startup")
def on_startup():
    settings.validate()
    init_db()
    from backend.database.seed import seed_action_library, seed_users, seed_system_config
    db = next(get_db())
    try:
        seed_action_library(db)
        seed_users(db)
        seed_system_config(db)
    finally:
        db.close()

    # ── 预加载 YOLO 模型（避免首次打开摄像头时等待）──
    logger.info("正在预加载 YOLO 姿态模型，首次启动可能需要数十秒...")
    try:
        from models.engine import model_manager
        model_manager._ensure_loaded()
        logger.info("YOLO 模型预加载完成 (%s)", settings.MODEL_PATH)
    except Exception as e:
        logger.warning("模型预加载失败（将在首次使用时再次尝试）: %s", e)

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
