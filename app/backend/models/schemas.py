"""Pydantic schemas for API requests and responses."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class CoreStatsModel(BaseModel):
    """Representation of the main combat stats."""

    atk: int = Field(ge=0)
    defense: int = Field(ge=0)
    mag: int = Field(ge=0)
    agi: int = Field(ge=0)


class CombatantModel(BaseModel):
    """Snapshot of a combatant."""

    id: str
    name: str
    level: int
    max_hp: int
    max_mp: int
    hp: int
    mp: int
    stats: CoreStatsModel
    exp: int
    gold: int
    inventory: Dict[str, int]
    spells: List[str]
    is_boss: bool = False
    next_exp: int


class BattleFlagsModel(BaseModel):
    """Flags describing the battle start conditions."""

    surprised: bool = False
    preemptive: bool = False


class BattleStateModel(BaseModel):
    """Battle state sent to the frontend."""

    id: str
    turn: str
    log: List[str]
    player: CombatantModel
    enemy: CombatantModel
    ended: bool
    flags: BattleFlagsModel


class NewGameRequest(BaseModel):
    """Request payload to create a new game."""

    name: Optional[str] = None


class EncounterRollRequest(BaseModel):
    """Request payload to check for encounters."""

    areaId: str = Field(alias="areaId")
    counter: int = 0

    class Config:
        populate_by_name = True


class EncounterRollResponse(BaseModel):
    """Response describing encounter result."""

    encounter: bool
    threshold: int
    enemy: Optional[CombatantModel] = None


class BattleStartRequest(BaseModel):
    """Request payload to start a battle."""

    player: CombatantModel
    enemy: CombatantModel


class BattleActRequest(BaseModel):
    """Request payload to act in battle."""

    battleId: str = Field(alias="battleId")
    action: str
    payload: Dict[str, str] | None = None

    class Config:
        populate_by_name = True


class ShopBuyRequest(BaseModel):
    """Request payload for buying an item."""

    itemId: str = Field(alias="itemId")
    n: int

    class Config:
        populate_by_name = True


class InnRestRequest(BaseModel):
    """Request payload for resting at an inn."""

    player: CombatantModel
    price: int


class LocationResponse(BaseModel):
    """Location metadata response."""

    id: str
    name: str
    type: str
    neighbors: List[str]
    encounter: Optional[str] = None
    innPrice: Optional[int] = None
    shop: Optional[List[str]] = None


class SaveRequest(BaseModel):
    """Placeholder for server-side save."""

    payload: Dict


class LoadResponse(BaseModel):
    """Placeholder for server-side load."""

    payload: Dict

*** End of File
