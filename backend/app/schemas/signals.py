"""Delivery signal bins. See the Signals section of docs/api-contract.md.

Only these numbers are accepted. Unknown fields are rejected, so nothing else
(an image, a frame, landmarks) can be sent along with a bin.
"""

from pydantic import BaseModel, ConfigDict, Field

MAX_BINS = 360  # one hour of 10-second bins in one request


class Bin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_start_ms: int = Field(ge=0)
    measured: bool = True
    # camera values: null with the camera off, or when the picture could not be measured
    facing_pct: float | None = Field(default=None, ge=0, le=1)
    posture_ok_pct: float | None = Field(default=None, ge=0, le=1)
    gesture_rate: float | None = Field(default=None, ge=0, le=1)
    expressiveness: float | None = Field(default=None, ge=0, le=1)
    face_visible_pct: float | None = Field(default=None, ge=0, le=1)
    # voice values: sent with or without the camera
    volume: float | None = Field(default=None, ge=0, le=1)
    pitch_variation: float | None = Field(default=None, ge=0)  # semitones; null when nobody spoke


class SignalsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bins: list[Bin] = Field(max_length=MAX_BINS)
