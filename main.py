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

ATTACK_PRIORITY = [
    1409,
    1408,
    1039,
    981,
]


def _finalize_choice(preferred_indexes, options, max_count):
    chosen = []

    for idx in preferred_indexes:
        if (
            isinstance(idx, int)
            and idx >= 0
            and idx < len(options)
            and idx not in chosen
        ):
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

    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)

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

    types = [opt.get("type") for opt in options]

    # YES / NO prompts
    yes_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_YES
    ]

    if yes_indexes:
        return _finalize_choice(
            [yes_indexes[0]],
            options,
            max_count
        )

    # EVOLVE
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

    # ABILITIES
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

    # PLAY CARDS
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

    # ATTACH ENERGY
    attach_options = [
        (i, opt)
        for i, opt in enumerate(options)
        if opt.get("type") == OPT_ATTACH
    ]

    if attach_options:

        # Prefer Active Pokémon
        active_targets = [
            idx
            for idx, opt in attach_options
            if opt.get("inPlayArea") == 4
        ]

        if active_targets:
            return _finalize_choice(
                [active_targets[0]],
                options,
                max_count
            )

        return _finalize_choice(
            [attach_options[0][0]],
            options,
            max_count
        )

    # ATTACK
    attack_options = [
        (i, opt.get("attackId"))
        for i, opt in enumerate(options)
        if opt.get("type") == OPT_ATTACK
    ]

    if attack_options:

        for preferred_attack in ATTACK_PRIORITY:
            for idx, attack_id in attack_options:
                if attack_id == preferred_attack:
                    return _finalize_choice(
                        [idx],
                        options,
                        max_count
                    )

        return _finalize_choice(
            [attack_options[0][0]],
            options,
            max_count
        )

    # END TURN BEFORE RETREAT
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

    # RETREAT ONLY AS LAST RESORT
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

    # DISCARD
    discard_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_DISCARD
    ]

    if discard_indexes:
        return _finalize_choice(
            [discard_indexes[0]],
            options,
            max_count
        )

    # CARD SELECTION
    card_indexes = [
        i for i, t in enumerate(types)
        if t == OPT_CARD
    ]

    if card_indexes:
        return _finalize_choice(
            [card_indexes[0]],
            options,
            max_count
        )

    return _finalize_choice(
        list(range(len(options))),
        options,
        max_count
    )