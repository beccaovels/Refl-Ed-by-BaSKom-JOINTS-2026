"""Subject profiles offered in Setup."""

from fastapi import APIRouter

from app.core.config import settings
from app.schemas.profiles import ProfileOut
from app.services import profiles

router = APIRouter(tags=["profiles"])


@router.get("/profiles", response_model=list[ProfileOut])
def list_profiles():
    """Only tested profiles, unless SHOW_UNTESTED_PROFILES=true in backend/.env for local development."""
    return profiles.list_tested(include_untested=settings.show_untested_profiles)
