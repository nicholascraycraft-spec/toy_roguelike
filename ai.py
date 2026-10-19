from actors import attack, disturb, move_actor
from items import pick_up
from level import compute_fov, get_flow, step_downhill
from vec import chebyshev


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