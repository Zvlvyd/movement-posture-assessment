import uvicorn
from config.settings import settings

if __name__ == '__main__':
    uvicorn.run('backend.main:app', host=settings.HOST, port=settings.PORT, reload=True)
