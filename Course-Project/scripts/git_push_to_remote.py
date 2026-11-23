"""Helper script to push the CourseAgentAI repository to GitHub using Dulwich or standard Git.
Usage:
    python scripts/git_push_to_remote.py <remote_url>
Example:
    python scripts/git_push_to_remote.py https://github.com/my-org/CourseAgentAI.git
"""

import sys
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/git_push_to_remote.py <github_repository_url>")
        print("Example: python scripts/git_push_to_remote.py https://github.com/my-org/CourseAgentAI.git")
        return

    remote_url = sys.argv[1].strip()
    print(f"Pushing repository from {ROOT_DIR} to {remote_url}...")
    
    repo = Repo(str(ROOT_DIR))
    try:
        # Check if remote 'origin' exists or add it
        config = repo.get_config()
        config.set(("remote", "origin"), "url", remote_url)
        config.write_to_path()
        print(f"Configured remote 'origin' -> {remote_url}")
        
        # Push to remote
        print("Executing push to 'main' branch...")
        porcelain.push(repo, remote_location=remote_url, refspecs=["refs/heads/main:refs/heads/main"])
        print("Push completed successfully!")
    except Exception as exc:
        print(f"Push notice / error: {exc}")
        print("\nIf authentication is required, you can push using:")
        print(f"1. Remote with token: https://<TOKEN>@github.com/<OWNER>/<REPO>.git")
        print("2. Standard git CLI: git push -u origin main")

if __name__ == "__main__":
    main()
