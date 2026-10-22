#!/usr/bin/env python3
"""
AIML Project — Live Guided Presentation
Press ENTER at each step to execute the pre-filled command.
Everything is real — no simulation, no fake output.
"""

import os
import sys
import subprocess

CYAN    = "\033[96m"
GREEN   = "\033[92m"
YELLOW  = "\033[93m"
RED     = "\033[91m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR    = os.path.join(PROJECT_DIR, "3scale_ws_api_for_java")

def clear():
    os.system("clear")

def header():
    print(f"{CYAN}{BOLD}")
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║   🤖 GitConflict AI — Merge Conflict Prediction System          ║")
    print("  ║   XGBoost ML Model  •  Real Git Conflict Analysis               ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")

def section(title):
    print(f"\n{YELLOW}{BOLD}{'─'*68}")
    print(f"  {title}")
    print(f"{'─'*68}{RESET}\n")

def run_step(description, cmd, cwd=None):
    """Show description, show command, wait for Enter, run it."""
    print(f"{DIM}  {description}{RESET}")
    print(f"{GREEN}{BOLD}  $ {RESET}{BOLD}{cmd}{RESET}")
    try:
        input(f"  {DIM}[Press ENTER to run]{RESET}")
    except (EOFError, KeyboardInterrupt):
        print()
    print()
    subprocess.run(cmd, shell=True, cwd=cwd or PROJECT_DIR)
    print()

def pause(msg=""):
    if msg:
        print(f"\n{GREEN}  ✔  {msg}{RESET}")
    try:
        input(f"\n  {DIM}─── Press ENTER to continue ───{RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()

def main():
    clear()
    header()

    print(f"""  {BOLD}What this project does:{RESET}
  We trained an XGBoost ML model on historical Git merge conflicts.
  When a developer merges two branches and gets a conflict, our system
  automatically extracts 12 conflict features and predicts the best resolution:

    {GREEN}• keep_local{RESET}    — accept our branch changes
    {CYAN}• keep_incoming{RESET} — accept their branch changes  
    {YELLOW}• combine_both{RESET}  — manual combination needed

  {BOLD}Today's Demo:{RESET}
  We use a 5th UNSEEN repository (3scale_ws_api_for_java) — never in training.
  We take two real branches, trigger a real Git conflict, and run our AI system.

  {BOLD}Steps:{RESET}
  1. Inspect the 5th unseen GitHub repository
  2. Set up two real conflicting branches
  3. Show exactly what each branch changed
  4. Preview the conflicting Java source file
  5. Run our AI Merge tool — extract features, get prediction, resolve
  6. Verify the resolved commit in git log
""")
    pause()

    # ─── STEP 1: The 5th unseen repo ─────────────────────────────────────────
    clear()
    header()
    section("STEP 1 — The 5th Unknown Repository (Never Seen by Model)")

    run_step(
        "This is 3scale_ws_api_for_java — cloned from merge-nature.netlify.app.\nNever used in training. Real-world Java API project.",
        "git log --oneline -6",
        REPO_DIR
    )

    run_step(
        "Show commit details for the two branches we will merge:",
        "git log -1 --format='LOCAL :    %h | Author: %ae | %s' 4650578d && "
        "git log -1 --format='INCOMING:  %h | Author: %ae | %s' d623f491",
        REPO_DIR
    )

    pause("Two real commits by two different developers on the same Java file")

    # ─── STEP 4: Set up branches ──────────────────────────────────────────────
    clear()
    header()
    section("STEP 2 — Set Up Conflicting Branches")

    # Silent cleanup first
    subprocess.run("git checkout -f master 2>/dev/null; git branch -D feature/local-changes feature/incoming-update 2>/dev/null; true",
                   shell=True, cwd=REPO_DIR, capture_output=True)

    run_step(
        "Create feature/local-changes from commit 4650578d (tiago@3scale.net):",
        "git checkout -b feature/local-changes 4650578d",
        REPO_DIR
    )

    run_step(
        "Create feature/incoming-update pointing to commit d623f491 (geoffd123@hotmail.com):",
        "git branch feature/incoming-update d623f491",
        REPO_DIR
    )

    run_step(
        "Confirm both branches exist and their tips:",
        "git branch -v | grep feature/",
        REPO_DIR
    )

    pause()

    # ─── STEP 5: Show the diff (what each branch changed) ────────────────────
    clear()
    header()
    section("STEP 3 — What Each Branch Changed vs Common Ancestor")

    run_step(
        "Lines changed in feature/local-changes since the common ancestor:",
        "git diff --stat $(git merge-base feature/local-changes feature/incoming-update) feature/local-changes",
        REPO_DIR
    )

    run_step(
        "Lines changed in feature/incoming-update since the common ancestor:",
        "git diff --stat $(git merge-base feature/local-changes feature/incoming-update) feature/incoming-update",
        REPO_DIR
    )

    pause("Both branches touched the same Java file → conflict guaranteed")

    # ─── STEP 6: Show the actual Java code that will conflict ─────────────────
    clear()
    header()
    section("STEP 4 — Preview the Conflicting Java File")

    run_step(
        "What does the local branch version of Api2Impl.java look like? (first 30 lines)",
        "git show feature/local-changes:src/net/threescale/api/v2/Api2Impl.java 2>/dev/null | head -30 || "
        "echo '(binary/missing — Java conflict is in the class logic)'",
        REPO_DIR
    )

    run_step(
        "Show the diff of the conflicting section between both branches:",
        "git diff feature/local-changes feature/incoming-update -- src/net/threescale/api/v2/Api2Impl.java | head -50",
        REPO_DIR
    )

    pause()

    # ─── STEP 7: Run the AI Merge Tool ───────────────────────────────────────
    clear()
    header()
    section("STEP 5 — Run AI Smart Merge (Feature Extraction + Model Prediction)")

    print(f"""  {BOLD}What happens when you run ai_merge.py:{RESET}
  1. Triggers real {BOLD}git merge --no-commit --no-ff{RESET}
  2. Scans working tree → extracts 12 conflict features live
  3. Sends feature vector to XGBoost model for inference
  4. Displays prediction + confidence
  5. Lets you resolve with one keypress
""")

    try:
        input(f"  {DIM}[Press ENTER to run ai_merge.py on the real repo]{RESET}\n")
    except (EOFError, KeyboardInterrupt):
        print()

    print(f"{GREEN}{BOLD}  $ python3 ai_merge.py feature/incoming-update{RESET}\n")
    subprocess.run(
        f"{sys.executable} {os.path.join(PROJECT_DIR, 'ai_merge.py')} feature/incoming-update",
        shell=True, cwd=REPO_DIR
    )

    # ─── STEP 8: Show the result in git log ──────────────────────────────────
    clear()
    header()
    section("STEP 6 — Verify: Real Commit Created in Git Log")

    run_step(
        "Check the git log — a real AI-resolved merge commit should appear at the top:",
        "git log --oneline -5",
        REPO_DIR
    )

    run_step(
        "Show the full details of the merge commit (author, message, files changed):",
        "git show --stat HEAD",
        REPO_DIR
    )

    run_step(
        "Confirm the working tree is now clean (no pending conflicts):",
        "git status",
        REPO_DIR
    )

    pause()

    # ─── DONE ─────────────────────────────────────────────────────────────────
    clear()
    header()
    section("DEMO COMPLETE — What We Showed")
    print(f"""
  {GREEN}1.{RESET} Cloned a real unseen repo: {BOLD}3scale_ws_api_for_java{RESET} (from Merge-Nature dataset, never in training)
  {GREEN}2.{RESET} Set up two real developer branches (different authors, same Java file)
  {GREEN}3.{RESET} Showed exactly what each branch changed vs the common ancestor
  {GREEN}4.{RESET} Previewed the actual conflicting Java source code diff
  {GREEN}5.{RESET} Ran our AI Smart Merge tool:
       • Real git merge triggered → conflict detected in Api2Impl.java
       • 12 features auto-extracted from the live Git working tree
       • XGBoost model returned prediction + confidence score
       • Conflict resolved → real git commit created
  {GREEN}6.{RESET} Verified the merge commit in git log with git show --stat

  {BOLD}Model:{RESET}     XGBoost V3  |  3 classes  |  Trained on 4 open-source Java repos
  {BOLD}Dataset:{RESET}   Merge-Nature research dataset (GitHub merge conflicts)
  {BOLD}Pipeline:{RESET}  Git → Feature Extraction (12 features) → XGBoost → Prediction
""")
    print(f"{CYAN}{'─'*68}{RESET}\n")


if __name__ == "__main__":
    main()
