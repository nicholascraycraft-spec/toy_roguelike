import random
from level import *
import sys

def test_effects_preserve_indices():
    """No effect may leave actors and turn_order disagreeing."""
    for kind, effect in WAND_EFFECTS.items():
        lvl, start = load(MAP)
        game = Game(random.Random(0), Actor(Vec(0,0), "@", given_name="you", species=HUMAN))
        game.levels.append(lvl)
        place_actor(lvl, game.player, start)
        victim = next(a for a in lvl.turn_order if a is not game.player)
        try:
            effect(game, victim)
        except GameOver:
            pass
        for a in lvl.turn_order:
            assert lvl.actors[a.pos] is a, f"{kind.name}: index desync"
        assert len(lvl.actors) == len(lvl.turn_order), f"{kind.name}: count mismatch"

def test_generation(trials=50):
    for seed in range(trials):
        rng = random.Random(seed)
        lvl = gen_rooms_level(rng, 79, 21, depth=1)
        assert lvl.up_stair is not None, f"seed {seed}: no up stair"
        assert lvl.down_stair is not None, f"seed {seed}: no down stair"
        assert lvl.up_stair != lvl.down_stair, f"seed {seed}: stairs coincide"
        assert len(lvl.rooms) >= 2, f"seed {seed}: too few rooms"
        for a in lvl.turn_order:
            assert lvl.actors[a.pos] is a, f"seed {seed}: actor index desync"
    print(f"generation: {trials} seeds ok")

def test_beam_stops_at_walls():
    lvl, _ = load(MAP)
    path = beam_path(lvl, Vec(1, 1), Vec(1, 0))
    assert all(lvl[p].transparent for p in path)

def test_flow_field_distances():
    lvl, start = load(MAP)
    flow = flow_field(lvl, [start])
    assert flow[start] == 0
    assert all(flow[p] >= 0 for p in flow)

def test_beam_zero_direction():
    lvl, start = load(MAP)
    path = beam_path(lvl, start, Vec(0, 0))
    assert path == [start], f"zero direction produced {len(path)} cells"

def test_speed_clamps():
    rng = random.Random(0)
    player = Actor(Vec(0, 0), "@", given_name="you", species=HUMAN)
    game = Game(rng, player)
    a = Actor(Vec(0,0), "r", species=RAT)
    base = a.speed
    for _ in range(5):
        adjust_speed(game, a, -1, "", "")
    assert a.speed_mod == -1
    assert a.speed < base



if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    test_generation(n)
    test_beam_stops_at_walls()
    test_beam_zero_direction()
    test_flow_field_distances()
    test_speed_clamps()