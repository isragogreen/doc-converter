#!/usr/bin/env python3
"""
Document Converter: PDF/DOCX → MD (via MinerU) → Cleaned MD (via Ollama)
Robust, fault-tolerant, cross-platform (Windows, Linux, Raspberry Pi, Docker)
Goal: ALWAYS produce an MD file, even if Ollama or MinerU fails.
"""

import os
import subprocess
from pathlib import Path
import psutil
import shutil
import sys
from typing import Optional, List
import requests
import time

# === OPTIONAL: Git support ===
try:
    import git
    GIT_AVAILABLE = True
except ImportError:
    print("Warning: gitpython not installed. Git operations disabled.")
    GIT_AVAILABLE = False
    git = None

# === CONFIGURATION ===
GITHUB_REPO_SSH = "git@github.com:isragogreen/doc-converter.git"
GITHUB_REPO_HTTPS = "https://github.com:isragogreen/doc-converter.git"

# Prefer SSH. Use HTTPS only if GITHUB_TOKEN is set
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
if GITHUB_TOKEN:
    GITHUB_REPO = f"https://{GITHUB_TOKEN}@github.com/isragogreen/doc-converter.git"
    print("Using HTTPS with token.")
else:
    GITHUB_REPO = GITHUB_REPO_SSH
    print("Using SSH (recommended). Make sure SSH keys are configured.")

LOCAL_CLONE_DIR = Path("./github_clone").resolve()
GITHUB_FOLDER = "docs"           # Source: original documents
OUTPUT_DIR = LOCAL_CLONE_DIR / "output"  # Target: cleaned .md files

SUPPORTED_EXTS = {'.pdf', '.html', '.docx', '.md', '.txt', '.jpg', '.jpeg', '.png', '.epub'}
RAM_GB = psutil.virtual_memory().total / (1024**3)

# === Ollama Settings ===
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3:3.8b-mini-4k-instruct-q4_k_m"
OLLAMA_TIMEOUT = 180  # 3 minutes max per request
MAX_CHUNK_SIZE = 2500  # Safe chunk size for ~4K tokens
OVERLAP = 200  # Small overlap for chunking

# === HELPER: Run shell/git commands safely ===
def run_cmd(cmd: List[str], cwd=LOCAL_CLONE_DIR, check=True) -> subprocess.CompletedProcess:
    """Run a shell command and return result. Log stderr on failure."""
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding='utf-8'
    )
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}\nSTDERR: {result.stderr}")
    return result

# === GIT: Get last commit time for a file ===
def get_file_commit_time(repo, file_path: Path) -> float:
    """Return Unix timestamp of last commit for file. 0.0 if unavailable."""
    if not GIT_AVAILABLE or not repo or not file_path.exists():
        return 0.0
    try:
        rel_path = os.path.relpath(file_path, LOCAL_CLONE_DIR)
        commit = next(repo.iter_commits(paths=rel_path, max_count=1))
        return commit.committed_date
    except:
        return 0.0

# === GIT: Clone or update repo ===
def clone_or_update_repo():
    """Clone repo if missing, or pull latest. Return repo object or None."""
    if not GIT_AVAILABLE:
        print("Git not available. Creating folders manually.")
        LOCAL_CLONE_DIR.mkdir(exist_ok=True)
        (LOCAL_CLONE_DIR / GITHUB_FOLDER).mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(exist_ok=True)
        return None

    if not LOCAL_CLONE_DIR.exists():
        print(f"Cloning repo via SSH: {GITHUB_REPO}")
        return git.Repo.clone_from(GITHUB_REPO, LOCAL_CLONE_DIR)
    else:
        print("Updating repo...")
        repo = git.Repo(LOCAL_CLONE_DIR)
        repo.remotes.origin.fetch()
        repo.git.reset('--hard', 'origin/main')
        repo.git.clean('-fd')
        return repo

# === GIT: Commit and push changes ===
def commit_and_push(repo, changed_files: List[Path], deleted_files: List[Path]):
    """Commit added/modified files and removed files. Push to GitHub."""
    if not GIT_AVAILABLE or not repo:
        print("Git unavailable. Skipping commit.")
        return

    if not changed_files and not deleted_files:
        print("No changes to commit.")
        return

    print(f"Committing {len(changed_files)} new/updated + {len(deleted_files)} deleted files...")

    # Add new/modified
    for f in changed_files:
        repo.index.add([str(f)])

    # Remove deleted
    for f in deleted_files:
        repo.index.remove([str(f)], working_tree=True)

    repo.index.commit(f"Auto: processed {len(changed_files)} doc(s), removed {len(deleted_files)} extra")

    try:
        repo.remotes.origin.push()
        print("Push successful.")
    except Exception as e:
        if GITHUB_TOKEN:
            print("SSH push failed. Trying HTTPS...")
            # Save original URL
            original_url = repo.remotes.origin.url
            # Set HTTPS URL with token
            repo.remotes.origin.set_url(f"https://{GITHUB_TOKEN}@github.com/isragogreen/doc-converter.git")
            try:
                repo.remotes.origin.push()
                print("HTTPS push successful.")
            except Exception as https_error:
                # Restore original URL and report error
                repo.remotes.origin.set_url(original_url)
                print(f"HTTPS push also failed: {https_error}")
                print(f"Push failed completely: {e}")
        else:
            print(f"Push failed: {e}")

# === STEP 1: Convert with MinerU (non-text files only) ===
def convert_with_mineru(input_path: Path) -> Optional[str]:
    """
    Convert PDF/DOCX/etc → Markdown using MinerU.
    Returns raw markdown text or None on failure.
    """
    temp_dir = OUTPUT_DIR / f"__temp_{input_path.stem}_{int(time.time())}"
    temp_dir.mkdir(exist_ok=True)

    print(f"  → Running MinerU on {input_path.name}...")
    cmd = ['mineru', '-p', str(input_path), '-o', str(temp_dir)]
    result = run_cmd(cmd, check=False)

    if result.returncode != 0:
        print(f"  MinerU failed: {result.stderr}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    md_files = list(temp_dir.rglob("*.md"))
    if not md_files:
        print("  No .md file generated by MinerU.")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return None

    raw_md = md_files[0].read_text(encoding='utf-8')
    shutil.rmtree(temp_dir, ignore_errors=True)
    return raw_md

# === STEP 2: Correct with Ollama (single chunk) ===
def correct_with_ollama(text: str) -> str:
    """Single chunk correction with fallback to original text on error."""
    prompt = f"""You are a document cleaner. Fix OCR errors, remove page numbers, headers, footers, watermarks, and garbage. Keep the original language, structure, and meaning 100%. Output ONLY clean markdown.

Document:
{text}

Clean markdown:
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        print("  → Sending to Ollama for cleanup...")
        response = requests.post(OLLAMA_URL, json=payload, timeout=OLLAMA_TIMEOUT)
        if response.status_code == 200:
            result = response.json()
            cleaned = result.get('response', '').strip()
            if cleaned:
                print("  Ollama cleanup successful.")
                return cleaned
            else:
                print("  Ollama returned empty response.")
        else:
            print(f"  Ollama error {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"  Ollama unreachable: {e}")

    print("  Ollama FAILED. Using raw MinerU output.")
    return text  # FALLBACK to raw

# === STEP 2 EXT: Chunked correction ===
def correct_with_ollama_chunked(raw_md: str) -> str:
    """
    Split long text into overlapping chunks, correct each, then merge.
    Preserves context across boundaries. Falls back per chunk to raw.
    Small overlap to avoid redundancy.
    """
    CHUNK_SIZE = MAX_CHUNK_SIZE  # 2500 chars
    # OVERLAP is defined as a global constant

    if len(raw_md) <= CHUNK_SIZE:
        return correct_with_ollama(raw_md)

    print(f"  Text too long ({len(raw_md)} chars). Splitting into chunks...")

    chunks = []
    start = 0
    while start < len(raw_md):
        end = min(start + CHUNK_SIZE, len(raw_md))
        chunk = raw_md[start:end]
        chunks.append(chunk)
        start = end - OVERLAP
        if start >= len(raw_md):
            break

    corrected_chunks = []
    for i, chunk in enumerate(chunks):
        print(f"    → Chunk {i+1}/{len(chunks)} ({len(chunk)} chars)")
        corrected = correct_with_ollama(chunk)
        corrected_chunks.append(corrected)

    # Reconstruct with overlap handling
    final_parts = [corrected_chunks[0]]
    for i in range(1, len(corrected_chunks)):
        curr = corrected_chunks[i]
        # Simple append with trim if overlap matches (approx)
        overlap_text = final_parts[-1][-OVERLAP:]
        if curr.startswith(overlap_text):
            final_parts.append(curr[OVERLAP:])
        else:
            final_parts.append(curr)

    result = "".join(final_parts)
    print(f"  Reconstructed cleaned MD ({len(result)} chars)")
    return result

# === PROCESS ONE FILE ===
def process_single_file(repo, input_path: Path, output_path: Path) -> bool:
    """
    Process one file.
    Returns True if output was created/modified.
    """
    # Skip if up to date
    if GIT_AVAILABLE and repo:
        in_time = get_file_commit_time(repo, input_path)
        out_time = get_file_commit_time(repo, output_path) if output_path.exists() else 0.0
        if in_time <= out_time:
            print(f"  [Skipped] {input_path.name} (up to date)")
            return False
    else:
        if output_path.exists() and input_path.stat().st_mtime <= output_path.stat().st_mtime:
            print(f"  [Skipped] {input_path.name} (up to date)")
            return False

    print(f"  [Processing] {input_path.name} → {output_path.name}")

    try:
        if input_path.suffix.lower() in {'.md', '.txt'}:
            # Text files: just copy
            shutil.copy2(input_path, output_path)
            print(f"  [Copied] {output_path.name}")
            return True
        else:
            # Non-text: MinerU → Ollama (chunked)
            raw_md = convert_with_mineru(input_path)
            if not raw_md:
                print(f"  [Failed] MinerU failed for {input_path.name}")
                return False

            final_md = correct_with_ollama_chunked(raw_md)
            output_path.write_text(final_md, encoding='utf-8')
            print(f"  [Saved] {output_path.name}")
            return True
    except Exception as e:
        print(f"  [Error] Unexpected error: {e}")
        return False

# === CLEANUP: Remove orphaned .md files in output/ ===
def cleanup_orphaned_outputs() -> List[Path]:
    """Delete .md files in output/ with no matching input in docs/."""
    if not (LOCAL_CLONE_DIR / GITHUB_FOLDER).exists():
        return []

    input_stems = {
        f.stem for f in (LOCAL_CLONE_DIR / GITHUB_FOLDER).rglob('*')
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    }

    deleted = []
    for md_file in OUTPUT_DIR.glob("*.md"):
        if md_file.stem not in input_stems:
            print(f"  [Cleanup] Deleting orphaned: {md_file.name}")
            md_file.unlink()
            deleted.append(md_file)
    return deleted

# === MAIN ===
def main():
    print(f"\nDocument Converter Started")
    print(f"RAM: {RAM_GB:.1f} GB | Mode: {'SSH' if 'github.com' in GITHUB_REPO else 'HTTPS'}")

    # 1. Clone / update repo
    repo = None
    try:
        repo = clone_or_update_repo()
    except Exception as e:
        print(f"Git clone/update failed: {e}. Continuing without git.")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # 2. Cleanup orphaned outputs
    deleted_files = cleanup_orphaned_outputs()

    # 3. Find files to process
    source_dir = LOCAL_CLONE_DIR / GITHUB_FOLDER
    if not source_dir.exists():
        print(f"Source folder '{GITHUB_FOLDER}' not found!")
        return

    all_input_files = [
        f for f in source_dir.rglob('*')
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS
    ]
    print(f"Found {len(all_input_files)} supported files in '{GITHUB_FOLDER}/'")

    to_process = []
    for f in all_input_files:
        out_path = OUTPUT_DIR / f"{f.stem}.md"
        if GIT_AVAILABLE and repo:
            if get_file_commit_time(repo, f) > get_file_commit_time(repo, out_path) or not out_path.exists():
                to_process.append(f)
        else:
            if not out_path.exists() or f.stat().st_mtime > out_path.stat().st_mtime:
                to_process.append(f)

    if not to_process:
        print("All files up to date.")
        if deleted_files and repo:
            commit_and_push(repo, [], deleted_files)
        return

    print(f"Processing {len(to_process)} file(s):")
    changed_files = []

    for idx, input_path in enumerate(to_process, 1):
        print(f"\n[{idx}/{len(to_process)}]", end=" ")
        out_path = OUTPUT_DIR / f"{input_path.stem}.md"
        if process_single_file(repo, input_path, out_path):
            changed_files.append(out_path)

    # 4. Commit & push
    if changed_files or deleted_files:
        commit_and_push(repo, changed_files, deleted_files)
    else:
        print("No changes to commit.")

    print("\nDone!")

if __name__ == "__main__":
    main()
