"""
PTCG AI Battle Agent — V2 (Competitive)
========================================
Modular, scoring-based agent for the Hop's archetype deck.
Every decision is driven by board evaluation and action scoring.

Architecture:
  1. Constants & Card Database
  2. Memory System
  3. Helper Functions
  4. Board Evaluation Engine
  5. Scoring Engines (Play, Attach, Evolve, Ability, Retreat, Attack, Boss)
  6. Action Selection
  7. Main Agent Function
"""

import random

# =============================================================================
# SECTION 1: CONSTANTS & CARD DATABASE
# =============================================================================

# --- Option types (from the cabt engine) ---
OPT_NUMBER  = 0
OPT_YES     = 1
OPT_NO      = 2
OPT_CARD    = 3
OPT_PLAY    = 7
OPT_ATTACH  = 8
OPT_EVOLVE  = 9
OPT_ABILITY = 10
OPT_DISCARD = 11
OPT_RETREAT = 12
OPT_ATTACK  = 13
OPT_END     = 14

# --- In-play area codes ---
AREA_ACTIVE = 4
AREA_BENCH  = 5

# --- Pokémon Card IDs ---
DUNSPARCE         = 65    # Basic, Colorless, 60 HP
DUDUNSPARCE       = 66    # Stage 1 (from Dunsparce), 140 HP, Ability: Run Away Draw
HOPS_PHANTUMP     = 878   # Basic, Psychic, 70 HP
HOPS_TREVENANT    = 879   # Stage 1 (from Phantump), 140 HP
HOPS_SNORLAX      = 304   # Basic, Colorless, 150 HP, Ability: Extra Helpings

# --- Trainer Card IDs ---
BUDDY_BUDDY_POFFIN = 1086  # Item: bench 2 basics ≤70 HP
NIGHT_STRETCHER    = 1097  # Item: recover Pokémon/Energy from discard
HOPS_BAG           = 1115  # Item: search 2 basic Hop's Pokémon
POKEGEAR           = 1122  # Item: top 7, grab a Supporter
POKE_PAD           = 1152  # Item: search non-Rule Box Pokémon
HOPS_CHOICE_BAND   = 1171  # Tool: -1 energy cost, +30 dmg for Hop's

# --- Supporter Card IDs ---
BOSS_ORDERS        = 1182  # Switch in opponent's bench Pokémon
COLRESS_TENACITY   = 1194  # Search Stadium + Energy
BROCK_SCOUTING     = 1210  # Search up to 2 Basic or 1 Evolution Pokémon
LILLIES_DETERM     = 1227  # Shuffle hand, draw 6 (8 if 6 prizes left)

# --- Stadium Card IDs ---
POSTWICK           = 1255  # Hop's Pokémon do +30 damage

# --- Energy Card IDs ---
TELEPATH_PSYCHIC   = 19    # Special Energy: {P}
MIST_ENERGY        = 11    # Special Energy: {C}, prevents effects
LEGACY_ENERGY      = 12    # Special Energy: provides all types

# --- The Deck (60 cards) ---
_DECK = [
    65, 65, 65, 65,          # 4x Dunsparce
    878, 878, 878, 878,      # 4x Hop's Phantump
    1122, 1122, 1122, 1122,  # 4x Pokégear 3.0
    1171, 1171, 1171, 1171,  # 4x Hop's Choice Band
    1152, 1152, 1152, 1152,  # 4x Poké Pad
    1086, 1086, 1086, 1086,  # 4x Buddy-Buddy Poffin
    1227, 1227, 1227, 1227,  # 4x Lillie's Determination
    1255, 1255, 1255, 1255,  # 4x Postwick
    19, 19, 19, 19,          # 4x Telepath Psychic Energy
    11, 11, 11, 11,          # 4x Mist Energy
    66, 66, 66,              # 3x Dudunsparce
    1097, 1097, 1097,        # 3x Night Stretcher
    1115, 1115, 1115,        # 3x Hop's Bag
    879, 879,                # 2x Hop's Trevenant
    304, 304,                # 2x Hop's Snorlax
    1210, 1210,              # 2x Brock's Scouting
    1182, 1182,              # 2x Boss's Orders
    1194, 1194,              # 2x Colress's Tenacity
    12,                      # 1x Legacy Energy
]

# --- Card classification ---
POKEMON_IDS = {DUNSPARCE, DUDUNSPARCE, HOPS_PHANTUMP, HOPS_TREVENANT, HOPS_SNORLAX}
BASIC_POKEMON = {DUNSPARCE, HOPS_PHANTUMP, HOPS_SNORLAX}
EVOLUTION_POKEMON = {DUDUNSPARCE, HOPS_TREVENANT}
HOPS_POKEMON = {HOPS_PHANTUMP, HOPS_TREVENANT, HOPS_SNORLAX}
ENGINE_POKEMON = {DUDUNSPARCE}  # Draw engine — protect, don't waste energy
ATTACKER_POKEMON = {HOPS_TREVENANT, HOPS_SNORLAX}
STARTER_POKEMON = {DUNSPARCE, HOPS_PHANTUMP}  # Evolve targets

SUPPORTER_IDS = {BOSS_ORDERS, COLRESS_TENACITY, BROCK_SCOUTING, LILLIES_DETERM}
ITEM_IDS = {BUDDY_BUDDY_POFFIN, NIGHT_STRETCHER, HOPS_BAG, POKEGEAR, POKE_PAD}
ENERGY_IDS = {TELEPATH_PSYCHIC, MIST_ENERGY, LEGACY_ENERGY}

# --- Attack database: {card_id: [(move_name, base_damage, energy_cost_count, is_conditional)]} ---
ATTACK_DB = {
    DUNSPARCE:      [("Gnaw", 10, 1, False), ("Dig", 30, 2, False)],
    DUDUNSPARCE:    [("Land Crush", 90, 3, False)],
    HOPS_PHANTUMP:  [("Splashing Dodge", 10, 1, False)],
    HOPS_TREVENANT: [("Horrifying Revenge", 30, 1, True), ("Corner", 90, 3, False)],
    HOPS_SNORLAX:   [("Dynamic Press", 140, 3, False)],
}

# Horrifying Revenge: 30 base, +100 if ally was KO'd last turn = 130
HORRIFYING_REVENGE_BONUS = 100

# --- Game phase thresholds ---
EARLY_GAME_TURN = 3
MID_GAME_TURN = 7
LATE_GAME_PRIZES = 3  # ≤3 prizes remaining = late game


# =============================================================================
# SECTION 2: MEMORY SYSTEM
# =============================================================================

_memory = {
    "turn": 0,
    "supporter_used_this_turn": False,
    "energy_attached_this_turn": False,
    "retreated_this_turn": False,
    "abilities_used_this_turn": set(),
    "ally_ko_last_turn": False,
    "pending_boss": False,
    "pending_card_context": None,  # what card prompted the CARD selection
    "last_prize_count": 6,
    "game_started": False,
}


def _reset_memory():
    """Reset memory at the start of a new game."""
    _memory["turn"] = 0
    _memory["supporter_used_this_turn"] = False
    _memory["energy_attached_this_turn"] = False
    _memory["retreated_this_turn"] = False
    _memory["abilities_used_this_turn"] = set()
    _memory["ally_ko_last_turn"] = False
    _memory["pending_boss"] = False
    _memory["pending_card_context"] = None
    _memory["last_prize_count"] = 6
    _memory["game_started"] = False


def _new_turn_memory():
    """Reset per-turn flags. Called when we detect a new turn."""
    _memory["supporter_used_this_turn"] = False
    _memory["energy_attached_this_turn"] = False
    _memory["retreated_this_turn"] = False
    _memory["abilities_used_this_turn"] = set()


# =============================================================================
# SECTION 3: HELPER FUNCTIONS
# =============================================================================

def _finalize_choice(preferred_indexes, options, max_count):
    """Return a list of chosen option indexes, padding with remaining if needed."""
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
    """Extract (your_team, opponent_team) from the observation."""
    cur = obs_dict.get("current")
    if not cur:
        return None, None
    try:
        your_idx = cur["yourIndex"]
        return cur["players"][your_idx], cur["players"][1 - your_idx]
    except Exception:
        return None, None


def _active_pokemon(team):
    """Get the active Pokémon dict, or None."""
    if not team:
        return None
    active_list = team.get("active") or []
    return active_list[0] if active_list else None


def _bench_pokemon(team):
    """Get list of bench Pokémon dicts."""
    if not team:
        return []
    return team.get("bench") or []


def _all_pokemon(team):
    """Get all Pokémon in play (active + bench)."""
    result = []
    active = _active_pokemon(team)
    if active:
        result.append(active)
    result.extend(_bench_pokemon(team))
    return result


def _pokemon_id(pokemon):
    """Get the card ID of a Pokémon."""
    if not pokemon:
        return None
    return pokemon.get("id")


def _pokemon_hp(pokemon):
    """Get current HP of a Pokémon."""
    if not pokemon:
        return 0
    return pokemon.get("hp", 0)


def _pokemon_max_hp(pokemon):
    """Get max HP of a Pokémon."""
    if not pokemon:
        return 1
    return max(pokemon.get("maxHp", 1), 1)


def _hp_percent(pokemon):
    """Get HP as a fraction 0.0-1.0."""
    if not pokemon:
        return 0.0
    return _pokemon_hp(pokemon) / _pokemon_max_hp(pokemon)


def _energy_count(pokemon):
    """Count energies attached to a Pokémon."""
    if not pokemon:
        return 0
    return len(pokemon.get("energies") or [])


def _total_energy(team):
    """Count total energies across all Pokémon in play."""
    return sum(_energy_count(p) for p in _all_pokemon(team))


def _prize_count(team):
    """Number of prize cards remaining."""
    if not team:
        return 6
    return len(team.get("prizes") or [])


def _hand_cards(team):
    """Get list of cards in hand."""
    if not team:
        return []
    return team.get("hand") or []


def _discard_pile(team):
    """Get list of cards in discard pile."""
    if not team:
        return []
    return team.get("discard") or []


def _pokemon_stage(pokemon):
    """Get evolution stage (0=basic, 1=stage1, 2=stage2)."""
    if not pokemon:
        return 0
    return pokemon.get("stage", 0)


def _has_tool(pokemon):
    """Check if Pokémon has a tool attached."""
    if not pokemon:
        return False
    tools = pokemon.get("tools") or pokemon.get("tool") or []
    if isinstance(tools, list):
        return len(tools) > 0
    return bool(tools)


def _get_tool_id(pokemon):
    """Get the tool card ID attached to a Pokémon, or None."""
    if not pokemon:
        return None
    tools = pokemon.get("tools") or pokemon.get("tool") or []
    if isinstance(tools, list) and tools:
        t = tools[0]
        return t.get("id") if isinstance(t, dict) else t
    if isinstance(tools, dict):
        return tools.get("id")
    return None


def _is_hops_pokemon(pokemon):
    """Check if this is a Hop's Pokémon (for damage bonuses)."""
    pid = _pokemon_id(pokemon)
    return pid in HOPS_POKEMON


def _count_pokemon_by_id(team, card_id):
    """Count how many Pokémon with a specific card ID are in play."""
    return sum(1 for p in _all_pokemon(team) if _pokemon_id(p) == card_id)


def _find_pokemon_in_play(team, card_id):
    """Find all Pokémon with a given card ID in play."""
    return [p for p in _all_pokemon(team) if _pokemon_id(p) == card_id]


def _card_id_from_hand(team, hand_index):
    """Get card ID from hand by index."""
    hand = _hand_cards(team)
    if hand_index is not None and 0 <= hand_index < len(hand):
        card = hand[hand_index]
        if isinstance(card, dict):
            return card.get("id")
        return card
    return None


# =============================================================================
# SECTION 4: BOARD EVALUATION ENGINE
# =============================================================================

def _calculate_damage_modifiers(team):
    """
    Calculate total damage bonus for Hop's Pokémon attacks.
    Sources: Postwick (stadium), Hop's Choice Band (tool), Snorlax ability.
    """
    bonus = 0

    # Check for Postwick in play (stadium)
    # The stadium is tracked in the game state; we approximate by checking
    # if we played it. For safety, we always assume it might be in play
    # if we have Postwick in deck. We'll check the actual stadium field if available.
    # For now, count Snorlax ability bonus
    snorlax_count = _count_pokemon_by_id(team, HOPS_SNORLAX)
    if snorlax_count > 0:
        bonus += 30  # Extra Helpings: Hop's Pokémon +30

    return bonus


def _get_attacker_damage(pokemon, team, ally_ko_last_turn=False):
    """
    Estimate the damage this Pokémon can deal if it attacks.
    Returns list of (attack_index, estimated_damage, energy_cost, attack_name).
    """
    pid = _pokemon_id(pokemon)
    if pid not in ATTACK_DB:
        return []

    energy = _energy_count(pokemon)
    is_hops = _is_hops_pokemon(pokemon)
    has_choice_band = (_get_tool_id(pokemon) == HOPS_CHOICE_BAND)

    # Damage modifiers for Hop's Pokémon
    hop_bonus = 0
    if is_hops:
        hop_bonus += _calculate_damage_modifiers(team)
        if has_choice_band:
            hop_bonus += 30  # Choice Band: +30 for Hop's

    results = []
    for idx, (name, base_dmg, cost, is_conditional) in enumerate(ATTACK_DB[pid]):
        effective_cost = cost
        if is_hops and has_choice_band:
            effective_cost = max(1, cost - 1)  # Choice Band: -1 energy cost

        if energy < effective_cost:
            continue  # Can't afford this attack

        dmg = base_dmg
        if pid == HOPS_TREVENANT and name == "Horrifying Revenge" and ally_ko_last_turn:
            dmg += HORRIFYING_REVENGE_BONUS

        if is_hops:
            dmg += hop_bonus

        results.append((idx, dmg, effective_cost, name))

    return results


def evaluate_board(you, opp):
    """
    Comprehensive board evaluation. Returns a dict with all relevant metrics.
    """
    my_active = _active_pokemon(you)
    opp_active = _active_pokemon(opp)
    my_bench = _bench_pokemon(you)
    opp_bench = _bench_pokemon(opp)

    my_prizes = _prize_count(you)
    opp_prizes = _prize_count(opp)

    # Detect if ally was KO'd (prize count dropped for opponent)
    ally_ko = _memory.get("ally_ko_last_turn", False)

    # Available attacks for our active
    my_attacks = _get_attacker_damage(my_active, you, ally_ko) if my_active else []
    can_attack = len(my_attacks) > 0
    best_attack_dmg = max((a[1] for a in my_attacks), default=0)

    # Can we KO opponent's active?
    opp_hp = _pokemon_hp(opp_active) if opp_active else 0
    can_ko = best_attack_dmg >= opp_hp and opp_hp > 0

    # Backup attackers on bench
    backup_attackers = []
    for bp in my_bench:
        bp_attacks = _get_attacker_damage(bp, you, ally_ko)
        if bp_attacks:
            backup_attackers.append((bp, bp_attacks))

    # Count key Pokémon
    dudunsparce_count = _count_pokemon_by_id(you, DUDUNSPARCE)
    trevenant_count = _count_pokemon_by_id(you, HOPS_TREVENANT)
    snorlax_count = _count_pokemon_by_id(you, HOPS_SNORLAX)

    board = {
        # Active Pokémon state
        "my_active": my_active,
        "my_active_hp": _pokemon_hp(my_active),
        "my_active_hp_pct": _hp_percent(my_active),
        "my_active_energy": _energy_count(my_active),
        "my_active_id": _pokemon_id(my_active),
        "my_active_is_hops": _is_hops_pokemon(my_active),

        # Opponent active state
        "opp_active": opp_active,
        "opp_active_hp": _pokemon_hp(opp_active),
        "opp_active_hp_pct": _hp_percent(opp_active),
        "opp_active_energy": _energy_count(opp_active),
        "opp_active_id": _pokemon_id(opp_active),

        # Bench
        "my_bench": my_bench,
        "my_bench_size": len(my_bench),
        "opp_bench": opp_bench,
        "opp_bench_size": len(opp_bench),

        # Energy
        "my_total_energy": _total_energy(you),
        "opp_total_energy": _total_energy(opp),

        # Prizes
        "my_prizes": my_prizes,
        "opp_prizes": opp_prizes,
        "prize_diff": opp_prizes - my_prizes,  # positive = we're winning

        # Combat
        "can_attack": can_attack,
        "best_attack_dmg": best_attack_dmg,
        "my_attacks": my_attacks,
        "can_ko": can_ko,
        "ally_ko_last_turn": ally_ko,

        # Team composition
        "dudunsparce_count": dudunsparce_count,
        "trevenant_count": trevenant_count,
        "snorlax_count": snorlax_count,
        "backup_attackers": backup_attackers,

        # Phase & mode (computed below)
        "game_phase": "EARLY",
        "strategic_mode": "SETUP",

        # Hand
        "hand_size": len(_hand_cards(you)),
    }

    # Determine game phase
    turn = _memory.get("turn", 0)
    if my_prizes <= 2 or opp_prizes <= 2:
        board["game_phase"] = "ENDGAME"
    elif my_prizes <= LATE_GAME_PRIZES or opp_prizes <= LATE_GAME_PRIZES:
        board["game_phase"] = "LATE"
    elif turn <= EARLY_GAME_TURN:
        board["game_phase"] = "EARLY"
    else:
        board["game_phase"] = "MID"

    # Determine strategic mode
    prize_diff = board["prize_diff"]
    if board["game_phase"] == "EARLY":
        board["strategic_mode"] = "SETUP"
    elif prize_diff >= 2:
        board["strategic_mode"] = "AGGRESSIVE"  # We're ahead, press advantage
    elif prize_diff <= -2:
        board["strategic_mode"] = "COMEBACK"    # We're behind, need to catch up
    elif board["my_active_hp_pct"] < 0.3 and not can_attack:
        board["strategic_mode"] = "DEFENSIVE"   # Need to retreat/heal
    else:
        board["strategic_mode"] = "PRIZE_RACE"  # Close game, race for prizes

    return board


# =============================================================================
# SECTION 5: SCORING ENGINES
# =============================================================================

# ---------- Score: PLAY (cards from hand) ----------

def _score_play_card(opt, options, you, opp, board):
    """
    Score playing a card from hand.
    Returns (score, description).
    """
    hand_pos = opt.get("index")
    card_id = _card_id_from_hand(you, hand_pos)
    if card_id is None:
        return (10, "unknown card")

    phase = board["game_phase"]
    mode = board["strategic_mode"]

    # --- Supporters (only 1 per turn) ---
    if card_id in SUPPORTER_IDS:
        if _memory.get("supporter_used_this_turn"):
            return (-100, "already used supporter")

        if card_id == BOSS_ORDERS:
            # Boss is valuable when we can KO a bench target
            if board["opp_bench_size"] == 0:
                return (-50, "boss no targets")
            # High value if we can attack this turn
            if board["can_attack"]:
                # Check if any bench target is KO-able
                best_dmg = board["best_attack_dmg"]
                for bp in board["opp_bench"]:
                    if best_dmg >= _pokemon_hp(bp):
                        # Can KO a bench target!
                        value = 800
                        if board["opp_prizes"] <= 2:
                            value = 1200  # Could win the game
                        return (value, "boss can KO bench target")
                # Can't KO but can drag up a weak target
                return (200, "boss drag weak target")
            else:
                return (50, "boss but can't attack")

        elif card_id == LILLIES_DETERM:
            # Draw supporter — more valuable with small hand
            hand_size = board["hand_size"]
            if hand_size <= 2:
                return (500, "lillie small hand")
            elif hand_size <= 4:
                return (350, "lillie medium hand")
            elif phase == "EARLY" and board["my_prizes"] == 6:
                return (400, "lillie early game 8 cards")
            else:
                return (200, "lillie large hand")

        elif card_id == BROCK_SCOUTING:
            # Search Pokémon — best early game for setup
            if phase == "EARLY":
                return (450, "brock early setup")
            elif board["my_bench_size"] < 3:
                return (350, "brock need bench")
            else:
                return (150, "brock late")

        elif card_id == COLRESS_TENACITY:
            # Search Stadium + Energy
            if phase == "EARLY":
                return (380, "colress early")
            else:
                return (200, "colress mid-late")

        return (150, "generic supporter")

    # --- Items ---
    if card_id == BUDDY_BUDDY_POFFIN:
        # Bench 2 basics ≤70 HP — amazing early
        if phase == "EARLY" and board["my_bench_size"] < 3:
            return (600, "poffin early bench fill")
        elif board["my_bench_size"] < 2:
            return (450, "poffin need bench")
        elif board["my_bench_size"] < 4:
            return (250, "poffin more bench")
        else:
            return (100, "poffin full bench")

    elif card_id == HOPS_BAG:
        # Search 2 basic Hop's Pokémon
        if phase == "EARLY" and board["my_bench_size"] < 3:
            return (550, "hops bag early")
        elif board["trevenant_count"] == 0 and board["snorlax_count"] == 0:
            return (400, "hops bag need attackers")
        elif board["my_bench_size"] < 4:
            return (300, "hops bag more bench")
        else:
            return (100, "hops bag full")

    elif card_id == NIGHT_STRETCHER:
        # Recover from discard — check if key Pokémon are in discard
        discard = _discard_pile(you)
        has_key_pokemon_in_discard = False
        for c in discard:
            cid = c.get("id") if isinstance(c, dict) else c
            if cid in POKEMON_IDS:
                has_key_pokemon_in_discard = True
                break
        if has_key_pokemon_in_discard:
            return (350, "stretcher recover key pokemon")
        else:
            return (150, "stretcher")

    elif card_id == POKEGEAR:
        # Find a Supporter — more valuable early or when hand is low
        if not _memory.get("supporter_used_this_turn"):
            if phase == "EARLY":
                return (300, "pokegear early find supporter")
            return (200, "pokegear find supporter")
        return (50, "pokegear already used supporter")

    elif card_id == POKE_PAD:
        # Search for non-Rule Box Pokémon
        if phase == "EARLY" and board["my_bench_size"] < 3:
            return (350, "pokepad early")
        elif board["trevenant_count"] == 0:
            return (300, "pokepad need trevenant")
        return (150, "pokepad")

    # --- Tools ---
    elif card_id == HOPS_CHOICE_BAND:
        # Attach to a Hop's Pokémon for -1 cost, +30 dmg
        # Check if any Hop's Pokémon in play needs it
        hops_in_play = [p for p in _all_pokemon(you) if _is_hops_pokemon(p) and not _has_tool(p)]
        if hops_in_play:
            return (400, "choice band on hops pokemon")
        return (50, "choice band no target")

    # --- Stadium ---
    elif card_id == POSTWICK:
        # +30 damage for all Hop's Pokémon (both sides)
        hops_count = sum(1 for p in _all_pokemon(you) if _is_hops_pokemon(p))
        if hops_count > 0:
            return (450, "postwick boost hops")
        return (100, "postwick no hops in play")

    # --- Energy cards played from hand (if applicable) ---
    if card_id in ENERGY_IDS:
        return (200, "energy from hand")

    return (100, "generic play")


def _score_play(opt, options, you, opp, board):
    """Score a PLAY action."""
    score, _ = _score_play_card(opt, options, you, opp, board)
    return score


# ---------- Score: ATTACH (energy to Pokémon) ----------

def _score_attach(opt, you, opp, board):
    """
    Score attaching energy to a specific Pokémon.
    Higher score = better attachment target.
    """
    if _memory.get("energy_attached_this_turn"):
        return -100  # Already attached this turn (shouldn't happen, but safeguard)

    area = opt.get("inPlayArea")
    index = opt.get("inPlayIndex", 0)

    # Identify the target Pokémon
    target = None
    if area == AREA_ACTIVE:
        target = _active_pokemon(you)
    elif area == AREA_BENCH:
        bench = _bench_pokemon(you)
        if 0 <= index < len(bench):
            target = bench[index]

    if not target:
        return 0

    pid = _pokemon_id(target)
    energy = _energy_count(target)
    hp_pct = _hp_percent(target)
    is_active = (area == AREA_ACTIVE)
    is_hops = _is_hops_pokemon(target)
    has_band = (_get_tool_id(target) == HOPS_CHOICE_BAND)

    score = 0

    # --- Priority 1: Can this Pokémon attack next turn with this energy? ---
    if pid in ATTACK_DB:
        for name, base_dmg, cost, _ in ATTACK_DB[pid]:
            effective_cost = cost
            if is_hops and has_band:
                effective_cost = max(1, cost - 1)

            energy_after = energy + 1
            if energy_after >= effective_cost and energy < effective_cost:
                # This energy ENABLES an attack!
                if is_active:
                    score += 600  # Active can attack next turn
                else:
                    score += 400  # Bench can attack if promoted

    # --- Priority 2: Active Pokémon bonus ---
    if is_active:
        score += 100

    # --- Priority 3: Attacker Pokémon priority ---
    if pid in ATTACKER_POKEMON:
        score += 200
    elif pid == HOPS_PHANTUMP:
        score += 150  # Will become Trevenant
    elif pid == DUNSPARCE:
        score += 50   # Low priority
    elif pid in ENGINE_POKEMON:
        score += 30   # Dudunsparce doesn't need energy usually

    # --- Priority 4: Building toward expensive attacks ---
    if pid in ATTACK_DB:
        best_cost = max(c for _, _, c, _ in ATTACK_DB[pid])
        if is_hops and has_band:
            best_cost = max(1, best_cost - 1)
        energy_needed = best_cost - energy
        if energy_needed > 0:
            # Closer to attacking = higher priority
            score += (5 - energy_needed) * 30

    # --- Penalty: Low HP (might get KO'd, wasting energy) ---
    if hp_pct < 0.3 and is_active:
        score -= 200  # Likely to be KO'd

    # --- Penalty: Engine Pokémon (don't waste energy on draw support) ---
    if pid in ENGINE_POKEMON:
        score -= 100

    # --- Bonus: Hop's Trevenant with ally KO (Horrifying Revenge) ---
    if pid == HOPS_TREVENANT and _memory.get("ally_ko_last_turn"):
        if energy == 0:
            score += 300  # 1 energy enables Horrifying Revenge

    return score


# ---------- Score: EVOLVE ----------

def _score_evolve(opt, you, opp, board):
    """
    Score evolving a Pokémon.
    """
    # Try to determine what we're evolving into
    hand_pos = opt.get("index")
    card_id = _card_id_from_hand(you, hand_pos)

    score = 0

    if card_id == DUDUNSPARCE:
        # Almost always evolve — draw 3 cards per turn is critical
        score = 700
        # Slight bonus if we have small hand
        if board["hand_size"] <= 3:
            score += 100

    elif card_id == HOPS_TREVENANT:
        # Evolve when beneficial
        if _memory.get("ally_ko_last_turn"):
            score = 800  # Horrifying Revenge available!
        elif board["game_phase"] in ("MID", "LATE", "ENDGAME"):
            score = 600  # Need attackers
        elif board["game_phase"] == "EARLY":
            score = 400  # OK to evolve early for HP boost
        else:
            score = 500

    else:
        # Unknown evolution — still generally good
        score = 300

    return score


# ---------- Score: ABILITY ----------

def _score_ability(opt, you, opp, board):
    """
    Score using an ability.
    Most abilities in our deck should be used (draw, damage boost).
    """
    # Dudunsparce's Run Away Draw: draw 3 cards, then shuffle+end turn option
    # Snorlax's Extra Helpings: passive (always active when in play)
    # Both are generally always beneficial to activate

    score = 500  # Default: use abilities

    # If it's a draw ability and we have a large hand, slightly less priority
    if board["hand_size"] >= 8:
        score = 300

    return score


# ---------- Score: RETREAT ----------

def _score_retreat(opt, you, opp, board):
    """
    Score retreating the active Pokémon.
    """
    my_active = board["my_active"]
    if not my_active:
        return -100

    pid = board["my_active_id"]
    hp_pct = board["my_active_hp_pct"]
    can_attack = board["can_attack"]

    score = -50  # Base: slight penalty (retreating costs energy, wastes turn options)

    # --- Strong reasons to retreat ---

    # Can't attack at all
    if not can_attack:
        # Check if bench has a ready attacker
        if board["backup_attackers"]:
            score += 400  # Retreat to bring in someone who can attack
        else:
            score += 100  # No one can attack, but still might be useful

    # Active at critical HP and bench has ready attacker
    if hp_pct < 0.3:
        if board["backup_attackers"]:
            score += 300  # Save from KO, bring in attacker
        else:
            score += 150  # Save from KO

    # Active is an engine Pokémon (Dudunsparce) — don't risk it in active
    if pid in ENGINE_POKEMON and board["backup_attackers"]:
        score += 350

    # Active is a basic that should be on bench (Dunsparce, Phantump)
    if pid in STARTER_POKEMON and _pokemon_stage(my_active) == 0:
        if board["backup_attackers"]:
            score += 200

    # --- Reasons NOT to retreat ---

    # Can attack and deal good damage
    if can_attack and board["best_attack_dmg"] >= 60:
        score -= 200

    # Can KO opponent
    if board["can_ko"]:
        score -= 500  # Don't retreat if we can KO!

    # Already retreated this turn
    if _memory.get("retreated_this_turn"):
        score -= 1000

    return score


# ---------- Score: ATTACK ----------

def _score_attack(opt, you, opp, board):
    """
    Score a specific attack option.
    """
    my_active = board["my_active"]
    opp_active = board["opp_active"]
    if not my_active or not opp_active:
        return 100  # Default: attack if nothing else

    pid = board["my_active_id"]
    ally_ko = _memory.get("ally_ko_last_turn", False)
    attacks = _get_attacker_damage(my_active, you, ally_ko)

    if not attacks:
        return 50  # Can't determine, but attacking is usually good

    # The option might have an attackId or index
    attack_id = opt.get("attackId")
    attack_index = opt.get("index", 0)

    # Find the matching attack from our database
    # If we have multiple attack options, try to match by index
    all_attack_options = [i for i, o in enumerate(board.get("_all_options", []))
                         if o.get("type") == OPT_ATTACK]

    # Use the attack data if we can match it
    best_dmg = 0
    best_name = ""
    if attacks:
        # If there's only one attack available, use it
        if len(attacks) == 1:
            _, best_dmg, _, best_name = attacks[0]
        else:
            # Try to match by checking which attack option this is
            # among all attack options presented
            for idx, (atk_idx, dmg, cost, name) in enumerate(attacks):
                if dmg > best_dmg:
                    best_dmg = dmg
                    best_name = name

    opp_hp = _pokemon_hp(opp_active)

    score = 100  # Base score: attacking is good

    # Can KO?
    if best_dmg >= opp_hp and opp_hp > 0:
        score += 800
        # Would this win the game?
        prizes_taken = 1  # Standard KO
        if board["my_prizes"] <= prizes_taken:
            score += 2000  # GAME WINNING

    # Damage efficiency
    score += best_dmg * 2

    # Horrifying Revenge bonus (thematic: use it when it's powered up)
    if pid == HOPS_TREVENANT and ally_ko and best_name == "Horrifying Revenge":
        score += 300

    # Corner (prevents retreat) bonus
    if best_name == "Corner":
        score += 100  # Lock opponent in place

    # Penalty for self-damage (Snorlax Dynamic Press)
    if pid == HOPS_SNORLAX and best_name == "Dynamic Press":
        my_hp = _pokemon_hp(my_active)
        if my_hp <= 80:
            score -= 500  # Would KO ourselves
        else:
            score -= 80  # Self-damage tax

    return score


# ---------- Score: END TURN ----------

def _score_end(you, opp, board):
    """Score ending the turn. Usually low — only end when nothing useful is left."""
    return 0  # Baseline — other actions should score higher


# ---------- Score: Boss Target Selection ----------

def _score_boss_target(bench_pokemon, you, opp, board):
    """
    Score an opponent's bench Pokémon as a Boss's Orders target.
    Higher = better target to drag active.
    """
    pid = _pokemon_id(bench_pokemon)
    hp = _pokemon_hp(bench_pokemon)
    max_hp = _pokemon_max_hp(bench_pokemon)
    energy = _energy_count(bench_pokemon)
    stage = _pokemon_stage(bench_pokemon)

    best_dmg = board["best_attack_dmg"]

    score = 0

    # Can we KO this target?
    if best_dmg >= hp and hp > 0:
        score += 500
        # Would this win the game?
        prizes_left = board["my_prizes"]
        if prizes_left <= 1:
            score += 1000  # Game winning KO

    # How damaged is it? (easier to KO)
    damage_taken = max_hp - hp
    if damage_taken > 0:
        score += damage_taken  # Already damaged targets are better

    # Energy invested (we deny their investment)
    score += energy * 60

    # Evolution stage (higher stage = more investment to replace)
    score += stage * 40

    # Is it an engine Pokémon? (draw support, ability Pokémon)
    # We can't know exactly, but evolved Pokémon with 0 energy are likely support
    if stage > 0 and energy == 0:
        score += 80  # Likely an engine

    # Is it a high-HP Pokémon sitting on bench (main attacker charging)?
    if max_hp >= 140 and energy >= 2:
        score += 120  # Taking out a charging attacker

    # Low HP targets are easier KOs even without being pre-damaged
    if hp <= 70:
        score += 100

    return score


# =============================================================================
# SECTION 6: ACTION SELECTION
# =============================================================================

def _select_main_action(options, types, you, opp, board):
    """
    Score all available main actions and return the index of the best one.
    Handles: PLAY, ATTACH, EVOLVE, ABILITY, RETREAT, ATTACK, END
    """
    scored = []

    for i, opt in enumerate(options):
        t = opt.get("type")

        if t == OPT_EVOLVE:
            s = _score_evolve(opt, you, opp, board)
        elif t == OPT_ABILITY:
            s = _score_ability(opt, you, opp, board)
        elif t == OPT_PLAY:
            s = _score_play(opt, options, you, opp, board)
        elif t == OPT_ATTACH:
            s = _score_attach(opt, you, opp, board)
        elif t == OPT_ATTACK:
            s = _score_attack(opt, you, opp, board)
        elif t == OPT_RETREAT:
            s = _score_retreat(opt, you, opp, board)
        elif t == OPT_END:
            s = _score_end(you, opp, board)
        elif t == OPT_YES:
            s = 50  # Usually say yes (handled separately for most cases)
        elif t == OPT_NO:
            s = -10
        elif t == OPT_DISCARD:
            s = -20  # Discard is usually forced
        else:
            s = 0

        scored.append((s, i))

    if not scored:
        return 0

    # Sort by score descending, return best index
    scored.sort(key=lambda x: (-x[0], x[1]))
    return scored[0][1]


def _select_best_attack(options, types, you, opp, board):
    """
    When multiple ATTACK options are available, pick the best one.
    """
    attack_indexes = [i for i, t in enumerate(types) if t == OPT_ATTACK]
    if len(attack_indexes) <= 1:
        return attack_indexes[0] if attack_indexes else 0

    my_active = board["my_active"]
    opp_active = board["opp_active"]
    ally_ko = _memory.get("ally_ko_last_turn", False)

    if not my_active or not opp_active:
        return attack_indexes[0]

    attacks = _get_attacker_damage(my_active, you, ally_ko)
    opp_hp = _pokemon_hp(opp_active)

    best_idx = attack_indexes[0]
    best_score = -1

    for rank, atk_opt_idx in enumerate(attack_indexes):
        # Match attack option to our attack database by position
        if rank < len(attacks):
            _, dmg, cost, name = attacks[rank]
        else:
            dmg, cost, name = 0, 0, "unknown"

        score = dmg * 2

        # KO bonus
        if dmg >= opp_hp and opp_hp > 0:
            score += 800
            if board["my_prizes"] <= 1:
                score += 2000

        # Self-damage penalty
        if name == "Dynamic Press":
            my_hp = _pokemon_hp(my_active)
            if my_hp <= 80:
                score -= 1000
            else:
                score -= 80

        # Corner lock bonus
        if name == "Corner":
            score += 100

        # Horrifying Revenge powered up
        if name == "Horrifying Revenge" and ally_ko:
            score += 300

        # Energy efficiency (prefer cheaper attacks that still KO)
        if cost > 0 and dmg >= opp_hp:
            score += (10 - cost) * 20  # Prefer cheaper KOs

        if score > best_score:
            best_score = score
            best_idx = atk_opt_idx

    return best_idx


def _select_boss_target(options, types, opp, board):
    """
    Select the best Boss's Orders target from CARD options.
    """
    card_indexes = [i for i, t in enumerate(types) if t == OPT_CARD]
    if not card_indexes:
        return 0

    opp_bench = board["opp_bench"]
    if not opp_bench:
        return card_indexes[0]

    best_idx = card_indexes[0]
    best_score = -1

    for ci, card_opt_idx in enumerate(card_indexes):
        if ci < len(opp_bench):
            target = opp_bench[ci]
            score = _score_boss_target(target, None, opp, board)
        else:
            score = 0

        if score > best_score:
            best_score = score
            best_idx = card_opt_idx

    return best_idx


def _select_card_target(options, types, you, opp, board):
    """
    Handle CARD selection for various contexts.
    """
    card_indexes = [i for i, t in enumerate(types) if t == OPT_CARD]
    if not card_indexes:
        return 0

    # Check if this is a Boss's Orders target selection
    if _memory.get("pending_boss") and opp:
        _memory["pending_boss"] = False
        return _select_boss_target(options, types, opp, board)

    # Default: pick first card option
    return card_indexes[0]


def _select_discard(options, types, you, opp, board):
    """
    When forced to discard, pick the least valuable card.
    Prefer discarding energy over Pokémon/trainers.
    """
    discard_indexes = [i for i, t in enumerate(types) if t == OPT_DISCARD]
    if not discard_indexes:
        return 0

    # Try to discard energy (least impactful) first
    best_idx = discard_indexes[0]
    best_priority = 999

    for di in discard_indexes:
        opt = options[di]
        hand_pos = opt.get("index")
        card_id = _card_id_from_hand(you, hand_pos)

        if card_id in ENERGY_IDS:
            priority = 1  # Discard energy first
        elif card_id in ITEM_IDS:
            priority = 2
        elif card_id in SUPPORTER_IDS:
            priority = 3
        elif card_id in POKEMON_IDS:
            priority = 4  # Keep Pokémon
        else:
            priority = 2

        if priority < best_priority:
            best_priority = priority
            best_idx = di

    return best_idx


def _handle_retreat_target(options, types, you, opp, board):
    """
    When retreating, select the best bench Pokémon to promote.
    """
    card_indexes = [i for i, t in enumerate(types) if t == OPT_CARD]
    if not card_indexes:
        return card_indexes[0] if card_indexes else 0

    my_bench = board["my_bench"]
    if not my_bench:
        return card_indexes[0]

    ally_ko = _memory.get("ally_ko_last_turn", False)
    best_idx = card_indexes[0]
    best_score = -1

    for ci, card_opt_idx in enumerate(card_indexes):
        if ci >= len(my_bench):
            continue

        bp = my_bench[ci]
        pid = _pokemon_id(bp)
        attacks = _get_attacker_damage(bp, you, ally_ko)

        score = 0

        # Can attack immediately?
        if attacks:
            best_dmg = max(a[1] for a in attacks)
            score += best_dmg * 3

            # Can KO opponent?
            if board["opp_active"] and best_dmg >= _pokemon_hp(board["opp_active"]):
                score += 500

        # Prefer attackers over engines
        if pid in ATTACKER_POKEMON:
            score += 200
        elif pid in ENGINE_POKEMON:
            score -= 300  # Don't promote draw engine

        # HP consideration (prefer tanky Pokémon)
        score += _pokemon_hp(bp)

        # Trevenant with Horrifying Revenge ready
        if pid == HOPS_TREVENANT and ally_ko:
            score += 400

        if score > best_score:
            best_score = score
            best_idx = card_opt_idx

    return best_idx


# =============================================================================
# SECTION 7: MAIN AGENT FUNCTION
# =============================================================================

def agent(obs_dict, config=None):
    """
    Main agent entry point. Called by the cabt engine for every decision.
    """
    # --- Deck submission (game start) ---
    if obs_dict.get("select") is None:
        _reset_memory()
        _memory["game_started"] = True
        return _DECK

    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)

    if not options:
        return _finalize_choice([], options, max_count)

    types = [opt.get("type") for opt in options]
    you, opp = _get_players(obs_dict)

    # --- Detect new turn and update memory ---
    if you:
        my_prizes = _prize_count(you)
        last_prizes = _memory.get("last_prize_count", 6)

        # Detect if opponent took prizes (our ally was KO'd)
        # This is approximate — if our prize count changed between decisions
        # within the same turn, it means opponent KO'd us last turn
        if opp:
            opp_prizes = _prize_count(opp)
            if opp_prizes < _memory.get("_last_opp_prizes", 6):
                _memory["ally_ko_last_turn"] = True
            _memory["_last_opp_prizes"] = opp_prizes

        _memory["last_prize_count"] = my_prizes

    # Check if this looks like a new turn (first main action decision)
    # A heuristic: if we see PLAY/ATTACH/EVOLVE/ABILITY/ATTACK/END/RETREAT together
    has_end = OPT_END in types
    has_main_actions = any(t in types for t in [OPT_PLAY, OPT_ATTACH, OPT_EVOLVE,
                                                  OPT_ABILITY, OPT_ATTACK, OPT_RETREAT])
    if has_end and has_main_actions:
        # This is a main action decision — likely start of our turn actions
        if not _memory.get("_in_main_phase"):
            _memory["turn"] += 1
            _new_turn_memory()
            _memory["_in_main_phase"] = True
            # Reset ally KO flag after we've had a chance to use it
            # (keep it True for the whole turn so Horrifying Revenge can use it)
    else:
        _memory["_in_main_phase"] = False

    # --- Build board evaluation ---
    board = None
    if you and opp:
        board = evaluate_board(you, opp)
        # Store all options in board for cross-referencing
        board["_all_options"] = options

    # ===== Decision routing =====

    # --- YES/NO decisions ---
    yes_indexes = [i for i, t in enumerate(types) if t == OPT_YES]
    no_indexes = [i for i, t in enumerate(types) if t == OPT_NO]

    if yes_indexes and no_indexes:
        # Both YES and NO available — this is a prompt (ability trigger, etc.)
        # Generally say YES to ability triggers (draw, damage boost)
        # But say NO in rare cases
        if board and board["hand_size"] >= 10:
            # Might not want to draw more if hand is huge
            # Still usually YES for abilities though
            pass
        return _finalize_choice([yes_indexes[0]], options, max_count)

    if yes_indexes and not no_indexes:
        # Only YES — must confirm
        return _finalize_choice([yes_indexes[0]], options, max_count)

    if no_indexes and not yes_indexes and len(options) == 1:
        # Only NO — forced
        return _finalize_choice([no_indexes[0]], options, max_count)

    # --- CARD selection (targets for Boss, items, bench selection, etc.) ---
    if all(t == OPT_CARD for t in types):
        if _memory.get("pending_boss") and opp and board:
            # Boss's Orders target selection
            chosen = _select_boss_target(options, types, opp, board)
            _memory["pending_boss"] = False
            return _finalize_choice([chosen], options, max_count)

        if _memory.get("retreated_this_turn") and board:
            # Choosing which bench Pokémon to promote after retreat
            chosen = _handle_retreat_target(options, types, you, opp, board)
            return _finalize_choice([chosen], options, max_count)

        # Generic card selection — pick first
        return _finalize_choice([0], options, max_count)

    # --- NUMBER selection (e.g., coin flip results) ---
    if all(t == OPT_NUMBER for t in types):
        return _finalize_choice([0], options, max_count)

    # --- DISCARD selection ---
    if all(t == OPT_DISCARD for t in types):
        if board:
            chosen = _select_discard(options, types, you, opp, board)
            return _finalize_choice([chosen], options, max_count)
        return _finalize_choice([0], options, max_count)

    # --- Main action decision (mixed action types) ---
    # This is the core decision: what to do on our turn

    # Special handling: if only attacks are available, pick best attack
    attack_indexes = [i for i, t in enumerate(types) if t == OPT_ATTACK]
    non_attack_non_end = [i for i, t in enumerate(types)
                          if t not in (OPT_ATTACK, OPT_END, OPT_NO)]

    if attack_indexes and not non_attack_non_end and board:
        # Only attacks and END available — pick best attack
        best_attack = _select_best_attack(options, types, you, opp, board)
        return _finalize_choice([best_attack], options, max_count)

    if board:
        # Full scoring-based selection
        best_idx = _select_main_action(options, types, you, opp, board)
        chosen_opt = options[best_idx]
        chosen_type = chosen_opt.get("type")

        # Update memory based on chosen action
        if chosen_type == OPT_PLAY:
            hand_pos = chosen_opt.get("index")
            card_id = _card_id_from_hand(you, hand_pos)
            if card_id in SUPPORTER_IDS:
                _memory["supporter_used_this_turn"] = True
            if card_id == BOSS_ORDERS:
                _memory["pending_boss"] = True
        elif chosen_type == OPT_ATTACH:
            _memory["energy_attached_this_turn"] = True
        elif chosen_type == OPT_RETREAT:
            _memory["retreated_this_turn"] = True
        elif chosen_type == OPT_ATTACK:
            # After attacking, ally_ko flag should reset next turn
            pass

        return _finalize_choice([best_idx], options, max_count)

    # --- Fallback: no board state available ---
    # Use simple priority: YES > EVOLVE > ABILITY > PLAY > ATTACH > ATTACK > END
    priority_order = [OPT_YES, OPT_EVOLVE, OPT_ABILITY, OPT_PLAY,
                      OPT_ATTACH, OPT_ATTACK, OPT_END, OPT_RETREAT,
                      OPT_DISCARD, OPT_NO]

    for target_type in priority_order:
        idxs = [i for i, t in enumerate(types) if t == target_type]
        if idxs:
            return _finalize_choice([idxs[0]], options, max_count)

    # Absolute fallback
    return _finalize_choice(list(range(len(options))), options, max_count)


# --- Keep random_agent for testing ---
def random_agent(obs_dict, config=None):
    """Random baseline agent for testing."""
    if obs_dict.get("select") is None:
        return _DECK
    select = obs_dict["select"]
    options = select.get("option", [])
    max_count = select.get("maxCount", 1)
    if not options:
        return []
    return random.sample(range(len(options)), min(max_count, len(options)))