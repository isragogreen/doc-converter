#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path
import psutil
import shutil
import sys
from typing import Optional, List

# Try to import git, if it fails, inform the user
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    print("Warning: gitpython module not found. Git functionality will be limited.")
    GIT_AVAILABLE = False
    git = None

# === CONFIG ===
GITHUB_REPO_SSH = "git@github.com:isragogreen/doc-converter.git"
GITHUB_REPO_HTTPS = "https://github.com/isragogreen/doc-converter.git"

# Auto-detect: SSH or HTTPS
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if GITHUB_TOKEN:
    GITHUB_REPO = f"https://{GITHUB_TOKEN}@github.com/isragogreen/doc-converter.git"
else:
    GITHUB_REPO = GITHUB_REPO_SSH

LOCAL_CLONE_DIR = Path("./github_clone").resolve()
GITHUB_FOLDER = "docs"
OUTPUT_DIR = LOCAL_CLONE_DIR / "output"

SUPPORTED_EXTS = {'.pdf', '.html', '.docx', '.md', '.txt', '.jpg', '.jpeg', '.png', '.epub'}
RAM_GB = psutil.virtual_memory().total / (1024**3)

# === UTILS ===
def run_git_cmd(cmd, cwd=LOCAL_CLONE_DIR, check=True):
    """Safely run git command."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True, encoding='utf-8'
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"Git error: {result.stderr}")
    return result

def get_file_commit_time(repo, file_path: Path) -> float:
    """Get last commit timestamp for a file."""
    if not GIT_AVAILABLE or not repo:
        return 0.0
        
    try:
        rel_path = os.path.relpath(file_path, LOCAL_CLONE_DIR)
        commit = next(repo.iter_commits(paths=rel_path, max_count=1))
        return commit.committed_date
    except:
        return 0.0

def clone_or_update_repo():
    """Clone or update repository."""
    if not GIT_AVAILABLE:
        print("Git functionality not available. Skipping repository operations.")
        # Create the directory structure manually
        LOCAL_CLONE_DIR.mkdir(exist_ok=True)
        (LOCAL_CLONE_DIR / GITHUB_FOLDER).mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)
        return None
        
    if not LOCAL_CLONE_DIR.exists():
        print("Cloning repository...")
        return git.Repo.clone_from(GITHUB_REPO, LOCAL_CLONE_DIR)  # type: ignore
    else:
        print("Updating repository...")
        repo = git.Repo(LOCAL_CLONE_DIR)  # type: ignore
        repo.remotes.origin.fetch()
        repo.git.reset('--hard', 'origin/main')
        repo.git.clean('-fd')
        return repo

def commit_and_push_if_changed(repo, changed_files: List[Path]):
    """Push only if there are changes."""
    if not GIT_AVAILABLE or not repo:
        print("Git functionality not available. Skipping commit and push.")
        return
        
    if not changed_files:
        print("No changes to commit.")
        return

    print(f"Committing {len(changed_files)} file(s)...")
    for f in changed_files:
        repo.index.add([str(f)])
    repo.index.commit(f"Auto: processed {len(changed_files)} doc(s)")

    try:
        repo.remotes.origin.push()
        print("Push successful.")
    except Exception as e:
        if GITHUB_TOKEN:
            print("SSH push failed, trying HTTPS...")
            repo.remotes.origin.set_url(GITHUB_REPO)
            repo.remotes.origin.push()
            print("HTTPS push successful.")
        else:
            raise e

def process_file(repo, input_path: Path, output_path: Path) -> Optional[Path]:
    """Process one file."""
    # If git is not available, skip timestamp checking and process all files
    if GIT_AVAILABLE and repo:
        input_time = get_file_commit_time(repo, input_path)
        output_time = get_file_commit_time(repo, output_path) if output_path.exists() else 0.0

        if input_time <= output_time:
            print(f"Up to date: {input_path.name}")
            return None
    else:
        # If git is not available, check file modification times
        if output_path.exists():
            input_time = input_path.stat().st_mtime
            output_time = output_path.stat().st_mtime
            if input_time <= output_time:
                print(f"Up to date: {input_path.name}")
                return None

    print(f"Processing: {input_path.name} → {output_path.name}")

    try:
        if input_path.suffix.lower() in {'.md', '.txt'}:
            shutil.copy2(input_path, output_path)
            print(f"Copied: {output_path}")
        else:
            temp_dir = output_path.parent / f"__temp_{input_path.stem}"
            temp_dir.mkdir(exist_ok=True)

            cmd = ['mineru', '-p', str(input_path), '-o', str(temp_dir)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError(f"MinerU error: {result.stderr}")

            md_files = list(temp_dir.rglob("*.md"))
            if not md_files:
                raise RuntimeError("MinerU did not generate MD file")
            md_file = md_files[0]
            shutil.move(str(md_file), str(output_path))
            shutil.rmtree(temp_dir, ignore_errors=True)
            print(f"Converted: {output_path}")

        return output_path
    except Exception as e:
        print(f"ERROR processing {input_path.name}: {e}")
        return None

def check_for_changes_and_process(repo) -> List[Path]:
    """Check for changes in docs folder and process files accordingly."""
    source_folder = LOCAL_CLONE_DIR / GITHUB_FOLDER
    if not source_folder.exists():
        print(f"Folder '{GITHUB_FOLDER}' not found in repository.")
        return []

    # Check if output directory exists and has MD files
    output_exists = OUTPUT_DIR.exists()
    md_files_exist = False
    
    if output_exists:
        md_files = list(OUTPUT_DIR.glob("*.md"))
        md_files_exist = len(md_files) > 0
        print(f"Found {len(md_files)} MD files in output directory.")
    
    # If no MD files exist, we need to process all files
    if not md_files_exist:
        print("No MD files found in output. Processing all files from docs folder...")
        changed_files = []
        for file_path in source_folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTS:
                md_path = OUTPUT_DIR / f"{file_path.stem}.md"
                result = process_file(repo, file_path, md_path)
                if result:
                    changed_files.append(result)
        return changed_files
    else:
        print("MD files already exist in output. Checking for updates...")
        # Process only changed files
        changed_files = []
        for file_path in source_folder.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTS:
                md_path = OUTPUT_DIR / f"{file_path.stem}.md"
                result = process_file(repo, file_path, md_path)
                if result:
                    changed_files.append(result)
        return changed_files

# === MAIN ===
def main():
    print(f"RAM: {RAM_GB:.1f} GB | Repo: {GITHUB_REPO.split('@')[-1] if '@' in GITHUB_REPO else GITHUB_REPO}")

    try:
        repo = clone_or_update_repo()
    except Exception as e:
        print(f"Git error: {e}")
        # Continue without git functionality
        repo = None

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Process files based on changes
    changed_files = check_for_changes_and_process(repo)

    if changed_files:
        commit_and_push_if_changed(repo, changed_files)
    else:
        print("All files are up to date. Nothing to do.")

if __name__ == "__main__":
    main()