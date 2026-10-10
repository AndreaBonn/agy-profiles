import fcntl
import subprocess
import sys
from pathlib import Path

from conftest import SCRIPT, PoolEnv

# --- which failures ban an account ------------------------------------------------------


def test_authentication_failure_does_not_ban_the_account(env: PoolEnv) -> None:
    env.flag("auth", "acc1")

    env.run("-p", "hi")

    assert env.called() == ["acc1", "acc2"]
    assert env.state()["ineligible"] == []


def test_generic_error_does_not_ban_the_account(env: PoolEnv) -> None:
    env.flag("error", "acc1")

    env.run("-p", "hi")

    assert env.called() == ["acc1"]
    assert env.state()["ineligible"] == []


def test_checking_an_already_banned_account_again_does_not_list_it_twice(env: PoolEnv) -> None:
    env.flag("inelig", "acc1")

    env.run("pool", "check", "acc1")
    env.run("pool", "check", "acc1")

    assert env.state()["ineligible"] == ["acc1"]


# --- quota error log --------------------------------------------------------------------


def test_quota_error_log_keeps_the_entries_of_every_account_hit(env: PoolEnv) -> None:
    env.flag("quota", "acc1")
    env.flag("quota", "acc2")

    env.run("-p", "hi")

    log = (env.pool_dir / "quota-errors.log").read_text()
    assert "acc1" in log and "acc2" in log


# --- state lock -------------------------------------------------------------------------


def test_state_changes_wait_for_whoever_holds_the_state_lock(env: PoolEnv) -> None:
    with open(env.pool_dir / "state.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPT), "pool", "use", "acc2"],
            env=env.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            try:
                proc.wait(timeout=1)
                finished_while_locked = True
            except subprocess.TimeoutExpired:
                finished_while_locked = False
            fcntl.flock(lock, fcntl.LOCK_UN)
            returncode = proc.wait(timeout=60)
        finally:
            proc.kill()

    assert not finished_while_locked
    assert returncode == 0
    assert env.state()["current"] == "acc2"


# --- pool directory ---------------------------------------------------------------------


def test_pool_directory_is_created_with_all_its_missing_parents(
    env: PoolEnv, tmp_path: Path
) -> None:
    nested = tmp_path / "a" / "b" / "pool"

    result = env.run("pool", "status", extra_env={"AGY_POOL_DIR": str(nested)})

    assert result.returncode == 0
    assert (nested / "state.json").exists()
