import time

import pytest
from conftest import PoolEnv

EXIT_ALL_EXHAUSTED = 75
HOUR = 3600


def hit_ago(hours: float) -> float:
    return time.time() - hours * HOUR


# --- dispatch: when does a command go through the failover? -----------------------------


@pytest.mark.parametrize(
    "args", [["-p", "hi"], ["--print", "hi"], ["--prompt", "hi"], ["--prompt=hi"]]
)
def test_print_flags_run_through_the_failover(env: PoolEnv, args: list[str]) -> None:
    env.flag("quota", "acc1")

    result = env.run(*args)

    assert result.returncode == 0
    assert env.called() == ["acc1", "acc2"]


@pytest.mark.parametrize("value", ["0", "", "true"])
def test_prompt_runs_do_not_rotate_unless_failover_is_exactly_1(env: PoolEnv, value: str) -> None:
    env.flag("quota", "acc1")

    result = env.run("-p", "hi", extra_env={"AGY_POOL_FAILOVER": value})

    assert result.returncode == 1  # agy's own quota failure, passed through: no rotation
    assert env.called() == ["acc1"]
    assert "nessun cambio automatico" in result.stderr


@pytest.mark.parametrize("args", [[], ["--printer"], ["chat", "--model", "x"]])
def test_other_invocations_are_interactive_without_failover(env: PoolEnv, args: list[str]) -> None:
    env.flag("quota", "acc1")

    result = env.run(*args)

    assert result.returncode == 1  # agy's own quota failure, passed through: no rotation
    assert env.called() == ["acc1"]
    assert "sessione su acc1" in result.stderr


def test_arguments_reach_agy_unchanged_in_both_modes(env: PoolEnv) -> None:
    env.run("-p", "two words", "--flag=a b")
    env.run("chat", "x")

    assert env.agy_args() == ["<-p><two words><--flag=a b>", "<chat><x>"]


def test_interactive_session_starts_on_the_current_account(env: PoolEnv) -> None:
    env.write_state({"current": "acc3", "quota_hit": {}, "ineligible": []})

    result = env.run()

    assert "risposta da acc3" in result.stdout


def test_interactive_session_propagates_the_agy_exit_code(env: PoolEnv) -> None:
    env.flag("error", "acc1")

    assert env.run().returncode == 2


def test_interactive_without_usable_accounts_fails(bare_env: PoolEnv) -> None:
    result = bare_env.run()

    assert result.returncode == 1
    assert "nessun account utilizzabile" in result.stderr


# --- ring construction ------------------------------------------------------------------


def test_run_without_usable_accounts_fails_without_calling_agy(bare_env: PoolEnv) -> None:
    result = bare_env.run("-p", "hi")

    assert result.returncode == 1
    assert "nessun account utilizzabile" in result.stderr
    assert bare_env.called() == []


def test_accounts_without_a_token_are_never_used(env: PoolEnv) -> None:
    env.add_account("acc0", token=False)

    env.run("-p", "hi")

    assert env.called() == ["acc1"]


def test_all_accounts_ineligible_fails_instead_of_exhausted(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {}, "ineligible": ["acc1", "acc2", "acc3"]})

    result = env.run("-p", "hi")

    assert result.returncode == 1
    assert env.called() == []


def test_unknown_current_account_starts_the_ring_from_the_first(env: PoolEnv) -> None:
    env.write_state({"current": "ghost", "quota_hit": {}, "ineligible": []})

    env.run("-p", "hi")

    assert env.called() == ["acc1"]


def test_ring_follows_natural_order_past_nine_accounts(env: PoolEnv) -> None:
    for name in ("acc9", "acc10"):
        env.add_account(name)
    for name in ("acc1", "acc2", "acc3", "acc9"):
        env.flag("quota", name)

    env.run("-p", "hi")

    assert env.called() == ["acc1", "acc2", "acc3", "acc9", "acc10"]


# --- quota window -----------------------------------------------------------------------


def test_account_hit_more_than_five_hours_ago_is_tried_again(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {"acc1": hit_ago(6)}, "ineligible": []})

    env.run("-p", "hi")

    assert env.called() == ["acc1"]
    assert env.state()["quota_hit"] == {}


def test_account_hit_within_five_hours_is_skipped(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {"acc1": hit_ago(4)}, "ineligible": []})

    env.run("-p", "hi")

    assert env.called() == ["acc2"]


def test_reset_window_is_configurable_through_the_environment(env: PoolEnv) -> None:
    env.write_state({"current": None, "quota_hit": {"acc1": hit_ago(2)}, "ineligible": []})

    env.run("-p", "hi", extra_env={"AGY_POOL_RESET_HOURS": "1"})

    assert env.called() == ["acc1"]


def test_exhaustion_message_estimates_the_earliest_reset(env: PoolEnv) -> None:
    oldest = hit_ago(4)
    env.write_state(
        {
            "current": None,
            "quota_hit": {"acc1": hit_ago(1), "acc2": oldest, "acc3": hit_ago(2)},
            "ineligible": [],
        }
    )
    expected = time.strftime("%F %H:%M", time.localtime(oldest + 5 * HOUR))

    result = env.run("-p", "hi")

    assert result.returncode == EXIT_ALL_EXHAUSTED
    assert env.called() == []
    assert f"Primo ripristino stimato: {expected} (stima: 5h dal primo errore)" in result.stderr


def test_exhaustion_message_reports_a_fractional_window(env: PoolEnv) -> None:
    env.write_state(
        {
            "current": None,
            "quota_hit": {n: hit_ago(0.1) for n in ("acc1", "acc2", "acc3")},
            "ineligible": [],
        }
    )

    result = env.run("-p", "hi", extra_env={"AGY_POOL_RESET_HOURS": "2.5"})

    assert "stima: 2.5h dal primo errore" in result.stderr


def test_all_accounts_failing_authentication_exit_75_without_a_fake_reset_estimate(
    env: PoolEnv,
) -> None:
    for name in ("acc1", "acc2", "acc3"):
        env.flag("auth", name)

    result = env.run("-p", "hi")

    assert result.returncode == EXIT_ALL_EXHAUSTED
    assert env.called() == ["acc1", "acc2", "acc3"]
    assert "Primo ripristino stimato" not in result.stderr
    assert env.state()["quota_hit"] == {}


def test_authentication_failure_rotates_to_the_next_account(env: PoolEnv) -> None:
    env.flag("auth", "acc1")

    result = env.run("-p", "hi")

    assert "risposta da acc2" in result.stdout
    assert "acc1: auth, passo al successivo" in result.stderr


# --- output capture ---------------------------------------------------------------------


def test_agy_output_is_echoed_to_stdout_including_its_stderr(env: PoolEnv) -> None:
    env.flag("error", "acc1")

    result = env.run("-p", "hi")

    assert "boom" in result.stdout


def test_quota_error_log_records_account_and_error_text(env: PoolEnv) -> None:
    env.flag("quota", "acc1")

    env.run("-p", "hi")

    log = (env.pool_dir / "quota-errors.log").read_text()
    assert "acc1" in log and "429 RESOURCE_EXHAUSTED" in log


def test_quota_error_log_is_not_written_for_other_failures(env: PoolEnv) -> None:
    env.flag("error", "acc1")

    env.run("-p", "hi")

    assert not (env.pool_dir / "quota-errors.log").exists()


def test_quota_message_after_a_long_output_is_still_detected(env: PoolEnv) -> None:
    env.flag("big", "acc1")

    result = env.run("-p", "hi")

    log = (env.pool_dir / "quota-errors.log").read_text()
    assert "risposta da acc2" in result.stdout
    assert len(log) < 5_000


def test_binary_output_with_a_quota_message_does_not_crash_the_failover(env: PoolEnv) -> None:
    env.flag("bin", "acc1")

    result = env.run("-p", "hi")

    assert result.returncode == 0
    assert env.called() == ["acc1", "acc2"]


# --- agy discovery ----------------------------------------------------------------------


def test_missing_agy_fails_with_a_clear_message(env: PoolEnv) -> None:
    result = env.run("-p", "hi", extra_env={"PATH": "/nonexistent"})

    assert result.returncode == 1
    assert "agy non trovato" in result.stderr


def test_agy_falls_back_to_the_local_bin_directory(env: PoolEnv) -> None:
    local = env.home / ".local" / "bin"
    local.mkdir(parents=True)
    (env.bin_dir / "agy").rename(local / "agy")

    result = env.run("-p", "hi", extra_env={"PATH": "/nonexistent"})

    assert "risposta da acc1" in result.stdout
