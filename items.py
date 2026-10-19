from dataclasses import dataclass
from actors import adjust_speed, die, disturb, move_actor, push_from
from level import compute_fov, free_cells
from vec import Vec, chebyshev

def identify(game, kind):
    if kind in game.identified:
        return False
    game.identified.add(kind)
    return True
@dataclass(frozen=True, slots=True)
class ItemKind:
    name: str                    # true name: "bell of opening"
    glyph: str
    style_key: str
    weight: int = 10
    stackable: bool = False
    appearances: tuple = ()
    proper: bool = False
    use: str = ""

@dataclass
class Item:
    kind: ItemKind
    count: int = 1
    charges: int = 5
    # later: enchantment, identified, cursed

class Bells:
    RANNA    = ItemKind("Ranna the Sleeper",    "(", "item", weight=20, proper=True, use = "ring")
    MOSRAEL  = ItemKind("Mosrael the Waker",    "(", "item", weight=35, proper=True, use = "ring")
    KIBETH   = ItemKind("Kibeth the Walker",    "(", "item", weight=30, proper=True, use = "ring")
    DYRIM    = ItemKind("Dyrim the Speaker",    "(", "item", weight=35, proper=True, use = "ring")
    BELGAER  = ItemKind("Belgaer the Thinker",  "(", "item", weight=40, proper=True, use = "ring")
    SARANETH = ItemKind("Saraneth the Binder",  "(", "item", weight=45, proper=True, use = "ring")
    ASTARAEL = ItemKind("Astarael the Weeper",  "(", "item", weight=50, proper=True, use = "ring")
BELLS = [v for v in vars(Bells).values() if isinstance(v, ItemKind)]

BELL_APPEARANCES = [
    "shimmering bell", "tarnished bell",  "squat bell",
    "hairline-cracked bell", "verdigris bell", "bone-handled bell",
    "smooth grey bell"
    # "pitted iron bell",  "narrow silver bell",
    # "wide-mouthed bell", "blackened bell",
    # "leather-wrapped bell", "hollow bell",
]


#region BELLS
# grammar behavior
def a(game, item):
    name = item_name(game, item)
    if item.kind.proper and (item.kind in game.identified
                             or item.kind not in game.appearance):
        return name
    return f"{'an' if name[0] in 'aeiou' else 'a'} {name}"

def audience(game, actor, radius=None):
    """Everyone who can hear the bell, including the ringer. Hearing wakes you."""
    for other in list(game.level.turn_order):
        if other.deaf:
            continue
        if radius is not None and chebyshev(other.pos, actor.pos) > radius:
            continue
        disturb(game, other)
        yield other

def heard(game, actor, other):
    """Should the ringer be told what happened to this hearer?"""
    return other is not actor and other.pos in compute_fov(game.level, actor.pos)

def bell_ranna(game, actor, item):
    game.msgs.add("A sweet, sleepy tone rolls outward.")
    for other in audience(game, actor, radius=8):
        other.asleep = game.rng.randint(5, 15)
        if heard(game, actor, other):
            game.msgs.add(f"The {other.name} falls asleep.")

def bell_mosrael(game, actor, item):
    game.msgs.add("A jangling shriek claws at the walls.")
    for other in audience(game, actor):        # whole level; audience() woke them
        other.target_pos = actor.pos
        # other.target_age = -10                 # 15 turns of pursuit

def bell_kibeth(game, actor, item):
    game.msgs.add("The bell chimes, and feet obey it.")
    for other in audience(game, actor, radius=1):
        if other is actor:
            continue
        if push_from(game, other, actor.pos):
            other.frozen = 1                   # so they don't just step back
            if heard(game, actor, other):
                game.msgs.add(f"The {other.name} stumbles backward.")
        else:
            game.msgs.add(f"The {other.name} is driven against the wall.")

def bell_dyrim(game, actor, item):
    game.msgs.add("A clear, articulate note.")
    unknown = [it for it in actor.inventory
               if it.kind not in game.identified and it.kind in game.appearance]
    if not unknown:
        game.msgs.add("Nothing you carry has anything to say.")
        return
    target = game.rng.choice(unknown)
    identify(game, target.kind)
    game.msgs.add(f"It names itself: {item_name(game, target)}.")

def bell_belgaer(game, actor, item):
    game.msgs.add("The tone hangs, thoughtful, and does not fade.")
    level = game.level
    roll = game.rng.randint(1, 20)
    if roll >= 8:
        for y in range(level.h):
            for x in range(level.w):
                p = Vec(x, y)
                old_memory = level.remembered.get(p)
                remembered_items = old_memory[1] if old_memory is not None else []
                level.remembered[p] = (level[p], remembered_items)
        game.msgs.add("The shape of this place settles into your mind.")
        return

    if roll >= 3:
        game.msgs.add("The note wavers, and takes something with it.")
        level.remembered = {p: v for p, v in level.remembered.items()
                            if game.rng.random() >= 0.5}
        return
    game.msgs.add("Belgaer rings itself. You forget what you knew.")
    level.remembered.clear()
    forgettable = [k for k in game.identified if k in game.appearance]
    if forgettable:
        game.identified.discard(game.rng.choice(forgettable))
        game.msgs.add("A name goes out of you.")

def bell_saraneth(game, actor, item):
    game.msgs.add("A deep, commanding peal.")
    for other in audience(game, actor, radius=4):
        if other is actor:
            continue
        margin = game.rng.randint(1, 20) - other.species.level * 2
        if margin > 10:
            other.frozen = game.rng.randint(2, 5)
            game.msgs.add(f"The {other.name} is bound fast.")
        elif margin > 4:
            other.frozen = 1
            game.msgs.add(f"The {other.name} falters.")
        else:
            other.target_pos = actor.pos
            # other.target_age = -10
            game.msgs.add(f"The {other.name} shrugs off the command!")

def bell_astarael(game, actor, item):
    game.msgs.add("Astarael sounds, and everything that hears it must sleep.")
    for other in audience(game, actor, radius=2):
        if other is not actor:
            die(game, actor, other)

    # the ringer pays regardless — deafness only softens it
    if not actor.deaf:
        die(game, actor, actor)
        return
    actor.hp -= game.rng.randint(1, actor.max_hp)
    game.msgs.add("Even muffled, the note goes through you.")
    if actor.hp <= 0:
        die(game, actor, actor)

BELL_EFFECTS = {
    Bells.RANNA:    bell_ranna,
    Bells.MOSRAEL:  bell_mosrael,
    Bells.KIBETH:   bell_kibeth,
    Bells.DYRIM:    bell_dyrim,
    Bells.BELGAER:  bell_belgaer,
    Bells.SARANETH: bell_saraneth,
    Bells.ASTARAEL: bell_astarael,
}
# endregion

#region WANDS

def wand_repulsion(game, actor, target):
    if actor is target and actor is game.player:
        game.msgs.add("You feel a tug from every direction.")
        return
    if push_from(game, target, actor.pos):
        target.frozen = max(target.frozen, 1)
        game.msgs.add(f"The {target.name} is hurled backward!")
    else:
        game.msgs.add(f"The {target.name} shudders but holds position.")

def wand_sleep(game, actor, target):
    target.asleep = game.rng.randint(10, 25)
    target.frozen = 3
    game.msgs.add(f"The {target.name} falls asleep.")

def wand_death(game, actor, target):
    game.msgs.add(f"The {target.name} is struck by a bolt of death!")
    die(game, actor, target)

def wand_striking(game, actor, target):
    dmg = game.rng.randint(2, 12)
    target.hp -= dmg
    disturb(game, target)
    game.msgs.add(f"The {target.name} is hit by an invisible force!")
    if target.hp <= 0:
        die(game, actor, target)

def wand_slow(game, actor, target):
    adjust_speed(game, target, -1,
                 f"The {target.name} speeds up!",
                 f"The {target.name} slows down.")

def wand_speed(game, actor, target):
    adjust_speed(game, target, +1,
                 f"The {target.name} speeds up!",
                 f"The {target.name} slows down.")

def wand_teleport(game, actor, target):
    level = game.level
    candidates = free_cells(level)
    if not candidates:
        game.msgs.add("Nothing happens.")
        return
    dest = game.rng.choice(candidates)
    move_actor(level, target, dest)
    game.msgs.add(f"The {target.name} vanishes!")


def wand_nothing(game, actor, target):
    game.msgs.add("Nothing happens.")

class Wands:
    REPULSION = ItemKind("wand of repulsion",    "/", "item", weight=20, use="zap")
    SLEEPING  = ItemKind("wand of sleeping",      "/", "item", weight=20, use="zap")
    DEATH     = ItemKind("wand of death",         "/", "item", weight=20, use="zap")
    STRIKING  = ItemKind("wand of striking",      "/", "item", weight=20, use="zap")
    SLOW      = ItemKind("wand of slow monster",  "/", "item", weight=20, use="zap")
    SPEED     = ItemKind("wand of speed monster", "/", "item", weight=20, use="zap")
    TELEPORT  = ItemKind("wand of teleportation", "/", "item", weight=20, use="zap")
    NOTHING   = ItemKind("wand of nothing",       "/", "item", weight=20, use="zap")
    DIGGING   = ItemKind("wand of digging",       "/", "item", weight=20, use="zap")
WANDS = [v for v in vars(Wands).values() if isinstance(v, ItemKind)]

WAND_APPEARANCES = [
    "shimmering wand", "tarnished wand", "oak wand", "brass wand",
    "curved wand", "hexagonal wand", "spiked wand", "jeweled wand",
    "balsa wand", "pine wand", "plywood wand"
]

WAND_EFFECTS = {
    Wands.REPULSION: wand_repulsion,
    Wands.SLEEPING:  wand_sleep,
    Wands.DEATH:     wand_death,
    Wands.STRIKING:  wand_striking,
    Wands.SLOW:      wand_slow,
    Wands.SPEED:     wand_speed,
    Wands.TELEPORT:  wand_teleport,
    Wands.NOTHING:   wand_nothing,
    Wands.DIGGING:   None,            # handled in zap_wand; acts on the path
}
ITEMS = WANDS + BELLS
# endregion

#region GOAL
# not in ITEMS, so it never generates at random; placed once on GOAL_DEPTH
BOOK = ItemKind("the Book of the Dead", "?", "item", weight=50, proper=True)
# endregion

def item_name(game, item):
    if item.kind in game.identified or item.kind not in game.appearance:
        return item.kind.name
    return game.appearance[item.kind]


def pick_up(game, actor, item=None):
    level = game.level
    stack = level.items.get(actor.pos)
    if not stack:
        game.msgs.add("There's nothing here to pick up.")
        return
    if item is None:
        item = stack[-1]
    stack.remove(item)
    if not stack:
        del level.items[actor.pos]
    actor.inventory.append(item)
    if actor is game.player:
        game.msgs.add(f"You pick up {a(game, item)}.")
        if item.kind is BOOK and not game.book_taken:
            rouse_dungeon(game)
    else:
        game.msgs.add(f"The {actor.name} picks up {a(game, item)}.")

def rouse_dungeon(game):
    """Taking the Book wakes the floor and sets everything on the player's trail."""
    game.book_taken = True
    game.msgs.add("The Book's pages stir. Something in the dark wakes, and turns toward you.")
    for other in game.level.turn_order:
        if other is not game.player:
            disturb(game, other)
            other.target_pos = game.player.pos

def drop(game, actor, item):
    level = game.level
    actor.inventory.remove(item)
    level.items.setdefault(actor.pos, []).append(item)
    if actor is game.player:
        game.msgs.add(f"You drop {a(game, item)}.")
    else:
        game.msgs.add(f"The {actor.name} drops {a(game, item)}.")