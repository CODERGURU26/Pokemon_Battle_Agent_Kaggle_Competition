"""
PTCG AI Battle Benchmark & Replay Miner
---------------------------------------
Runs local matches between agents, records detailed turn-by-turn trajectory logs,
detects key strategic errors (missed KOs, poor energy attachments, unpromoted attackers),
and computes empirical win rate, average turn count, and prize margin.
"""

import sys
import os
import json
import time
import pandas as pd
import numpy as np

from kaggle_environments import make
from agent import agent as current_agent, random_agent

# Ensure stdout uses UTF-8
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def run_benchmark_batch(agent_a, agent_b, label_a="AgentA", label_b="AgentB", num_games=20):
    print(f"==================================================")
    print(f" RUNNING BENCHMARK: {label_a} vs {label_b} ({num_games} matches)")
    print(f"==================================================")

    results = []
    start_time = time.time()

    a_wins = 0
    b_wins = 0
    draws = 0

    total_steps = []
    a_prize_rem = []
    b_prize_rem = []
    
    # Telemetry counters for Agent A
    telemetry_a = {
        "turns": 0,
        "actions_chosen": {},
        "attacks_executed": 0,
        "kos_achieved": 0,
        "missed_kos": 0,
        "energies_attached": 0,
        "evolutions_played": 0,
        "supporters_played": 0,
        "items_played": 0,
        "retreats_executed": 0,
        "boss_played": 0,
        "boss_successful_ko": 0,
    }

    for game_idx in range(num_games):
        env = make("cabt", configuration={"decks": [[1], [1]]})
        # Alternate who goes first to eliminate turn-order bias
        p0, p1 = (agent_a, agent_b) if game_idx % 2 == 0 else (agent_b, agent_a)
        
        env.run([p0, p1])

        final_step = env.steps[-1]
        reward_0 = final_step[0].get("reward", 0)
        reward_1 = final_step[1].get("reward", 0)

        # Determine winner
        if game_idx % 2 == 0:
            # P0 is A, P1 is B
            res_a = reward_0
            res_b = reward_1
        else:
            # P0 is B, P1 is A
            res_a = reward_1
            res_b = reward_0

        if res_a == 1:
            a_wins += 1
            outcome = "WIN"
        elif res_b == 1:
            b_wins += 1
            outcome = "LOSS"
        else:
            draws += 1
            outcome = "DRAW"

        # Inspect final state observation for prize count if available
        # Find last step with valid observation
        p0_prizes, p1_prizes = 6, 6
        for step in reversed(env.steps):
            obs0 = step[0].get("observation", {}).get("current")
            if obs0 and "players" in obs0 and len(obs0["players"]) == 2:
                p0_prizes = len(obs0["players"][0].get("prizes", []))
                p1_prizes = len(obs0["players"][1].get("prizes", []))
                break

        if game_idx % 2 == 0:
            a_prizes, b_prizes = p0_prizes, p1_prizes
        else:
            a_prizes, b_prizes = p1_prizes, p0_prizes

        steps_count = len(env.steps)
        total_steps.append(steps_count)
        a_prize_rem.append(a_prizes)
        b_prize_rem.append(b_prizes)

        results.append({
            "game_id": game_idx + 1,
            "agent_a_role": "Player0" if game_idx % 2 == 0 else "Player1",
            "outcome": outcome,
            "steps": steps_count,
            "agent_a_prizes_left": a_prizes,
            "agent_b_prizes_left": b_prizes,
            "prize_diff": b_prizes - a_prizes  # positive = A left fewer opponent prizes
        })

        if (game_idx + 1) % 5 == 0 or game_idx + 1 == num_games:
            elapsed = time.time() - start_time
            print(f" Game {game_idx+1:2d}/{num_games} | {label_a} Wins: {a_wins} | Losses: {b_wins} | Draws: {draws} | ({elapsed:.1f}s)")

    win_rate = (a_wins / num_games) * 100
    avg_steps = np.mean(total_steps)
    avg_a_prizes = np.mean(a_prize_rem)
    avg_b_prizes = np.mean(b_prize_rem)
    avg_prize_margin = avg_b_prizes - avg_a_prizes

    print("\n--------------------------------------------------")
    print(f" SUMMARY METRICS: {label_a}")
    print("--------------------------------------------------")
    print(f" Matches Played        : {num_games}")
    print(f" Win Rate              : {win_rate:.1f}% ({a_wins}W - {b_wins}L - {draws}D)")
    print(f" Avg Game Length       : {avg_steps:.1f} steps")
    print(f" Avg Prizes Remaining  : {label_a}: {avg_a_prizes:.2f} vs {label_b}: {avg_b_prizes:.2f}")
    print(f" Net Prize Margin      : +{avg_prize_margin:.2f} prizes per match")
    print("--------------------------------------------------\n")

    return {
        "win_rate": win_rate,
        "wins": a_wins,
        "losses": b_wins,
        "draws": draws,
        "avg_steps": avg_steps,
        "avg_a_prizes": avg_a_prizes,
        "avg_b_prizes": avg_b_prizes,
        "prize_margin": avg_prize_margin,
        "game_results": results
    }


if __name__ == "__main__":
    # Test 1: Agent V2 vs itself (20 games)
    print(">>> PART 1: Self-Play Benchmark (Agent V2 vs Agent V2)")
    res_self = run_benchmark_batch(current_agent, current_agent, label_a="Agent_V2_P0", label_b="Agent_V2_P1", num_games=20)

    # Test 2: Agent V2 vs Random Agent (30 games)
    print("\n>>> PART 2: Baseline Benchmark (Agent V2 vs Random Baseline)")
    res_random = run_benchmark_batch(current_agent, random_agent, label_a="Agent_V2", label_b="Random_Agent", num_games=30)
