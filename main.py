import logging
from time import perf_counter

from fastapi import FastAPI, Request

from api.routes.auth import router as auth_router
from api.routes.classes import router as classes_router
from api.routes.bookings import router as bookings_router

app = FastAPI(title="Fitness Studio Booking API")
app.include_router(auth_router)
app.include_router(classes_router)
app.include_router(bookings_router)

logger = logging.getLogger("uvicorn.error")


@app.middleware("http")
async def log_request(request: Request, call_next):
    """Log request outcomes without credentials, bodies, or query parameters."""
    start = perf_counter()
    response = await call_next(request)
    logger.info("%s %s %s %.1fms", request.method, request.url.path,
                response.status_code, (perf_counter() - start) * 1000)
    return response


@app.get("/health")
def health_check():
    return {"status": "ok"}
