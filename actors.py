
from dataclasses import dataclass, field
from level import compute_fov, free_cells, passable
from vec import Vec
#region SPECIES

@dataclass(frozen=True, slots=True)
class Species:
    name: str
    glyph: str
    style_key: str
    speed: int = 12
    max_hp: int = 8
    ac: int = 7
    attacks: tuple = ()
    level: int = 0
    freq: int = 4
    hands: bool = False
    earless: bool = False
    mr: int = 0

NEWT    = Species("newt",     ":", "monster", speed=6,  max_hp=2,  ac=8, level=0,
                  freq=5, attacks=(('bite', 1, 3),))
RAT     = Species("sewer rat","r", "monster", speed=12, max_hp=3,  ac=7, level=0,
                  freq=5, attacks=(('bite', 1, 3),))
JACKAL  = Species("jackal",   "d", "monster", speed=12, max_hp=4,  ac=7, level=0,
                  freq=3, attacks=(('bite', 1, 2),))
GRID_BUG= Species("grid bug", "x", "monster", speed=12, max_hp=2,  ac=9, level=0,
                  freq=3, attacks=(('bite', 1, 1),), earless=True)
LICHEN  = Species("lichen",   "F", "monster", speed=6,  max_hp=4,  ac=9, level=0,
                  freq=4, attacks=(('touch', 0, 0),), earless=True)

HUMAN   = Species("human",    "@", "monster", speed=12, max_hp=12, ac=7, level=0,
                  freq=0, attacks=(('hit', 1, 3),), hands=True)
# depth 0 — first floors
BAT      = Species("bat",          "B", "monster", speed=22, max_hp=3,  ac=8, level=0,
                   freq=4, attacks=(('bite', 1, 4),))
ACID_BLOB= Species("acid blob",    "b", "monster", speed=3,  max_hp=5,  ac=8, level=0,
                   freq=3, attacks=(('touch', 1, 4),), earless=True)
GARTER   = Species("garter snake", "S", "monster", speed=8,  max_hp=4,  ac=8, level=0,
                   freq=3, attacks=(('bite', 1, 2),))
SEWER_FLY= Species("sewer fly",    "F", "monster", speed=18, max_hp=2,  ac=9, level=0,
                   freq=3, attacks=(('bite', 1, 2),))

# depth 1
CAVE_SPIDER= Species("cave spider","s", "monster", speed=12, max_hp=5,  ac=3, level=1,
                   freq=4, attacks=(('bite', 1, 2),))
GIANT_ANT= Species("giant ant",    "a", "monster", speed=18, max_hp=8,  ac=3, level=1,
                   freq=3, attacks=(('bite', 1, 4),))
HILL_ORC = Species("hill orc",     "o", "monster", speed=9,  max_hp=10, ac=6, level=1,
                   freq=4, attacks=(('hit', 1, 6),), hands=True)
DWARF    = Species("dwarf",        "h", "monster", speed=6,  max_hp=9,  ac=6, level=1,
                   freq=3, attacks=(('hit', 1, 8),), hands=True, mr=10)
FLOATING_EYE=Species("floating eye","e","monster", speed=1,  max_hp=10, ac=9, level=1,
                   freq=3, attacks=(), earless=True, mr=10)
KOBOLD  = Species("kobold",   "k", "monster", speed=12,  max_hp=6,  ac=7, level=1,
                  freq=4, attacks=(('hit', 1, 4),), hands=True, mr=10)
GNOME   = Species("gnome",    "G", "monster", speed=12,  max_hp=8,  ac=5, level=1,
                  freq=3, attacks=(('hit', 1, 6),), hands=True, mr=10)

# depth 2
HOMUNCULUS=Species("homunculus",   "i", "monster", speed=12, max_hp=8,  ac=6, level=2,
                   freq=2, attacks=(('bite', 1, 3),), hands=True, mr=10)
ROTHE    = Species("rothe",        "q", "monster", speed=9,  max_hp=12, ac=7, level=2,
                   freq=3, attacks=(('butt', 1, 3), ('bite', 1, 8)))
BLUE_JELLY=Species("blue jelly",   "j", "monster", speed=1,  max_hp=14, ac=8, level=2,
                   freq=2, attacks=(('touch', 0, 0),), earless=True)
GIANT_BEETLE=Species("giant beetle","c","monster", speed=6,  max_hp=14, ac=4, level=2,
                   freq=3, attacks=(('bite', 3, 6),))

# depth 3
LEPRECHAUN=Species("leprechaun",   "l", "monster", speed=15, max_hp=10, ac=8, level=3,
                   freq=2, attacks=(('claw', 1, 2),), hands=True, mr=20)
YELLOW_LIGHT=Species("yellow light","y","monster", speed=15, max_hp=8,  ac=0, level=3,
                   freq=2, attacks=(), earless=True)
SOLDIER  = Species("soldier",      "u", "monster", speed=10, max_hp=16, ac=3, level=3,
                   freq=2, attacks=(('hit', 1, 8),), hands=True, mr=10)

# depth 4-6
OGRE     = Species("ogre",         "O", "monster", speed=10, max_hp=20, ac=5, level=4,
                   freq=3, attacks=(('hit', 2, 5),), hands=True)
CENTAUR  = Species("forest centaur","C","monster", speed=18, max_hp=18, ac=4, level=4,
                   freq=2, attacks=(('hit', 1, 6),), hands=True, mr=10)
ZOMBIE   = Species("ghoul",        "Z", "monster", speed=6,  max_hp=22, ac=4, level=5,
                   freq=3, attacks=(('claw', 1, 4), ('claw', 1, 4)), earless=True)
TROLL    = Species("troll",        "T", "monster", speed=12, max_hp=30, ac=4, level=6,
                   freq=2, attacks=(('hit', 4, 2), ('bite', 2, 6)), hands=True, mr=10)

MONSTERS = [NEWT, RAT, JACKAL, GRID_BUG, LICHEN, KOBOLD, GNOME,
            BAT, ACID_BLOB, GARTER, SEWER_FLY,
            CAVE_SPIDER, GIANT_ANT, HILL_ORC, DWARF, FLOATING_EYE,
            HOMUNCULUS, ROTHE, BLUE_JELLY, GIANT_BEETLE,
            LEPRECHAUN, YELLOW_LIGHT, SOLDIER,
            OGRE, CENTAUR, ZOMBIE, TROLL]
SPECIES_BY_GLYPH = {s.glyph: s for s in MONSTERS}
# endregion

def xp_value(species):
    return 1 + species.level * species.level + species.max_hp // 2

XP_THRESHOLDS = [0, 20, 40, 80, 160, 320, 640, 1280, 2560, 5120]

def gain_xp(game, actor, amount):
    before = actor.xp_level
    actor.xp += amount
    if actor.xp_level == before:
        return
    for _ in range(actor.xp_level - before):
        roll = game.rng.randint(1, 8)
        actor.hp_gained += roll
        actor.hp += roll
    if actor is game.player:
        game.msgs.add(f"Welcome to experience level {actor.xp_level}.")

@dataclass
class Actor:
    pos: Vec
    glyph: str
    given_name: str | None = None
    energy: int = 0
    species: Species = RAT
    # max_hp: int = 10
    hp: int = 10
    xp: int = 0
    hp_gained: int = 0
    inventory: list = field(default_factory=list)
    asleep: bool = 0
    frozen: bool = 0
    deafness: int = 0
    confused: int = 0
    speed_mod: int = 0

    @property
    def xp_level(self):
        n = 1
        for t in XP_THRESHOLDS:
            if self.xp >= t:
                n = XP_THRESHOLDS.index(t) + 1
        return n
    @property
    def max_hp(self):
        return self.species.max_hp + self.hp_gained
    @property
    def speed(self):
        return max(1, int(self.species.speed * (1 + self.speed_mod * 0.5)))
    @property
    def name(self):
        return self.given_name or self.species.name
    @property
    def deaf(self):
        return self.species.earless or self.deafness > 0
    
    # monster AI fields
    target_pos: Vec | None = None      # where I think the player is
    # target_age: int = 0                # turns since I actually saw them

class GameOver(Exception):
    def __init__(self, reason):
        self.reason = reason

def die(game, killer, target):
    level = game.level

    # drop inventory
    for item in target.inventory:
        level.items.setdefault(target.pos, []).append(item)
    target.inventory.clear()

    game.msgs.add(f"the {(target.name)} dies.")
    del level.actors[target.pos]
    level.turn_order.remove(target)
    if killer is not None and killer is not target:
        # killer.xp += xp_value(target.species)
        gain_xp(game, killer, xp_value(target.species))
    if target is game.player:
        # later in development we would make a bones file here.s
        raise GameOver("killed")

def resists(game, target):#, kind) # kind as in the damage_kind
    if game.rng.randint(1, 100) <= target.species.mr:
        game.msgs.add(f"The {target.name} resists!")
        return True
    return False


def to_hit(game, actor, target):
    """NetHack-style: lower AC is better, and stronger attackers hit more."""
    level = actor.xp_level if actor is game.player else actor.species.level
    return 10 + target.species.ac + level

def attack(game, actor, target):
    rng = game.rng
    for ak_name, dice, sides in actor.species.attacks:
        if rng.randint(1, 20) >= to_hit(game, actor, target):
            game.msgs.add(f"the {(actor.name)} misses the {(target.name)}.")
            continue
        dmg = sum(rng.randint(1, sides) for _ in range(dice))
        target.hp -= dmg
        disturb(game, target)
        game.msgs.add(f"the {(actor.name)} {(ak_name)}s the {(target.name)}.")
        if target.hp <= 0:
            die(game, actor, target)
            return


def spawn(species, pos):
    return Actor(pos, species.glyph, species=species, hp=species.max_hp)

def place_actor(level, actor, start):
    actor.pos = start
    level.actors[start] = actor
    level.turn_order.append(actor)

def spawn_at(level, species, pos):
    actor = spawn(species, pos)
    place_actor(level, actor, pos)
    return actor

def move_actor(level, actor, dest):
    # not responsible for ensuring ismovable()
    del level.actors[actor.pos]
    actor.pos = dest
    level.actors[dest] = actor

def pick_species(rng, depth):
    cap = depth + 1
    if rng.random() < 0.05:
        cap += rng.randint(1, 3)          # out-of-depth surprise
    pool = [s for s in MONSTERS if s.freq > 0 and s.level <= cap]
    return rng.choices(pool, weights=[s.freq for s in pool])[0]

def disturb(game, actor):
    """Wake a sleeping actor. Being frozen is separate and unaffected."""
    if actor.asleep > 0:
        actor.asleep = 0
        if actor is game.player:
            game.msgs.add("You wake up!")

def adjust_speed(game, target, delta, faster_msg, slower_msg):
    old = target.speed_mod
    target.speed_mod = max(-1, min(1, old + delta))
    if target.speed_mod == old:
        game.msgs.add("Nothing happens.")
        return
    game.msgs.add(faster_msg if delta > 0 else slower_msg)

def push_from(game, other, origin):
    """Shove `other` one step directly away from `origin`. Returns True if moved."""
    level = game.level
    d = Vec((other.pos.x > origin.x) - (other.pos.x < origin.x),
            (other.pos.y > origin.y) - (other.pos.y < origin.y))
    if d == Vec(0, 0):
        return False                      # standing on the ringer, nowhere to go
    dest = other.pos + d
    if not passable(level, dest):
        return False
    move_actor(level, other, dest)
    return True

def spawn_wanderer(game):
    level, rng = game.level, game.rng
    fov = compute_fov(level, game.player.pos)
    candidates = [p for p in free_cells(level) if p not in fov]
    if not candidates:
        return
    actor = spawn_at(level, pick_species(rng, game.depth), rng.choice(candidates))
    if game.book_taken:                  # the dungeon knows where you are
        actor.target_pos = game.player.pos