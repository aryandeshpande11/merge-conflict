import ast
from pathlib import Path
from typing import Dict, Any

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    "malicious_commit",
    [
        "abc; whoami",
        "abc && whoami",
        "abc | whoami",
        "$(whoami)",
        "`whoami`",
        "abc > /tmp/hacked",
        "-v",
        "--upload-pack=whoami",
    ],
)
def test_command_injection_prevention(client: TestClient, git_repo_fixture: Dict[str, Any], malicious_commit: str):
    """Test 33: Command injection strings in commit hash are strictly blocked."""
    repo_dir = str(git_repo_fixture["repo_dir"])
    response = client.post(
        "/api/v1/analyze-repository",
        json={"repository_path": repo_dir, "merge_commit": malicious_commit},
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower() or "git" in response.json()["detail"].lower()


def test_malicious_repository_path(client: TestClient):
    """Test 33: Malicious command characters in repository path are rejected."""
    bad_paths = [
        "/tmp/repo; cat /etc/passwd",
        "C:\\repo & dir",
        "$(id)",
    ]
    for p in bad_paths:
        response = client.post(
            "/api/v1/analyze-repository",
            json={"repository_path": p, "merge_commit": "1234567"},
        )
        assert response.status_code == 400


def test_static_code_security_scan():
    """Test 49: Static security scan ensures no dangerous patterns in backend app code."""
    app_dir = Path(__file__).resolve().parent.parent / "app"
    dangerous_patterns = ["os.system(", "shell=True", "eval(", "exec("]

    for py_file in app_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for pattern in dangerous_patterns:
            assert pattern not in content, f"Security violation: Found '{pattern}' in {py_file}"
