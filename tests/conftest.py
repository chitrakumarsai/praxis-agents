import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> str:
    """Run git in ``root`` with a throwaway identity, so tests don't depend on user config."""
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
