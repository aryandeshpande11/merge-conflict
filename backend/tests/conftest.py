import os
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.model_service import model_service


@pytest.fixture(scope="session", autouse=True)
def initialize_model():
    """Ensure ModelService loads the model once for all tests."""
    model_service.load_model()
    assert model_service.is_loaded, f"Failed to initialize model: {model_service.load_error}"


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def valid_payload() -> Dict[str, Any]:
    """Standard valid 12-feature prediction payload."""
    return {
        "Conflicting_Files_Count": 2,
        "Author_Match": 0,
        "Lines_Changed_Local": 15,
        "Lines_Changed_Incoming": 10,
        "Total_Lines_Changed": 25,
        "Conflict_Chunk_Count": 3,
        "Avg_Chunk_Size": 8.33,
        "Local_Conflict_Lines": 15,
        "Incoming_Conflict_Lines": 10,
        "Local_Incoming_Ratio": 1.5,
        "Primary_File_Type": 0,
        "Time_Diff_Hours": 24.5,
    }


@pytest.fixture
def sample_conflict_text() -> str:
    """Standard Git conflict marker text."""
    return (
        "<<<<<<< HEAD\n"
        "public void calculate() {\n"
        "    int localResult = 42;\n"
        "}\n"
        "=======\n"
        "public void calculate() {\n"
        "    int incomingResult = 99;\n"
        "}\n"
        ">>>>>>> feature-branch\n"
    )


@pytest.fixture
def git_repo_fixture(tmp_path):
    """
    Creates a temporary Git repository fixture containing:
    1. A base commit on 'main'
    2. A branch 'branch-local' with edits
    3. A branch 'branch-incoming' with conflicting edits
    4. A merge commit resolving the conflict
    5. A non-merge commit
    6. A clean merge commit with no conflicts
    """
    repo_dir = tmp_path / "fixture_repo"
    repo_dir.mkdir()

    def run_git(args):
        return subprocess.run(
            ["git"] + args,
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )

    # 1. Init
    run_git(["init", "-b", "main"])
    run_git(["config", "user.name", "Tester"])
    run_git(["config", "user.email", "tester@example.com"])

    # 2. Base commit
    file_path = repo_dir / "Service.java"
    file_path.write_text("public class Service {\n    int a = 1;\n}\n", encoding="utf-8")
    run_git(["add", "Service.java"])
    run_git(["commit", "-m", "Initial commit"])
    base_commit = run_git(["rev-parse", "HEAD"]).stdout.strip()

    # 3. Local branch
    run_git(["checkout", "-b", "branch-local"])
    file_path.write_text("public class Service {\n    int a = 100;\n}\n", encoding="utf-8")
    run_git(["commit", "-am", "Local change"])
    local_commit = run_git(["rev-parse", "HEAD"]).stdout.strip()

    # 4. Incoming branch
    run_git(["checkout", "main"])
    run_git(["checkout", "-b", "branch-incoming"])
    file_path.write_text("public class Service {\n    int a = 200;\n}\n", encoding="utf-8")
    run_git(["commit", "-am", "Incoming change"])
    incoming_commit = run_git(["rev-parse", "HEAD"]).stdout.strip()

    # 5. Merge with conflict and resolve
    run_git(["checkout", "branch-local"])
    subprocess.run(["git", "merge", "branch-incoming"], cwd=str(repo_dir), capture_output=True, text=True)
    file_path.write_text("public class Service {\n    int a = 300;\n}\n", encoding="utf-8")
    run_git(["add", "Service.java"])
    run_git(["commit", "-m", "Merge branch-incoming into branch-local"])
    conflict_merge_commit = run_git(["rev-parse", "HEAD"]).stdout.strip()

    # 6. Clean merge commit (no conflict)
    other_file = repo_dir / "Other.java"
    other_file.write_text("public class Other {}", encoding="utf-8")
    run_git(["checkout", "-b", "clean-branch-1"])
    run_git(["add", "Other.java"])
    run_git(["commit", "-m", "Add Other.java"])

    run_git(["checkout", "branch-local"])
    run_git(["checkout", "-b", "clean-branch-2"])
    readme_file = repo_dir / "README.md"
    readme_file.write_text("# Readme", encoding="utf-8")
    run_git(["add", "README.md"])
    run_git(["commit", "-m", "Add README.md"])

    run_git(["merge", "--no-ff", "clean-branch-1", "-m", "Clean merge commit"])
    clean_merge_commit = run_git(["rev-parse", "HEAD"]).stdout.strip()

    # Checkout back to main
    run_git(["checkout", "main"])

    return {
        "repo_dir": repo_dir,
        "base_commit": base_commit,
        "conflict_merge_commit": conflict_merge_commit,
        "clean_merge_commit": clean_merge_commit,
        "non_merge_commit": base_commit,
    }
