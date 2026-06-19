import random

OPT_YES = 1
OPT_NO = 2
OPT_CARD = 3
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ABILITY = 10
OPT_DISCARD = 11
OPT_RETREAT = 12
OPT_ATTACK = 13
OPT_END = 14

_DECK = [
    46, 46, 46, 46,
    719, 719, 719, 719,
    259, 259, 259, 259,
    99, 99,

    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2, 2, 2, 2, 2,
    2, 2, 2, 2, 2, 2
]


def _finalize_choice(preferred_indexes, options, max_count):
    chosen = []

    for idx in preferred_indexes:
        if idx not in chosen and 0 <= idx < len(options):
            chosen.append(idx)

    if len(chosen) < max_count:
        for i in range(len(options)):
            if i not in chosen:
                chosen.append(i)
            if len(chosen) >= max_count:
                break

    return chosen[:max_count]


def random_agent(obs_dict, config=None):
    if obs_dict.get("select") is None:
        return _DECK

    options = obs_dict["select"].get("option", [])
    max_count = obs_dict["select"].get("maxCount", 1)

    if not options:
        return []

    return random.sample(
        range(len(options)),
        min(max_count, len(options))
    )


def agent(obs_dict, config=None):

    if obs_dict.get("select") is None:
        return _DECK

    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)

    if not options:
        return []

    types = []

    for opt in options:
        t = opt.get("type")

        if isinstance(t, str):
            mapping = {
                "Yes": OPT_YES,
                "No": OPT_NO,
                "Card": OPT_CARD,
                "Play": OPT_PLAY,
                "Attach": OPT_ATTACH,
                "Evolve": OPT_EVOLVE,
                "Ability": OPT_ABILITY,
                "Discard": OPT_DISCARD,
                "Retreat": OPT_RETREAT,
                "Attack": OPT_ATTACK,
                "End": OPT_END,
            }
            t = mapping.get(t, t)

        types.append(t)

    # -----------------------------
    # YES/NO prompts
    # -----------------------------
    yes_indexes = [i for i, t in enumerate(types) if t == OPT_YES]
    no_indexes = [i for i, t in enumerate(types) if t == OPT_NO]

    if yes_indexes and not no_indexes:
        return _finalize_choice([yes_indexes[0]], options, max_count)

    # -----------------------------
    # EVOLVE FIRST
    # -----------------------------
    evolve_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_EVOLVE
    ]

    if evolve_indexes:
        return _finalize_choice(
            [evolve_indexes[0]],
            options,
            max_count
        )

    # -----------------------------
    # USE ABILITIES
    # -----------------------------
    ability_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_ABILITY
    ]

    if ability_indexes:
        return _finalize_choice(
            [ability_indexes[0]],
            options,
            max_count
        )

    # -----------------------------
    # PLAY CARDS
    # -----------------------------
    play_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_PLAY
    ]

    if play_indexes:
        return _finalize_choice(
            [play_indexes[0]],
            options,
            max_count
        )

    # -----------------------------
    # ATTACH ENERGY
    # -----------------------------
    attach_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_ATTACH
    ]

    if attach_indexes:
        return _finalize_choice(
            [attach_indexes[0]],
            options,
            max_count
        )

    # -----------------------------
    # ATTACK
    # -----------------------------
    attack_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_ATTACK
    ]

    if attack_indexes:
        return _finalize_choice(
            [attack_indexes[-1]],
            options,
            max_count
        )

    # -----------------------------
    # RETREAT ONLY IF NEEDED
    # -----------------------------
    retreat_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_RETREAT
    ]

    if retreat_indexes:
        return _finalize_choice(
            [retreat_indexes[0]],
            options,
            max_count
        )

    # -----------------------------
    # END TURN LAST
    # -----------------------------
    end_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_END
    ]

    if end_indexes:
        return _finalize_choice(
            [end_indexes[0]],
            options,
            max_count
        )

    return _finalize_choice(
        list(range(len(options))),
        options,
        max_count
    )