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

FAKE_AGY = """#!/bin/sh
acc="${HOME##*/}"
echo "$acc" >> "$AGY_CALLS"
printf '<%s>' "$@" >> "$AGY_ARGS"; echo >> "$AGY_ARGS"
[ -f "$AGY_FAKE_DIR/quota_$acc" ] && { echo "Error: 429 RESOURCE_EXHAUSTED quota" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/inelig_$acc" ] && { echo "Eligibility check failed: not eligible" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/auth_$acc" ] && { echo "Authentication required" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/error_$acc" ] && { echo "boom" >&2; exit 2; }
[ -f "$AGY_FAKE_DIR/talk_$acc" ] && { echo "the quota policy returns 429 sometimes"; exit 0; }
[ -f "$AGY_FAKE_DIR/big_$acc" ] && {
  head -c 10000 /dev/zero | tr '\\0' x; echo; echo "Error: 429 quota" >&2; exit 1; }
[ -f "$AGY_FAKE_DIR/bin_$acc" ] && { printf '\\377\\376 429 quota\\n'; exit 1; }
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
    """Module loaded once: for pure functions that touch no filesystem state."""
    return load_module()


@pytest.fixture
def fresh_pool(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Module reloaded with HOME and AGY_POOL_DIR inside tmp_path, for filesystem tests."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("AGY_POOL_DIR", str(tmp_path / "home" / ".agy-pool"))
    monkeypatch.delenv("AGY_POOL_RESET_HOURS", raising=False)
    (tmp_path / "home").mkdir()
    return load_module()


class PoolEnv:
    """A throwaway HOME with a fake ``agy`` first in PATH, driving the real script."""

    def __init__(self, root: Path) -> None:
        self.home = root / "home"
        self.fake = root / "fake"
        self.calls = root / "calls.txt"
        self.args_log = root / "args.txt"
        self.bin_dir = root / "bin"
        for directory in (self.home, self.fake, self.bin_dir):
            directory.mkdir()
        agy = self.bin_dir / "agy"
        agy.write_text(FAKE_AGY)
        agy.chmod(agy.stat().st_mode | stat.S_IXUSR)
        self.env = {
            **os.environ,
            "HOME": str(self.home),
            "PATH": f"{self.bin_dir}:{os.environ['PATH']}",
            "AGY_FAKE_DIR": str(self.fake),
            "AGY_CALLS": str(self.calls),
            "AGY_ARGS": str(self.args_log),
        }
        self.env.pop("AGY_POOL_DIR", None)
        self.env.pop("AGY_POOL_RESET_HOURS", None)

    @property
    def pool_dir(self) -> Path:
        return self.home / ".agy-pool"

    def add_account(self, name: str, *, token: bool = True) -> None:
        token_dir = self.pool_dir / name / ".gemini" / "antigravity-cli"
        token_dir.mkdir(parents=True)
        if token:
            (token_dir / "antigravity-oauth-token").write_text("{}")

    def flag(self, kind: str, name: str) -> None:
        (self.fake / f"{kind}_{name}").write_text("")

    def run(
        self, *args: str, extra_env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            env={**self.env, **(extra_env or {})},
            capture_output=True,
            text=True,
            errors="replace",
            timeout=60,
        )

    def called(self) -> list[str]:
        return self.calls.read_text().split() if self.calls.exists() else []

    def agy_args(self) -> list[str]:
        return self.args_log.read_text().splitlines() if self.args_log.exists() else []

    def state(self) -> dict:
        return json.loads((self.pool_dir / "state.json").read_text())

    def write_state(self, state: dict) -> None:
        self.pool_dir.mkdir(parents=True, exist_ok=True)
        (self.pool_dir / "state.json").write_text(json.dumps(state))

    def shared_settings(self) -> dict:
        return json.loads((self.pool_dir / "shared/antigravity-cli/settings.json").read_text())


@pytest.fixture
def env(tmp_path: Path) -> PoolEnv:
    pool_env = PoolEnv(tmp_path)
    for name in ("acc1", "acc2", "acc3"):
        pool_env.add_account(name)
    return pool_env


@pytest.fixture
def bare_env(tmp_path: Path) -> PoolEnv:
    """Same as ``env`` but with no account at all."""
    return PoolEnv(tmp_path)
