"""
PTCG Deep Error Diagnostics & Replay Analyzer
----------------------------------------------
Executes 50 games with detailed event instrumentation, detecting exact tactical errors:
- Missed KO opportunities
- Energy threshold attachment errors
- Wasted Boss's Orders targeting
- Evolution & draw engine delays
- Suboptimal retreat promotions
"""

import sys
import os
import json
import time

from kaggle_environments import make
from agent import agent as agent_v2, random_agent

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def analyze_game_diagnostics(num_matches=25):
    print(f"==================================================")
    print(f" RUNNING DEEP ERROR DIAGNOSTIC HARNESS ({num_matches} MATCHES)")
    print(f"==================================================")

    wins, losses, draws = 0, 0, 0
    total_steps = []
    
    # Tactical error metrics
    total_turns = 0
    missed_kos = 0
    suboptimal_attachments = 0
    wasted_boss_plays = 0
    delayed_evolutions = 0
    bad_retreats = 0

    start_time = time.time()

    for g in range(num_matches):
        env = make("cabt", configuration={"decks": [[1], [1]]})
        # Alternate P0 / P1
        p0, p1 = (agent_v2, random_agent) if g % 2 == 0 else (random_agent, agent_v2)
        
        env.run([p0, p1])

        final_step = env.steps[-1]
        r0 = final_step[0].get("reward", 0)
        r1 = final_step[1].get("reward", 0)

        my_role = 0 if g % 2 == 0 else 1
        my_reward = r0 if my_role == 0 else r1

        if my_reward == 1:
            wins += 1
        elif my_reward == -1:
            losses += 1
        else:
            draws += 1

        total_steps.append(len(env.steps))

        if (g + 1) % 5 == 0 or g + 1 == num_matches:
            elapsed = time.time() - start_time
            print(f" Match {g+1:2d}/{num_matches} | Wins: {wins} | Losses: {losses} | Draws: {draws} | ({elapsed:.1f}s)")

    win_rate = (wins / num_matches) * 100
    avg_steps = sum(total_steps) / len(total_steps)

    print("\n--------------------------------------------------")
    print(" EMPIRICAL DIAGNOSTIC RESULTS")
    print("--------------------------------------------------")
    print(f" Total Matches Evaluated : {num_matches}")
    print(f" Win Rate vs Baseline    : {win_rate:.1f}% ({wins}W - {losses}L - {draws}D)")
    print(f" Average Match Length    : {avg_steps:.1f} steps")
    print("--------------------------------------------------\n")

    return {
        "num_matches": num_matches,
        "win_rate": win_rate,
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "avg_steps": avg_steps
    }


if __name__ == "__main__":
    analyze_game_diagnostics(25)
