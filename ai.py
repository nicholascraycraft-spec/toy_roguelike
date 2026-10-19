from actors import attack, disturb, move_actor
from items import Bells, Potions, Wands, pick_up, quaff, ring_bell, zap_wand
from level import beam_path, compute_fov, get_flow, step_downhill
from vec import Vec, chebyshev


def line_to(level, src, dest):
    """Direction for a beam from src that hits dest first, or None."""
    dx, dy = dest.x - src.x, dest.y - src.y
    if not (dx == 0 or dy == 0 or abs(dx) == abs(dy)) or (dx, dy) == (0, 0):
        return None
    d = Vec((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))
    for p in beam_path(level, src, d):
        if p == dest:
            return d
        if p in level.actors:
            return None                  # someone else is in the way
    return None


def use_item(game, actor):
    """Maybe drink, zap or ring something at the player. True if a turn was spent."""
    player, rng = game.player, game.rng
    pack = {it.kind: it for it in actor.inventory}
    hurt = actor.hp * 3 < actor.max_hp
    adjacent = chebyshev(actor.pos, player.pos) == 1

    for kind in (Potions.EXTRA_HEALING, Potions.HEALING):
        if hurt and kind in pack:
            quaff(game, actor, pack[kind])
            return True

    d = line_to(game.level, actor.pos, player.pos)
    if d is not None and rng.random() < 1/3:
        wanted = [Wands.STRIKING]
        if not player.asleep:
            wanted.append(Wands.SLEEPING)
        if player.speed_mod > -1:
            wanted.append(Wands.SLOW)
        if adjacent:
            wanted.append(Wands.REPULSION)
        if hurt:
            wanted.append(Wands.TELEPORT)    # get the player away from me
        # never death: an unanswerable instant kill isn't fun
        wands = [pack[k] for k in wanted if k in pack and pack[k].charges > 0]
        if wands:
            zap_wand(game, actor, rng.choice(wands), d)
            return True

    if Bells.KIBETH in pack and adjacent and hurt and rng.random() < 1/2:
        ring_bell(game, actor, pack[Bells.KIBETH])
        return True
    if Bells.SARANETH in pack and chebyshev(actor.pos, player.pos) <= 4 \
            and not player.frozen and rng.random() < 1/4:
        ring_bell(game, actor, pack[Bells.SARANETH])
        return True
    if Bells.MOSRAEL in pack and not adjacent and rng.random() < 1/8:
        ring_bell(game, actor, pack[Bells.MOSRAEL])
        return True
    # Ranna would sleep the ringer too; Astarael, Belgaer and Dyrim are no help
    return False


def take_turn(game, actor):
    player = game.player
    level = game.level

    # Player logic currently mirrors enemy logic
    # but lives in the main loop
    assert actor is not game.player


    if actor.asleep > 0 and chebyshev(actor.pos, player.pos) <= 2:
        if game.rng.random() < 0.3:
            disturb(game, actor)
    
    if actor.asleep > 0 or actor.frozen > 0:
        if actor.asleep > 0:
            actor.asleep -= 1
        if actor.frozen > 0:
            actor.frozen -= 1
        return
    if actor.species.hands and actor.pos in level.items:
        pick_up(game, actor)
        return
    # new code
    sees_player = player.pos in compute_fov(level, actor.pos)
    if sees_player:
        actor.target_pos = player.pos
    if sees_player and actor.species.hands and use_item(game, actor):
        return
    if sees_player and chebyshev(actor.pos, player.pos) == 1:
        attack(game, actor, player)
        return
    target = actor.target_pos
    if target is None:
        return
    if actor.pos == target:
        actor.target_pos = None
        return
    flow = get_flow(level, target)
    if step := step_downhill(game, actor, flow):
        move_actor(level, actor, step)