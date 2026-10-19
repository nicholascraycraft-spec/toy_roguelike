from level import Rect
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
            
# claude's help implementing https://journal.stuffwithstuff.com/2014/12/21/rooms-and-mazes/
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
    level.down_stair = down.center()
    level[level.up_stair] = STAIRS_UP
    level[level.down_stair] = STAIRS_DOWN

    assert connected(level), "generator produced a disconnected level"
    return level