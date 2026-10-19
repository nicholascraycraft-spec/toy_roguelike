
from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class Terrain:
    name: str
    glyph: str
    walkable: bool
    transparent: bool
    diggable: bool = True

FLOOR       = Terrain("floor", ".", True, True)
WALL        = Terrain("wall", "#", False, False)
DOOR_CLOSED = Terrain("closed door", "+", False, False)
DOOR_OPEN   = Terrain("open door", "'", True, True)
STAIRS_DOWN = Terrain("staircase down", ">", True, True, diggable=False)
STAIRS_UP   = Terrain("staircase up", "<", True, True, diggable=False)

def open_door(game, p):
    assert game.level[p] == DOOR_CLOSED
    game.level[p] = DOOR_OPEN
    game.msgs.add("You open the door.")

def close_door(game, p):
    assert game.level[p] == DOOR_OPEN
    game.level[p] = DOOR_CLOSED
    game.msgs.add("You close the door.")