import os
from datetime import timedelta

class Settings:
    DB_TYPE: str = os.getenv('DB_TYPE', 'mysql')
    DB_HOST: str = os.getenv('DB_HOST', 'localhost')
    DB_PORT: int = int(os.getenv('DB_PORT', '3306'))
    DB_USER: str = os.getenv('DB_USER', 'root')
    DB_PASSWORD: str = os.getenv('DB_PASSWORD', 'Zly20050708')
    DB_NAME: str = os.getenv('DB_NAME', 'pose_correction')

    @property
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == 'sqlite':
            return 'sqlite:///./pose_correction.db'
        return f'mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4'

    SECRET_KEY: str = os.getenv('SECRET_KEY', 'pose-correction-secret-key-2026')
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    MODEL_PATH: str = os.getenv('MODEL_PATH', 'yolov8n-pose.pt')
    HIGH_PRECISION_MODEL_PATH: str = os.getenv('HIGH_PRECISION_MODEL_PATH', 'yolov8s-pose.pt')
    DEVICE: str = os.getenv('DEVICE', 'auto')

    HOST: str = os.getenv('HOST', '0.0.0.0')
    PORT: int = int(os.getenv('PORT', '8002'))

    CORS_ORIGINS: list = ['http://localhost:5173', 'http://localhost:5179', 'http://localhost:3000', 'http://127.0.0.1:5173', 'http://127.0.0.1:5179', 'http://10.244.112.152:5173', 'http://10.244.112.152:5179']

settings = Settings()

