"""Analyze the cards in the current deck embedded in agent.py."""
import csv
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

deck_ids = {65, 878, 1122, 1171, 1152, 1086, 1227, 1255, 19, 11, 66, 1097, 1115, 879, 304, 1210, 1182, 1194, 12}

with open('EN_Card_Data.csv', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    rows = list(reader)

cols = list(rows[0].keys())
stage_col = cols[4]
move_col = cols[13]
cost_col = cols[14]
dmg_col = cols[15]
effect_col = cols[16]
prev_col = cols[7]

print("=== DECK CARDS ===")
for r in rows:
    cid = int(r['Card ID'])
    if cid in deck_ids:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:80]
        print(f"ID={cid:>5} | {r['Card Name']:30s} | Stage={r[stage_col]:25s} | HP={r['HP']:>5} | Type={r['Type']:5s} | Prev={r[prev_col]:20s} | Move={r[move_col]:25s} | Cost={str(r.get(cost_col,'')):12s} | Dmg={str(r.get(dmg_col,'')):8s} | Eff={eff}")

# Look for evolution lines connected to our pokemon
print("\n=== EVOLUTION LINES FOR DECK POKEMON ===")
deck_names = set()
for r in rows:
    if int(r['Card ID']) in deck_ids:
        deck_names.add(r['Card Name'])

for r in rows:
    prev = r[prev_col]
    if prev in deck_names or r['Card Name'] in deck_names:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:60]
        print(f"ID={int(r['Card ID']):>5} | {r['Card Name']:30s} | Stage={r[stage_col]:25s} | HP={r['HP']:>5} | Prev={prev:20s} | Move={r[move_col]:25s} | Cost={str(r.get(cost_col,'')):12s} | Dmg={str(r.get(dmg_col,'')):8s}")

# All Supporter and Item cards
print("\n=== ALL SUPPORTERS ===")
for r in rows:
    stage = r[stage_col]
    if 'Supporter' in stage:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:120]
        print(f"ID={int(r['Card ID']):>5} | {r['Card Name']:30s} | {stage:20s} | Eff={eff}")

print("\n=== ALL ITEMS ===")
for r in rows:
    stage = r[stage_col]
    if 'Item' in stage:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:120]
        print(f"ID={int(r['Card ID']):>5} | {r['Card Name']:30s} | {stage:20s} | Eff={eff}")

# Pokemon with evolution chains (Stage 1, Stage 2)
print("\n=== STAGE 1 POKEMON (for evolution decks) ===")
for r in rows:
    stage = r[stage_col]
    if 'Stage 1' in stage:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:60]
        print(f"ID={int(r['Card ID']):>5} | {r['Card Name']:30s} | HP={r['HP']:>5} | Type={r['Type']:5s} | Prev={r[prev_col]:20s} | Move={r[move_col]:25s} | Cost={str(r.get(cost_col,'')):12s} | Dmg={str(r.get(dmg_col,'')):8s}")

print("\n=== STAGE 2 POKEMON ===")
for r in rows:
    stage = r[stage_col]
    if 'Stage 2' in stage:
        eff = str(r.get(effect_col, '')).replace('\n', ' ')[:60]
        print(f"ID={int(r['Card ID']):>5} | {r['Card Name']:30s} | HP={r['HP']:>5} | Type={r['Type']:5s} | Prev={r[prev_col]:20s} | Move={r[move_col]:25s} | Cost={str(r.get(cost_col,'')):12s} | Dmg={str(r.get(dmg_col,'')):8s}")
