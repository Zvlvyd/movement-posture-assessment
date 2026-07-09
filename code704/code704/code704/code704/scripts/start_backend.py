import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import uvicorn
from config.settings import settings
uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=False)
