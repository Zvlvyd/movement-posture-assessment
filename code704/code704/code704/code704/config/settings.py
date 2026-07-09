"""
Application settings — loaded from environment variables with sensible defaults.

多机部署快速参考：
  数据库服务器那台不需要额外设置（默认连本机 MySQL）。
  其他电脑只需设置 3 个环境变量：
    set DB_HOST=<数据库服务器的 IP>
    set CORS_ALLOW_LAN=true
    set DEEPSEEK_API_KEY=sk-your-key    （可选，共用服务器 Key 则无需设置）

  .env 文件支持：在 run.py 同级目录创建 .env 文件，每行 KEY=VALUE。
"""
import os
import socket

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _project_path(value: str) -> str:
    """Resolve relative asset paths from the project root, independent of cwd."""
    return value if os.path.isabs(value) else os.path.join(_PROJECT_ROOT, value)


def _get_lan_ip() -> str:
    """探测本机局域网 IP，失败返回 127.0.0.1"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _load_dotenv():
    """简易 .env 加载器，在 Settings 类定义前加载，使环境变量影响类属性默认值。"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    if not os.path.isfile(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


# 在 Settings 类定义之前加载 .env，确保 os.getenv() 默认值可被覆盖
_load_dotenv()


class Settings:
    """Central application configuration.

    配置优先级：环境变量 > .env 文件 > 代码默认值
    """

    # ── Database ──────────────────────────────────────────
    DB_TYPE: str = os.getenv("DB_TYPE", "mysql")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "3306"))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "pose_correction")

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            return "sqlite:///./pose_correction.db"
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    # ── Auth ──────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ── Seed Users (created on first startup if not exist) ──
    DEFAULT_ADMIN_USERNAME: str = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD: str = os.getenv("DEFAULT_ADMIN_PASSWORD", "")
    DEFAULT_COACH_USERNAME: str = os.getenv("DEFAULT_COACH_USERNAME", "coach")
    DEFAULT_COACH_PASSWORD: str = os.getenv("DEFAULT_COACH_PASSWORD", "")

    # ── Model ─────────────────────────────────────────────
    MODEL_PATH: str = _project_path(os.getenv("MODEL_PATH", "yolov8s-pose.pt"))
    HIGH_PRECISION_MODEL_PATH: str = _project_path(os.getenv("HIGH_PRECISION_MODEL_PATH", "yolov8s-pose.pt"))
    DEVICE: str = os.getenv("DEVICE", "auto")

    # ── Server ────────────────────────────────────────────
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8002"))

    # ── DeepSeek AI ───────────────────────────────────────
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")

    # ── CORS ──────────────────────────────────────────────
    # CORS_ALLOW_LAN=true 时自动将本机局域网 IP 加入白名单
    CORS_ALLOW_LAN: bool = os.getenv("CORS_ALLOW_LAN", "false").lower() in ("1", "true", "yes")
    # CORS_EXTRA_ORIGINS 手动追加额外来源，逗号分隔
    CORS_EXTRA_ORIGINS: str = os.getenv("CORS_EXTRA_ORIGINS", "")

    # ── Feature Flags ─────────────────────────────────────
    ENABLE_TEST_ENDPOINTS: bool = os.getenv("ENABLE_TEST_ENDPOINTS", "false").lower() in ("1", "true", "yes")

    def validate(self):
        """启动时校验必需配置项，缺失则抛出 ValueError 并给出明确提示。"""
        errors = []
        if not self.SECRET_KEY:
            errors.append("SECRET_KEY 未设置 — 请在 .env 文件或环境变量中设置 (建议: openssl rand -hex 32)")
        if self.DB_TYPE == "mysql" and not self.DB_PASSWORD:
            errors.append("DB_PASSWORD 未设置 — 请在 .env 文件或环境变量中设置数据库密码")
        if errors:
            raise ValueError("配置校验失败:\n  " + "\n  ".join(errors))

    @property
    def CORS_ORIGINS(self) -> list:
        """动态计算 CORS 允许来源列表"""
        origins = [
            "http://localhost:5173",
            "http://localhost:5179",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5179",
            "http://127.0.0.1:3000",
        ]
        # 自动加入本机局域网 IP
        if self.CORS_ALLOW_LAN:
            lan_ip = _get_lan_ip()
            if lan_ip != "127.0.0.1":
                for port in (5173, 5179, 3000):
                    origins.append(f"http://{lan_ip}:{port}")
                    origins.append(f"https://{lan_ip}:{port}")
        # 手动追加额外来源
        if self.CORS_EXTRA_ORIGINS:
            for origin in self.CORS_EXTRA_ORIGINS.split(","):
                origin = origin.strip()
                if origin and origin not in origins:
                    origins.append(origin)
        return origins


# Singleton instance
settings = Settings()
