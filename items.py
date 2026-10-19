from dataclasses import dataclass
from actors import The, adjust_speed, die, disturb, move_actor, push_from, resists, verb
from level import beam_path, compute_fov, dig_path, free_cells
from terrain import FLOOR, WALL
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
    freq: int = 1                # relative chance of generating

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
            game.msgs.add(f"{The(game, other)} {verb(game, other, 'fall')} asleep.")

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
                game.msgs.add(f"{The(game, other)} {verb(game, other, 'stumble')} backward.")
        else:
            game.msgs.add(f"{The(game, other)} {verb(game, other, 'be')} driven against the wall.")

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
            game.msgs.add(f"{The(game, other)} {verb(game, other, 'be')} bound fast.")
        elif margin > 4:
            other.frozen = 1
            game.msgs.add(f"{The(game, other)} {verb(game, other, 'falter')}.")
        else:
            other.target_pos = actor.pos
            # other.target_age = -10
            game.msgs.add(f"{The(game, other)} {verb(game, other, 'shrug')} off the command!")

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
        game.msgs.add(f"{The(game, target)} {verb(game, target, 'be')} hurled backward!")
    else:
        game.msgs.add(f"{The(game, target)} {verb(game, target, 'shudder')} but "
                      f"{verb(game, target, 'hold')} position.")

def wand_sleep(game, actor, target):
    target.asleep = game.rng.randint(10, 25)
    target.frozen = 3
    game.msgs.add(f"{The(game, target)} {verb(game, target, 'fall')} asleep.")

def wand_death(game, actor, target):
    game.msgs.add(f"{The(game, target)} {verb(game, target, 'be')} struck by a bolt of death!")
    die(game, actor, target)

def wand_striking(game, actor, target):
    dmg = game.rng.randint(2, 12)
    target.hp -= dmg
    disturb(game, target)
    game.msgs.add(f"{The(game, target)} {verb(game, target, 'be')} hit by an invisible force!")
    if target.hp <= 0:
        die(game, actor, target)

def wand_slow(game, actor, target):
    adjust_speed(game, target, -1,
                 f"{The(game, target)} {verb(game, target, 'speed')} up!",
                 f"{The(game, target)} {verb(game, target, 'slow')} down.")

def wand_speed(game, actor, target):
    adjust_speed(game, target, +1,
                 f"{The(game, target)} {verb(game, target, 'speed')} up!",
                 f"{The(game, target)} {verb(game, target, 'slow')} down.")

def wand_teleport(game, actor, target):
    level = game.level
    candidates = free_cells(level)
    if not candidates:
        game.msgs.add("Nothing happens.")
        return
    dest = game.rng.choice(candidates)
    move_actor(level, target, dest)
    game.msgs.add(f"{The(game, target)} {verb(game, target, 'vanish')}!")


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
# endregion

#region POTIONS

def heal(actor, amount, max_bonus):
    """Restore HP; overflow past full raises max HP a little."""
    if actor.hp + amount > actor.max_hp:
        actor.hp_gained += max_bonus
    actor.hp = min(actor.max_hp, actor.hp + amount)

def potion_healing(game, actor, item):
    heal(actor, sum(game.rng.randint(1, 4) for _ in range(6)), 1)
    say(game, actor, "You feel better." if actor is game.player
        else f"{The(game, actor)} looks better.")

def potion_extra_healing(game, actor, item):
    heal(actor, sum(game.rng.randint(1, 8) for _ in range(6)), 2)
    say(game, actor, "You feel much better." if actor is game.player
        else f"{The(game, actor)} looks much better.")

def potion_sleeping(game, actor, item):
    actor.asleep = game.rng.randint(5, 15)
    say(game, actor, f"{The(game, actor)} suddenly {verb(game, actor, 'fall')} asleep.")

def potion_confusion(game, actor, item):
    actor.confused += game.rng.randint(10, 20)
    say(game, actor, "Huh, what? Where am I?" if actor is game.player
        else f"{The(game, actor)} looks confused.")

def potion_water(game, actor, item):
    if actor is game.player:
        game.msgs.add("This tastes like water.")

class Potions:
    HEALING       = ItemKind("potion of healing",       "!", "item", freq=4, use="quaff")
    EXTRA_HEALING = ItemKind("potion of extra healing", "!", "item", freq=2, use="quaff")
    SLEEPING      = ItemKind("potion of sleeping",      "!", "item", use="quaff")
    CONFUSION     = ItemKind("potion of confusion",     "!", "item", use="quaff")
    WATER         = ItemKind("potion of water",         "!", "item", use="quaff")
POTIONS = [v for v in vars(Potions).values() if isinstance(v, ItemKind)]

POTION_APPEARANCES = [
    "murky potion", "fizzing potion", "milky potion", "smoky potion",
    "cloudy potion", "bubbly potion", "oily potion", "ruby potion",
]

POTION_EFFECTS = {
    Potions.HEALING:       potion_healing,
    Potions.EXTRA_HEALING: potion_extra_healing,
    Potions.SLEEPING:      potion_sleeping,
    Potions.CONFUSION:     potion_confusion,
    Potions.WATER:         potion_water,
}

ITEMS = WANDS + BELLS + POTIONS
# endregion

#region GOAL
# not in ITEMS, so it never generates at random; placed once on GOAL_DEPTH
BOOK = ItemKind("the Book of the Dead", "?", "item", weight=50, proper=True)
# endregion

#region USING ITEMS
# Shared by the player's commands and monster AI, so messages are written for
# any actor and only show when the player can see who's acting.

def seen(game, actor):
    player = game.player
    if actor is player:
        return True
    return player.asleep <= 0 and actor.pos in compute_fov(game.level, player.pos)

def say(game, actor, text):
    if seen(game, actor):
        game.msgs.add(text)

def learn(game, actor, kind):
    """You only learn what an item is by watching it used."""
    if seen(game, actor):
        identify(game, kind)

def possessive(game, actor):
    return "Your" if actor is game.player else f"{The(game, actor)}'s"

def ring_bell(game, actor, item):
    say(game, actor, f"{The(game, actor)} {verb(game, actor, 'ring')} {a(game, item)}.")
    kind = item.kind
    if actor.confused and game.rng.random() < 0.5:
        kind = game.rng.choice(BELLS)       # a fumbled stroke sounds another bell
        say(game, actor, f"{possessive(game, actor)} hand slips, and the bell speaks wrongly.")
    effect = BELL_EFFECTS.get(kind)
    if effect is None:
        game.msgs.add("Nothing happens.")
        return
    effect(game, actor, item)
    if kind is item.kind:
        learn(game, actor, item.kind)

def quaff(game, actor, item):
    actor.inventory.remove(item)
    say(game, actor, f"{The(game, actor)} {verb(game, actor, 'drink')} {a(game, item)}.")
    POTION_EFFECTS[item.kind](game, actor, item)
    learn(game, actor, item.kind)

def do_digging(game, actor, item, d):
    from dungeon import GOAL_DEPTH, travel   # dungeon imports items
    if d == Vec(0, 0):
        if actor is not game.player:
            return                          # only the player falls through holes
        if game.depth >= GOAL_DEPTH:
            game.msgs.add("The bolt glances off the bedrock.")
            return
        game.msgs.add("You dig a hole in the floor.")
        identify(game, item.kind)
        travel(game, +1)
        game.level.flows.clear()
        return

    dug = 0
    for p in dig_path(game.level, actor.pos, d):
        game.animate(p)
        if game.level[p] is WALL:
            game.level[p] = FLOOR
            dug += 1
    if dug:
        game.level.flows.clear()
    say(game, actor, "The bolt digs through the rock." if dug
        else "The bolt bores into nothing.")
    if dug:
        learn(game, actor, item.kind)

def zap_wand(game, actor, item, d):
    if item.charges <= 0:
        say(game, actor, "You wrest nothing from it." if actor is game.player
            else f"{The(game, actor)} shakes {a(game, item)}, but nothing comes out.")
        return
    item.charges -= 1
    say(game, actor, f"{The(game, actor)} {verb(game, actor, 'zap')} {a(game, item)}.")

    # digging acts on terrain, not on whoever the beam hits
    if item.kind is Wands.DIGGING:
        do_digging(game, actor, item, d)
        return

    hit_anything = False
    for p in beam_path(game.level, actor.pos, d):
        game.animate(p)
        target = game.level.actors.get(p)
        if target is None:
            continue
        hit_anything = True
        if not resists(game, target):
            WAND_EFFECTS[item.kind](game, actor, target)
            learn(game, actor, item.kind)
        break

    if not hit_anything:
        say(game, actor, "The bolt fades.")
# endregion

def item_name(game, item):
    if item.kind in game.identified or item.kind not in game.appearance:
        return item.kind.name
    name = game.appearance[item.kind]
    if called := game.called.get(item.kind):
        name += f" called {called}"
    return name


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