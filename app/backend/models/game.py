"""High-level game services shared across FastAPI routers."""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Dict, List

from fastapi import HTTPException

from .domain import Combatant, CoreStats, combatant_to_dict

APP_VERSION = "0.1.0"
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_json(path: Path) -> List | Dict:
    """Load JSON from disk."""

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


class GameData:
    """Container for static data and helper factories."""

    def __init__(self) -> None:
        self.monsters_raw = load_json(DATA_DIR / "monsters.json")
        self.spells = {entry["id"]: entry for entry in load_json(DATA_DIR / "spells.json")}
        self.items = {entry["id"]: entry for entry in load_json(DATA_DIR / "items.json")}
        self.maps = load_json(DATA_DIR / "maps.json")
        self.monsters = {entry["id"]: entry for entry in self.monsters_raw}
        self.monsters_by_area: Dict[str, List[Dict]] = {}
        for monster in self.monsters_raw:
            self.monsters_by_area.setdefault(monster["area"], []).append(monster)
        self.area_level = {"grass": 2, "cave": 8, "boss": 20}
        self.area_bonus = {
            "grass": {"hp": (0, 5), "atk": (0, 2), "def": (0, 2), "mag": (0, 1), "agi": (0, 2)},
            "cave": {"hp": (2, 12), "atk": (1, 4), "def": (1, 4), "mag": (0, 3), "agi": (1, 3)},
            "boss": {"hp": (0, 0), "atk": (0, 0), "def": (0, 0), "mag": (0, 0), "agi": (0, 0)},
        }
        self.rng = random.Random()

    def new_player(self, name: str) -> Combatant:
        """Create a new player with the default stats."""

        stats = CoreStats(atk=5, defense=3, mag=4, agi=4)
        return Combatant(
            id="player",
            name=name or "ゆうしゃ",
            level=1,
            max_hp=24,
            max_mp=6,
            hp=24,
            mp=6,
            stats=stats,
            exp=0,
            gold=0,
            inventory={"herb": 2},
            spells=["heal", "fire"],
            next_exp=int(10 + (1 ** 1.6)),
        )

    def generate_enemy(self, area: str) -> Combatant:
        """Generate an enemy from the area tables."""

        monsters = self.monsters_by_area.get(area)
        if not monsters:
            raise HTTPException(status_code=404, detail="No monsters for this area")
        template = self.rng.choice(monsters)
        bonuses = self.area_bonus.get(area, self.area_bonus["grass"])
        base = template["base"]
        hp = base["hp"] + self.rng.randint(*bonuses["hp"])
        mp = base["mp"] + self.rng.randint(*bonuses["mag"])
        atk = base["atk"] + self.rng.randint(*bonuses["atk"])
        defense = base["def"] + self.rng.randint(*bonuses["def"])
        mag = base["mag"] + self.rng.randint(*bonuses["mag"])
        agi = base["agi"] + self.rng.randint(*bonuses["agi"])
        return Combatant(
            id=template["id"],
            name=template["name"],
            level=self.area_level.get(area, 1),
            max_hp=hp,
            max_mp=mp,
            hp=hp,
            mp=mp,
            stats=CoreStats(atk=atk, defense=defense, mag=mag, agi=agi),
            exp=template.get("exp", 0),
            gold=template.get("gold", 0),
            inventory={},
            spells=template.get("skills", []),
            is_boss=template["area"] == "boss",
            next_exp=0,
        )

    def build_combatant_from_payload(self, data: Dict) -> Combatant:
        """Recreate a combatant from API data."""

        stats = CoreStats(
            atk=data["stats"]["atk"],
            defense=data["stats"]["defense"],
            mag=data["stats"]["mag"],
            agi=data["stats"]["agi"],
        )
        return Combatant(
            id=data["id"],
            name=data["name"],
            level=data.get("level", 1),
            max_hp=data["max_hp"],
            max_mp=data["max_mp"],
            hp=data["hp"],
            mp=data["mp"],
            stats=stats,
            exp=data.get("exp", 0),
            gold=data.get("gold", 0),
            inventory=data.get("inventory", {}),
            spells=data.get("spells", []),
            is_boss=data.get("is_boss", False),
            next_exp=data.get("next_exp", 0),
        )

    def location(self, location_id: str) -> Dict:
        """Return location metadata."""

        data = self.maps.get(location_id)
        if not data:
            raise HTTPException(status_code=404, detail="Location not found")
        return {
            "id": location_id,
            "name": data["name"],
            "type": data["type"],
            "neighbors": data.get("neighbors", []),
            "encounter": data.get("encounter"),
            "innPrice": data.get("innPrice"),
            "shop": data.get("shop"),
        }

    def encounter_roll(self, area: str, counter: int) -> Dict:
        """Resolve encounter roll returning threshold and optional enemy."""

        threshold = self.rng.randint(4, 7)
        encounter = counter >= threshold
        enemy = None
        if encounter:
            enemy = combatant_to_dict(self.generate_enemy(area))
        return {"encounter": encounter, "threshold": threshold, "enemy": enemy}

    def cors_origins(self) -> List[str]:
        """Return CORS origins configured via env."""

        return os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")

*** End of File
