"""Battle handling endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from models.domain import (
    award_loot,
    enemy_turn,
    level_up,
    process_player_action,
    start_battle,
)
from models.schemas import BattleActRequest, BattleStartRequest

router = APIRouter(prefix="/api", tags=["battles"])


@router.post("/battle/start")
def battle_start(payload: BattleStartRequest, request: Request):
    """Initialize a battle and store it in the application state."""

    data = request.app.state.data
    battles = request.app.state.battles
    player = data.build_combatant_from_payload(payload.player.dict())
    enemy = data.build_combatant_from_payload(payload.enemy.dict())
    session = start_battle(player, enemy)
    battles[session.id] = session
    return session.snapshot()


@router.post("/battle/act")
def battle_act(payload: BattleActRequest, request: Request):
    """Execute a player action and advance the battle."""

    battles = request.app.state.battles
    session = battles.get(payload.battleId)
    if not session:
        raise HTTPException(status_code=404, detail="Battle not found")
    data = request.app.state.data
    process_player_action(session, payload.action, payload.payload or {}, data.items, data.spells)
    if session.ended and session.enemy.hp <= 0 and payload.action != "run":
        award_loot(session.player, session.enemy)
        session.log.extend(level_up(session.player, session.rng))
    if not session.ended and session.turn == "enemy":
        enemy_turn(session, data.spells)
        if session.ended and session.enemy.hp <= 0:
            award_loot(session.player, session.enemy)
            session.log.extend(level_up(session.player, session.rng))
    if session.ended:
        session.turn = "end"
    return session.snapshot()
