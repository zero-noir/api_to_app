from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from storage.db import init_db
from routers.generator import router as generator_router

init_db()
app = FastAPI(title=settings.app_name, version='1.0.0')
origins=[o.strip() for o in settings.cors_origins.split(',') if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(generator_router)

@app.get('/')
def root():
    return {'ok': True, 'service': settings.app_name}
