"""Who is calling. No real authentication: after login the frontend sends X-User-Id on every request."""

from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.core.db import get_session
from app.models import Material, TeachingSession, User


def current_user(
    x_user_id: str | None = Header(default=None),
    db: Session = Depends(get_session),
) -> User:
    user = db.get(User, x_user_id) if x_user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Silakan masuk terlebih dahulu.")
    return user


def own_session(db: Session, session_id: str, user: User) -> TeachingSession:
    """The session, if it belongs to `user`. Someone else's session is reported as not found, not as forbidden."""
    session = db.get(TeachingSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Sesi tidak ditemukan.")
    return session


def own_material(db: Session, material_id: str, user: User) -> Material:
    """The material, if it belongs to `user`. Someone else's is reported as not found."""
    material = db.get(Material, material_id)
    if material is None or material.user_id != user.id:
        raise HTTPException(status_code=404, detail="Materi tidak ditemukan.")
    return material
