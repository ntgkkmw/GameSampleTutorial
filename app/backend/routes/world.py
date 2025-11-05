"""World exploration related endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from models.schemas import EncounterRollRequest, EncounterRollResponse, LocationResponse

router = APIRouter(prefix="/api", tags=["world"])


@router.get("/world/location/{location_id}", response_model=LocationResponse)
def get_location(location_id: str, request: Request):
    """Return details about a location."""

    data = request.app.state.data
    return data.location(location_id)


@router.post("/encounter/roll", response_model=EncounterRollResponse)
def roll_encounter(payload: EncounterRollRequest, request: Request):
    """Roll for a random encounter."""

    data = request.app.state.data
    return data.encounter_roll(payload.areaId, payload.counter)
