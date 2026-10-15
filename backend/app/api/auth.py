"""Demo login. Not real authentication: it only tells the backend which local teacher is using the app."""

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db import get_session
from app.models import User
from app.schemas.users import LoginIn, UserOut

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=UserOut)
def login(body: LoginIn, db: Session = Depends(get_session)):
    """Returns the teacher with this email, creating them if new. The frontend then sends X-User-Id."""
    email = body.email.lower()
    user = db.exec(select(User).where(User.email == email)).first()
    if user is None:
        user = User(name=body.name, email=email)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:  # the same email was registered by a request a moment ago
            db.rollback()
            user = db.exec(select(User).where(User.email == email)).one()
    return user
