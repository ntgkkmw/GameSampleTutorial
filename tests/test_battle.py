import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.backend.models.domain import (
    Combatant,
    CoreStats,
    attempt_run,
    physical_damage,
    spell_damage,
)


class StaticRNG:
    """Deterministic RNG used to control combat rolls in tests."""

    def __init__(self, random_values=None, int_values=None):
        self.random_values = list(random_values or [])
        self.int_values = list(int_values or [])

    def random(self):
        if not self.random_values:
            return 0.0
        return self.random_values.pop(0)

    def randint(self, a, b):
        if not self.int_values:
            return a
        return self.int_values.pop(0)


def build_combatant(name: str, atk: int, defense: int, mag: int, agi: int, hp: int = 24, mp: int = 6) -> Combatant:
    stats = CoreStats(atk=atk, defense=defense, mag=mag, agi=agi)
    return Combatant(
        id=name,
        name=name,
        level=1,
        max_hp=hp,
        max_mp=mp,
        hp=hp,
        mp=mp,
        stats=stats,
        exp=0,
        gold=0,
        inventory={},
        spells=[],
        next_exp=10,
    )


def test_physical_damage_is_at_least_one():
    attacker = build_combatant("hero", 5, 3, 4, 5)
    defender = build_combatant("slime", 2, 2, 1, 2, hp=15)
    rng = StaticRNG(random_values=[0.99, 0.99], int_values=[-1, 1])
    damage, crit, miss = physical_damage(attacker, defender, rng)
    assert not miss
    assert damage >= 1


def test_critical_ignores_defense_reduction():
    attacker = build_combatant("hero", 6, 3, 4, 6)
    defender = build_combatant("tank", 2, 30, 1, 2, hp=40)
    normal_rng = StaticRNG(random_values=[0.99, 0.99], int_values=[-1])
    normal_damage, crit, miss = physical_damage(attacker, defender, normal_rng)
    assert not miss
    assert not crit
    crit_rng = StaticRNG(random_values=[0.0], int_values=[-1, 2])
    crit_damage, is_crit, _ = physical_damage(attacker, defender, crit_rng, force_crit=True)
    assert is_crit
    assert crit_damage > normal_damage


def test_run_chance_clamped_range():
    player = build_combatant("hero", 5, 3, 4, 20)
    enemy = build_combatant("fast", 4, 4, 2, 1)
    chance_high = 0.4 + (player.stats.agi - enemy.stats.agi) * 0.05
    assert 0.2 <= max(0.2, min(chance_high, 0.9)) <= 0.9
    player_slow = build_combatant("slow", 5, 3, 4, 1)
    enemy_fast = build_combatant("quick", 4, 4, 2, 15)
    chance_low = 0.4 + (player_slow.stats.agi - enemy_fast.stats.agi) * 0.05
    assert 0.2 <= max(0.2, min(chance_low, 0.9)) <= 0.9


def test_heal_does_not_exceed_max_hp():
    caster = build_combatant("hero", 5, 3, 6, 6)
    caster.hp = 20
    spell = {"type": "heal", "power": "12-16", "scale": "MAG*0.5"}
    rng = random.Random(1)
    healed, _ = spell_damage(caster, caster, spell, rng)
    caster.hp = min(caster.max_hp, caster.hp + healed)
    assert caster.hp <= caster.max_hp


def test_boss_run_always_fails():
    player = build_combatant("hero", 5, 3, 4, 10)
    boss = build_combatant("boss", 10, 8, 6, 8, hp=120)
    boss.is_boss = True
    rng = StaticRNG(random_values=[0.0])
    assert not attempt_run(player, boss, rng)
