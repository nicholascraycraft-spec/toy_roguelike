# Toy Roguelike

A small NetHack-style roguelike for the terminal, written in plain Python
with `curses`.

Climb down to level 6, find the Book of the Dead, and carry it back out the
up staircase on the first floor. Picking up the Book wakes the dungeon, so
expect company on the way back.

## Running

```
python main.py              # a new random dungeon
python main.py --seed 1234  # replay a dungeon; the seed is shown when a run ends
python main.py --test       # hand-made sandbox with every bell, wand and potion
python tests.py             # run the tests
```

On Windows, `curses` isn't built in. Install it first:

```
pip install windows-curses
```

## Controls

Press `?` in the game for this list.

| Key | Action |
| --- | --- |
| `h j k l y u b n`, arrows, numpad | move (moving into a monster attacks it) |
| `.` | wait a turn |
| `<` `>` | go up / down stairs |
| `,` `d` | pick up / drop |
| `i` | inventory |
| `a` | use or apply a tool (ring a bell) |
| `z` | zap a wand, then choose a direction |
| `q` | quaff a potion |
| `o` `c` | open / close a door |
| `;` `:` | look around with a cursor / look here |
| `#pray` | ask the Charter for help; it won't answer if you ask too often |
| `#call` | nickname an unidentified kind of item ("murky potion called red stuff") |
| `#apply` `#quaff` `#zap` | same as `a`, `q`, `z` |
| `#?` | list extended commands (`#` takes any unique prefix, like `#p` or `#q`) |
| `?` | help |
| `Q` | quit |

## Items

Bells, wands and potions start under random appearances ("verdigris bell",
"oak wand", "murky potion") and are identified once their effect is seen.
The seven bells are the necromancer's bells from Garth Nix's Old Kingdom
books, and some are dangerous to ring. Being confused can make a bell sound
as the wrong one.

## Code layout

| File | What's in it |
| --- | --- |
| `main.py` | game loop and commands |
| `pray.py` | prayer: timeout, troubles, the Charter's moods |
| `actors.py` | monster species, combat, experience, message grammar |
| `items.py` | bells, wands, potions, their effects, and using them; the Book |
| `dungeon.py` | level generation (rooms and mazes), the sandbox map, stairs |
| `level.py` | the map grid, field of view, monster pathing |
| `ai.py` | monster turns |
| `render.py` | drawing the map, messages and status line |
| `terrain.py`, `vec.py` | terrain types, grid vectors and rectangles |
| `tests.py` | tests, run with `python tests.py` |
