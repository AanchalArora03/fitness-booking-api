from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from api.routes.classes import response_timezone
from core.exceptions import BookingConflictError, ClassNotFoundError
from models.user import User
from schemas.booking import BookingCreate, BookingResponse
from services import booking_service

router = APIRouter(tags=["Bookings"])


@router.post("/book", response_model=BookingResponse, status_code=201)
def book_class(
    data: BookingCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        return booking_service.book_class(db, user.id, data)
    except ClassNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except BookingConflictError as exc:
        raise HTTPException(409, str(exc)) from exc


@router.get("/bookings", response_model=list[BookingResponse])
def list_bookings(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    zone: Annotated[ZoneInfo, Depends(response_timezone)],
):
    results = []
    for item in booking_service.get_user_bookings(db, user.id):
        result = BookingResponse.model_validate(item)
        result.fitness_class.date_time = result.fitness_class.date_time.astimezone(zone)
        results.append(result)
    return results
