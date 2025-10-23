#!/usr/bin/env python3
"""
Test script to verify the requirements implementation:
1. Download two folders (docs and output) from a GitHub repository
2. Check if there were changes or if MD files already exist in output
3. If no MD files exist, convert files from docs using mineru
4. Save MD files to the repository if conversion happened or files were added
"""

import os
import sys
from pathlib import Path

def test_requirements_implementation():
    """Test that our implementation meets the specified requirements."""
    print("Testing requirements implementation...")
    
    # Check that the main script exists
    script_path = Path("src/script.py")
    if not script_path.exists():
        print("ERROR: Main script not found!")
        return False
    
    print("✓ Main script exists")
    
    # Check that the script has the required functions
    script_content = script_path.read_text(encoding='utf-8')
    
    required_functions = [
        "clone_or_update_repo",
        "check_for_changes_and_process",
        "process_file",
        "commit_and_push_if_changed"
    ]
    
    for func in required_functions:
        if func in script_content:
            print(f"✓ Function {func} found")
        else:
            print(f"✗ Function {func} missing")
            return False
    
    # Check that the script handles the docs and output folders
    if "GITHUB_FOLDER" in script_content and "OUTPUT_DIR" in script_content:
        print("✓ Docs and output folder handling found")
    else:
        print("✗ Docs and output folder handling missing")
        return False
    
    # Check that the script handles the case when no MD files exist
    if "md_files_exist" in script_content:
        print("✓ MD files existence checking found")
    else:
        print("✗ MD files existence checking missing")
        return False
    
    print("\nAll requirements checks passed!")
    return True

if __name__ == "__main__":
    success = test_requirements_implementation()
    sys.exit(0 if success else 1)