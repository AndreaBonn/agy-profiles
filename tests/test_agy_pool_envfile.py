from pathlib import Path

import pytest
from conftest import PoolEnv

# --- parse_env_text ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("AGY_POOL_FAILOVER=1", {"AGY_POOL_FAILOVER": "1"}),
        ("export AGY_POOL_FAILOVER=1", {"AGY_POOL_FAILOVER": "1"}),
        ("  AGY_POOL_FAILOVER = 1  ", {"AGY_POOL_FAILOVER": "1"}),
        ('AGY_POOL_DIR="/a b"', {"AGY_POOL_DIR": "/a b"}),
        ("AGY_POOL_DIR='/a b'", {"AGY_POOL_DIR": "/a b"}),
        ("AGY_POOL_DIR=\"/a b'", {"AGY_POOL_DIR": "\"/a b'"}),
        ('AGY_POOL_DIR="', {"AGY_POOL_DIR": '"'}),
        ("AGY_POOL_DIR=", {"AGY_POOL_DIR": ""}),
        ("AGY_POOL_A=x=y", {"AGY_POOL_A": "x=y"}),
        ("AGY_POOL_A=1\nAGY_POOL_B=2", {"AGY_POOL_A": "1", "AGY_POOL_B": "2"}),
    ],
)
def test_parse_env_text_reads_agy_pool_pairs(pool, text: str, expected: dict[str, str]) -> None:
    assert pool.parse_env_text(text=text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "",
        "\n\n",
        "# AGY_POOL_FAILOVER=1",
        "AGY_POOL_FAILOVER",
        "PATH=/evil",
        "LD_PRELOAD=/evil.so",
        "export PATH=/evil",
        "XAGY_POOL_FAILOVER=1",
    ],
)
def test_parse_env_text_ignores_comments_malformed_lines_and_foreign_keys(pool, text: str) -> None:
    assert pool.parse_env_text(text=text) == {}


def test_parse_env_text_keeps_valid_pairs_next_to_ignored_ones(pool) -> None:
    text = "PATH=/evil\n# note\nAGY_POOL_FAILOVER=1\n"

    assert pool.parse_env_text(text=text) == {"AGY_POOL_FAILOVER": "1"}


# --- load_env_file, through the real script ---------------------------------------------


def env_file(env: PoolEnv, content: str) -> Path:
    path = env.home / "pool.env"
    path.write_text(content)
    env.env["AGY_POOL_ENV_FILE"] = str(path)
    env.env.pop("AGY_POOL_FAILOVER")
    return path


def test_env_file_can_turn_failover_on(env: PoolEnv) -> None:
    env_file(env, "AGY_POOL_FAILOVER=1\n")
    env.flag("quota", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0
    assert env.called() == ["acc1", "acc2"]


def test_env_file_with_failover_off_keeps_it_off(env: PoolEnv) -> None:
    env_file(env, "AGY_POOL_FAILOVER=0\n")
    env.flag("quota", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 1
    assert env.called() == ["acc1"]


def test_a_real_environment_variable_wins_over_the_env_file(env: PoolEnv) -> None:
    env_file(env, "AGY_POOL_FAILOVER=1\n")
    env.flag("quota", "acc1")

    result = env.run("-p", "hi", extra_env={"AGY_POOL_FAILOVER": "0"})

    assert result.returncode == 1
    assert env.called() == ["acc1"]


def test_env_file_can_move_the_pool_directory(env: PoolEnv) -> None:
    elsewhere = env.home / "elsewhere"
    token_dir = elsewhere / "accX" / ".gemini" / "antigravity-cli"
    token_dir.mkdir(parents=True)
    (token_dir / "antigravity-oauth-token").write_text("{}")
    env_file(env, f"AGY_POOL_DIR={elsewhere}\n")

    env.run("pool", "use", "accX")

    assert (elsewhere / "state.json").exists()
    assert not (env.pool_dir / "state.json").exists()


def test_env_file_does_not_touch_variables_outside_the_prefix(env: PoolEnv) -> None:
    env_file(env, "PATH=/nonexistent\nAGY_POOL_FAILOVER=1\n")
    env.flag("quota", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0  # a rewritten PATH would have hidden the fake agy
    assert env.called() == ["acc1", "acc2"]


def test_env_file_saved_with_a_utf8_bom_still_applies_its_first_key(env: PoolEnv) -> None:
    path = env_file(env, "")
    path.write_bytes(b"\xef\xbb\xbfAGY_POOL_FAILOVER=1\n")
    env.flag("quota", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0
    assert env.called() == ["acc1", "acc2"]


def test_missing_env_file_is_not_an_error(env: PoolEnv) -> None:
    env.env["AGY_POOL_ENV_FILE"] = str(env.home / "absent.env")

    result = env.run("pool", "status")

    assert result.returncode == 0
