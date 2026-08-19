from typing import TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


def get_or_404(db: Session, model: type[ModelT], id_: object, detail: str = "Not found") -> ModelT:
    obj = db.get(model, id_)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail)
    return obj


def commit_or_409(db: Session, conflict_detail: str = "This action conflicts with existing data") -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, conflict_detail)
