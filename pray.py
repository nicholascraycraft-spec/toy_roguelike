from actors import die

# Prayer, after NetHack: the Charter fixes your troubles if you haven't asked
# too recently. The timeout is hidden; praying too soon displeases, and
# praying too soon again while displeased brings down its anger.

GOD = "the Charter"
START_TIMEOUT = 300

def tick(game):
    """Once per turn: the timeout runs down, and with it the god's mood."""
    if game.prayer_timeout > 0:
        game.prayer_timeout -= 1
        if game.prayer_timeout == 0:
            game.god_angry = game.god_displeased = False

def major_trouble(player):
    return player.hp <= 5 or player.hp * 7 <= player.max_hp

def minor_trouble(player):
    return player.confused > 0

def new_timeout(rng):
    """Usually around 350, occasionally far shorter or longer."""
    return max(50, min(1000, int(rng.lognormvariate(5.86, 0.5))))

def pray(game):
    player, rng, msgs = game.player, game.rng, game.msgs
    msgs.add(f"You begin praying to {GOD}.")
    major, minor = major_trouble(player), minor_trouble(player)

    if game.god_angry:
        smite(game)
        return
    if major:
        safe = game.prayer_timeout < 200
    elif minor:
        safe = game.prayer_timeout < 100
    else:
        safe = game.prayer_timeout == 0
    if not safe:
        if game.god_displeased:
            game.god_angry = True
            game.prayer_timeout = max(game.prayer_timeout, 500)
            smite(game)
        else:
            game.god_displeased = True
            msgs.add(f"You feel that {GOD} is displeased.")
        return

    if major:
        player.hp = player.max_hp
        msgs.add("You feel much better.")
    if minor:
        player.confused = 0
        msgs.add("You feel less confused now.")
    if not (major or minor):
        msgs.add(f"You feel that {GOD} is well-pleased.")
    game.god_displeased = False
    game.prayer_timeout = new_timeout(rng)

def smite(game):
    player = game.player
    game.msgs.add(f"You feel that {GOD} is angry! Lightning strikes you!")
    player.hp -= sum(game.rng.randint(1, 6) for _ in range(2))
    if player.hp <= 0:
        die(game, None, player)
