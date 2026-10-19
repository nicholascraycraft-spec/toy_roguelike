# claude's help implementing https://journal.stuffwithstuff.com/2014/12/21/rooms-and-mazes/
from collections import deque
from actors import KOBOLD, RAT, GameOver, pick_species, place_actor, spawn_at
from items import BELLS, BOOK, ITEMS, POTIONS, WANDS, Item
from level import Level
from terrain import DOOR_CLOSED, FLOOR, STAIRS_DOWN, STAIRS_UP, WALL
from vec import Rect, Vec

def odd(rng, lo, hi):
    """Random odd int in [lo, hi]."""
    return rng.randrange(lo | 1, hi + 1, 2)

def place_rooms(rng, level, regions, attempts=60):
    rooms = []
    for _ in range(attempts):
        rw, rh = odd(rng, 3, 9), odd(rng, 3, 7)
        rx = odd(rng, 1, level.w - rw - 2)
        ry = odd(rng, 1, level.h - rh - 2)
        new = Rect(rx, ry, rw, rh)
        if any(new.inflate(1).intersects(r) for r in rooms):
            continue
        region = len(rooms)
        for p in new.cells():
            level[p] = FLOOR
            regions[p] = region
        rooms.append(new)
    return rooms

def carve_mazes(rng, level, regions, next_id):
    for y in range(1, level.h - 1, 2):
        for x in range(1, level.w - 1, 2):
            p = Vec(x, y)
            if level[p] is WALL:
                grow_maze(rng, level, regions, p, next_id)
                next_id += 1
    return next_id

def find_connectors(level, regions):
    conns = {}
    for y in range(1, level.h - 1):
        for x in range(1, level.w - 1):
            p = Vec(x, y)
            if level[p] is not WALL:
                continue
            adj = {regions[n] for n in (p + Vec(0,-1), p + Vec(0,1),
                                        p + Vec(-1,0), p + Vec(1,0))
                if n in regions}
            if len(adj) == 2:
                conns[p] = frozenset(adj)
    return conns

def carve(level, regions, p, region):
    level[p] = FLOOR
    regions[p] = region

def grow_maze(rng, level, regions, start, region, wiggle=0.5):
    cells = [start]
    carve(level, regions, start, region)
    last_dir = None
    while cells:
        cell = cells[-1]
        opts = []
        for d in (Vec(0,-1), Vec(0,1), Vec(-1,0), Vec(1,0)):
            if can_carve(level, cell, d):
                opts.append(d)
        if opts:
            d = last_dir if (last_dir in opts and rng.random() > wiggle) \
                else rng.choice(opts)
            carve(level, regions, cell + d, region)
            carve(level, regions, cell + d + d, region)
            cells.append(cell + d + d)
            last_dir = d
        else:
            cells.pop()
            last_dir = None

def can_carve(level, p, d):
    """Can we carve two cells in direction d without breaking into open space?"""
    beyond = p + d + d + d
    if beyond not in level or beyond.x == 0 or beyond.y == 0 \
    or beyond.x == level.w - 1 or beyond.y == level.h - 1:
        return False
    return level[p + d + d] is WALL

def touches_open(level, p):
    return sum(1 for n in (p + Vec(0,-1), p + Vec(0,1), p + Vec(-1,0), p + Vec(1,0))
            if level[n] is not WALL) > 2

def prune_dead_ends(level):
    changed = True
    while changed:
        changed = False
        for y in range(1, level.h - 1):
            for x in range(1, level.w - 1):
                p = Vec(x, y)
                if level[p] is WALL:
                    continue
                exits = sum(1 for n in (p + Vec(0,-1), p + Vec(0,1),
                                        p + Vec(-1,0), p + Vec(1,0))
                            if level[n] is not WALL)
                if exits == 1:
                    level[p] = WALL
                    changed = True

def find(parent, r):
    while parent[r] != r:
        parent[r] = parent[parent[r]]
        r = parent[r]
    return r

def traversable(level, p):
    return level[p] is not WALL

def connected(level) -> bool:
    cells = {Vec(x, y) for y in range(level.h) for x in range(level.w)
            if traversable(level, Vec(x, y))}
    if not cells:
        return False
    start = next(iter(cells))
    seen = {start}
    q = deque([start])
    while q:
        p = q.popleft()
        for n in p.neighbors():
            if n in cells and n not in seen:
                seen.add(n)
                q.append(n)
    return len(seen) == len(cells)

def connect_regions(rng, level, conns, num_regions, extra=0.03):
    parent = list(range(num_regions))
    remaining = dict(conns)

    while remaining:
        p = rng.choice(list(remaining))
        a, b = (find(parent, r) for r in remaining[p])

        if a != b:
            level[p] = DOOR_CLOSED if rng.random() < 0.4 else FLOOR
            parent[b] = a
            del remaining[p]
        else:
            # already-merged: keep a few as loops, discard the rest
            if rng.random() < extra and not touches_open(level, p):
                level[p] = FLOOR
            del remaining[p]

def place_monsters(rng, level, depth, count=None):
    if count is None:
        count = rng.randint(3, 6) + depth // 2
    forbidden = {level.up_stair, level.down_stair}
    for _ in range(count):
        for _ in range(20):                      # attempts to find a free cell
            room = rng.choice(level.rooms)
            p = Vec(rng.randrange(room.x, room.x + room.w),
                    rng.randrange(room.y, room.y + room.h))
            if p in forbidden or p in level.actors:
                continue
            if not level[p].walkable:
                continue
            spawn_at(level, pick_species(rng, depth), p)
            if rng.random() < 0.6:
                level.actors[p].asleep = rng.randint(50, 200)
            break
def place_items(rng, level, depth, count=None):
    if count is None:
        count = rng.randint(2, 4)
    for _ in range(count):
        for _ in range(20):
            room = rng.choice(level.rooms)
            p = Vec(rng.randrange(room.x, room.x + room.w),
                    rng.randrange(room.y, room.y + room.h))
            if p in level.items or not level[p].walkable:
                continue
            kind = rng.choices(ITEMS, weights=[k.freq for k in ITEMS])[0]
            level.items[p] = [Item(kind)]
            break


GOAL_DEPTH = 5      # 0-based: the Book is on Dlvl GOAL_DEPTH + 1, which is also the bottom

def place_goal(rng, level):
    """Put the Book somewhere away from the up stairs."""
    rooms = [r for r in level.rooms
             if level.up_stair not in set(r.cells())] or level.rooms
    while True:
        room = rng.choice(rooms)
        p = Vec(rng.randrange(room.x, room.x + room.w),
                rng.randrange(room.y, room.y + room.h))
        if level[p] is FLOOR:
            level.items.setdefault(p, []).append(Item(BOOK))
            return p

def carrying_book(actor):
    return any(it.kind is BOOK for it in actor.inventory)

def gen_rooms_level(rng, w, h, depth):



    level = Level(w, h)
    regions: dict[Vec, int] = {}

    rooms = place_rooms(rng, level, regions)
    next_id = carve_mazes(rng, level, regions, len(rooms))
    conns = find_connectors(level, regions)
    connect_regions(rng, level, conns, next_id)
    prune_dead_ends(level)


    level.rooms = rooms
    up, down = rng.sample(rooms, 2)
    level.up_stair = up.center()
    level[level.up_stair] = STAIRS_UP
    if depth < GOAL_DEPTH:              # the Book's floor is the bottom
        level.down_stair = down.center()
        level[level.down_stair] = STAIRS_DOWN

    assert connected(level), "generator produced a disconnected level"
    place_monsters(rng, level, depth, count=None)
    place_items(rng, level, depth)
    if depth == GOAL_DEPTH:
        place_goal(rng, level)
    return level

def generate(rng, w, h, depth):
    new_level = None
    if True:
        new_level = gen_rooms_level(rng, w, h, depth)
    # else:
    #     new_level, _ = load(MAP2)
    return new_level

def travel(game, delta):
    level = game.level
    dest_depth = game.depth + delta
    if dest_depth < 0:
        if carrying_book(game.player):
            raise GameOver("won")
        game.msgs.add("You won't leave without the Book of the Dead.")
        return

    if dest_depth > GOAL_DEPTH:
        game.msgs.add("There is nothing below this floor.")
        return

    del level.actors[game.player.pos]
    level.turn_order.remove(game.player)

    first_visit = len(game.levels) <= dest_depth
    while len(game.levels) <= dest_depth:
        new_level = generate(game.rng, 80, 21, depth=len(game.levels))
        game.levels.append(new_level)

    game.depth = dest_depth
    new = game.level
    arrival = new.up_stair if delta > 0 else new.down_stair
    place_actor(new, game.player, arrival)
    game.msgs.add(f"You climb {'down' if delta > 0 else 'up'} the stairs.")
    if first_visit and dest_depth == GOAL_DEPTH:
        game.msgs.add("A cold stillness hangs here. The Book is near.")

MAP = """\
##############################
#........###./////////.......#
#.rrk....+...................#
#........###....@>...<.......#
#........###..)))))))........#
#.##########################.#
#.........!!!!!..............#
##############################"""
def load(text):
    rows = text.splitlines()
    assert len({len(r) for r in rows}) == 1, f"ragged map: {[len(r) for r in rows]}"
    level = Level(len(rows[0]), len(rows))
    player_start = None
    bell_index = 0
    wand_index = 0
    potion_index = 0
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            p = Vec(x, y)
            level[p] = {"#": WALL,
                        "+": DOOR_CLOSED,
                        ">": STAIRS_DOWN,
                        "<": STAIRS_UP
                        }.get(ch, FLOOR)
            if ch == "@":
                player_start = p
            elif ch == "r":
                spawn_at(level, RAT, p)
            elif ch == "k":
                spawn_at(level, KOBOLD, p)
            elif ch == ")":
                level.items[p] = [Item(BELLS[bell_index % len(BELLS)])]
                bell_index += 1
            elif ch == "/":
                level.items[p] = [Item(WANDS[wand_index % len(WANDS)])]
                wand_index += 1
            elif ch == "!":
                level.items[p] = [Item(POTIONS[potion_index % len(POTIONS)])]
                potion_index += 1
            elif ch == "<":
                level.up_stair = p
            elif ch == ">":
                level.down_stair = p
    return level, player_start
