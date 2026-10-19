import random
import sys

from actors import (GIANT_ANT, HUMAN, NEWT, RAT, Actor, GameOver, adjust_speed,
                    The, place_actor, spawn, the, to_hit, verb)
from dungeon import GOAL_DEPTH, MAP, gen_rooms_level, generate, load, travel
from items import BOOK, POTION_EFFECTS, WAND_EFFECTS, Item, Potions, pick_up
from level import beam_path, flow_field
from main import Game, quaff
from terrain import STAIRS_DOWN, STAIRS_UP
from vec import Vec

def test_effects_preserve_indices():
    """No effect may leave actors and turn_order disagreeing."""
    for kind, effect in WAND_EFFECTS.items():
        if effect is None:               # digging acts on terrain, not actors
            continue
        lvl, start = load(MAP)
        game = Game(random.Random(0), Actor(Vec(0,0), "@", given_name="you", species=HUMAN))
        game.levels.append(lvl)
        place_actor(lvl, game.player, start)
        victim = next(a for a in lvl.turn_order if a is not game.player)
        try:
            effect(game, game.player, victim)
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



def test_goal_placed_once(trials=20):
    for seed in range(trials):
        lvl = gen_rooms_level(random.Random(seed), 80, 21, depth=GOAL_DEPTH)
        books = [it for stack in lvl.items.values() for it in stack
                 if it.kind is BOOK]
        assert len(books) == 1, f"seed {seed}: {len(books)} books"
        shallow = gen_rooms_level(random.Random(seed), 80, 21, depth=1)
        assert not any(it.kind is BOOK for stack in shallow.items.values()
                       for it in stack), f"seed {seed}: book on wrong floor"

def test_goal_floor_is_bottom(trials=20):
    for seed in range(trials):
        lvl = gen_rooms_level(random.Random(seed), 80, 21, depth=GOAL_DEPTH)
        assert lvl.down_stair is None, f"seed {seed}: stairs below the Book"
        assert not any(lvl[Vec(x, y)] is STAIRS_DOWN
                       for y in range(lvl.h) for x in range(lvl.w))

def test_first_floor_has_exit(trials=20):
    for seed in range(trials):
        lvl = generate(random.Random(seed), 80, 21, depth=0)
        assert lvl[lvl.up_stair] is STAIRS_UP, f"seed {seed}: no way out"
        assert lvl.up_stair not in lvl.actors, f"seed {seed}: start occupied"

def test_lower_ac_is_harder_to_hit():
    game = Game(random.Random(0), spawn(HUMAN, Vec(0, 0)))
    rat = spawn(RAT, Vec(1, 0))
    newt, ant = spawn(NEWT, Vec(2, 0)), spawn(GIANT_ANT, Vec(3, 0))
    assert to_hit(game, game.player, ant) < to_hit(game, game.player, newt)
    assert to_hit(game, rat, ant) < to_hit(game, rat, newt)

def test_book_rouses_floor():
    lvl, start = load(MAP)
    game = Game(random.Random(0), spawn(HUMAN, Vec(0, 0)))
    game.levels.append(lvl)
    place_actor(lvl, game.player, start)
    monsters = [m for m in lvl.turn_order if m is not game.player]
    for m in monsters:
        m.asleep = 100
    lvl.items[start] = [Item(BOOK)]
    pick_up(game, game.player)
    assert game.book_taken
    for m in monsters:
        assert not m.asleep and m.target_pos == start, f"{m.name} didn't wake"

def test_potions():
    game = Game(random.Random(0), spawn(HUMAN, Vec(0, 0)))
    p = game.player
    for kind in POTION_EFFECTS:          # every potion drinks without error
        p.inventory.append(Item(kind))
        quaff(game, p, p.inventory[-1])
        assert kind in game.identified and not p.inventory
    p.hp = 1
    p.inventory.append(Item(Potions.HEALING))
    quaff(game, p, p.inventory[0])
    assert p.hp > 1
    full = p.max_hp
    p.hp = full
    p.inventory.append(Item(Potions.HEALING))
    quaff(game, p, p.inventory[0])
    assert p.max_hp == full + 1 and p.hp == p.max_hp
    assert p.confused > 0               # from the confusion potion above

def test_messages_use_you():
    game = Game(random.Random(0), spawn(HUMAN, Vec(0, 0)))
    game.player.given_name = "you"
    kobold = spawn(RAT, Vec(1, 0))
    assert f"{The(game, game.player)} {verb(game, game.player, 'hit')} {the(game, kobold)}" \
        == "You hit the sewer rat"
    assert f"{The(game, kobold)} {verb(game, kobold, 'touch')} {the(game, game.player)}" \
        == "The sewer rat touches you"
    assert verb(game, game.player, "be") == "are" and verb(game, kobold, "be") == "is"

def test_escape_needs_book():
    lvl, start = load(MAP)
    game = Game(random.Random(0), Actor(Vec(0,0), "@", given_name="you", species=HUMAN))
    game.levels.append(lvl)
    place_actor(lvl, game.player, start)
    travel(game, -1)                     # no book: refused, still here
    assert game.depth == 0 and lvl.actors[start] is game.player
    game.player.inventory.append(Item(BOOK))
    try:
        travel(game, -1)
    except GameOver as e:
        assert e.reason == "won"
    else:
        assert False, "escaping with the book should win"


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    test_effects_preserve_indices()
    test_generation(n)
    test_beam_stops_at_walls()
    test_beam_zero_direction()
    test_flow_field_distances()
    test_speed_clamps()
    test_goal_placed_once()
    test_escape_needs_book()
    test_goal_floor_is_bottom()
    test_first_floor_has_exit()
    test_lower_ac_is_harder_to_hit()
    test_book_rouses_floor()
    test_potions()
    test_messages_use_you()
    print("all tests ok")