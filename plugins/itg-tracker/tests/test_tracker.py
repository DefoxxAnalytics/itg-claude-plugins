import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "tracker-update"))

import tracker

NOW = datetime.now().astimezone().replace(microsecond=0)
TODAY = NOW.replace(hour=0, minute=0, second=0)


@pytest.fixture
def world(tmp_path):
    claude_dir = tmp_path / "claude" / "projects"
    projects_root = tmp_path / "Projects"
    claude_dir.mkdir(parents=True)
    projects_root.mkdir()
    registry_path = tmp_path / "registry.json"
    registry = {
        "projects_root": str(projects_root),
        "roots": {"VSTX-Projects": "Versatex", "XLC-Projects": "XLC"},
        "people_default": "Ada",
        "projects": {},
    }
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    return claude_dir, projects_root, registry_path


def folder_for(claude_dir: Path, cwd: Path) -> Path:
    folder = claude_dir / tracker.encode_folder(str(cwd))
    folder.mkdir(exist_ok=True)
    return folder


def make_session(claude_dir: Path, cwd: Path, when: datetime, name: str = "s.jsonl") -> Path:
    cwd.mkdir(parents=True, exist_ok=True)
    session = folder_for(claude_dir, cwd) / name
    lines = [{"type": "summary", "summary": "x"}, {"type": "user", "cwd": str(cwd), "message": "private"}]
    session.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
    stamp = when.timestamp()
    os.utime(session, (stamp, stamp))
    return session


def git(repo: Path, *args: str, when: datetime | None = None) -> str:
    env = dict(os.environ)
    if when is not None:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when.isoformat()
    done = subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
        capture_output=True, text=True, env=env, check=True,
    )
    return done.stdout


def make_repo(path: Path, commits: list[datetime]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    for number, when in enumerate(commits):
        (path / "f.txt").write_text(str(number), encoding="utf-8")
        git(path, "add", "f.txt")
        git(path, "commit", "-q", "-m", f"change {number}", when=when)
    return path


def run_gather(world, since: datetime | None = None) -> dict:
    claude_dir, _, registry_path = world
    registry = tracker.load_registry(registry_path)
    return tracker.gather(claude_dir, registry, since=since, now=NOW)


def keys(result: dict) -> list[str]:
    return sorted(project["key"] for project in result["projects"])


def test_session_cwd_reads_first_line_that_has_one(tmp_path):
    session = tmp_path / "s.jsonl"
    session.write_text(
        json.dumps({"type": "summary"}) + "\n"
        + json.dumps({"cwd": "C:\\first", "message": "private"}) + "\n"
        + json.dumps({"cwd": "C:\\second"}) + "\n",
        encoding="utf-8",
    )
    assert tracker.session_cwd(session) == "C:\\first"


def test_session_cwd_is_none_without_one(tmp_path):
    session = tmp_path / "s.jsonl"
    session.write_text(json.dumps({"type": "summary"}) + "\nnot json\n", encoding="utf-8")
    assert tracker.session_cwd(session) is None


def test_encode_folder_matches_claude_code_names():
    assert (
        tracker.encode_folder(r"C:\Users\ada\Documents\Projects\VSTX-Projects\Portal-v2\.worktrees\be2")
        == "C--Users-ada-Documents-Projects-VSTX-Projects-Portal-v2--worktrees-be2"
    )


def test_only_work_roots_are_kept(world):
    claude_dir, projects_root, _ = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Alpha", NOW)
    make_session(claude_dir, projects_root / "XLC-Projects" / "Beta", NOW)
    make_session(claude_dir, projects_root / "Personal" / "Gamma", NOW)
    make_session(claude_dir, projects_root / "DEF-Projects" / "Delta", NOW)
    make_session(claude_dir, projects_root / "VSTX-Projects", NOW)
    make_session(claude_dir, projects_root.parent / "Elsewhere", NOW)
    result = run_gather(world, since=TODAY)
    assert keys(result) == [r"VSTX-Projects\Alpha", r"XLC-Projects\Beta"]
    business = {project["key"]: project["business"] for project in result["projects"]}
    assert business == {r"VSTX-Projects\Alpha": "Versatex", r"XLC-Projects\Beta": "XLC"}


def test_root_names_match_whatever_their_case(world):
    claude_dir, projects_root, _ = world
    make_session(claude_dir, projects_root / "vstx-projects" / "Alpha", NOW)
    assert keys(run_gather(world, since=TODAY)) == [r"vstx-projects\Alpha"]


def test_sessions_before_since_are_left_out(world):
    claude_dir, projects_root, _ = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Old", NOW - timedelta(days=3))
    make_session(claude_dir, projects_root / "VSTX-Projects" / "New", NOW)
    assert keys(run_gather(world, since=TODAY)) == [r"VSTX-Projects\New"]


def test_sessions_of_one_project_are_counted_together(world):
    claude_dir, projects_root, _ = world
    alpha = projects_root / "VSTX-Projects" / "Alpha"
    make_session(claude_dir, alpha, NOW, "a.jsonl")
    make_session(claude_dir, alpha, NOW, "b.jsonl")
    make_session(claude_dir, alpha / "sub", NOW, "c.jsonl")
    result = run_gather(world, since=TODAY)
    assert keys(result) == [r"VSTX-Projects\Alpha", r"VSTX-Projects\Alpha\sub"]
    assert result["projects"][0]["sessions"] == 2


def test_a_worktree_and_a_subfolder_fold_into_their_repo(world):
    claude_dir, projects_root, _ = world
    repo = make_repo(projects_root / "VSTX-Projects" / "Repo", [NOW - timedelta(hours=2)])
    worktree = projects_root / "VSTX-Projects" / "Repo-wt"
    git(repo, "worktree", "add", "-q", "-b", "side", str(worktree))
    (repo / "sub").mkdir()
    make_session(claude_dir, worktree, NOW, "a.jsonl")
    make_session(claude_dir, repo / "sub", NOW, "b.jsonl")
    result = run_gather(world, since=TODAY)
    assert keys(result) == [r"VSTX-Projects\Repo"]
    assert result["projects"][0]["sessions"] == 2


def test_commits_in_the_window_are_capped_at_20(world):
    claude_dir, projects_root, _ = world
    times = [TODAY - timedelta(days=1)] + [TODAY + timedelta(seconds=10 + n) for n in range(25)]
    repo = make_repo(projects_root / "VSTX-Projects" / "Repo", times)
    make_session(claude_dir, repo, NOW)
    project = run_gather(world, since=TODAY)["projects"][0]
    assert project["commit_count"] == 25
    assert len(project["commits"]) == 20
    assert project["commits"][0]["subject"] == "change 25"
    assert set(project["commits"][0]) == {"hash", "date", "subject"}


def test_new_is_judged_against_the_last_post(world):
    claude_dir, projects_root, registry_path = world
    repo = make_repo(projects_root / "VSTX-Projects" / "Repo", [NOW - timedelta(hours=3)])
    make_session(claude_dir, repo, NOW)
    tracker.record(registry_path, r"VSTX-Projects\Repo", 7, now=NOW - timedelta(hours=1))
    project = run_gather(world, since=TODAY)["projects"][0]
    assert project["new"] is False
    assert project["registry"]["row"] == 7
    git(repo, "commit", "-q", "--allow-empty", "-m", "later", when=NOW - timedelta(minutes=5))
    assert run_gather(world, since=TODAY)["projects"][0]["new"] is True


def test_the_draft_window_starts_at_the_start_of_the_day_of_the_last_post(world):
    claude_dir, projects_root, registry_path = world
    morning = TODAY + timedelta(minutes=1)
    repo = make_repo(projects_root / "VSTX-Projects" / "Repo", [TODAY - timedelta(hours=1), morning])
    make_session(claude_dir, repo, NOW)
    tracker.record(registry_path, r"VSTX-Projects\Repo", 7, now=morning + timedelta(minutes=1))
    project = run_gather(world, since=TODAY)["projects"][0]
    assert [commit["subject"] for commit in project["commits"]] == ["change 1"]
    assert project["window_start"] == TODAY.isoformat()


def test_the_draft_window_starts_at_local_midnight_whatever_zone_the_post_was_saved_in(world):
    claude_dir, projects_root, registry_path = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Alpha", NOW)
    posted_in_utc = (TODAY + timedelta(minutes=1)).astimezone(timezone.utc)
    tracker.record(registry_path, r"VSTX-Projects\Alpha", 7, now=posted_in_utc)
    assert run_gather(world, since=TODAY)["projects"][0]["window_start"] == TODAY.isoformat()


def test_unregistered_projects_are_always_new(world):
    claude_dir, projects_root, _ = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Plain", NOW)
    project = run_gather(world, since=TODAY)["projects"][0]
    assert project["registry"] is None
    assert project["new"] is True


def test_memory_changes_count_as_new_and_are_listed(world):
    claude_dir, projects_root, registry_path = world
    alpha = projects_root / "VSTX-Projects" / "Alpha"
    make_session(claude_dir, alpha, NOW)
    memory = folder_for(claude_dir, alpha) / "memory"
    memory.mkdir()
    (memory / "MEMORY.md").write_text("- [State](state.md) - where it stands", encoding="utf-8")
    (memory / "state.md").write_text("state", encoding="utf-8")
    earlier = (NOW - timedelta(hours=5)).timestamp()
    os.utime(memory / "MEMORY.md", (earlier, earlier))
    tracker.record(registry_path, r"VSTX-Projects\Alpha", 3, now=NOW - timedelta(hours=2))
    project = run_gather(world, since=TODAY)["projects"][0]
    assert project["new"] is True
    assert [item["name"] for item in project["memory_changed"]] == ["state.md"]
    assert project["memory_index"].startswith("- [State]")


def test_memory_is_found_whatever_the_folder_case(world):
    claude_dir, projects_root, _ = world
    alpha = projects_root / "VSTX-Projects" / "Alpha"
    make_session(claude_dir, alpha, NOW)
    other_case = claude_dir / tracker.encode_folder(str(alpha)).swapcase()
    (other_case / "memory").mkdir(parents=True)
    (other_case / "memory" / "MEMORY.md").write_text("index", encoding="utf-8")
    assert run_gather(world, since=TODAY)["projects"][0]["memory_index"] == "index"


def test_the_memory_index_is_capped(world):
    claude_dir, projects_root, _ = world
    alpha = projects_root / "VSTX-Projects" / "Alpha"
    make_session(claude_dir, alpha, NOW)
    memory = folder_for(claude_dir, alpha) / "memory"
    memory.mkdir()
    (memory / "MEMORY.md").write_text("x" * 5000, encoding="utf-8")
    assert len(run_gather(world, since=TODAY)["projects"][0]["memory_index"]) == tracker.MEMORY_INDEX_CAP == 4000


def test_a_project_without_memory_or_git(world):
    claude_dir, projects_root, _ = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Bare", NOW)
    project = run_gather(world, since=TODAY)["projects"][0]
    assert project["memory_index"] == ""
    assert project["memory_changed"] == []
    assert project["commits"] == []
    assert project["commit_count"] == 0


def test_alias_and_ignore(world):
    claude_dir, projects_root, registry_path = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Old-name", NOW)
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Skip", NOW)
    tracker.record(registry_path, r"VSTX-Projects\Main", 4, now=NOW - timedelta(days=1))
    tracker.alias(registry_path, r"VSTX-Projects\Old-name", r"VSTX-Projects\Main")
    tracker.ignore(registry_path, r"vstx-projects\skip")
    result = run_gather(world, since=TODAY)
    assert keys(result) == [r"VSTX-Projects\Main"]
    assert result["projects"][0]["registry"]["row"] == 4


def test_pending_counts_only_new_projects(world):
    claude_dir, projects_root, registry_path = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Fresh", NOW)
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Posted", NOW)
    tracker.record(registry_path, r"VSTX-Projects\Posted", 9, now=NOW)
    registry = tracker.load_registry(registry_path)
    assert tracker.pending(claude_dir, registry, since=TODAY, now=NOW) == 1


def test_since_defaults_to_the_last_run(world):
    claude_dir, projects_root, registry_path = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Before", NOW - timedelta(hours=3))
    make_session(claude_dir, projects_root / "VSTX-Projects" / "After", NOW)
    tracker.ran(registry_path, now=NOW - timedelta(hours=1))
    assert keys(run_gather(world)) == [r"VSTX-Projects\After"]


def test_registry_writes_keep_other_entries_and_leave_no_temp_file(world):
    _, _, registry_path = world
    tracker.record(registry_path, "A", 1, now=NOW, title="Alpha")
    tracker.ignore(registry_path, "B")
    tracker.ran(registry_path, now=NOW)
    saved = json.loads(registry_path.read_text(encoding="utf-8"))
    assert saved["projects"]["A"] == {"row": 1, "last_posted": NOW.isoformat(), "title": "Alpha"}
    assert saved["projects"]["B"] == {"ignore": True}
    assert saved["last_run"] == NOW.isoformat()
    assert saved["roots"] == {"VSTX-Projects": "Versatex", "XLC-Projects": "XLC"}
    assert sorted(path.name for path in registry_path.parent.iterdir() if path.is_file()) == ["registry.json"]


def test_cli_prints_json(world, capsys):
    claude_dir, projects_root, registry_path = world
    make_session(claude_dir, projects_root / "VSTX-Projects" / "Alpha", NOW)
    code = tracker.main([
        "--registry", str(registry_path), "--claude-dir", str(claude_dir),
        "gather", "--since", TODAY.isoformat(),
    ])
    assert code == 0
    assert [project["key"] for project in json.loads(capsys.readouterr().out)["projects"]] == [r"VSTX-Projects\Alpha"]
    assert tracker.main(["--registry", str(registry_path), "--claude-dir", str(claude_dir), "pending"]) == 0
    assert capsys.readouterr().out.strip() == "1"


def test_settings_live_in_each_person_s_own_folder(monkeypatch, tmp_path):
    monkeypatch.delenv("TRACKER_REGISTRY", raising=False)
    assert tracker.default_registry_path() == Path.home() / ".claude" / "tracker-update" / "registry.json"
    monkeypatch.setenv("TRACKER_REGISTRY", str(tmp_path / "mine.json"))
    assert tracker.default_registry_path() == tmp_path / "mine.json"


def test_init_writes_settings_from_the_template(tmp_path):
    path = tmp_path / "settings" / "registry.json"
    tracker.init_registry(path, projects_root=r"C:\Work", roots={"VSTX-Projects": "Versatex"}, people="Ada")
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["list"]["site"] == "/sites/ITG"
    assert saved["list"]["title"] == "Progress tracker list"
    assert saved["projects_root"] == r"C:\Work"
    assert saved["roots"] == {"VSTX-Projects": "Versatex"}
    assert saved["people_default"] == "Ada"
    assert saved["projects"] == {}
    assert "assigned_to" not in saved
    assert "last_run" not in saved


def test_init_never_replaces_existing_settings(tmp_path):
    path = tmp_path / "registry.json"
    tracker.init_registry(path, projects_root=r"C:\Work", roots={"VSTX-Projects": "Versatex"}, people="Ada")
    with pytest.raises(FileExistsError):
        tracker.init_registry(path, projects_root=r"C:\Other", roots={}, people="Bob")
    assert json.loads(path.read_text(encoding="utf-8"))["people_default"] == "Ada"


def test_person_sets_who_new_rows_are_assigned_to(tmp_path):
    path = tmp_path / "registry.json"
    tracker.init_registry(path, projects_root=r"C:\Work", roots={}, people="Ada")
    tracker.set_person(path, "Lovelace, Ada", 42)
    assert json.loads(path.read_text(encoding="utf-8"))["assigned_to"] == {"name": "Lovelace, Ada", "id": 42}


def test_cli_init_reads_roots_as_folder_equals_business(tmp_path, capsys):
    path = tmp_path / "registry.json"
    code = tracker.main(["--registry", str(path), "init", "--projects-root", r"C:\Work",
                         "--root", "VSTX-Projects=Versatex", "--root", "XLC-Projects=XLC", "--people", "Ada"])
    assert code == 0
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["roots"] == {"VSTX-Projects": "Versatex", "XLC-Projects": "XLC"}
    assert tracker.main(["--registry", str(path), "person", "--name", "Lovelace, Ada", "--id", "42"]) == 0
    assert json.loads(path.read_text(encoding="utf-8"))["assigned_to"]["id"] == 42


def test_without_settings_pending_is_zero_and_gather_says_how_to_start(tmp_path, capsys):
    missing = tmp_path / "none" / "registry.json"
    claude_dir = tmp_path / "projects"
    claude_dir.mkdir()
    assert tracker.main(["--registry", str(missing), "--claude-dir", str(claude_dir), "pending"]) == 0
    assert capsys.readouterr().out.strip() == "0"
    assert tracker.main(["--registry", str(missing), "--claude-dir", str(claude_dir), "gather"]) == 2
    assert "init" in capsys.readouterr().out
    assert not missing.exists()
