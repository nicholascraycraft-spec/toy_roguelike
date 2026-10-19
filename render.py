import curses

from level import compute_fov
from vec import Vec


STYLES = {}

def init_styles():
    curses.start_color()
    curses.use_default_colors()
    for i, color in enumerate((curses.COLOR_WHITE, curses.COLOR_RED,
                               curses.COLOR_GREEN, curses.COLOR_BLUE,
                               curses.COLOR_YELLOW, curses.COLOR_CYAN), start=1):
        curses.init_pair(i, color, -1)
    STYLES.update({
        "none":    0,
        "wall":    curses.color_pair(1),
        "monster": curses.color_pair(2) | curses.A_BOLD,
        "item":    curses.color_pair(5),
        "lit":     curses.color_pair(3),
        "memory":  curses.color_pair(4),
    })


def camera(level, focus, w, h):
    x = max(0, min(focus.x - w // 2, level.w - w))
    y = max(0, min(focus.y - h // 2, level.h - h))
    return Vec(x, y)

MAP_TOP = 1

def draw(stdscr, game, player, overlay=None):
    h, w = stdscr.getmaxyx()
    level = game.level
    if h < 4 or w < 2:
        return
    visible = {player.pos} if player.asleep > 0 else compute_fov(level, player.pos)
    stdscr.erase()
    map_h = h - 2
    origin = camera(level, player.pos, w, map_h)
    for y, row in enumerate(paint(level, visible, w, map_h, origin)):
        for x, (ch, style) in enumerate(row):
            if y + MAP_TOP >= h - 1 or x >= w - 1:
                continue
            if overlay:
                p = Vec(origin.x + x, origin.y + y)
                if p in overlay:
                    ch, key = overlay[p]
                    style = STYLES[key]
            try:
                stdscr.addch(y + MAP_TOP, x, ch, style)
            except curses.error:
                pass
    show_messages(stdscr, game.msgs.drain(), w)
    show_status(stdscr, game, w)
    stdscr.refresh()


def show_messages(stdscr, msgs, w):
    if not msgs:
        stdscr.addstr(0, 0, " " * (w - 1))
        return
    line = ""
    for m in msgs:
        if line and len(line) + len(m) + 1 > w - 10:
            stdscr.addstr(0, 0, (line + "  --More--")[:w - 1].ljust(w - 1))
            stdscr.refresh()
            stdscr.getch()
            line = ""
        line = f"{line} {m}".strip()
    stdscr.addstr(0, 0, line[:w - 1].ljust(w - 1))

def show_status(stdscr, game, w):
    p = game.player
    line = (f"HP:{p.hp}({p.max_hp})  Dlvl:{game.depth + 1}  "
        f"Xp:{p.xp_level}/{p.xp}  T:{game.turn}"
        + ("  Conf" if p.confused else ""))
    h, _ = stdscr.getmaxyx()
    stdscr.addstr(h - 1, 0, line[:w - 1].ljust(w - 1))


def paint(level, visible, w, h, origin=Vec(0, 0)):
    buf = [[(" ", STYLES["none"])] * w for _ in range(h)]

    for sy in range(h):
        for sx in range(w):
            p = Vec(origin.x + sx, origin.y + sy)
            if p not in level:
                continue

            if p in visible:
                terrain = level[p]
                stack = list(level.items.get(p, ()))
                level.remembered[p] = (terrain, stack)
            else:
                memory = level.remembered.get(p)
                if memory is None:
                    continue
                terrain, stack = memory

            glyph, key = terrain.glyph, "lit"
            if stack:
                top = stack[-1]
                glyph, key = top.kind.glyph, top.kind.style_key

            if p in visible:
                if actor := level.actors.get(p):
                    glyph, key = actor.glyph, actor.species.style_key
            else:
                key = "memory"

            buf[sy][sx] = (glyph, STYLES[key])

    return buf