"""Subject profiles: one YAML file per subject and phase in app/profiles/."""

from functools import lru_cache
from pathlib import Path

import yaml

PROFILE_DIR = Path(__file__).resolve().parent.parent / "profiles"


@lru_cache
def _all() -> dict[str, dict]:
    profiles = (yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(PROFILE_DIR.glob("*.yaml")))
    return {profile["id"]: profile for profile in profiles}


def get(profile_id: str) -> dict | None:
    return _all().get(profile_id)


def list_tested(include_untested: bool = False) -> list[dict]:
    """Profiles for the Setup screen, in the shape of GET /profiles.

    `include_untested` is for local development only, until a profile has
    passed its strong-versus-weak check.
    """
    return [
        {key: profile[key] for key in ("id", "subject", "grade", "phase", "label", "chapters")}
        for profile in _all().values()
        if include_untested or profile.get("tested")
    ]
