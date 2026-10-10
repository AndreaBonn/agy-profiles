import importlib.machinery
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "agy-pool"
EXIT_ALL_EXHAUSTED = 75

FAKE_AGY = """#!/bin/sh
acc="${HOME##*/}"
echo "$acc" >> "$AGY_CALLS"
[ -f "$AGY_FAKE_DIR/quota_$acc" ] && { echo "Error: 429 RESOURCE_EXHAUSTED quota" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/inelig_$acc" ] && { echo "Eligibility check failed: not eligible" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/error_$acc" ] && { echo "boom" >&2; exit 2; }
[ -f "$AGY_FAKE_DIR/talk_$acc" ] && { echo "the quota policy returns 429 sometimes"; exit 0; }
echo "risposta da $acc"
"""


def load_module():
    loader = importlib.machinery.SourceFileLoader("agy_pool", str(SCRIPT))
    spec = importlib.util.spec_from_loader("agy_pool", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def pool():
    return load_module()


class PoolEnv:
    def __init__(self, root: Path) -> None:
        self.home = root / "home"
        self.fake = root / "fake"
        self.calls = root / "calls.txt"
        bin_dir = root / "bin"
        for directory in (self.home, self.fake, bin_dir):
            directory.mkdir()
        agy = bin_dir / "agy"
        agy.write_text(FAKE_AGY)
        agy.chmod(agy.stat().st_mode | stat.S_IXUSR)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "AGY_FAKE_DIR": str(self.fake),
            "AGY_CALLS": str(self.calls),
        }
        self.env.pop("AGY_POOL_DIR", None)

    @property
    def pool_dir(self) -> Path:
        return self.home / ".agy-pool"

    def add_account(self, name: str) -> None:
        token_dir = self.pool_dir / name / ".gemini" / "antigravity-cli"
        token_dir.mkdir(parents=True)
        (token_dir / "antigravity-oauth-token").write_text("{}")

    def flag(self, kind: str, name: str) -> None:
        (self.fake / f"{kind}_{name}").write_text("")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def called(self) -> list[str]:
        return self.calls.read_text().split() if self.calls.exists() else []

    def state(self) -> dict:
        return json.loads((self.pool_dir / "state.json").read_text())


@pytest.fixture
def env(tmp_path: Path) -> PoolEnv:
    pool_env = PoolEnv(tmp_path)
    for name in ("acc1", "acc2", "acc3"):
        pool_env.add_account(name)
    return pool_env


def test_failover_quota_on_first_account_answers_from_second(env: PoolEnv) -> None:
    env.flag("quota", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0
    assert "risposta da acc2" in result.stdout
    assert env.called() == ["acc1", "acc2"]
    assert env.state()["current"] == "acc2"


def test_failover_next_run_starts_from_last_working_account(env: PoolEnv) -> None:
    env.flag("quota", "acc1")
    env.run("-p", "hi")

    result = env.run("-p", "again")

    assert "risposta da acc2" in result.stdout
    assert env.called() == ["acc1", "acc2", "acc2"]


def test_failover_all_accounts_in_quota_exits_75_with_reset_estimate(env: PoolEnv) -> None:
    for name in ("acc1", "acc2", "acc3"):
        env.flag("quota", name)

    result = env.run("-p", "hi")

    assert result.returncode == EXIT_ALL_EXHAUSTED
    assert env.called() == ["acc1", "acc2", "acc3"]
    assert "tutti i 3 account" in result.stderr
    assert "Primo ripristino stimato" in result.stderr


def test_failover_rerun_after_exhaustion_does_not_call_agy(env: PoolEnv) -> None:
    for name in ("acc1", "acc2", "acc3"):
        env.flag("quota", name)
    env.run("-p", "hi")

    result = env.run("-p", "hi")

    assert result.returncode == EXIT_ALL_EXHAUSTED
    assert len(env.called()) == 3


def test_failover_ineligible_account_is_skipped_on_later_runs(env: PoolEnv) -> None:
    env.flag("inelig", "acc1")
    first = env.run("-p", "hi")

    second = env.run("-p", "hi")

    assert "risposta da acc2" in first.stdout
    assert "risposta da acc2" in second.stdout
    assert env.called() == ["acc1", "acc2", "acc2"]
    assert env.state()["ineligible"] == ["acc1"]


def test_failover_generic_error_is_returned_without_rotating(env: PoolEnv) -> None:
    env.flag("error", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 2
    assert env.called() == ["acc1"]


def test_failover_exit_zero_mentioning_quota_is_not_a_quota_error(env: PoolEnv) -> None:
    env.flag("talk", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0
    assert env.called() == ["acc1"]
    assert env.state()["quota_hit"] == {}


def test_status_ignores_directories_that_are_not_accounts(env: PoolEnv) -> None:
    (env.pool_dir / "backup").mkdir()

    status = env.run("pool", "status").stdout

    assert "backup" not in status
    assert "acc1" in status


def test_status_marks_account_with_quota_hit(env: PoolEnv) -> None:
    env.flag("quota", "acc1")
    env.run("-p", "hi")

    status = env.run("pool", "status").stdout

    acc1_line = next(line for line in status.splitlines() if "acc1" in line)
    acc3_line = next(line for line in status.splitlines() if "acc3" in line)
    assert "quota finita" in acc1_line
    assert "pronto" in acc3_line


def test_init_bridges_claude_code_config(env: PoolEnv) -> None:
    claude = env.home / ".claude"
    (claude / "rules").mkdir(parents=True)
    (claude / "rules" / "python-stack.md").write_text("# Python Stack\nuse uv\n")
    (claude / "rules" / "database.md").write_text("# Database: conventions\n")
    (claude / "skills" / "my-skill").mkdir(parents=True)
    (claude / "skills" / "my-skill" / "SKILL.md").write_text("---\nname: my-skill\n---\n")
    (claude / "agents").mkdir()
    (claude / "agents" / "reviewer.md").write_text(
        "---\nname: reviewer\nmodel: claude-opus-5-5\ntools: Read, Grep\n"
        "description: d\n---\nbody\n"
    )

    result = env.run("pool", "init")

    shared = env.pool_dir / "shared" / "config"
    assert result.returncode == 0
    agents_md = (shared / "AGENTS.md").read_text()
    assert "Database: conventions" in agents_md
    assert f"@[python-stack]({claude}/rules/python-stack.md)" in agents_md
    assert (shared / "skills").resolve() == (claude / "skills").resolve()
    agent = (shared / "agents" / "reviewer.md").read_text()
    assert "name: reviewer" in agent and "description: d" in agent
    assert "model:" not in agent and "tools:" not in agent
    settings = json.loads((env.pool_dir / "shared/antigravity-cli/settings.json").read_text())
    assert "command(ls)" in settings["permissions"]["allow"]
    assert f"read_file({claude}/rules)" in settings["permissions"]["allow"]
    assert (env.pool_dir / "acc1/.gemini/config").resolve() == shared.resolve()


def test_init_keeps_an_existing_agents_md(env: PoolEnv) -> None:
    (env.home / ".claude" / "rules").mkdir(parents=True)
    shared = env.pool_dir / "shared" / "config"
    shared.mkdir(parents=True)
    (shared / "AGENTS.md").write_text("my own rules\n")

    env.run("pool", "init")

    assert (shared / "AGENTS.md").read_text() == "my own rules\n"


AGENT = "---\nname: a\nmodel: claude-opus-5-5\ntools: Read, Grep\ndescription: d\n---\nbody\n"


def test_convert_agent_drops_model_and_tools_keeps_the_rest(pool) -> None:
    converted = pool.convert_agent(text=AGENT)

    assert converted == "---\nname: a\ndescription: d\n---\nbody\n"


def test_convert_agent_drops_multiline_tools_list(pool) -> None:
    text = "---\nname: a\ntools:\n  - Read\n  - Grep\ndescription: d\n---\nbody\n"

    assert pool.convert_agent(text=text) == "---\nname: a\ndescription: d\n---\nbody\n"


def test_convert_agent_keeps_model_text_inside_the_body(pool) -> None:
    text = "---\nname: a\nmodel: x\n---\nmodel: stays here\ntools: and here\n"

    converted = pool.convert_agent(text=text)

    assert "model: x" not in converted
    assert "model: stays here\ntools: and here\n" in converted


def test_convert_agent_without_frontmatter_is_unchanged(pool) -> None:
    assert pool.convert_agent(text="just text\n") == "just text\n"


@pytest.mark.parametrize(
    ("returncode", "text", "expected"),
    [
        (0, "all good", "ok"),
        (0, "mentions quota and 429", "ok"),
        (1, "Error 429 RESOURCE_EXHAUSTED", "quota"),
        (1, "rate limit reached", "quota"),
        (1, "Eligibility Check failed: not eligible", "ineligible"),
        (1, "Authentication required", "auth"),
        (2, "segfault", "error"),
    ],
)
def test_classify_maps_output_to_status(pool, returncode: int, text: str, expected: str) -> None:
    assert pool.classify(returncode=returncode, tail=text.encode()) == expected


def test_natural_key_sorts_numbers_numerically(pool) -> None:
    names = ["acc10", "acc2", "acc1"]

    assert sorted(names, key=pool.natural_key) == ["acc1", "acc2", "acc10"]


def test_build_agents_md_indexes_every_rule_and_inlines_those_that_fit(
    pool, tmp_path: Path
) -> None:
    (tmp_path / "python-stack.md").write_text("# Python Stack\nsmall\n")
    (tmp_path / "other.md").write_text("# Other topic\n")

    text = pool.build_agents_md(rules_dir=tmp_path)

    assert "Other topic" in text and "Python Stack" in text
    assert f"@[python-stack]({tmp_path}/python-stack.md)" in text
    assert "@[other]" not in text


def test_build_agents_md_skips_inlining_rules_over_the_budget(pool, tmp_path: Path) -> None:
    (tmp_path / "security.md").write_text("# Security\n" + "x" * (pool.AGENTS_MD_BUDGET + 1))

    text = pool.build_agents_md(rules_dir=tmp_path)

    assert "| Security |" in text
    assert "@[security]" not in text
