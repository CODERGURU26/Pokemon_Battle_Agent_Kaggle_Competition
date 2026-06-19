"""
build_deck.py
--------------
Reads EN_Card_Data.csv and builds a simple, low-variance 60-card deck
focused on ONE energy type (default: Fire / {R}), then writes deck.csv
in the format the cabt engine expects (one Card ID per line, 60 lines).

WHY a single-type deck?
A mono-type deck means almost every card in your hand can power almost
every attacker. That keeps your rule-based agent's energy-attachment
logic simple (no juggling "do I have enough Water AND Fire energy?").
You can experiment with other types later by changing TARGET_TYPE below.

HOW IT SCORES POKEMON
Many Pokemon have multiple rows in the CSV (one row per move/ability).
We group all rows by Card ID first, then for each Pokemon we look at
its best attacking move and compute a simple "damage per energy" score:
    score = max_damage / (number of energy symbols in that move's cost)
Pokemon with no usable damage value (abilities only, or "x" damage that
depends on game state) get a small fallback score so they can still be
picked if needed, but real attackers are preferred.

HOW TO RUN
    python build_deck.py
This writes deck.csv in the same folder. Open it and you'll see 60 lines
of numbers -- those are Card IDs from EN_Card_Data.csv.
"""

import re
import csv
import sys
from collections import defaultdict

CSV_PATH = "EN_Card_Data.csv"
OUTPUT_PATH = "deck.csv"

# Change this to build a deck around a different type.
# Common type symbols seen in this dataset: {G} Grass, {R} Fire, {W} Water,
# {F} Fighting, {D} Darkness, {C} Colorless, {L} Lightning, {P} Psychic, {M} Metal
TARGET_TYPE = "{R}"

# Basic Energy card IDs are fixed in this dataset (rows 1-8, one per type).
# We map type symbol -> Basic Energy Card ID by reading the CSV directly
# below, so this script doesn't break if the dataset ever changes order.


def count_energy_symbols(cost_str):
    """Cost strings look like '{R}{R}' or '{R}●●' where '●' = any/colorless
    energy required by some special cards. We count total symbols as the
    energy cost size, regardless of symbol type, for a rough cost estimate."""
    if not cost_str or cost_str == "n/a" or str(cost_str) == "nan":
        return 0
    cost_str = str(cost_str)
    braces = re.findall(r"\{[^}]+\}", cost_str)
    dots = cost_str.count("●")
    return len(braces) + dots


def parse_damage(damage_str):
    """Damage can be a plain number, blank, or have suffixes like '30x' or
    '120+'. We strip non-digit trailing characters and parse what's left.
    Returns None if there's no usable numeric damage."""
    if damage_str is None:
        return None
    s = str(damage_str).strip()
    if s == "" or s.lower() == "nan":
        return None
    match = re.match(r"(\d+)", s)
    if not match:
        return None
    return int(match.group(1))


def load_cards(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def main():
    rows = load_cards(CSV_PATH)

    # Find the Basic Energy card ID matching TARGET_TYPE
    basic_energy_id = None
    for row in rows:
        if row["Stage (Pokémon)/Type (Energy and Trainer)"] == "Basic Energy" \
                and row["Type"].strip() == TARGET_TYPE:
            basic_energy_id = int(row["Card ID"])
            break

    if basic_energy_id is None:
        print(f"Could not find a Basic Energy card for type {TARGET_TYPE}.")
        sys.exit(1)

    # Group rows by Card ID so each Pokemon is scored once, not once per move
    by_card_id = defaultdict(list)
    for row in rows:
        by_card_id[row["Card ID"]].append(row)

    candidates = []  # (score, card_id, name, hp, stage)
    for card_id, card_rows in by_card_id.items():
        first = card_rows[0]
        stage = first["Stage (Pokémon)/Type (Energy and Trainer)"]
        ptype = first["Type"].strip()

        # Only consider Basic Pokemon of our target type for simplicity.
        # (Basic Pokemon don't need an evolution line to be playable --
        # keeps deck construction and early-game logic much simpler.)
        if stage != "Basic Pokémon" or ptype != TARGET_TYPE:
            continue

        best_score = 0.0
        best_damage = None
        for r in card_rows:
            dmg = parse_damage(r.get("Damage"))
            cost = count_energy_symbols(r.get("Cost"))
            if dmg is not None and cost > 0:
                score = dmg / cost
                if score > best_score:
                    best_score = score
                    best_damage = dmg

        if best_damage is None:
            # No clean numeric attack found (ability-only or scaling damage)
            # -- give a small fallback score so it's not auto-excluded,
            # but real attackers will rank above it.
            best_score = 0.1

        try:
            hp = float(first["HP"])
        except (ValueError, TypeError):
            hp = 0.0

        candidates.append((best_score, int(card_id), first["Card Name"], hp, stage))

    # Rank attackers by damage-per-energy score, prefer higher HP as tiebreak
    candidates.sort(key=lambda c: (c[0], c[3]), reverse=True)

    print(f"Found {len(candidates)} Basic Pokemon of type {TARGET_TYPE}.")
    print("\nTop 10 by damage-per-energy score:")
    for score, cid, name, hp, stage in candidates[:10]:
        print(f"  score={score:5.1f}  HP={hp:5.0f}  id={cid:<5}  {name}")

    # Pick our top attackers. We'll run 4 copies each of the top 3
    # attackers (12 cards), 1 copy of the next-best backup (1 card),
    # and fill the rest with Basic Energy to keep things simple and
    # consistent. Real competitive decks also use Trainer/Supporter
    # cards, but we're keeping this first version intentionally simple
    # so it's easy to read, debug, and extend.
    top_attackers = candidates[:3]
    deck = []
    for score, cid, name, hp, stage in top_attackers:
        deck.extend([cid] * 4)  # 4 copies is the max allowed per card normally

    backup = candidates[3] if len(candidates) > 3 else None
    if backup:
        deck.extend([backup[1]] * 2)

    # Fill remaining slots with Basic Energy of our target type
    remaining = 60 - len(deck)
    deck.extend([basic_energy_id] * remaining)

    if len(deck) != 60:
        print(f"WARNING: deck has {len(deck)} cards, expected 60.")

    with open(OUTPUT_PATH, "w", newline="") as f:
        for card_id in deck:
            f.write(f"{card_id}\n")

    print(f"\nWrote {len(deck)}-card deck to {OUTPUT_PATH} (for your own reference)")
    print("Attackers used:")
    for score, cid, name, hp, stage in top_attackers:
        print(f"  4x  id={cid:<5} {name} (HP {hp:.0f})")
    if backup:
        print(f"  2x  id={backup[1]:<5} {backup[2]} (HP {backup[3]:.0f})")
    print(f"  {remaining}x  Basic Energy id={basic_energy_id} ({TARGET_TYPE})")
    print("\nNOTE: This is a deliberately simple starter deck (no Trainers/")
    print("Supporters/evolutions yet) so the rule-based agent stays easy to")
    print("reason about. Once your agent works end-to-end, come back and")
    print("swap in a more advanced deck.")

    # IMPORTANT: agent.py does NOT read deck.csv at runtime. Kaggle executes
    # main.py as a raw code string with no __file__ available, so it can't
    # locate a sibling file on disk. Instead, agent.py embeds the deck
    # directly as a Python list. If you change your deck, copy the block
    # printed below and paste it into agent.py's "_DECK = [...]" assignment.
    print("\n" + "=" * 60)
    print("COPY THIS into agent.py's _DECK = [...] if you change your deck:")
    print("=" * 60)
    print("_DECK = [")
    for i in range(0, len(deck), 12):
        chunk = deck[i:i + 12]
        print("    " + ", ".join(str(c) for c in chunk) + ",")
    print("]")


if __name__ == "__main__":
    main()
