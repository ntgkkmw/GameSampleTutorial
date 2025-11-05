"""Player related endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Request

from models.domain import combatant_to_dict
from models.game import APP_VERSION
from models.schemas import NewGameRequest

router = APIRouter(prefix="/api", tags=["players"])


@router.post("/new_game")
def new_game(payload: NewGameRequest, request: Request):
    """Create a new player and return the initial game state."""

    data = request.app.state.data
    name = (payload.name or "").strip() or "ゆうしゃ"
    player = data.new_player(name)
    seed = data.rng.randint(1, 1_000_000)
    return {
        "version": APP_VERSION,
        "player": combatant_to_dict(player),
        "location": "start_town",
        "seed": seed,
        "progress": {"boss_defeated": False},
    }

