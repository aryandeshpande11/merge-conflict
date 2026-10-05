import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd

from app.schemas.prediction import (
    ConflictPredictionRequest,
    ConflictFeatures,
)


FEATURE_NAMES: List[str] = [
    "Conflicting_Files_Count",
    "Author_Match",
    "Lines_Changed_Local",
    "Lines_Changed_Incoming",
    "Total_Lines_Changed",
    "Conflict_Chunk_Count",
    "Avg_Chunk_Size",
    "Local_Conflict_Lines",
    "Incoming_Conflict_Lines",
    "Local_Incoming_Ratio",
    "Primary_File_Type",
    "Time_Diff_Hours",
]

# Validation regex for commit hashes and Git references (security against injection)
GIT_REF_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\./~^]{2,64}$")


class FeatureService:
    """
    Service responsible for:
    - Maintaining feature definitions and ordering
    - Converting prediction requests into pandas DataFrames
    - Parsing conflict markers from raw text
    - Safe Git feature extraction for repository analysis
    """

    FEATURE_NAMES: List[str] = FEATURE_NAMES

    @classmethod
    def get_feature_names(cls) -> List[str]:
        return cls.FEATURE_NAMES.copy()

    @classmethod
    def request_to_dataframe(cls, request: ConflictPredictionRequest) -> pd.DataFrame:
        """
        Converts a validated Pydantic prediction request into a pandas DataFrame
        with columns ordered precisely according to the training feature schema.
        """
        data = request.model_dump()
        ordered_data = {feat: [data[feat]] for feat in cls.FEATURE_NAMES}
        return pd.DataFrame(ordered_data, columns=cls.FEATURE_NAMES)

    @classmethod
    def dict_to_dataframe(cls, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Converts a dictionary of features into a pandas DataFrame
        validating that all 12 required features are present.
        """
        missing = [f for f in cls.FEATURE_NAMES if f not in data]
        if missing:
            raise ValueError(f"Missing required features: {missing}")

        ordered_data = {feat: [data[feat]] for feat in cls.FEATURE_NAMES}
        return pd.DataFrame(ordered_data, columns=cls.FEATURE_NAMES)

    @classmethod
    def get_file_type(cls, filename: str) -> int:
        """
        Classify file extension into broad categories used by the model:
        0: Code (java, kt, scala, py, js, ts, etc.)
        1: Config (xml, json, yaml, yml, properties, gradle, pom)
        2: Docs (md, txt, rst, html)
        3: Other
        """
        if not filename:
            return 3

        ext = filename.split(".")[-1].lower() if "." in filename else "unknown"
        java_code_types = ["java", "kt", "scala", "py", "c", "cpp", "h", "go", "rs", "js", "ts"]
        config_types = ["xml", "json", "yaml", "yml", "properties", "gradle", "pom", "toml", "ini"]
        doc_types = ["md", "txt", "rst", "html", "adoc"]

        if ext in java_code_types:
            return 0  # Code
        if ext in config_types:
            return 1  # Config
        if ext in doc_types:
            return 2  # Docs
        return 3      # Other

    @classmethod
    def parse_conflict_text(cls, text: str) -> ConflictFeatures:
        """
        Analyses the ACTUAL conflict markers in raw text to get deep features:
        - Conflict_Chunk_Count
        - Avg_Chunk_Size
        - Local_Conflict_Lines
        - Incoming_Conflict_Lines
        - Local_Incoming_Ratio
        """
        total_chunks = 0
        total_local_lines = 0
        total_incoming_lines = 0

        in_local = False
        in_incoming = False
        local_count = 0
        incoming_count = 0

        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("<<<<<<<"):
                total_chunks += 1
                in_local = True
                in_incoming = False
            elif stripped.startswith("======="):
                in_local = False
                in_incoming = True
            elif stripped.startswith(">>>>>>>"):
                in_local = False
                in_incoming = False
            elif in_local:
                local_count += 1
            elif in_incoming:
                incoming_count += 1

        total_local_lines += local_count
        total_incoming_lines += incoming_count

        avg_chunk = (total_local_lines + total_incoming_lines) / max(total_chunks, 1)
        ratio = round(total_local_lines / max(total_incoming_lines, 1), 4)

        return ConflictFeatures(
            Conflict_Chunk_Count=total_chunks,
            Avg_Chunk_Size=round(avg_chunk, 2),
            Local_Conflict_Lines=total_local_lines,
            Incoming_Conflict_Lines=total_incoming_lines,
            Local_Incoming_Ratio=ratio,
        )

    # -------------------------------------------------------------------------
    # Secure Git Repository Analysis Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _run_git_cmd(cls, args: List[str], cwd: Path) -> Tuple[str, int]:
        """
        Executes a git command securely using subprocess with shell disabled.
        """
        cmd = ["git"] + args
        try:
            res = subprocess.run(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )
            return res.stdout.strip(), res.returncode
        except subprocess.TimeoutExpired:
            return "", -1
        except Exception as e:
            return f"Git execution error: {str(e)}", -1

    @classmethod
    def validate_repository_path(cls, path_str: str) -> Path:
        """Validates that repository path exists and contains a .git folder."""
        path = Path(path_str).resolve()
        if not path.exists() or not path.is_dir():
            raise ValueError(f"Invalid repository path: '{path_str}' does not exist or is not a directory.")

        out, rc = cls._run_git_cmd(["rev-parse", "--is-inside-work-tree"], path)
        if rc != 0 or out.strip().lower() != "true":
            raise ValueError(f"Directory '{path_str}' is not a valid Git repository.")

        return path

    @classmethod
    def validate_git_ref(cls, ref_str: str) -> str:
        """Validates commit hash or branch name to prevent shell injection or flag abuse."""
        ref = ref_str.strip()
        if not GIT_REF_PATTERN.match(ref) or ref.startswith("-"):
            raise ValueError(f"Invalid Git commit or reference: '{ref_str}'")
        return ref

    @classmethod
    def analyze_git_repository_merge(cls, repo_path_str: str, merge_commit_str: str) -> Dict[str, Any]:
        """
        Replays the merge commit in a safe manner to extract the exact 12 features.
        Preserves original git state with cleanup in finally block.
        """
        repo_path = cls.validate_repository_path(repo_path_str)
        merge_commit = cls.validate_git_ref(merge_commit_str)

        # 1. Get parents of the merge commit
        out, rc = cls._run_git_cmd(["log", "-1", "--format=%H %P", merge_commit], repo_path)
        if rc != 0 or not out:
            raise ValueError(f"Could not inspect commit '{merge_commit}' in repository.")

        parts = out.split()
        if len(parts) < 3:
            raise ValueError(f"Commit '{merge_commit}' is not a merge commit (needs at least 2 parents).")

        _, p1, p2 = parts[0], parts[1], parts[2]

        # 2. Find common ancestor
        base, rc = cls._run_git_cmd(["merge-base", p1, p2], repo_path)
        if rc != 0 or not base:
            raise ValueError(f"Common ancestor could not be found for parents {p1[:7]} and {p2[:7]}.")

        # 3. Save current HEAD to restore later
        original_head, _ = cls._run_git_cmd(["rev-parse", "HEAD"], repo_path)

        try:
            # Clean and checkout p1
            cls._run_git_cmd(["reset", "--hard"], repo_path)
            out_co, rc_co = cls._run_git_cmd(["checkout", "-f", p1], repo_path)
            if rc_co != 0:
                raise ValueError(f"Failed to checkout parent 1 ({p1[:7]}): {out_co}")

            # Merge p2 without committing
            _, rc_merge = cls._run_git_cmd(["merge", "--no-commit", "--no-ff", p2], repo_path)
            if rc_merge == 0:
                raise ValueError(f"Merge between {p1[:7]} and {p2[:7]} completed cleanly without conflict.")

            # Detect conflicting files
            conflicts_out, _ = cls._run_git_cmd(["diff", "--name-only", "--diff-filter=U"], repo_path)
            conflicting_files = [f for f in conflicts_out.split("\n") if f.strip()]
            if not conflicting_files:
                raise ValueError("Merge failed but no conflicting files were identified.")

            # Feature 1: Conflicting_Files_Count
            conflicting_files_count = len(conflicting_files)

            # Feature 2: Author_Match
            author_p1, _ = cls._run_git_cmd(["log", "-1", "--format=%ae", p1], repo_path)
            author_p2, _ = cls._run_git_cmd(["log", "-1", "--format=%ae", p2], repo_path)
            author_match = 1 if (author_p1 and author_p2 and author_p1 == author_p2) else 0

            # Features 3, 4, 5: Lines changed local and incoming vs ancestor
            lines_p1 = cls._get_lines_changed_internal(base, p1, repo_path)
            lines_p2 = cls._get_lines_changed_internal(base, p2, repo_path)
            total_lines = lines_p1 + lines_p2

            # Features 6, 7, 8, 9, 10: Conflict chunk stats from working tree
            chunk_count, avg_chunk, local_lines, incoming_lines = cls._get_conflict_stats_internal(
                repo_path, conflicting_files
            )
            ratio = round(local_lines / max(incoming_lines, 1), 4)

            # Feature 11: Primary_File_Type
            primary_file_type = cls.get_file_type(conflicting_files[0]) if conflicting_files else 3

            # Feature 12: Time_Diff_Hours
            time_diff = cls._get_commit_time_diff_internal(p1, p2, repo_path)

            features = {
                "Conflicting_Files_Count": conflicting_files_count,
                "Author_Match": author_match,
                "Lines_Changed_Local": lines_p1,
                "Lines_Changed_Incoming": lines_p2,
                "Total_Lines_Changed": total_lines,
                "Conflict_Chunk_Count": chunk_count,
                "Avg_Chunk_Size": avg_chunk,
                "Local_Conflict_Lines": local_lines,
                "Incoming_Conflict_Lines": incoming_lines,
                "Local_Incoming_Ratio": ratio,
                "Primary_File_Type": primary_file_type,
                "Time_Diff_Hours": time_diff,
            }

            return features

        finally:
            # Always cleanly restore git state
            cls._run_git_cmd(["merge", "--abort"], repo_path)
            cls._run_git_cmd(["reset", "--hard"], repo_path)
            if original_head:
                cls._run_git_cmd(["checkout", "-f", original_head], repo_path)

    @classmethod
    def _get_lines_changed_internal(cls, base: str, target: str, repo_path: Path) -> int:
        out, _ = cls._run_git_cmd(["diff", "--shortstat", base, target], repo_path)
        insertions, deletions = 0, 0
        try:
            for part in out.split(","):
                if "insertion" in part:
                    insertions = int(part.strip().split()[0])
                elif "deletion" in part:
                    deletions = int(part.strip().split()[0])
        except Exception:
            pass
        return insertions + deletions

    @classmethod
    def _get_conflict_stats_internal(
        cls, repo_path: Path, conflicting_files: List[str]
    ) -> Tuple[int, float, int, int]:
        total_chunks = 0
        total_local_lines = 0
        total_incoming_lines = 0

        for filepath in conflicting_files:
            if not filepath:
                continue
            file_full_path = repo_path / filepath
            if not file_full_path.exists():
                continue

            try:
                with open(file_full_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()

                in_local = False
                in_incoming = False
                local_count = 0
                incoming_count = 0

                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped.startswith("<<<<<<<"):
                        total_chunks += 1
                        in_local = True
                        in_incoming = False
                    elif stripped.startswith("======="):
                        in_local = False
                        in_incoming = True
                    elif stripped.startswith(">>>>>>>"):
                        in_local = False
                        in_incoming = False
                    elif in_local:
                        local_count += 1
                    elif in_incoming:
                        incoming_count += 1

                total_local_lines += local_count
                total_incoming_lines += incoming_count
            except Exception:
                pass

        avg_chunk = (total_local_lines + total_incoming_lines) / max(total_chunks, 1)
        return total_chunks, round(avg_chunk, 2), total_local_lines, total_incoming_lines

    @classmethod
    def _get_commit_time_diff_internal(cls, p1: str, p2: str, repo_path: Path) -> float:
        t1, _ = cls._run_git_cmd(["log", "-1", "--format=%ct", p1], repo_path)
        t2, _ = cls._run_git_cmd(["log", "-1", "--format=%ct", p2], repo_path)
        try:
            diff_hours = abs(int(t1) - int(t2)) / 3600
            return round(diff_hours, 2)
        except Exception:
            return 0.0
