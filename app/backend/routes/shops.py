"""Shopping and resting endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from models.domain import combatant_to_dict
from models.schemas import InnRestRequest, ShopBuyRequest

router = APIRouter(prefix="/api", tags=["shops"])


@router.post("/shop/buy")
def shop_buy(payload: ShopBuyRequest, request: Request):
    """Return purchase cost information."""

    data = request.app.state.data
    item = data.items.get(payload.itemId)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.n <= 0 or payload.n > 9:
        raise HTTPException(status_code=400, detail="Invalid quantity")
    cost = payload.n * 8
    return {"item": item, "cost": cost}


@router.post("/inn/rest")
def inn_rest(payload: InnRestRequest, request: Request):
    """Rest at an inn to fully recover."""

    data = request.app.state.data
    player = data.build_combatant_from_payload(payload.player.dict())
    player.hp = player.max_hp
    player.mp = player.max_mp
    player.gold = max(0, player.gold - payload.price)
    return combatant_to_dict(player)

*** End of File
