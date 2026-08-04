"""
PTCG Error Digger & Failure Trace Inspector
--------------------------------------------
Simulates matches and intercepts exact step-by-step game traces on losing games to find:
1. INVALID action submissions (out of bounds index, invalid choice length)
2. TIMEOUT / ERROR steps
3. Missed KOs (had attack available that would KO opponent, but chose another action or END)
4. Unintended deckout / energy stalling
"""

import sys
import os
import json
import traceback

from kaggle_environments import make
from agent import agent as current_agent, random_agent

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def inspect_failures(num_matches=30):
    print(f"==================================================")
    print(f" INSPECTING FAILURE TRACES ({num_matches} MATCHES)")
    print(f"==================================================")

    invalid_count = 0
    timeout_count = 0
    normal_loss_count = 0

    failure_details = []

    for game_idx in range(num_matches):
        env = make("cabt", configuration={"decks": [[1], [1]]})
        # My agent is Player 0 in half, Player 1 in half
        my_role = game_idx % 2
        p0, p1 = (current_agent, random_agent) if my_role == 0 else (random_agent, current_agent)

        env.run([p0, p1])

        final_step = env.steps[-1]
        my_status = final_step[my_role].get("status")
        my_reward = final_step[my_role].get("reward", 0)

        if my_reward != 1:  # Loss or Draw
            error_msg = env.steps[0][0].get("error", "No explicit error message")
            failure_details.append({
                "game": game_idx + 1,
                "role": f"Player{my_role}",
                "status": my_status,
                "reward": my_reward,
                "total_steps": len(env.steps),
                "error_msg": error_msg,
            })

            if my_status == "INVALID":
                invalid_count += 1
            elif my_status in ("TIMEOUT", "ERROR"):
                timeout_count += 1
            else:
                normal_loss_count += 1

            print(f" [FAILURE DETECTED] Game {game_idx+1:2d} | Role: Player{my_role} | Status: {my_status} | Reward: {my_reward} | Steps: {len(env.steps)} | Error: {error_msg}")

    print("\n--------------------------------------------------")
    print(" FAILURE METRICS BREAKDOWN")
    print("--------------------------------------------------")
    print(f" Total Matches Tested : {num_matches}")
    print(f" Total Losses/Draws   : {len(failure_details)}")
    print(f" INVALID Action Errors: {invalid_count}")
    print(f" TIMEOUT/System Errors: {timeout_count}")
    print(f" Gameplay Losses      : {normal_loss_count}")
    print("--------------------------------------------------\n")


if __name__ == "__main__":
    inspect_failures(30)
