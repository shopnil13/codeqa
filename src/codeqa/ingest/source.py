import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from codeqa.config import get_settings


@dataclass
class ResolvedSource:
    local_path: Path
    commit_sha: str
    source_url: str | None


def _run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def resolve_source(path_or_url: str) -> ResolvedSource:
    """Accept a local path or a git URL; shallow clone URLs into the cache dir."""

    if path_or_url.startswith(("http://", "https://", "git@")):
        settings = get_settings()
        cache_root = Path(settings.cache_dir) / "repos"
        cache_root.mkdir(parents=True, exist_ok=True)
        dest = cache_root / str(uuid.uuid4())
        subprocess.run(
            ["git", "clone", "--depth", "1", path_or_url, str(dest)],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=dest)
        return ResolvedSource(local_path=dest, commit_sha=commit_sha, source_url=path_or_url)

    local_path = Path(path_or_url).resolve()
    if not local_path.exists():
        raise FileNotFoundError(f"path does not exist: {local_path}")

    commit_sha = ""
    try:
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=local_path)
    except subprocess.CalledProcessError:
        pass  # not a git repo, or dirty clone with no commits

    return ResolvedSource(local_path=local_path, commit_sha=commit_sha, source_url=None)
