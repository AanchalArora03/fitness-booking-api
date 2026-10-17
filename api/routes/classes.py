from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from api.dependencies import get_current_user, get_db
from models.user import User
from schemas.fitness_class import ClassCreate, ClassResponse
from services import class_service

router = APIRouter(tags=["Classes"])


def response_timezone(timezone: Annotated[str, Query()] = "Asia/Kolkata") -> ZoneInfo:
    try:
        return ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise HTTPException(422, "Unknown timezone. Use an IANA name such as Asia/Kolkata.") from exc


def class_response(item, zone: ZoneInfo) -> ClassResponse:
    result = ClassResponse.model_validate(item)
    result.date_time = result.date_time.astimezone(zone)
    return result


@router.post("/classes", response_model=ClassResponse, status_code=201)
def create_class(
    data: ClassCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    try:
        return class_service.create_class(db, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/classes", response_model=list[ClassResponse])
def list_classes(
    db: Annotated[Session, Depends(get_db)],
    zone: Annotated[ZoneInfo, Depends(response_timezone)],
):
    return [class_response(item, zone) for item in class_service.get_upcoming_classes(db)]
