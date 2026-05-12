from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth as auth_router
from app.api.v1 import contests as contests_router
from app.api.v1 import problems as problems_router
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.integrations.judges import registry
from app.integrations.judges.codeforces import CodeforcesAdapter
from app.models.enums import ExternalSource


@asynccontextmanager
async def lifespan(app: FastAPI):
    registry.register(
        ExternalSource.codeforces,
        CodeforcesAdapter(settings.CF_SERVICE_ACCOUNT, settings.CF_SERVICE_PASSWORD),
    )
    yield
    await engine.dispose()


app = FastAPI(title="AlgosyHub", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth_router.router, prefix="/api/v1")
app.include_router(problems_router.router, prefix="/api/v1")
app.include_router(contests_router.router, prefix="/api/v1")


@app.get("/healthz", tags=["system"])
async def healthz():
    return {"status": "ok"}
