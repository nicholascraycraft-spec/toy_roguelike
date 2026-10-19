from collections import deque
import math
from fractions import Fraction
from typing import TYPE_CHECKING

if TYPE_CHECKING:          # actors imports level, so only import for type hints
    from actors import Actor
from terrain import WALL
from vec import Vec

class Level:
    def __init__(self, w, h, fill=WALL):
        self.w, self.h = w, h
        self._terrain = [fill] * (w * h)
        self.remembered: dict[Vec, tuple] = {}
        self.items: dict[Vec, list] = {}
        self.actors: dict[Vec, "Actor"] = {}   # spatial index
        self.turn_order: list["Actor"] = []    # iteration order
        self.up_stair: Vec | None = None
        self.down_stair: Vec | None = None
        self.flows = {} # pos vecs to flows

    def __contains__(self, p): return 0 <= p.x < self.w and 0 <= p.y < self.h
    def __getitem__(self, p):  return self._terrain[p.y * self.w + p.x]
    def __setitem__(self, p, t): self._terrain[p.y * self.w + p.x] = t


def passable(level, p):
    return p in level and level[p].walkable and p not in level.actors

def free_cells(level):
    return [Vec(x, y) for y in range(level.h) for x in range(level.w)
            if level[Vec(x, y)].walkable and Vec(x, y) not in level.actors]

def get_flow(level, target_pos):
    if target_pos not in level.flows:
        level.flows[target_pos] = flow_field(level, [target_pos])
    return level.flows[target_pos]

# dijkstra map for flowing towards the player
def flow_field(level, sources):
    dist = {s: 0 for s in sources}
    q = deque(sources)
    while q:
        p = q.popleft()
        for n in p.neighbors():
            if n not in dist and n in level and level[n].walkable:
                dist[n] = dist[p] + 1
                q.append(n)
    return dist


def step_downhill(game, actor, dist):
    level = game.level
    here = dist.get(actor.pos)
    if here is None:
        return None
    options = [
        p for p in actor.pos.neighbors()
        if p in dist
        and dist[p] < here
        and p not in level.actors
    ]
    if not options:
        return None
    best = min(dist[p] for p in options)
    return game.rng.choice([p for p in options if dist[p] == best])

# https://www.albertford.com/shadowcasting/
def compute_fov(level, origin):
    visible = {origin}
    def mark_visible(vec):
        visible.add(vec)
    def is_blocking(vec):
        return vec not in level or not level[vec].transparent
    class Quadrant:
        north = 0
        east = 1
        south = 2
        west = 3

        def __init__(self, cardinal, origin):
            self.cardinal = cardinal
            self.ox, self.oy = origin

        def transform(self, tile):
            row, col = tile
            if self.cardinal == self.north:
                return (self.ox + col, self.oy - row)
            if self.cardinal == self.south:
                return (self.ox + col, self.oy + row)
            if self.cardinal == self.east:
                return (self.ox + row, self.oy + col)
            if self.cardinal == self.west:
                return (self.ox - row, self.oy + col)
    
    def is_symmetric(row, tile):
        row_depth, col = tile
        return (col >= row.depth * row.start_slope
            and col <= row.depth * row.end_slope)        
    def round_ties_up(n):
        return math.floor(n + 0.5)

    def round_ties_down(n):
        return math.ceil(n - 0.5)    
    
    class Row:
        def __init__(self, depth, start_slope, end_slope):
            self.depth = depth
            self.start_slope = start_slope
            self.end_slope = end_slope

        def tiles (self):
            min_col = round_ties_up(self.depth * self.start_slope)
            max_col = round_ties_down(self.depth * self.end_slope)
            for col in range(min_col, max_col + 1):
                yield (self.depth, col)
        def next(self):
            return Row(
                self.depth + 1,
                self.start_slope,
                self.end_slope)
    def slope(tile):
        row_depth, col = tile
        return Fraction(2 * col - 1, 2 * row_depth)
    

    for i in range(4):
        quadrant = Quadrant(i, origin)


        def reveal(tile):
            x, y = quadrant.transform(tile)
            mark_visible(Vec(x, y))

        def is_wall(tile):
            if tile is None:
                return False
            x, y = quadrant.transform(tile)
            return is_blocking(Vec(x, y))
        
        def is_floor(tile):
            if tile is None:
                return False
            x, y = quadrant.transform(tile)
            return not is_blocking(Vec(x, y))
        
        def scan(row):
            prev_tile = None
            for tile in row.tiles():
                if is_wall(tile) or is_symmetric(row, tile):
                    reveal(tile)
                if is_wall(prev_tile) and is_floor(tile):
                    row.start_slope = slope(tile)
                if is_floor(prev_tile) and is_wall(tile):
                    next_row = row.next()
                    next_row.end_slope = slope(tile)
                    scan(next_row)
                prev_tile = tile
            if is_floor(prev_tile):
                scan(row.next())

        first_row = Row(1, Fraction(-1), Fraction(1))
        scan(first_row)
    return visible

def beam_path(level, origin, d, max_range=13):
    """Cells a beam passes through, stopping at the first wall or actor."""
    path = []
    p = origin
    if d == Vec(0,0):
        return [origin]
    for _ in range(max_range):
        p = p + d
        if p not in level or not level[p].transparent:
            break
        path.append(p)
        # if p in level.actors:
        #     break
    return path


def dig_path(level, origin, d, max_range=8):
    """Cells a digging beam bores through, ignoring what's solid."""
    if d == Vec(0, 0):
        return []
    path, p = [], origin
    for _ in range(max_range):
        p = p + d
        if p not in level:
            break
        if p.x in (0, level.w - 1) or p.y in (0, level.h - 1):
            break                      # never breach the outer shell
        path.append(p)
    return path

# testing main for room layout
def dump(level) -> str:
    return "\n".join(
        "".join(level[Vec(x, y)].glyph for x in range(level.w))
        for y in range(level.h)
    )

