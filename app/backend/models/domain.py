"""Domain logic for the retro RPG battle system."""
from __future__ import annotations

import math
import random
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CoreStats:
    """Core stats shared by both player and enemy combatants."""

    atk: int
    defense: int
    mag: int
    agi: int


@dataclass
class Combatant:
    """Mutable state of a combat participant."""

    id: str
    name: str
    level: int
    max_hp: int
    max_mp: int
    hp: int
    mp: int
    stats: CoreStats
    exp: int = 0
    gold: int = 0
    inventory: Dict[str, int] = field(default_factory=dict)
    spells: List[str] = field(default_factory=list)
    is_boss: bool = False
    next_exp: int = 0

    def clone(self) -> "Combatant":
        """Return a copy of the combatant for snapshot serialization."""

        return Combatant(
            id=self.id,
            name=self.name,
            level=self.level,
            max_hp=self.max_hp,
            max_mp=self.max_mp,
            hp=self.hp,
            mp=self.mp,
            stats=CoreStats(
                atk=self.stats.atk,
                defense=self.stats.defense,
                mag=self.stats.mag,
                agi=self.stats.agi,
            ),
            exp=self.exp,
            gold=self.gold,
            inventory=dict(self.inventory),
            spells=list(self.spells),
            is_boss=self.is_boss,
            next_exp=self.next_exp,
        )


@dataclass
class BattleFlags:
    """Flags that describe modifiers applied when the battle started."""

    surprised: bool = False
    preemptive: bool = False


@dataclass
class BattleSession:
    """In-memory representation of an on-going battle."""

    id: str
    player: Combatant
    enemy: Combatant
    turn: str
    log: List[str]
    flags: BattleFlags
    rng: random.Random
    ended: bool = False

    def snapshot(self) -> Dict:
        """Build a serializable snapshot of the session."""

        return {
            "id": self.id,
            "turn": self.turn,
            "log": list(self.log),
            "player": combatant_to_dict(self.player),
            "enemy": combatant_to_dict(self.enemy),
            "ended": self.ended,
            "flags": {
                "surprised": self.flags.surprised,
                "preemptive": self.flags.preemptive,
            },
        }


def combatant_to_dict(entity: Combatant) -> Dict:
    """Serialize a combatant."""

    return {
        "id": entity.id,
        "name": entity.name,
        "level": entity.level,
        "max_hp": entity.max_hp,
        "max_mp": entity.max_mp,
        "hp": entity.hp,
        "mp": entity.mp,
        "stats": {
            "atk": entity.stats.atk,
            "defense": entity.stats.defense,
            "mag": entity.stats.mag,
            "agi": entity.stats.agi,
        },
        "exp": entity.exp,
        "gold": entity.gold,
        "inventory": dict(entity.inventory),
        "spells": list(entity.spells),
        "is_boss": entity.is_boss,
        "next_exp": entity.next_exp,
    }


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a numeric value between the supplied bounds."""

    return max(minimum, min(value, maximum))


def parse_power_range(expr: str) -> Tuple[int, int]:
    """Parse a power expression such as ``"10-14"`` into a numeric range."""

    low, high = expr.split("-")
    return int(low), int(high)


def calc_next_exp(level: int) -> int:
    """Compute the experience needed for the next level."""

    return math.floor(10 + (level ** 1.6))


def roll_preemptive(player: Combatant, enemy: Combatant, rng: random.Random) -> BattleFlags:
    """Determine whether the battle starts with surprise or preemptive attacks."""

    base_preemptive = 0.20
    base_surprise = 0.10
    agi_diff = player.stats.agi - enemy.stats.agi
    adj = clamp(agi_diff * 0.01, -0.10, 0.10)
    preemptive_chance = clamp(base_preemptive + adj, 0.05, 0.35)
    surprise_chance = clamp(base_surprise - adj, 0.05, 0.35)
    roll = rng.random()
    if roll < preemptive_chance:
        return BattleFlags(preemptive=True, surprised=False)
    if roll < preemptive_chance + surprise_chance:
        return BattleFlags(preemptive=False, surprised=True)
    return BattleFlags()


def physical_damage(
    attacker: Combatant,
    defender: Combatant,
    rng: random.Random,
    *,
    force_crit: bool = False,
    force_miss: bool = False,
) -> Tuple[int, bool, bool]:
    """Calculate physical damage from ``attacker`` to ``defender``.

    Returns a tuple ``(damage, is_critical, is_miss)``.
    """

    if force_miss:
        return 0, False, True

    miss_chance = clamp(0.05 + (defender.stats.agi - attacker.stats.agi) * 0.03, 0.02, 0.30)
    if not force_crit and rng.random() < miss_chance:
        return 0, False, True

    crit_chance = clamp(0.05 + (attacker.stats.agi - defender.stats.agi) * 0.02, 0.02, 0.15)
    is_crit = force_crit or rng.random() < crit_chance

    base_roll = attacker.stats.atk + rng.randint(-1, 2)
    if is_crit:
        crit_bonus = attacker.stats.atk + rng.randint(1, 3)
        damage = max(1, base_roll + crit_bonus)
    else:
        damage = max(1, base_roll - defender.stats.defense // 2)
    return damage, is_crit, False


def spell_damage(
    caster: Combatant,
    target: Combatant,
    spell: Dict,
    rng: random.Random,
) -> Tuple[int, str]:
    """Resolve a spell effect and return value and message suffix."""

    low, high = parse_power_range(spell["power"])
    base = rng.randint(low, high)
    scale = 0.0
    if spell["scale"].startswith("MAG"):
        coef = float(spell["scale"].split("*")[1])
        scale = math.floor(caster.stats.mag * coef)
    total = base + int(scale)
    if spell["type"] == "attack":
        return max(1, total), "ダメージ!"
    if spell["type"] == "heal":
        healed = min(total, target.max_hp - target.hp)
        return healed, "HPを回復した!"
    raise ValueError("Unsupported spell type")


def heal_amount(caster: Combatant, spell: Dict, rng: random.Random) -> int:
    """Calculate the healing amount for a spell and apply it."""

    value, _ = spell_damage(caster, caster, spell, rng)
    return value


def apply_item_effect(user: Combatant, target: Combatant, item: Dict, rng: random.Random) -> str:
    """Apply the effect of an item and return a log string."""

    item_type = item["type"]
    if item_type == "heal":
        low, high = parse_power_range(item["power"])
        amount = rng.randint(low, high)
        healed = min(amount, target.max_hp - target.hp)
        target.hp += healed
        return f"{target.name}のHPが{healed}かいふくした!"
    if item_type == "mp":
        low, high = parse_power_range(item["power"])
        amount = rng.randint(low, high)
        restored = min(amount, target.max_mp - target.mp)
        target.mp += restored
        return f"{target.name}のMPが{restored}かいふくした!"
    if item_type == "revive":
        if target.hp > 0:
            return f"{target.name}はまだ元気だ!"
        if item.get("power") == "half":
            target.hp = max(1, target.max_hp // 2)
        else:
            target.hp = target.max_hp
        return f"{target.name}はよみがえった!"
    if item_type == "cure_poison":
        return "しかし なにもおこらなかった..."  # Poison not implemented yet.
    raise ValueError("Unsupported item type")


def attempt_run(player: Combatant, enemy: Combatant, rng: random.Random) -> bool:
    """Determine whether the player successfully runs from battle."""

    if enemy.is_boss:
        return False
    base = 0.4
    diff = player.stats.agi - enemy.stats.agi
    chance = clamp(base + diff * 0.05, 0.2, 0.9)
    return rng.random() < chance


def award_loot(player: Combatant, enemy: Combatant) -> None:
    """Grant experience and gold after a victory."""

    player.exp += enemy.exp
    player.gold += enemy.gold


def level_up(player: Combatant, rng: random.Random) -> List[str]:
    """Apply level-up stat increases and return log lines."""

    logs = []
    while player.level < 99 and player.exp >= player.next_exp:  # type: ignore[attr-defined]
        player.level += 1
        hp_gain = rng.randint(3, 6)
        mp_gain = rng.randint(1, 3)
        atk_gain = rng.randint(0, 2)
        def_gain = rng.randint(0, 2)
        mag_gain = rng.randint(0, 2)
        agi_gain = rng.randint(0, 2)
        player.max_hp += hp_gain
        player.max_mp += mp_gain
        player.stats.atk += atk_gain
        player.stats.defense += def_gain
        player.stats.mag += mag_gain
        player.stats.agi += agi_gain
        player.hp = min(player.max_hp, player.hp + hp_gain)
        player.mp = min(player.max_mp, player.mp + mp_gain)
        logs.append(
            f"{player.name}はレベル{player.level}にあがった! HP+{hp_gain} MP+{mp_gain}"
        )
        player.next_exp = player.level * 2 + calc_next_exp(player.level)  # type: ignore[attr-defined]
    return logs


def enemy_turn(session: BattleSession, spells: Dict[str, Dict]) -> None:
    """Execute the enemy's turn, mutating the battle session."""

    if session.ended:
        return
    enemy = session.enemy
    player = session.player
    log = session.log
    rng = session.rng
    available_spells = [spells[s] for s in enemy.spells if s in spells and spells[s]["type"] in {"attack", "heal"} and enemy.mp >= spells[s]["mp"]]
    action_choice = "attack"
    if available_spells:
        # Simple AI: heal if HP below 40%, else cast attack sometimes
        if enemy.hp < enemy.max_hp * 0.4 and any(sp["type"] == "heal" for sp in available_spells):
            action_choice = "heal"
        elif rng.random() < 0.3:
            action_choice = "attack_spell"
    if action_choice == "attack":
        damage, crit, miss = physical_damage(enemy, player, rng)
        if miss:
            log.append(f"{enemy.name}のこうげき! しかし はずれた!")
        else:
            player.hp = max(0, player.hp - damage)
            suffix = "!!" if crit else "!"
            log.append(f"{enemy.name}のこうげき! {damage}のダメージ{suffix}")
    elif action_choice == "heal":
        heal_spell = next(sp for sp in available_spells if sp["type"] == "heal")
        enemy.mp -= heal_spell["mp"]
        before = enemy.hp
        healed, _ = spell_damage(enemy, enemy, heal_spell, rng)
        enemy.hp = min(enemy.max_hp, before + healed)
        log.append(f"{enemy.name}は{heal_spell['name']}をとなえた! {healed}かいふくした!")
    else:  # attack spell
        attack_spell = available_spells[0]
        enemy.mp -= attack_spell["mp"]
        damage, suffix = spell_damage(enemy, player, attack_spell, rng)
        player.hp = max(0, player.hp - damage)
        log.append(f"{enemy.name}は{attack_spell['name']}をとなえた! {damage}{suffix}")
    if player.hp <= 0:
        session.ended = True
        session.turn = "end"
        log.append(f"{player.name}はたおれてしまった...")
    else:
        session.turn = "player"


def start_battle(player: Combatant, enemy: Combatant, rng_seed: Optional[int] = None) -> BattleSession:
    """Create a new battle session and return it."""

    rng = random.Random(rng_seed or random.randint(1, 1_000_000))
    flags = roll_preemptive(player, enemy, rng)
    turn = "player"
    if flags.surprised:
        turn = "enemy"
    elif not flags.preemptive:
        # Determine initiative normally
        if rng.random() < 0.5 + clamp((player.stats.agi - enemy.stats.agi) * 0.05, -0.3, 0.3):
            turn = "player"
        else:
            turn = "enemy"
    session = BattleSession(
        id=str(uuid.uuid4()),
        player=player,
        enemy=enemy,
        turn=turn,
        log=[],
        flags=flags,
        rng=rng,
    )
    if flags.preemptive:
        session.log.append("先制こうげきのチャンスだ!")
    elif flags.surprised:
        session.log.append("ふいをつかれた! 気をつけろ!")
    return session


def process_player_action(
    session: BattleSession,
    action: str,
    payload: Dict,
    items: Dict[str, Dict],
    spells: Dict[str, Dict],
) -> None:
    """Handle the player's selected action."""

    if session.ended or session.turn != "player":
        return
    player = session.player
    enemy = session.enemy
    log = session.log
    rng = session.rng

    if action == "attack":
        damage, crit, miss = physical_damage(player, enemy, rng)
        if miss:
            log.append("プレイヤーはこうげき! しかし あたらなかった!")
        else:
            enemy.hp = max(0, enemy.hp - damage)
            suffix = "!!" if crit else "!"
            log.append(f"プレイヤーはこうげき! {damage}のダメージ{suffix}")
    elif action == "spell":
        spell_id = payload.get("spellId")
        if spell_id not in player.spells:
            log.append("そのまほうは まだつかえない!")
            session.turn = "enemy"
            return
        spell = spells.get(spell_id)
        if not spell:
            log.append("まほうのちしきがたりない!")
            session.turn = "enemy"
            return
        if player.mp < spell["mp"]:
            log.append("MPがたりない!")
            session.turn = "enemy"
            return
        player.mp -= spell["mp"]
        if spell["type"] == "attack":
            damage, suffix = spell_damage(player, enemy, spell, rng)
            enemy.hp = max(0, enemy.hp - damage)
            log.append(f"{spell['name']}! {damage}{suffix}")
        elif spell["type"] == "heal":
            before = player.hp
            healed, suffix = spell_damage(player, player, spell, rng)
            player.hp = min(player.max_hp, before + healed)
            log.append(f"{spell['name']}! {healed}{suffix}")
    elif action == "item":
        item_id = payload.get("itemId")
        if not item_id or player.inventory.get(item_id, 0) <= 0:
            log.append("アイテムを もっていない!")
            session.turn = "enemy"
            return
        item = items.get(item_id)
        if not item:
            log.append("そのアイテムは つかえない!")
            session.turn = "enemy"
            return
        target = player if item["type"] != "revive" else player
        result = apply_item_effect(player, target, item, rng)
        player.inventory[item_id] -= 1
        log.append(result)
    elif action == "run":
        if attempt_run(player, enemy, rng):
            log.append("うまく にげだした!")
            session.ended = True
            session.turn = "end"
            return
        log.append("しかし にげきれなかった!")
    else:
        log.append("なにもしなかった...")

    if enemy.hp <= 0:
        session.ended = True
        session.turn = "end"
        log.append(f"{enemy.name}をたおした!")
    else:
        session.turn = "enemy"


