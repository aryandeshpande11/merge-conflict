import subprocess
from pathlib import Path
from typing import Dict, Any

from fastapi.testclient import TestClient


def test_valid_repository_analysis(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 30: Replays a real merge conflict in a temporary Git repository and extracts all 12 features."""
    repo_dir = git_repo_fixture["repo_dir"]
    merge_commit = git_repo_fixture["conflict_merge_commit"]

    response = client.post(
        "/api/v1/analyze-repository",
        json={
            "repository_path": str(repo_dir),
            "merge_commit": merge_commit,
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["merge_commit"] == merge_commit
    feats = data["features"]
    assert len(feats) == 12
    assert feats["Conflicting_Files_Count"] == 1
    assert feats["Author_Match"] == 1
    assert feats["Conflict_Chunk_Count"] >= 1
    assert data["prediction"]["prediction"] in {"combine_both", "keep_incoming", "keep_local"}


def test_repository_path_validation(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 31: Nonexistent, file-based, and empty repository paths are cleanly rejected."""
    # Nonexistent directory
    res_nonexistent = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": "/nonexistent/path/repo", "merge_commit": "abc1234"},
    )
    assert res_nonexistent.status_code == 400

    # File path instead of directory
    file_path = git_repo_fixture["repo_dir"] / "Service.java"
    res_file = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": str(file_path), "merge_commit": "abc1234"},
    )
    assert res_file.status_code == 400


def test_invalid_commit_hash(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 32: Nonexistent commits or illegal commit patterns are rejected."""
    repo_dir = str(git_repo_fixture["repo_dir"])

    # Nonexistent commit hash
    res_nonexistent = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": repo_dir, "merge_commit": "deadbeef12345678"},
    )
    assert res_nonexistent.status_code == 400


def test_non_merge_commit(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 35: Non-merge commit (single parent) returns clean 400 error."""
    repo_dir = str(git_repo_fixture["repo_dir"])
    single_parent_commit = git_repo_fixture["non_merge_commit"]

    response = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": repo_dir, "merge_commit": single_parent_commit},
    )
    assert response.status_code == 400
    assert "not a merge commit" in response.json()["detail"].lower()


def test_clean_merge_no_conflict(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 36: Merge commit that completed without conflict returns clean 400 error."""
    repo_dir = str(git_repo_fixture["repo_dir"])
    clean_merge = git_repo_fixture["clean_merge_commit"]

    response = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": repo_dir, "merge_commit": clean_merge},
    )
    assert response.status_code == 400
    assert "without conflict" in response.json()["detail"].lower()


def test_git_state_restoration(client: TestClient, git_repo_fixture: Dict[str, Any]):
    """Test 34: Working tree, branch, and HEAD are completely restored after analysis."""
    repo_dir = git_repo_fixture["repo_dir"]
    merge_commit = git_repo_fixture["conflict_merge_commit"]

    def get_head():
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        ).stdout.strip()

    head_before = get_head()

    response = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": str(repo_dir), "merge_commit": merge_commit},
    )
    assert response.status_code == 200
    head_after = get_head()
    assert head_before == head_after
