"""Finds the work projects worked on in Claude Code, for the tracker-update skill.

    python tracker.py init --folder PATH=BUSINESS ... --project PATH=BUSINESS ... --people NAME
                                               (--folder: a folder of projects; --project: one project)
    python tracker.py add-folder PATH --business B [--single]
    python tracker.py remove-folder PATH
    python tracker.py person --name "Last, First" --id N
    python tracker.py gather [--since ISO]     projects with sessions since then, as JSON
    python tracker.py pending                  how many of them have something not yet posted
    python tracker.py projects                 every project that has a row, with what its notes can be drafted from
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
import time
from datetime import datetime, timedelta
from pathlib import Path, PureWindowsPath

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "registry.template.json"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
MEMORY_INDEX_CAP = 4000
COMMITS_SHOWN = 20
LINES_SEARCHED_FOR_CWD = 50
SAVE_ATTEMPTS = 6
SAVE_WAIT_SECONDS = 0.2
DOCS_SHOWN = 5
HISTORY_COMMITS = 40
HISTORY_DAYS = 730
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


def init_registry(path: Path, projects_root: str, roots: dict, people: str, folders: list[dict] | None = None) -> None:
    """A person's first settings, from the template; existing settings are never replaced."""
    if path.exists():
        raise FileExistsError(f"Settings already exist: {path}")
    registry = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    registry.update({"projects_root": projects_root, "roots": roots, "folders": folders or [], "people_default": people, "projects": {}})
    save_registry(path, registry)


def folder_entry(path: str, business: str, single: bool) -> dict:
    """A work folder for the settings; it must be a full path, such as D:\\Dev."""
    if not PureWindowsPath(path).is_absolute():
        raise ValueError(f"Give the full path of the folder, such as D:\\Dev: {path}")
    return {"path": str(PureWindowsPath(path)), "business": business, "kind": PROJECT if single else PROJECTS}


def add_folder(path: Path, folder: str, business: str, single: bool = False) -> None:
    entry = folder_entry(folder, business, single)
    registry = load_registry(path)
    kept = [item for item in registry.get("folders", []) if item["path"].casefold() != entry["path"].casefold()]
    registry["folders"] = kept + [entry]
    save_registry(path, registry)


def remove_folder(path: Path, folder: str) -> bool:
    wanted = str(PureWindowsPath(folder)).casefold()
    registry = load_registry(path)
    folders = registry.get("folders", [])
    kept = [item for item in folders if item["path"].casefold() != wanted]
    registry["folders"] = kept
    save_registry(path, registry)
    return len(kept) != len(folders)


def set_person(path: Path, name: str, user_id: int) -> None:
    registry = load_registry(path)
    registry["assigned_to"] = {"name": name, "id": user_id}
    save_registry(path, registry)


def _replace(temporary: str, path: Path) -> None:
    """os.replace, waiting out the moment Windows refuses because a scanner or indexer has the file open."""
    for attempt in range(SAVE_ATTEMPTS):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == SAVE_ATTEMPTS - 1:
                raise
            time.sleep(SAVE_WAIT_SECONDS)


def save_registry(path: Path, registry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".registry-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            json.dump(registry, file, indent=2, ensure_ascii=False)
            file.write("\n")
        _replace(temporary, path)
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


PROJECTS, PROJECT = "projects", "project"


def _inside(path: PureWindowsPath, folder: PureWindowsPath) -> bool:
    return len(path.parts) >= len(folder.parts) and all(a.casefold() == b.casefold() for a, b in zip(path.parts, folder.parts))


def work_folders(registry: dict) -> list[tuple[PureWindowsPath, str, str]]:
    """Every work folder as (path, business, kind), most specific first.

    A folder of kind "projects" holds projects: each path inside it is a project, the folder alone is none. A folder of
    kind "project" is one project: everything in it is that project. The older settings, `roots` under
    `projects_root`, mean the same: one name holds projects, several names ("DEF-Projects/tool") are one project.
    """
    found = []
    if registry.get("projects_root"):
        projects_root = PureWindowsPath(registry["projects_root"])
        for name, business in registry.get("roots", {}).items():
            parts = PureWindowsPath(name).parts
            found.append((projects_root.joinpath(*parts), business, PROJECT if len(parts) > 1 else PROJECTS))
    for folder in registry.get("folders", []):
        found.append((PureWindowsPath(folder["path"]), folder["business"], folder.get("kind", PROJECTS)))
    return sorted(found, key=lambda item: -len(item[0].parts))


def _place(path: PureWindowsPath, registry: dict) -> tuple[str, str, PureWindowsPath] | None:
    """The key, business and folder of the project holding this path, or None when it is not work.

    Keys are relative to `projects_root` when the project is under it (so older settings keep their keys), and
    otherwise start at the work folder's own name ("Dev\\Beta" for a project in D:\\Dev).
    """
    projects_root = PureWindowsPath(registry["projects_root"]) if registry.get("projects_root") else None
    for folder, business, kind in work_folders(registry):
        if not _inside(path, folder):
            continue
        if kind == PROJECT:
            project = PureWindowsPath(*path.parts[:len(folder.parts)])
        elif len(path.parts) > len(folder.parts):
            project = path
        else:
            continue
        if projects_root is not None and _inside(project, projects_root) and len(project.parts) > len(projects_root.parts):
            key = PureWindowsPath(*project.parts[len(projects_root.parts):])
        else:
            key = PureWindowsPath(*project.parts[len(folder.parts) - 1:])
        return str(key), business, project
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
    placed = _place(PureWindowsPath(cwd), registry)
    if placed is None:
        return None
    repo = repository(Path(cwd))
    if repo is not None:
        repo_placed = _place(PureWindowsPath(repo), registry)
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


def project_folders(registry: dict) -> list[PureWindowsPath]:
    """Every folder on this machine that the settings count as one project."""
    found = []
    for folder, _, kind in work_folders(registry):
        here = Path(str(folder))
        if not here.is_dir():
            continue
        if kind == PROJECT:
            found.append(folder)
        else:
            found.extend(PureWindowsPath(str(child)) for child in here.iterdir() if child.is_dir())
    return found


def registered_folders(registry: dict) -> list[PureWindowsPath]:
    """The folder of every project that has a row, wherever it sits under a work folder.

    A session can register a project nested deeper than its work folder (a tool inside a client's folder), which
    listing the work folders' own children does not reach.
    """
    starts = [PureWindowsPath(registry["projects_root"])] if registry.get("projects_root") else []
    starts += [folder.parent for folder, _, _ in work_folders(registry)]
    found = []
    for key, entry in registry["projects"].items():
        if "row" not in entry:
            continue
        for start in starts:
            candidate = start / PureWindowsPath(key)
            if Path(str(candidate)).is_dir():
                found.append(candidate)
                break
    return found


def readme_of(folder: Path) -> str | None:
    for file in sorted(folder.glob("*.md")):
        if file.stem.casefold() == "readme":
            return str(file)
    return None


def docs_of(folder: Path) -> list[str]:
    pages = sorted((folder / "docs").glob("*.md"), key=lambda page: page.stat().st_mtime, reverse=True)
    return [str(page) for page in pages[:DOCS_SHOWN]]


def projects(claude_dir: Path, registry: dict, now: datetime | None = None) -> dict:
    """Each project folder whose project has a row, with the files and history its notes page can be drafted from."""
    now = now or now_local()
    found: dict[str, dict] = {}
    for folder in project_folders(registry) + registered_folders(registry):
        placed = _place(folder, registry)
        if placed is None:
            continue
        key, business, project = placed
        tracked = resolve(registry, key)
        if tracked is None or tracked[1] is None or "row" not in tracked[1]:
            continue
        key, entry = tracked
        path = Path(str(project))
        repo = repository(path)
        if repo is not None and not same_folder(repo, path):
            repo = None
        memory = memory_folder(claude_dir, path)
        found[str(project).casefold()] = {
            "key": key, "path": str(path), "business": business, "row": entry["row"], "title": entry.get("title"),
            "readme": readme_of(path),
            "docs": docs_of(path),
            "commits": commits_since(repo, now - timedelta(days=HISTORY_DAYS))[:HISTORY_COMMITS] if repo else [],
            "memory_index": memory_index(memory),
            "memory_notes": [item["path"] for item in memory_changes(memory, datetime.min.replace(tzinfo=now.tzinfo))],
        }
    listed = sorted(found.values(), key=lambda item: (item["key"].casefold(), item["path"].casefold()))
    return {"generated": now.isoformat(), "projects": listed}


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--claude-dir", type=Path, default=CLAUDE_PROJECTS)
    commands = parser.add_subparsers(dest="command", required=True)
    starting = commands.add_parser("init")
    starting.add_argument("--projects-root", default="")
    starting.add_argument("--root", action="append", default=[], metavar="FOLDER=BUSINESS")
    starting.add_argument("--folder", action="append", default=[], metavar="PATH=BUSINESS")
    starting.add_argument("--project", action="append", default=[], metavar="PATH=BUSINESS")
    starting.add_argument("--people", required=True)
    adding = commands.add_parser("add-folder")
    adding.add_argument("folder")
    adding.add_argument("--business", required=True)
    adding.add_argument("--single", action="store_true")
    removing = commands.add_parser("remove-folder")
    removing.add_argument("folder")
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
    commands.add_parser("projects")
    options = parser.parse_args(arguments)

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    registry_path = options.registry or default_registry_path()
    if options.command == "init":
        try:
            if options.root and not options.projects_root:
                raise ValueError("--root needs --projects-root; use --folder with a full path instead")
            if not (options.root or options.folder or options.project):
                raise ValueError("Name at least one work folder: --folder PATH=BUSINESS or --project PATH=BUSINESS")
            roots = dict(item.split("=", 1) for item in options.root)
            folders = [folder_entry(*item.rsplit("=", 1), single=False) for item in options.folder]
            folders += [folder_entry(*item.rsplit("=", 1), single=True) for item in options.project]
            init_registry(registry_path, options.projects_root, roots, options.people, folders)
        except (FileExistsError, ValueError, TypeError) as error:
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
    elif options.command == "add-folder":
        try:
            add_folder(registry_path, options.folder, options.business, options.single)
        except ValueError as error:
            print(error)
            return 1
    elif options.command == "remove-folder":
        if not remove_folder(registry_path, options.folder):
            print(f"Not in the settings: {options.folder}")
            return 1
    elif options.command in ("gather", "pending"):
        registry = load_registry(options.registry)
        since = parse_time(options.since) if options.since else None
        if options.command == "gather":
            print(json.dumps(gather(options.claude_dir, registry, since=since), indent=2, ensure_ascii=False))
        else:
            print(pending(options.claude_dir, registry, since=since))
    elif options.command == "projects":
        print(json.dumps(projects(options.claude_dir, load_registry(options.registry)), indent=2, ensure_ascii=False))
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
