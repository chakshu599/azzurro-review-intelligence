from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db, dispose_db
from app.routers.api import router, seed_properties
from app.db import async_session_maker

@asynccontextmanager
async def lifespan(app:FastAPI):
    await init_db()
    async with async_session_maker() as db:
        await seed_properties(db)
    yield
    await dispose_db()

app=FastAPI(title=settings.app_name,version=settings.app_version,lifespan=lifespan,docs_url="/docs",openapi_url="/openapi.json")
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins_list,allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router)
