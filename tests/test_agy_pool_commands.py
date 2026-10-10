import time
from pathlib import Path

import pytest
from conftest import PoolEnv

CHECK_PROMPT = "Reply with the single word OK"


def status_line(env: PoolEnv, name: str) -> str:
    out = env.run("pool", "status").stdout
    return next(line for line in out.splitlines() if name in line)


# --- status ---------------------------------------------------------------------------


def test_status_without_subcommand_is_status(env: PoolEnv) -> None:
    result = env.run("pool")

    assert result.returncode == 0
    assert "acc1  pronto" in result.stdout


def test_status_flags_account_without_login(env: PoolEnv) -> None:
    env.add_account("acc4", token=False)

    assert "senza login" in status_line(env, "acc4")
    assert "senza login" not in status_line(env, "acc1")


def test_status_flags_ineligible_account(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {}, "ineligible": ["acc2"]})

    assert "non idoneo" in status_line(env, "acc2")
    assert "non idoneo" not in status_line(env, "acc1")


def test_status_marks_only_the_current_account_with_a_star(env: PoolEnv) -> None:
    env.write_state({"current": "acc2", "quota_hit": {}, "ineligible": []})

    assert status_line(env, "acc2").startswith("*")
    assert status_line(env, "acc1").startswith(" ")


def test_status_shows_the_estimated_reset_time_for_a_quota_hit(env: PoolEnv) -> None:
    hit = time.time() - 3600
    env.write_state({"current": None, "quota_hit": {"acc1": hit}, "ineligible": []})
    expected = time.strftime("%F %H:%M", time.localtime(hit + 5 * 3600))

    assert f"ripristino stimato {expected}" in status_line(env, "acc1")


# --- use / next -----------------------------------------------------------------------


def test_use_sets_the_current_account(env: PoolEnv) -> None:
    result = env.run("pool", "use", "acc3")

    assert result.returncode == 0
    assert env.state()["current"] == "acc3"
    assert "account corrente: acc3" in result.stderr


@pytest.mark.parametrize(("current", "expected"), [("acc1", "acc2"), ("acc3", "acc1")])
def test_next_moves_to_the_following_account_and_wraps(
    env: PoolEnv, current: str, expected: str
) -> None:
    env.write_state({"current": current, "quota_hit": {}, "ineligible": []})

    env.run("pool", "next")

    assert env.state()["current"] == expected


def test_next_with_a_single_usable_account_stays_on_it(tmp_path: Path) -> None:
    single = PoolEnv(tmp_path)
    single.add_account("only")

    single.run("pool", "next")

    assert single.state()["current"] == "only"


def test_next_skips_ineligible_accounts(env: PoolEnv) -> None:
    env.write_state({"current": "acc1", "quota_hit": {}, "ineligible": ["acc2"]})

    env.run("pool", "next")

    assert env.state()["current"] == "acc3"


def test_use_unknown_account_fails_without_touching_the_state(env: PoolEnv) -> None:
    env.write_state({"current": "acc1", "quota_hit": {}, "ineligible": []})

    result = env.run("pool", "use", "ghost")

    assert result.returncode == 1
    assert "account sconosciuto: ghost" in result.stderr
    assert env.state()["current"] == "acc1"


def test_next_without_usable_accounts_fails(bare_env: PoolEnv) -> None:
    result = bare_env.run("pool", "next")

    assert result.returncode == 1
    assert "nessun account utilizzabile" in result.stderr


# --- check ----------------------------------------------------------------------------


def test_check_reports_each_account_and_records_quota(env: PoolEnv) -> None:
    env.flag("quota", "acc1")

    result = env.run("pool", "check")

    assert "== acc1: quota" in result.stdout
    assert "== acc2: ok" in result.stdout
    assert set(env.state()["quota_hit"]) == {"acc1"}


def test_check_with_names_only_probes_those_accounts_with_the_check_prompt(env: PoolEnv) -> None:
    env.run("pool", "check", "acc2")

    assert env.called() == ["acc2"]
    assert env.agy_args() == [f"<-p><{CHECK_PROMPT}>"]


def test_check_without_names_skips_accounts_without_a_token(env: PoolEnv) -> None:
    env.add_account("acc4", token=False)

    env.run("pool", "check")

    assert env.called() == ["acc1", "acc2", "acc3"]


# --- login ----------------------------------------------------------------------------


def test_login_creates_the_account_links_shared_state_and_launches_agy(env: PoolEnv) -> None:
    result = env.run("pool", "login", "acc4")

    state_dir = env.pool_dir / "acc4" / ".gemini" / "antigravity-cli"
    assert "risposta da acc4" in result.stdout
    assert env.agy_args() == ["<>"]
    assert (state_dir / "history.jsonl").is_symlink()
    assert (state_dir / "mcp").resolve() == (env.pool_dir / "shared/antigravity-cli/mcp").resolve()


def test_login_clears_the_ineligible_mark_of_that_account_only(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {}, "ineligible": ["acc1", "acc2"]})

    env.run("pool", "login", "acc1")

    assert env.state()["ineligible"] == ["acc2"]


def test_login_without_a_name_prints_usage_and_fails(env: PoolEnv) -> None:
    result = env.run("pool", "login")

    assert result.returncode == 1
    assert "uso: agy-pool pool" in result.stderr
    assert env.called() == []


def test_unknown_pool_subcommand_prints_usage_and_fails(env: PoolEnv) -> None:
    result = env.run("pool", "bogus")

    assert result.returncode == 1
    assert "uso: agy-pool pool" in result.stderr


# --- setup ----------------------------------------------------------------------------


def test_setup_on_a_machine_without_a_pool_does_nothing(bare_env: PoolEnv) -> None:
    result = bare_env.run("pool", "setup")

    assert result.returncode == 0
    assert not bare_env.pool_dir.exists()


def test_setup_links_every_account_to_the_shared_state(env: PoolEnv) -> None:
    result = env.run("pool", "setup")

    shared = env.pool_dir / "shared" / "antigravity-cli"
    assert "acc1: stato condiviso collegato" in result.stderr
    for name in ("acc1", "acc2", "acc3"):
        link = env.pool_dir / name / ".gemini" / "antigravity-cli" / "conversations"
        assert link.resolve() == (shared / "conversations").resolve()


def test_setup_never_shares_the_oauth_token(env: PoolEnv) -> None:
    env.run("pool", "setup")

    token = env.pool_dir / "acc1/.gemini/antigravity-cli/antigravity-oauth-token"
    assert token.is_file() and not token.is_symlink()


def test_setup_grants_every_account_its_own_read_rules(env: PoolEnv) -> None:
    env.run("pool", "setup")

    allow = env.shared_settings()["permissions"]["allow"]
    for name in ("acc1", "acc2", "acc3"):
        base = env.pool_dir / name / ".gemini" / "antigravity-cli"
        assert f"read_file({base}/mcp)" in allow
        assert f"read_file({base}/brain)" in allow


def test_setup_seeds_the_shared_config_from_the_users_own_agy_config(env: PoolEnv) -> None:
    config = env.home / ".gemini" / "config"
    config.mkdir(parents=True)
    (config / "AGENTS.md").write_text("my rules\n")

    env.run("pool", "setup")

    assert (env.pool_dir / "shared/config/AGENTS.md").read_text() == "my rules\n"


def test_setup_run_twice_changes_nothing(env: PoolEnv) -> None:
    env.run("pool", "setup")
    first = env.shared_settings()

    result = env.run("pool", "setup")

    assert result.returncode == 0
    assert env.shared_settings() == first


# --- init -----------------------------------------------------------------------------


def test_init_without_a_claude_dir_still_succeeds_and_creates_no_agents_md(env: PoolEnv) -> None:
    result = env.run("pool", "init")

    allow = env.shared_settings()["permissions"]["allow"]
    assert result.returncode == 0
    assert not (env.pool_dir / "shared/config/AGENTS.md").exists()
    assert "command(ls)" in allow
    assert not any("/.claude" in rule for rule in allow)


def test_init_grants_reads_only_for_claude_paths_that_exist(env: PoolEnv) -> None:
    (env.home / ".claude").mkdir()
    (env.home / ".claude" / "CLAUDE.md").write_text("# me\n")

    env.run("pool", "init")

    allow = env.shared_settings()["permissions"]["allow"]
    assert f"read_file({env.home}/.claude/CLAUDE.md)" in allow
    assert f"read_file({env.home}/.claude/skills)" not in allow
    assert f"read_file({env.home}/.claude/rules)" not in allow


def test_init_run_twice_keeps_one_copy_of_every_rule(env: PoolEnv) -> None:
    (env.home / ".claude" / "rules").mkdir(parents=True)

    env.run("pool", "init")
    result = env.run("pool", "init")

    allow = env.shared_settings()["permissions"]["allow"]
    assert result.returncode == 0
    assert len(allow) == len(set(allow))


# --- main dispatch --------------------------------------------------------------------


def write_claude_agent(env: PoolEnv) -> Path:
    agents = env.home / ".claude" / "agents"
    agents.mkdir(parents=True)
    (agents / "r.md").write_text("---\nname: r\nmodel: x\n---\nbody\n")
    return env.pool_dir / "shared/config/agents/r.md"


def test_a_prompt_run_syncs_claude_agents_first(env: PoolEnv) -> None:
    mirrored = write_claude_agent(env)

    env.run("-p", "hi")

    assert mirrored.read_text() == "---\nname: r\n---\nbody\n"


def test_pool_subcommands_that_do_not_set_up_leave_agents_alone(env: PoolEnv) -> None:
    mirrored = write_claude_agent(env)

    env.run("pool", "status")

    assert not mirrored.exists()
