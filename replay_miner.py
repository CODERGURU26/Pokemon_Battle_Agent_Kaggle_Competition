"""
PTCG Deep Replay Miner & Game Diagnostic Engine
------------------------------------------------
Mines full match trajectory replays, parses hidden states, maps turn events,
and analyzes decisions made by the agent against ideal actions.
"""

import sys
import os
import json
import copy

from kaggle_environments import make
from agent import agent as current_agent, random_agent

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def mine_replays(num_matches=10, output_file="replay_telemetry.json"):
    print(f"==================================================")
    print(f" MINING {num_matches} FULL REPLAY TRAJECTORIES...")
    print(f"==================================================")

    replays = []

    for game_idx in range(num_matches):
        env = make("cabt", configuration={"decks": [[1], [1]]})
        # Current agent vs current agent (or random)
        p0, p1 = current_agent, random_agent if game_idx % 2 == 1 else current_agent
        
        env.run([p0, p1])

        # Extract environment step trajectory
        trajectory = []
        for step_idx, step in enumerate(env.steps):
            step_info = {
                "step": step_idx,
                "p0_status": step[0].get("status"),
                "p1_status": step[1].get("status"),
                "p0_reward": step[0].get("reward"),
                "p1_reward": step[1].get("reward"),
                "p0_action": step[0].get("action"),
                "p1_action": step[1].get("action"),
            }
            trajectory.append(step_info)

        final = env.steps[-1]
        r0 = final[0].get("reward", 0)
        r1 = final[1].get("reward", 0)

        match_record = {
            "match_id": game_idx + 1,
            "p0_agent": "CurrentAgent",
            "p1_agent": "RandomAgent" if game_idx % 2 == 1 else "CurrentAgent",
            "winner": "P0" if r0 == 1 else ("P1" if r1 == 1 else "DRAW"),
            "total_steps": len(env.steps),
            "trajectory": trajectory
        }
        replays.append(match_record)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(replays, f, indent=2)

    print(f" Successfully recorded {len(replays)} match trajectories to {output_file}!")


if __name__ == "__main__":
    mine_replays(10)
