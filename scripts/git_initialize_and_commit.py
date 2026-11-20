"""Initialize git repository and create initial commit using dulwich."""

import os
from pathlib import Path
from dulwich import porcelain
from dulwich.repo import Repo

ROOT_DIR = Path(__file__).resolve().parent.parent

def main():
    print(f"Working in: {ROOT_DIR}")
    
    # Initialize repository
    repo_path = str(ROOT_DIR)
    git_dir = ROOT_DIR / ".git"
    
    if not git_dir.exists():
        repo = porcelain.init(repo_path)
        print("Initialized Git repository at:", git_dir)
    else:
        repo = Repo(repo_path)
        print("Existing Git repository found.")
        
    # Set default branch to main if possible
    try:
        repo.refs.set_symbolic_ref(b"HEAD", b"refs/heads/main")
    except Exception as e:
        print("Note on branch HEAD:", e)
        
    # Read .gitignore patterns
    ignore_patterns = set()
    gitignore_file = ROOT_DIR / ".gitignore"
    if gitignore_file.exists():
        for line in gitignore_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ignore_patterns.add(line.rstrip("/"))
                
    print(f"Ignore patterns: {ignore_patterns}")
    
    # Add all files honoring .gitignore
    files_to_add = []
    for root, dirs, files in os.walk(repo_path):
        rel_root = Path(root).relative_to(ROOT_DIR)
        parts = rel_root.parts
        
        # Check if directory should be skipped
        skip_dir = False
        for part in parts:
            if part == ".git" or part in ignore_patterns:
                skip_dir = True
                break
        if skip_dir:
            continue
            
        # Prune dirs in place to avoid descending into ignored directories
        dirs[:] = [d for d in dirs if d != ".git" and d not in ignore_patterns]
        
        for file in files:
            rel_file = (rel_root / file).as_posix()
            # Check pattern matches
            if any(p in parts for p in ignore_patterns) or file in ignore_patterns:
                continue
            if any(file.endswith(p.replace("*", "")) for p in ignore_patterns if p.startswith("*")):
                continue
            files_to_add.append(rel_file)
            
    print(f"Total files identified to stage: {len(files_to_add)}")
    
    # Add files
    porcelain.add(repo, paths=files_to_add)
    print("Staged files in repository.")
    
    # Commit
    commit_msg = b"feat: complete CourseAgentAI submission package, all 12 assignments, final report, and docs"
    author = b"CourseAgentAI Team <courseagentai@university.edu>"
    
    commit_sha = porcelain.commit(
        repo,
        message=commit_msg,
        author=author,
        committer=author
    )
    print(f"Successfully committed! Commit SHA: {commit_sha.decode('ascii') if isinstance(commit_sha, bytes) else commit_sha}")
    
    # Show branch status
    branch = porcelain.active_branch(repo)
    print(f"Active branch: {branch.decode('utf-8') if isinstance(branch, bytes) else branch}")

if __name__ == "__main__":
    main()
