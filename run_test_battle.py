"""
run_test_battle.py
-------------------
Runs a local test battle using your agent (from agent.py) against itself,
and saves a visual HTML replay you can open in a browser.

HOW TO RUN
    python run_test_battle.py

WHAT IT DOES
  1. Loads your agent function from agent.py.
  2. Starts a cabt battle: your agent vs. itself (mirror match).
  3. Prints the final result (win/loss/draw + how many steps it took).
  4. Saves result.html in this same folder -- open it in any browser to
     watch a turn-by-turn visual replay of the match.

WHY TEST AGAINST YOURSELF FIRST?
This is exactly what Kaggle does too -- when you upload a submission,
it first runs a "Validation Episode" of your agent against a copy of
itself before letting it loose on the ladder. If your agent can't even
finish a mirror match cleanly, it's not ready to submit yet.

ALSO INCLUDED: a quick comparison vs. the random_agent baseline, so you
can confirm your rule-based logic is actually doing something different
from (and hopefully better than) picking moves at random.
"""

from kaggle_environments import make
from agent import agent, random_agent


def run_one(agent_a, agent_b, label):
    # The "decks" passed into make() here are placeholders -- our agent
    # ignores them and submits its OWN deck (embedded directly inside
    # agent.py) the moment the engine asks for it. This matches how
    # Kaggle's real submission flow works: only your agent.py controls
    # what deck you actually play.
    env = make("cabt", configuration={"decks": [[1], [1]]})
    env.run([agent_a, agent_b])

    final = env.steps[-1]
    status_a, status_b = final[0]["status"], final[1]["status"]
    reward_a, reward_b = final[0]["reward"], final[1]["reward"]

    print(f"\n--- {label} ---")
    print(f"Steps played: {len(env.steps)}")
    print(f"Final status: player0={status_a}  player1={status_b}")
    print(f"Final reward: player0={reward_a}  player1={reward_b}")

    if reward_a == 1:
        print("Result: Player 0 won")
    elif reward_b == 1:
        print("Result: Player 1 won")
    else:
        print("Result: Draw")

    return env


if __name__ == "__main__":
    print("Running mirror match: your agent vs. itself...")
    env = run_one(agent, agent, "Your agent vs itself")

    print("\nSaving HTML replay to result.html ...")
    try:
        with open("result.html", "w", encoding="utf-8") as f:
            f.write(env.render(mode="html"))
        print("Done. Open result.html in a browser to watch the replay.")
    except Exception as e:
        print(f"(Skipping HTML replay -- rendering not available: {e})")
        print("This does NOT affect your agent or submission, it's just a visual extra.")

    print("\nRunning sanity check: your agent vs. random baseline...")
    run_one(agent, random_agent, "Your agent (P0) vs random (P1)")
