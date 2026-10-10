import json
import os
import time
from pathlib import Path

import pytest

# --- link_one -------------------------------------------------------------------------


def test_link_one_creates_the_target_directory_and_links_to_it(fresh_pool, tmp_path: Path) -> None:
    link, target = tmp_path / "a" / "link", tmp_path / "shared" / "dir"

    fresh_pool.link_one(link=link, target=target)

    assert link.is_symlink() and link.resolve() == target.resolve()
    assert target.is_dir()


def test_link_one_does_not_invent_a_directory_for_a_file_like_target(
    fresh_pool, tmp_path: Path
) -> None:
    link, target = tmp_path / "link.jsonl", tmp_path / "shared" / "h.jsonl"

    fresh_pool.link_one(link=link, target=target)

    assert link.is_symlink() and not target.exists()


def test_link_one_is_idempotent_when_already_linked(fresh_pool, tmp_path: Path) -> None:
    link, target = tmp_path / "link", tmp_path / "target"
    fresh_pool.link_one(link=link, target=target)
    (target / "keep").write_text("1")

    fresh_pool.link_one(link=link, target=target)

    assert (link / "keep").read_text() == "1"


def test_link_one_repoints_a_symlink_that_points_elsewhere(fresh_pool, tmp_path: Path) -> None:
    link, old, target = tmp_path / "link", tmp_path / "old", tmp_path / "target"
    old.mkdir()
    link.symlink_to(old)

    fresh_pool.link_one(link=link, target=target)

    assert link.resolve() == target.resolve()
    assert old.is_dir()


def test_link_one_moves_existing_content_into_a_missing_target(fresh_pool, tmp_path: Path) -> None:
    link, target = tmp_path / "link", tmp_path / "shared" / "target"
    link.mkdir()
    (link / "conv.txt").write_text("history")

    fresh_pool.link_one(link=link, target=target)

    assert link.is_symlink()
    assert (target / "conv.txt").read_text() == "history"


def test_link_one_backs_up_existing_content_when_the_target_already_exists(
    fresh_pool, tmp_path: Path
) -> None:
    link, target = tmp_path / "link", tmp_path / "target"
    link.mkdir()
    (link / "mine.txt").write_text("local")
    target.mkdir()
    (target / "theirs.txt").write_text("shared")

    fresh_pool.link_one(link=link, target=target)

    backups = list(tmp_path.glob("link.pre-pool-*"))
    assert len(backups) == 1
    assert (backups[0] / "mine.txt").read_text() == "local"
    assert (link / "theirs.txt").read_text() == "shared"
    assert int(backups[0].name.rsplit("-", 1)[1]) <= int(time.time())


def test_link_one_creates_every_missing_parent_of_the_link(fresh_pool, tmp_path: Path) -> None:
    link, target = tmp_path / "a" / "b" / "link", tmp_path / "target"

    fresh_pool.link_one(link=link, target=target)

    assert link.is_symlink()


def test_link_one_moves_content_into_a_target_whose_parent_is_missing_at_depth(
    fresh_pool, tmp_path: Path
) -> None:
    link, target = tmp_path / "link", tmp_path / "x" / "y" / "target"
    link.mkdir()
    (link / "conv.txt").write_text("history")

    fresh_pool.link_one(link=link, target=target)

    assert (target / "conv.txt").read_text() == "history"


def test_link_one_moves_content_into_a_missing_target_whose_parent_exists(
    fresh_pool, tmp_path: Path
) -> None:
    (tmp_path / "shared").mkdir()
    link, target = tmp_path / "link", tmp_path / "shared" / "target"
    link.mkdir()
    (link / "conv.txt").write_text("history")

    fresh_pool.link_one(link=link, target=target)

    assert (target / "conv.txt").read_text() == "history"


# --- add_allow_rules ------------------------------------------------------------------


def test_add_allow_rules_creates_the_settings_file(fresh_pool) -> None:
    fresh_pool.add_allow_rules(rules=["read_file(/a)"])

    settings = fresh_pool.SHARED_DIR / "antigravity-cli" / "settings.json"
    assert json.loads(settings.read_text()) == {"permissions": {"allow": ["read_file(/a)"]}}


def test_add_allow_rules_keeps_existing_settings_and_never_duplicates(fresh_pool) -> None:
    settings = fresh_pool.SHARED_DIR / "antigravity-cli" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"theme": "dark", "permissions": {"allow": ["x"]}}))

    fresh_pool.add_allow_rules(rules=["x", "y", "y"])
    fresh_pool.add_allow_rules(rules=["y"])

    data = json.loads(settings.read_text())
    assert data == {"theme": "dark", "permissions": {"allow": ["x", "y"]}}


# --- sync_agents ----------------------------------------------------------------------


def agents_dirs(pool) -> tuple[Path, Path]:
    return pool.CLAUDE_AGENTS_DIR, pool.SHARED_DIR / "config" / "agents"


def test_sync_agents_without_a_claude_agents_dir_creates_nothing(fresh_pool) -> None:
    fresh_pool.sync_agents()

    assert not fresh_pool.SHARED_DIR.exists()


def test_sync_agents_writes_converted_copies(fresh_pool) -> None:
    source, target = agents_dirs(fresh_pool)
    source.mkdir(parents=True)
    (source / "r.md").write_text("---\nname: r\nmodel: x\n---\nbody\n")

    fresh_pool.sync_agents()

    assert (target / "r.md").read_text() == "---\nname: r\n---\nbody\n"


@pytest.mark.parametrize("copy_time", [1_000, 2_000])
def test_sync_agents_does_not_overwrite_a_copy_that_is_not_older_than_its_source(
    fresh_pool, copy_time: int
) -> None:
    source, target = agents_dirs(fresh_pool)
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "r.md").write_text("---\nname: new\n---\n")
    (target / "r.md").write_text("hand edited")
    os.utime(source / "r.md", (1_000, 1_000))
    os.utime(target / "r.md", (copy_time, copy_time))

    fresh_pool.sync_agents()

    assert (target / "r.md").read_text() == "hand edited"


def test_sync_agents_refreshes_a_copy_older_than_its_source(fresh_pool) -> None:
    source, target = agents_dirs(fresh_pool)
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "r.md").write_text("---\nname: new\n---\n")
    (target / "r.md").write_text("stale")
    os.utime(target / "r.md", (1_000, 1_000))

    fresh_pool.sync_agents()

    assert (target / "r.md").read_text() == "---\nname: new\n---\n"


def test_sync_agents_removes_copies_whose_source_is_gone_and_keeps_other_files(
    fresh_pool,
) -> None:
    source, target = agents_dirs(fresh_pool)
    source.mkdir(parents=True)
    target.mkdir(parents=True)
    (source / "keep.md").write_text("---\nname: keep\n---\n")
    (target / "gone.md").write_text("orphan")
    (target / "notes.txt").write_text("not an agent")

    fresh_pool.sync_agents()

    assert not (target / "gone.md").exists()
    assert (target / "keep.md").exists()
    assert (target / "notes.txt").exists()


# --- locked_state ---------------------------------------------------------------------


def test_locked_state_fills_in_keys_missing_from_an_older_state_file(fresh_pool) -> None:
    fresh_pool.POOL_DIR.mkdir(parents=True)
    fresh_pool.STATE_FILE.write_text(json.dumps({"current": "acc2"}))

    with fresh_pool.locked_state() as state:
        snapshot = dict(state)

    assert snapshot == {"current": "acc2", "quota_hit": {}, "ineligible": []}


def test_locked_state_persists_changes_made_inside_the_block(fresh_pool) -> None:
    with fresh_pool.locked_state() as state:
        state["current"] = "acc9"

    assert json.loads(fresh_pool.STATE_FILE.read_text())["current"] == "acc9"


def test_locked_state_discards_changes_when_the_block_raises(fresh_pool) -> None:
    with fresh_pool.locked_state() as state:
        state["current"] = "acc1"

    with pytest.raises(RuntimeError), fresh_pool.locked_state() as state:
        state["current"] = "half-done"
        raise RuntimeError("boom")

    assert json.loads(fresh_pool.STATE_FILE.read_text())["current"] == "acc1"
