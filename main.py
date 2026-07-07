import random

OPT_YES = 1
OPT_NO = 2
OPT_CARD = 3
OPT_NUMBER = 0
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ABILITY = 10
OPT_DISCARD = 11
OPT_RETREAT = 12
OPT_ATTACK = 13
OPT_END = 14

_DECK = [
    65,65,65,65,
    878,878,878,878,
    1122,1122,1122,1122,
    1171,1171,1171,1171,
    1152,1152,1152,1152,
    1086,1086,1086,1086,
    1227,1227,1227,1227,
    1255,1255,1255,1255,
    19,19,19,19,
    11,11,11,11,
    66,66,66,
    1097,1097,1097,
    1115,1115,1115,
    879,879,
    304,304,
    1210,1210,
    1182,1182,
    1194,1194,
    12,
]

def _finalize_choice(preferred_indexes, options, max_count):
    chosen = []
    for idx in preferred_indexes:
        if isinstance(idx, int) and 0 <= idx < len(options) and idx not in chosen:
            chosen.append(idx)
    if len(chosen) < max_count:
        for i in range(len(options)):
            if i not in chosen:
                chosen.append(i)
            if len(chosen) >= max_count:
                break
    return chosen[:max_count]

def score_option(opt, obs_dict):
    """Heuristic scoring for each option with board awareness"""
    t = opt.get("type")
    score = 0

    # Active Pokémon HP
    active_hp = obs_dict.get("activeHP", 999)
    opponent_active_hp = obs_dict.get("opponentActiveHP", 999)

    if t == OPT_ATTACK:
        dmg = opt.get("damage", 0)
        score += dmg
        # Prioritize KO potential
        if dmg >= opponent_active_hp:
            score += 100
        if opt.get("statusEffect"):  # e.g. Burn, Paralysis
            score += 30

    elif t == OPT_EVOLVE:
        # Evolving unlocks stronger attacks
        score += 40

    elif t == OPT_ATTACH:
        # Prefer attaching to active if it can attack soon
        if opt.get("inPlayArea") == 4:
            score += 30
        else:
            score += 15

    elif t == OPT_RETREAT:
        # Retreat if active is low HP
        if active_hp < 40:
            score += 50
        else:
            score -= 10

    elif t == OPT_ABILITY:
        score += 20

    elif t == OPT_PLAY:
        score += 15

    elif t == OPT_END:
        score -= 10  # discourage ending early

    elif t == OPT_NO:
        score -= 20  # strongly discourage NO unless forced

    elif t == OPT_CARD:
        score += 5

    elif t == OPT_DISCARD:
        score -= 5

    return score

def agent(obs_dict, config=None):
    if obs_dict.get("select") is None:
        return _DECK

    options = obs_dict["select"].get("option", [])
    max_count = obs_dict["select"].get("maxCount", 1)

    if not options:
        return []

    # Score all options
    scored = [(i, score_option(opt, obs_dict)) for i, opt in enumerate(options)]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Pick best option(s), randomize among ties
    best_score = scored[0][1]
    best_indexes = [i for i, s in scored if s == best_score]

    chosen = random.choice(best_indexes)
    return _finalize_choice([chosen], options, max_count)
