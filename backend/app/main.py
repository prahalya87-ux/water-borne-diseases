from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .database import Base, engine
from .routers import admin, alerts, assistant, auth, facilities, map as map_router, observations, reports, service_points, uploads, water_quality

if settings.AUTO_CREATE_TABLES:
    Base.metadata.create_all(bind=engine)

app = FastAPI(title="WaterGuard AI API", version="0.1.0",
              description="Water-borne disease surveillance platform. Citizen reports are UNVERIFIED until reviewed.")

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    fields = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "Validation failed", "detail": fields})


@app.get("/")
def root():
    return {"name": app.title, "docs": app.docs_url}


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(admin.router)
app.include_router(assistant.router)
app.include_router(uploads.router)
app.include_router(alerts.router)
app.include_router(facilities.router)
app.include_router(map_router.router)
app.include_router(water_quality.router)
app.include_router(service_points.router)
app.include_router(observations.router)