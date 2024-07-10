import subprocess
from pathlib import Path
from typing import List, Union


def is_git_installed() -> bool:
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def is_git_repo() -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_changed_files() -> List[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only"], capture_output=True, text=True, check=True
    )
    return result.stdout.strip().split("\n")


def get_staged_changes(file_path: str) -> str:
    result = subprocess.run(
        ["git", "diff", "--cached", file_path],
        capture_output=True,
        text=True,
        check=True,
    )
    # remove the 'diff' header
    return "\n".join(result.stdout.split("\n")[2:])


def get_diff(old_file: str, new_file: str):
    try:
        result = subprocess.run(
            ["git", "diff", "--no-index", "--", old_file, new_file],
            capture_output=True,
            text=True,
            check=True,
        )
        # remove the 'diff' header
        return "\n".join(result.stdout.split("\n")[2:])
    except subprocess.CalledProcessError as e:
        # Because git diff returns a non-zero exit code when there are differences
        return "\n".join(e.output.split("\n")[2:])


def run_git_diff(old_file: Union[str, Path], new_file: Union[str, Path]) -> str:
    if old_file is None:
        return get_staged_changes(str(new_file))
    else:
        return get_diff(str(old_file), str(new_file))
