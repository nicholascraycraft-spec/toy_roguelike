import curses
from dataclasses import dataclass, field

import math
import random
import sys

from actors import HUMAN, GameOver, attack, move_actor, place_actor, resists, spawn, spawn_wanderer
from ai import take_turn
from dungeon import GOAL_DEPTH, MAP, generate, load, travel
from items import BELL_APPEARANCES, BELL_EFFECTS, BELLS, WAND_APPEARANCES, WAND_EFFECTS, WANDS, ItemKind, Wands, a, drop, identify, pick_up
from level import Level, beam_path, compute_fov, dig_path, passable
from render import draw, init_styles
from terrain import DOOR_CLOSED, DOOR_OPEN, FLOOR, STAIRS_DOWN, STAIRS_UP, WALL, close_door, open_door
from vec import Vec

class Messages:
    def __init__(self):
        self.pending: list[str] = []
        self.history: list[str] = []

    def add(self, text):
        self.pending.append(text)

    def drain(self):
        self.history.extend(self.pending)
        out, self.pending = self.pending, []
        return out

class Game:
    def __init__(self, rng, player):
        self.rng = rng
        self.player = player
        self.msgs = Messages()
        self.turn = 0
        self.levels: list[Level] = []
        self.depth = 0
        self.appearance: dict[ItemKind, str] = {}
        self.identified: set[ItemKind] = set()
    @property
    def level(self):
        return self.levels[self.depth]


# from nethack
MOVES = {
    ord('.'): Vec( 0,  0), ord('s'): Vec( 0,  0),
    # vi keys
    ord('h'): Vec(-1,  0), ord('l'): Vec( 1,  0),
    ord('k'): Vec( 0, -1), ord('j'): Vec( 0,  1),
    ord('y'): Vec(-1, -1), ord('u'): Vec( 1, -1),
    ord('b'): Vec(-1,  1), ord('n'): Vec( 1,  1),

    # numpad, as digits (numlock on)
    ord('4'): Vec(-1,  0), ord('6'): Vec( 1,  0),
    ord('8'): Vec( 0, -1), ord('2'): Vec( 0,  1),
    ord('7'): Vec(-1, -1), ord('9'): Vec( 1, -1),
    ord('1'): Vec(-1,  1), ord('3'): Vec( 1,  1),

    # arrows and numpad keypad codes (numlock off)
    curses.KEY_LEFT:  Vec(-1,  0), curses.KEY_RIGHT: Vec( 1,  0),
    curses.KEY_UP:    Vec( 0, -1), curses.KEY_DOWN:  Vec( 0,  1),
    curses.KEY_HOME:  Vec(-1, -1), curses.KEY_PPAGE: Vec( 1, -1),
    curses.KEY_END:   Vec(-1,  1), curses.KEY_NPAGE: Vec( 1,  1),
    curses.KEY_A1:    Vec(-1, -1), curses.KEY_A3:    Vec( 1, -1),
    curses.KEY_C1:    Vec(-1,  1), curses.KEY_C3:    Vec( 1,  1),
}



def ring_bell(game, actor, item):
    # TODO: ringing while confused should mis-sound the bell
    game.msgs.add(f"You ring {a(game, item)}.")
    effect = BELL_EFFECTS.get(item.kind)
    if effect is None:
        game.msgs.add("Nothing happens.")
        return
    effect(game, actor, item)
    identify(game, item.kind)

def do_digging(game, stdscr, actor, item, d):
    if d == Vec(0, 0):
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
        draw(stdscr, game, game.player, overlay={p: ("*", "item")})
        curses.napms(40)
        if game.level[p] is WALL:
            game.level[p] = FLOOR
            dug += 1
    game.msgs.add("You dig through the rock." if dug
                  else "The bolt bores into nothing.")
    if dug:
        identify(game, item.kind)

def zap_wand(game, stdscr, actor, item, d):
    if item.charges <= 0:
        game.msgs.add("You wrest nothing from it.")
        return
    item.charges -= 1
    game.msgs.add(f"You zap {a(game, item)}.")

    # exceptional code for wants that dont act on agents
    if item.kind is Wands.DIGGING:
        do_digging(game, stdscr, actor, item, d)
        return

    hit_anything = False
    for p in beam_path(game.level, actor.pos, d):
        draw(stdscr, game, game.player, overlay={p: ("*", "item")})
        curses.napms(40)
        target = game.level.actors.get(p)
        if target is None:
            continue
        hit_anything = True
        if not resists(game, target):
            WAND_EFFECTS[item.kind](game, actor, target)
            identify(game, item.kind)
        break

    if not hit_anything:
        game.msgs.add("The bolt fades.")

#region ACTIONS




def get_direction(stdscr, game):
    game.msgs.add("In what direction?")
    draw(stdscr, game, game.player)
    key = stdscr.getch()
    return MOVES.get(key)

def choose_item(stdscr, game, player, title):
    if not player.inventory:
        game.msgs.add("You aren't carrying anything.")
        return None
    return show_menu(stdscr, title,
                    [(a(game, it), it) for it in player.inventory])

def cmd_quit(stdscr, game, player):
    raise GameOver("quit")


def cmd_wait(stdscr, game, player):
    return lambda: None


def cmd_ascend(stdscr, game, player):
    if game.level[player.pos] is STAIRS_UP:
        return lambda: travel(game, -1)
    game.msgs.add("You can't go up here.")
    return None


def cmd_inventory(stdscr, game, player):
    if not player.inventory:
        game.msgs.add("You aren't carrying anything.")
        return None
    show_menu(stdscr, "Inventory:",
            [(a(game, it), it) for it in player.inventory])
    return None                      # looking is free


def cmd_drop(stdscr, game, player):
    item = choose_item(stdscr, game, player, "What do you want to drop?")
    if item is None:
        return None
    return lambda: drop(game, player, item)


def _door_cmd(stdscr, game, player, want, action, complaint):
    d = get_direction(stdscr, game)
    if d is None:
        return None
    p = player.pos + d
    if p in game.level.actors:
        game.msgs.add("There's a monster in the way.")
    elif game.level[p] is want:
        return lambda: action(game, p)
    else:
        game.msgs.add(complaint)
    return None


def cmd_open(stdscr, game, player):
    return _door_cmd(stdscr, game, player, DOOR_CLOSED, open_door,
                    "There's no closed door there.")


def cmd_close(stdscr, game, player):
    return _door_cmd(stdscr, game, player, DOOR_OPEN, close_door,
                    "There's no open door there.")


def cmd_move(stdscr, game, player, d):
    level = game.level
    dest = player.pos + d
    if target := level.actors.get(dest):
        return lambda: attack(game, player, target)
    if level[dest] is DOOR_CLOSED:
        return lambda: open_door(game, dest)
    if passable(level, dest):
        return lambda: move_actor(level, player, dest)
    game.msgs.add("There's a wall in the way.")
    return None

def cmd_pickup(stdscr, game, player):
    level = game.level
    stack = level.items.get(player.pos)
    if not stack:
        game.msgs.add("There's nothing here to pick up.")
        return None
    if len(stack) == 1:
        return lambda: pick_up(game, player)
    item = show_menu(stdscr, "Pick up what?",
                    [(a(game, it), it) for it in stack])
    return None if item is None else (lambda: pick_up(game, player, item))


def cmd_apply(stdscr, game, player):
    item = choose_item(stdscr, game, player, "What do you want to apply?")
    if item is None:
        return None
    if item.kind.use == "ring":
        return lambda: ring_bell(game, player, item)
    if item.kind.use == "zap":
        d = get_direction(stdscr, game)
        if d is None:
            return None
        return lambda: zap_wand(game, stdscr, player, item, d)
    game.msgs.add("You can't apply that.")
    return None


def cmd_descend(stdscr, game, player):
    if game.level[player.pos] is STAIRS_DOWN:
        return lambda: travel(game, +1)
    game.msgs.add("You can't go down here.")
    return None

def describe(game, p):
    level = game.level
    if p not in level:
        return "You can't see there."

    player = game.player
    visible = (
        {player.pos} if player.asleep > 0
        else compute_fov(level, player.pos)
    )
    parts = []

    if p in visible:
        terrain = level[p]
        stack = level.items.get(p, ())
        prefix = "You see "
        if actor := level.actors.get(p):
            parts.append(
                actor.name + (" (asleep)" if actor.asleep else "")
            )
    else:
        memory = level.remembered.get(p)
        if memory is None:
            return "You can't see there."
        terrain, stack = memory
        prefix = "You remember "

    parts.extend(a(game, item) for item in stack)
    parts.append(terrain.name)
    return prefix + ", ".join(parts) + "."
def cmd_look(stdscr, game, player):
    cursor = player.pos
    level = game.level
    while True:
        game.msgs.add(describe(game, cursor))
        draw(stdscr, game, player, overlay={cursor: ("X", "item")})
        key = stdscr.getch()
        if key in (27, ord(' '), ord('\n')):
            return None
        if d := MOVES.get(key):
            dest = cursor + d
            if dest in level:
                cursor = dest

def cmd_look_down(stdscr, game, player):
    game.msgs.add(describe(game, player.pos))
    return None

COMMANDS = {
    ord(','): cmd_pickup,
    ord('.'): cmd_wait,
    ord('>'): cmd_descend,
    ord('<'): cmd_ascend,
    ord('i'): cmd_inventory,
    ord('d'): cmd_drop,
    ord('a'): cmd_apply,
    ord('o'): cmd_open,
    ord('c'): cmd_close,
    ord('q'): cmd_quit,
    ord(';'): cmd_look,
    ord(':'): cmd_look_down,
}

def get_action(stdscr, game, player):
    key = stdscr.getch()
    if key == curses.KEY_RESIZE:
        return None
    if cmd := COMMANDS.get(key):
        return cmd(stdscr, game, player)
    if d := MOVES.get(key):
        return cmd_move(stdscr, game, player, d)
    game.msgs.add("Unknown command.")
    return None
# endregion

def show_menu(stdscr, title, entries):
    """entries: list of (label, value). Returns the chosen value, or None."""
    if not entries:
        return None

    letters = "abcdefghijklmnopqrstuvwxyz"
    page = 0

    while True:
        h, w = stdscr.getmaxyx()
        if h < 4 or w < 5:
            return None

        page_size = min(len(letters), h - 3)
        page_count = (len(entries) + page_size - 1) // page_size
        page = min(page, page_count - 1)

        start = page * page_size
        shown = entries[start:start + page_size]

        stdscr.erase()
        heading = f"{title} ({page + 1}/{page_count})"
        stdscr.addstr(0, 0, heading[:w - 1])

        for i, (label, _) in enumerate(shown):
            line = f"{letters[i]} - {label}"
            stdscr.addstr(i + 2, 2, line[:w - 3])

        footer = "a-z: select | </>: page | ESC/space: cancel"
        stdscr.addstr(h - 1, 0, footer[:w - 1])
        stdscr.refresh()

        key = stdscr.getch()

        if key in (27, ord(' ')):
            return None
        if key in (ord('>'), curses.KEY_NPAGE):
            page = min(page + 1, page_count - 1)
            continue
        if key in (ord('<'), curses.KEY_PPAGE):
            page = max(page - 1, 0)
            continue

        idx = letters.find(chr(key)) if 0 <= key < 256 else -1
        if 0 <= idx < len(shown):
            return shown[idx][1]

def shuffle_appearances(game, kinds, pool):
    chosen = game.rng.sample(pool, len(kinds))
    for kind, app in zip(kinds, chosen):
        game.appearance[kind] = app

def regenerate(game):
    p = game.player
    if p.hp >= p.max_hp:
        return
    interval = max(3, 20 - p.max_hp // 2)
    if game.turn % interval == 0:
        p.hp += 1

def main(stdscr, test_map=False):

    try:
        init_styles()
        seed = 0
        rng = random.Random(seed)
        # player = Actor(Vec(0, 0), "@", given_name="you", species=HUMAN)
        player = spawn(HUMAN, Vec(0, 0))
        player.given_name = "you"
        game = Game(rng, player)
        shuffle_appearances(game, BELLS, BELL_APPEARANCES)
        shuffle_appearances(game, WANDS, WAND_APPEARANCES)

        if test_map:                     # hand-made sandbox with every item
            s_level, start = load(MAP)
        else:
            s_level = generate(rng, 80, 21, depth=0)
            start = s_level.up_stair     # where you'll escape with the Book
        game.levels.append(s_level)
        place_actor(s_level, player, start)
        game.msgs.add(f"Find the Book of the Dead on level {GOAL_DEPTH + 1} "
                      "and carry it back up the stairs.")

        curses.curs_set(0)
        stdscr.keypad(True)
        # h, w = stdscr.getmaxyx()

        while True: 
            
            # player turns
            level = game.level
            player.energy += player.speed
            while player.energy >= 12:
                
                if player.asleep > 0 or player.frozen > 0:
                    if player.asleep > 0:
                        player.asleep -= 1
                        game.msgs.add("You are asleep.")
                    if player.frozen > 0:
                        player.frozen -=1
                        if not player.asleep:
                            game.msgs.add("You are frozen.")
                    player.energy -= 12
                    draw(stdscr, game, player)
                    curses.napms(120)
                    continue
                else:
                    draw(stdscr, game, player)
                    if action := get_action(stdscr, game, player):
                        action()
                        player.energy -= 12
                
            # everyone else's turn
            level = game.level # refresh for player changed floor case
            level.flows.clear()
            for actor in list(level.turn_order):
                if actor is player:
                    continue
                actor.energy += actor.speed
                while actor.energy >= 12:
                    actor.energy -= 12
                    take_turn(game, actor)

            # note how players and monsters can have +/- moves per turn
            game.turn += 1

            # # spawn new monsters
            if rng.randint(1, 60 - game.player.xp_level*2) == 1:
                spawn_wanderer(game)
            regenerate(game) #regen between turns


    except GameOver as e:
        if e.reason == "quit":
            return
        if e.reason == "won":
            game.msgs.add(f"You escape the dungeon with the Book of the Dead "
                          f"in {game.turn} turns!")
        else:
            game.msgs.add("You die...")
        draw(stdscr, game, player)
        stdscr.getch()


if __name__ == "__main__":
    curses.wrapper(main, test_map="--test" in sys.argv)