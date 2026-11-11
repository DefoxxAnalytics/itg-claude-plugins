"""Finds the work projects worked on in Claude Code, for the tracker-update skill.

    python tracker.py init --projects-root DIR --root FOLDER=BUSINESS ... --people NAME
                                               (FOLDER may also be FOLDER/PROJECT: that one project only)
    python tracker.py person --name "Last, First" --id N
    python tracker.py gather [--since ISO]     projects with sessions since then, as JSON
    python tracker.py pending                  how many of them have something not yet posted
    python tracker.py record KEY --row N [--title T]
    python tracker.py ignore KEY
    python tracker.py alias KEY --to KEY
    python tracker.py ran

Each person's settings live in ~/.claude/tracker-update/registry.json (or $TRACKER_REGISTRY), outside the skill,
so that updating the skill keeps them. Of each session file it reads only the working folder ("cwd"), never the
conversation.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path, PureWindowsPath

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "registry.template.json"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
MEMORY_INDEX_CAP = 4000
COMMITS_SHOWN = 20
LINES_SEARCHED_FOR_CWD = 50
FIELD = "\x1f"


def now_local() -> datetime:
    return datetime.now().astimezone().replace(microsecond=0)


def parse_time(text: str) -> datetime:
    """A saved time in this laptop's zone, so that days start at local midnight."""
    return datetime.fromisoformat(text).astimezone()


def modified(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime).astimezone()


def start_of_day(moment: datetime) -> datetime:
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


def encode_folder(path: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def session_cwd(session: Path) -> str | None:
    with open(session, encoding="utf-8", errors="replace") as lines:
        for number, line in enumerate(lines):
            if number >= LINES_SEARCHED_FOR_CWD:
                return None
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict) and isinstance(record.get("cwd"), str):
                return record["cwd"]
    return None


def default_registry_path() -> Path:
    chosen = os.environ.get("TRACKER_REGISTRY")
    return Path(chosen) if chosen else Path.home() / ".claude" / "tracker-update" / "registry.json"


def load_registry(path: Path) -> dict:
    registry = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    registry.setdefault("roots", {})
    registry.setdefault("projects", {})
    return registry


def init_registry(path: Path, projects_root: str, roots: dict, people: str) -> None:
    """A person's first settings, from the template; existing settings are never replaced."""
    if path.exists():
        raise FileExistsError(f"Settings already exist: {path}")
    registry = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    registry.update({"projects_root": projects_root, "roots": roots, "people_default": people, "projects": {}})
    save_registry(path, registry)


def set_person(path: Path, name: str, user_id: int) -> None:
    registry = load_registry(path)
    registry["assigned_to"] = {"name": name, "id": user_id}
    save_registry(path, registry)


def save_registry(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(registry, file, indent=2, ensure_ascii=False)
            file.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _change(path: Path, key: str, entry: dict) -> None:
    registry = load_registry(path)
    registry["projects"][key] = entry
    save_registry(path, registry)


def record(path: Path, key: str, row: int, now: datetime | None = None, title: str | None = None) -> None:
    entry = {"row": row, "last_posted": (now or now_local()).isoformat()}
    if title:
        entry["title"] = title
    _change(path, key, entry)


def ignore(path: Path, key: str) -> None:
    _change(path, key, {"ignore": True})


def alias(path: Path, key: str, to: str) -> None:
    _change(path, key, {"alias_of": to})


def ran(path: Path, now: datetime | None = None) -> None:
    registry = load_registry(path)
    registry["last_run"] = (now or now_local()).isoformat()
    save_registry(path, registry)


def _find(projects: dict, key: str) -> tuple[str, dict] | None:
    wanted = key.casefold()
    for name, entry in projects.items():
        if name.casefold() == wanted:
            return name, entry
    return None


def resolve(registry: dict, key: str) -> tuple[str, dict | None] | None:
    """The key a project is tracked under and its entry; None when it is ignored."""
    for _ in range(10):
        found = _find(registry["projects"], key)
        if found is None:
            return key, None
        name, entry = found
        if entry.get("ignore"):
            return None
        if "alias_of" not in entry:
            return name, entry
        key = entry["alias_of"]
    return key, None


def _below_root(path: PureWindowsPath, projects_root: PureWindowsPath, roots: dict) -> tuple[str, str, PureWindowsPath] | None:
    """The key, business and folder of the project holding this path.

    A root of one name ("VSTX-Projects") holds many projects: the path itself is the project, and the root alone is
    none. A root of several names ("DEF-Projects/itg-claude-plugins") is one project: everything in it is that project,
    and its neighbours are not looked at.
    """
    try:
        relative = path.relative_to(projects_root)
    except ValueError:
        return None
    named = sorted(((PureWindowsPath(root).parts, business) for root, business in roots.items()), key=lambda item: -len(item[0]))
    for parts, business in named:
        if len(relative.parts) < len(parts) or any(a.casefold() != b.casefold() for a, b in zip(relative.parts, parts)):
            continue
        if len(parts) > 1:
            project = PureWindowsPath(*relative.parts[:len(parts)])
            return str(project), business, projects_root / project
        if len(relative.parts) >= 2:
            return str(relative), business, path
    return None


def _git(folder: Path, *args: str) -> subprocess.CompletedProcess | None:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        return subprocess.run(
            ["git", "-C", str(folder), *args], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=60, creationflags=flags,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def repository(folder: Path) -> Path | None:
    """The main working tree of the repository holding this folder; worktrees lead to it too."""
    if not folder.is_dir():
        return None
    done = _git(folder, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if done is None or done.returncode != 0 or not done.stdout.strip():
        return None
    return Path(done.stdout.strip()).parent


def same_folder(one: Path, other: Path) -> bool:
    return os.path.normcase(os.path.abspath(one)) == os.path.normcase(os.path.abspath(other))


def project_of(cwd: str, registry: dict) -> tuple[str, Path, str] | None:
    """The project key, folder and business of a session's working folder, or None when it is not work."""
    projects_root = PureWindowsPath(registry["projects_root"])
    roots = registry["roots"]
    folder = PureWindowsPath(cwd)
    placed = _below_root(folder, projects_root, roots)
    if placed is None:
        return None
    repo = repository(Path(cwd))
    if repo is not None:
        repo_placed = _below_root(PureWindowsPath(repo), projects_root, roots)
        if repo_placed is not None:
            return repo_placed[0], repo, repo_placed[1]
    return placed[0], Path(str(placed[2])), placed[1]


def commits_since(repo: Path, since: datetime) -> list[dict]:
    """The person's own commits on local branches: what others pushed, or fetched branches, never reach the draft."""
    configured = _git(repo, "config", "user.email")
    email = configured.stdout.strip() if configured is not None and configured.returncode == 0 else ""
    if not email:
        return []
    done = _git(repo, "log", "--branches", "--fixed-strings", f"--author={email}", f"--since={since.isoformat()}",
                f"--format=%h{FIELD}%cI{FIELD}%s")
    if done is None or done.returncode != 0:
        return []
    found = []
    for line in done.stdout.splitlines():
        parts = line.split(FIELD)
        if len(parts) == 3:
            found.append({"hash": parts[0], "date": parts[1], "subject": parts[2]})
    return found


def memory_folder(claude_dir: Path, project_path: Path) -> Path | None:
    wanted = encode_folder(str(project_path)).casefold()
    candidates = [
        entry / "memory" for entry in claude_dir.iterdir()
        if entry.is_dir() and entry.name.casefold() == wanted and (entry / "memory").is_dir()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda memory: max((file.stat().st_mtime for file in memory.glob("*.md")), default=0.0))


def memory_changes(memory: Path | None, since: datetime) -> list[dict]:
    if memory is None:
        return []
    changed = [
        {"name": file.name, "path": str(file), "modified": modified(file).isoformat()}
        for file in memory.glob("*.md")
        if file.name != "MEMORY.md" and modified(file) >= since
    ]
    return sorted(changed, key=lambda item: item["modified"], reverse=True)


def memory_index(memory: Path | None) -> str:
    if memory is None or not (memory / "MEMORY.md").is_file():
        return ""
    return (memory / "MEMORY.md").read_text(encoding="utf-8", errors="replace")[:MEMORY_INDEX_CAP]


def recent_sessions(claude_dir: Path, since: datetime) -> list[tuple[Path, datetime]]:
    sessions = []
    for session in claude_dir.glob("*/*.jsonl"):
        when = modified(session)
        if when >= since:
            sessions.append((session, when))
    return sessions


def gather(claude_dir: Path, registry: dict, since: datetime | None = None, now: datetime | None = None) -> dict:
    now = now or now_local()
    if since is None:
        since = parse_time(registry["last_run"]) if registry.get("last_run") else start_of_day(now)
    found: dict[str, dict] = {}
    for session, when in recent_sessions(claude_dir, since):
        cwd = session_cwd(session)
        if cwd is None:
            continue
        placed = project_of(cwd, registry)
        if placed is None:
            continue
        key, path, business = placed
        tracked = resolve(registry, key)
        if tracked is None:
            continue
        key, entry = tracked
        project = found.setdefault(key.casefold(), {
            "key": key, "path": str(path), "business": business, "registry": entry,
            "sessions": 0, "last_active": when,
        })
        project["sessions"] += 1
        project["last_active"] = max(project["last_active"], when)

    projects = []
    for project in sorted(found.values(), key=lambda item: item["key"].casefold()):
        entry = project["registry"]
        last_posted = parse_time(entry["last_posted"]) if entry and entry.get("last_posted") else None
        window_start = start_of_day(last_posted or since)
        path = Path(project["path"])
        repo = repository(path)
        if repo is not None and not same_folder(repo, path):
            repo = None
        commits = commits_since(repo, window_start) if repo else []
        memory = memory_folder(claude_dir, path)
        changed = memory_changes(memory, window_start)
        if last_posted is None:
            new = True
        else:
            new = bool(commits_since(repo, last_posted) if repo else []) or any(
                parse_time(item["modified"]) > last_posted for item in changed
            )
        projects.append({
            **project,
            "last_active": project["last_active"].isoformat(),
            "new": new,
            "window_start": window_start.isoformat(),
            "commit_count": len(commits),
            "commits": commits[:COMMITS_SHOWN],
            "memory_changed": changed,
            "memory_index": memory_index(memory),
        })
    return {"since": since.isoformat(), "generated": now.isoformat(), "projects": projects}


def pending(claude_dir: Path, registry: dict, since: datetime | None = None, now: datetime | None = None) -> int:
    return sum(1 for project in gather(claude_dir, registry, since=since, now=now)["projects"] if project["new"])


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--claude-dir", type=Path, default=CLAUDE_PROJECTS)
    commands = parser.add_subparsers(dest="command", required=True)
    starting = commands.add_parser("init")
    starting.add_argument("--projects-root", required=True)
    starting.add_argument("--root", action="append", default=[], metavar="FOLDER=BUSINESS")
    starting.add_argument("--people", required=True)
    naming = commands.add_parser("person")
    naming.add_argument("--name", required=True)
    naming.add_argument("--id", type=int, required=True)
    gathering = commands.add_parser("gather")
    gathering.add_argument("--since")
    counting = commands.add_parser("pending")
    counting.add_argument("--since")
    recording = commands.add_parser("record")
    recording.add_argument("key")
    recording.add_argument("--row", type=int, required=True)
    recording.add_argument("--title")
    ignoring = commands.add_parser("ignore")
    ignoring.add_argument("key")
    aliasing = commands.add_parser("alias")
    aliasing.add_argument("key")
    aliasing.add_argument("--to", required=True)
    commands.add_parser("ran")
    options = parser.parse_args(arguments)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    registry_path = options.registry or default_registry_path()
    if options.command == "init":
        roots = dict(item.split("=", 1) for item in options.root)
        try:
            init_registry(registry_path, options.projects_root, roots, options.people)
        except FileExistsError as error:
            print(error)
            return 1
        print(f"Settings written to {registry_path}")
        return 0
    if not registry_path.exists():
        if options.command == "pending":
            print(0)
            return 0
        print(f"No settings yet at {registry_path}. Run the first-run setup in SKILL.md: tracker.py init ...")
        return 2
    options.registry = registry_path
    if options.command == "person":
        set_person(registry_path, options.name, options.id)
    elif options.command in ("gather", "pending"):
        registry = load_registry(options.registry)
        since = parse_time(options.since) if options.since else None
        if options.command == "gather":
            print(json.dumps(gather(options.claude_dir, registry, since=since), indent=2, ensure_ascii=False))
        else:
            print(pending(options.claude_dir, registry, since=since))
    elif options.command == "record":
        record(options.registry, options.key, options.row, title=options.title)
    elif options.command == "ignore":
        ignore(options.registry, options.key)
    elif options.command == "alias":
        alias(options.registry, options.key, options.to)
    else:
        ran(options.registry)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
