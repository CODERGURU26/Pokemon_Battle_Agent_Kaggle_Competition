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

BOSS_ID = 1182  # Boss's Orders -- drag opponent's weakest bench to active

_DECK = [
    65, 65, 65, 65,
    878, 878, 878, 878,
    1122, 1122, 1122, 1122,
    1171, 1171, 1171, 1171,
    1152, 1152, 1152, 1152,
    1086, 1086, 1086, 1086,
    1227, 1227, 1227, 1227,
    1255, 1255, 1255, 1255,
    19, 19, 19, 19,
    11, 11, 11, 11,
    66, 66, 66,
    1097, 1097, 1097,
    1115, 1115, 1115,
    879, 879,
    304, 304,
    1210, 1210,
    1182, 1182,
    1194, 1194,
    12,
]

_boss_played = [False]


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


def _get_players(obs_dict):
    cur = obs_dict.get("current")
    if not cur:
        return None, None
    try:
        return cur["players"][cur["yourIndex"]], cur["players"][1 - cur["yourIndex"]]
    except Exception:
        return None, None


def random_agent(obs_dict, config=None):
    if obs_dict.get("select") is None:
        return _DECK
    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)
    if not options:
        return []
    return random.sample(range(len(options)), min(max_count, len(options)))


def agent(obs_dict, config=None):
    if obs_dict.get("select") is None:
        _boss_played[0] = False
        return _DECK

    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)

    if not options:
        return _finalize_choice([], options, max_count)

    types = [opt.get("type") for opt in options]
    you, opp = _get_players(obs_dict)

    # 1. YES first -- handles opening hand keep, who-goes-first,
    #    and ability trigger confirmations
    yes_indexes = [i for i, t in enumerate(types) if t == OPT_YES]
    if yes_indexes:
        return _finalize_choice([yes_indexes[0]], options, max_count)

    # 2. Evolve immediately
    evolve_indexes = [i for i, t in enumerate(types) if t == OPT_EVOLVE]
    if evolve_indexes:
        return _finalize_choice([evolve_indexes[0]], options, max_count)

    # 3. Use abilities
    ability_indexes = [i for i, t in enumerate(types) if t == OPT_ABILITY]
    if ability_indexes:
        return _finalize_choice([ability_indexes[0]], options, max_count)

    # 4. Smart PLAY: prioritize Boss's Orders when opponent has bench targets
    play_indexes = [i for i, t in enumerate(types) if t == OPT_PLAY]
    if play_indexes:
        _boss_played[0] = False
        if you and opp and opp.get("bench"):
            hand = you.get("hand", [])
            for opt_i in play_indexes:
                hand_pos = options[opt_i].get("index")
                if hand_pos is not None and hand_pos < len(hand):
                    if hand[hand_pos].get("id") == BOSS_ID:
                        _boss_played[0] = True
                        return _finalize_choice([opt_i], options, max_count)
        return _finalize_choice([play_indexes[0]], options, max_count)

    # 5. Smart CARD: after Boss's Orders, target lowest-HP opponent bench
    card_indexes = [i for i, t in enumerate(types) if t == OPT_CARD]
    if card_indexes:
        if _boss_played[0] and opp:
            opp_bench = opp.get("bench", [])
            if opp_bench and len(card_indexes) <= len(opp_bench):
                best_bench = min(
                    range(len(opp_bench)),
                    key=lambda i: opp_bench[i].get("hp", 9999) / max(opp_bench[i].get("maxHp", 1), 1)
                )
                _boss_played[0] = False
                return _finalize_choice([card_indexes[min(best_bench, len(card_indexes) - 1)]], options, max_count)
        _boss_played[0] = False
        return _finalize_choice([card_indexes[0]], options, max_count)

    # 6. Smart ATTACH: prefer Pokémon with most energy already
    #    (building toward attack cost fastest)
    attach_options = [
        (i, opt) for i, opt in enumerate(options)
        if opt.get("type") == OPT_ATTACH
    ]
    if attach_options:
        if you:
            energy_map = {}
            active_list = you.get("active") or []
            if active_list:
                energy_map[(4, 0)] = len(active_list[0].get("energies") or [])
            for j, b in enumerate(you.get("bench") or []):
                energy_map[(5, j)] = len(b.get("energies") or [])
            best_score = -1
            best_opt_i = attach_options[0][0]
            for opt_i, opt in attach_options:
                e = energy_map.get((opt.get("inPlayArea"), opt.get("inPlayIndex", 0)), 0)
                score = e + (0.5 if opt.get("inPlayArea") == 4 else 0)
                if score > best_score:
                    best_score = score
                    best_opt_i = opt_i
            return _finalize_choice([best_opt_i], options, max_count)
        else:
            active_targets = [idx for idx, opt in attach_options if opt.get("inPlayArea") == 4]
            if active_targets:
                return _finalize_choice([active_targets[0]], options, max_count)
            return _finalize_choice([attach_options[0][0]], options, max_count)

    # 7. Attack
    attack_indexes = [i for i, t in enumerate(types) if t == OPT_ATTACK]
    if attack_indexes:
        return _finalize_choice([attack_indexes[0]], options, max_count)

    # 8. End turn
    end_indexes = [i for i, t in enumerate(types) if t == OPT_END]
    if end_indexes:
        return _finalize_choice([end_indexes[0]], options, max_count)

    # 9. Retreat only as last resort
    retreat_indexes = [i for i, t in enumerate(types) if t == OPT_RETREAT]
    if retreat_indexes:
        return _finalize_choice([retreat_indexes[0]], options, max_count)

    # 10. Discard
    discard_indexes = [i for i, t in enumerate(types) if t == OPT_DISCARD]
    if discard_indexes:
        return _finalize_choice([discard_indexes[0]], options, max_count)

    # 11. NO only when it's the only option
    no_indexes = [i for i, t in enumerate(types) if t == OPT_NO]
    if no_indexes and len(options) == 1:
        return _finalize_choice([no_indexes[0]], options, max_count)

    # 12. Catch-all -- handles OPT_NUMBER (type 0) and any unknown types
    return _finalize_choice(list(range(len(options))), options, max_count)