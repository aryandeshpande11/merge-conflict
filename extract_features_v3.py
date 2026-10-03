import subprocess
import csv
import os

REPOS = ["dropwizard", "jbehave-core", "zanata-server", "grails-core"]

def run_cmd(cmd, cwd):
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, shell=True, encoding='utf-8', errors='replace')
    return result.stdout.strip() if result.stdout else "", result.returncode

def get_author_email(commit_hash, repo_path):
    out, _ = run_cmd(f'git log -1 --format="%ae" {commit_hash}', repo_path)
    return out

def get_lines_changed(base, target, repo_path):
    out, _ = run_cmd(f'git diff --shortstat {base} {target}', repo_path)
    insertions, deletions = 0, 0
    try:
        for part in out.split(','):
            if 'insertion' in part:
                insertions = int(part.strip().split()[0])
            elif 'deletion' in part:
                deletions = int(part.strip().split()[0])
    except:
        pass
    return insertions + deletions

def get_file_type(filename):
    """Classify file into broad categories for the model"""
    ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
    java_types = ['java', 'kt', 'scala']
    config_types = ['xml', 'json', 'yaml', 'yml', 'properties', 'gradle', 'pom']
    doc_types = ['md', 'txt', 'rst', 'html']
    if ext in java_types: return 0      # Code
    if ext in config_types: return 1    # Config
    if ext in doc_types: return 2       # Docs
    return 3                            # Other

def get_conflict_stats(repo_path):
    """
    Analyses the ACTUAL conflict markers in working tree to get deep features.
    Returns: (chunk_count, avg_chunk_size, local_lines, incoming_lines)
    """
    conflicts_out, _ = run_cmd('git diff --name-only --diff-filter=U', repo_path)
    if not conflicts_out:
        return 0, 0, 0, 0

    conflicting_files = conflicts_out.split('\n')
    total_chunks = 0
    total_local_lines = 0
    total_incoming_lines = 0

    for filepath in conflicting_files:
        if not filepath: continue
        try:
            with open(os.path.join(repo_path, filepath), 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            in_local = False
            in_incoming = False
            local_count = 0
            incoming_count = 0

            for line in content.split('\n'):
                if line.startswith('<<<<<<<'):
                    total_chunks += 1
                    in_local = True
                    in_incoming = False
                elif line.startswith('======='):
                    in_local = False
                    in_incoming = True
                elif line.startswith('>>>>>>>'):
                    in_local = False
                    in_incoming = False
                elif in_local:
                    local_count += 1
                elif in_incoming:
                    incoming_count += 1

            total_local_lines += local_count
            total_incoming_lines += incoming_count
        except:
            pass

    avg_chunk = (total_local_lines + total_incoming_lines) / max(total_chunks, 1)
    return total_chunks, round(avg_chunk, 2), total_local_lines, total_incoming_lines

def determine_label(merge_hash, p1, p2, conflicting_files, repo_path):
    if not conflicting_files: return "unknown"
    local_wins = 0
    incoming_wins = 0
    combine_count = 0

    for test_file in conflicting_files[:3]:  # Check up to 3 files for label accuracy
        if not test_file: continue
        merged_content, rc1 = run_cmd(f'git show {merge_hash}:{test_file}', repo_path)
        if rc1 != 0: continue
        p1_content, _ = run_cmd(f'git show {p1}:{test_file}', repo_path)
        p2_content, _ = run_cmd(f'git show {p2}:{test_file}', repo_path)

        if merged_content == p1_content:
            local_wins += 1
        elif merged_content == p2_content:
            incoming_wins += 1
        else:
            combine_count += 1

    total = local_wins + incoming_wins + combine_count
    if total == 0: return "unknown"
    if local_wins > incoming_wins and local_wins > combine_count:
        return "keep_local"
    elif incoming_wins > local_wins and incoming_wins > combine_count:
        return "keep_incoming"
    else:
        return "combine_both"

def get_commit_time_diff(p1, p2, repo_path):
    """Get time difference between the two parents in hours"""
    t1, _ = run_cmd(f'git log -1 --format="%ct" {p1}', repo_path)
    t2, _ = run_cmd(f'git log -1 --format="%ct" {p2}', repo_path)
    try:
        diff_hours = abs(int(t1) - int(t2)) / 3600
        return round(diff_hours, 2)
    except:
        return 0

def main():
    csv_filename = 'ml_features_v3.csv'

    with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'Repository',
            'Merge_Commit',
            'Conflicting_Files_Count',
            'Author_Match',
            'Lines_Changed_Local',
            'Lines_Changed_Incoming',
            'Total_Lines_Changed',
            'Conflict_Chunk_Count',       # NEW: how many <<<< ==== >>>> blocks
            'Avg_Chunk_Size',             # NEW: average lines per conflict chunk
            'Local_Conflict_Lines',       # NEW: lines of code on the LOCAL side of conflicts
            'Incoming_Conflict_Lines',    # NEW: lines of code on the INCOMING side of conflicts
            'Local_Incoming_Ratio',       # NEW: ratio of local vs incoming conflict lines
            'Primary_File_Type',          # NEW: type of the first conflicting file (0=code,1=config,2=doc,3=other)
            'Time_Diff_Hours',            # NEW: how long the two branches diverged before merging
            'Resolution_Label'
        ])

        for repo in REPOS:
            print(f"\nExtracting V3 features from: {repo}...")
            repo_path = os.path.join(os.getcwd(), repo)
            if not os.path.exists(repo_path):
                print(f"  Skipping, folder not found.")
                continue

            out, _ = run_cmd('git log --merges --format="%H %P"', repo_path)
            merges = out.split('\n')
            count = 0

            for merge in merges:
                if not merge: continue
                parts = merge.split()
                if len(parts) < 3: continue

                merge_hash, p1, p2 = parts[0], parts[1], parts[2]

                base, _ = run_cmd(f'git merge-base {p1} {p2}', repo_path)
                if not base: continue

                run_cmd('git reset --hard', repo_path)
                run_cmd(f'git checkout {p1}', repo_path)
                _, rc = run_cmd(f'git merge --no-commit --no-ff {p2}', repo_path)

                if rc != 0:
                    # Get conflicting files
                    conflicts_out, _ = run_cmd('git diff --name-only --diff-filter=U', repo_path)
                    conflicting_files = [f for f in conflicts_out.split('\n') if f]

                    # --- FEATURE EXTRACTION ---
                    author_p1 = get_author_email(p1, repo_path)
                    author_p2 = get_author_email(p2, repo_path)
                    author_match = 1 if author_p1 == author_p2 else 0

                    lines_p1 = get_lines_changed(base, p1, repo_path)
                    lines_p2 = get_lines_changed(base, p2, repo_path)
                    total_lines = lines_p1 + lines_p2

                    chunk_count, avg_chunk, local_lines, incoming_lines = get_conflict_stats(repo_path)

                    ratio = round(local_lines / max(incoming_lines, 1), 4)

                    file_type = get_file_type(conflicting_files[0]) if conflicting_files else 3

                    time_diff = get_commit_time_diff(p1, p2, repo_path)

                    # --- LABEL ---
                    label = determine_label(merge_hash, p1, p2, conflicting_files, repo_path)

                    writer.writerow([
                        repo, merge_hash, len(conflicting_files),
                        author_match, lines_p1, lines_p2, total_lines,
                        chunk_count, avg_chunk, local_lines, incoming_lines,
                        ratio, file_type, time_diff, label
                    ])
                    count += 1
                    print(f"  [{count}] Conflict at {merge_hash[:7]} | chunks={chunk_count} | label={label}")

                run_cmd('git merge --abort', repo_path)

            run_cmd('git reset --hard', repo_path)
            run_cmd('git checkout main 2>nul || git checkout master 2>nul', repo_path)

    print(f"\nV3 Dataset saved to {csv_filename}")

if __name__ == "__main__":
    main()
