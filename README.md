**English** | [Italiano](README.it.md)

```
  __ _   __ _  _   _
 / _` | / _` || | | |
| (_| || (_| || |_| |
 \__,_| \__, | \__, |
        |___/  |___/
```

# agy-profiles

Multiple Google accounts on Antigravity CLI without logging in again, plus your Claude Code configuration inside `agy`.

[![CI](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/agy-profiles/badges/test-badge.json)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/agy-profiles/badges/coverage-badge.json)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776ab)
![Platform](https://img.shields.io/badge/platform-linux-lightgrey)

> **Study project, unofficial.** It is not affiliated with or endorsed by Google, and it does not encourage bypassing Antigravity usage limits. How you use it, and whether your use complies with the [Antigravity terms](https://antigravity.google/terms/), is your own responsibility.

`agy-pool` is a command you run in place of `agy` (Antigravity CLI). It keeps each Google account in a separate profile, and you switch between them with one command instead of logging out and in every time.

`agy` normally keeps a single login per machine, in the system keyring. Anyone with a personal and a work account has to log in again at every switch. `agy-pool` runs `agy` with a different `HOME` directory for each account, so each login is done once. Conversations, history and configuration stay shared across profiles. The `pool init` command also brings the skills, rules and agents of an existing Claude Code configuration into `agy`.

## In practice

```text
$ agy-pool pool status
  acc1  pronto
  acc2  pronto
  acc3  senza login
$ agy-pool pool next
[agy-pool] account corrente: acc2
$ agy-pool pool status
  acc1  pronto
* acc2  pronto
  acc3  senza login
```

Real output on a test pool with three accounts, `acc3` having no login. The asterisk marks the current account. The messages are in Italian: `pronto` means ready, `senza login` means no login, `account corrente` means current account.

## What it does

- Keeps each account in a separate directory (`acc1`, `acc2`, ...), each with its own login.
- Changes the starting account with one command (`pool use`, `pool next`) and remembers the last one used.
- Shares conversations, history and configuration across accounts, so `-c` resumes a job even after a switch.
- With `pool init`, brings Claude Code skills, rules and agents into `agy`.
- On request, and only with `-p`, it can move to the next account when one answers with a quota error. This feature is experimental and **off by default** (see [Automatic account switch](#automatic-account-switch-experimental-off-by-default)).

## Tech stack

- Python 3.10 or later, standard library only, in a single file (`agy-pool`)
- [`uv`](https://docs.astral.sh/uv/) to run the script and the development tools
- pytest, coverage and ruff for tests, coverage and lint

## Prerequisites

- Linux. Tried only here, macOS not verified.
- [`agy`](https://antigravity.google/docs/getting-started?tab=cli) installed, and `uv`.
- A Google account with verified age. Without it, Antigravity answers "Eligibility check failed" and the account is left out of the rotation.

## Installation

1. `git clone https://github.com/AndreaBonn/agy-profiles.git`
2. `cd agy-profiles`
3. `ln -s "$PWD/agy-pool" ~/.local/bin/agy-pool`
4. `agy-pool pool status`

Step 4 must answer without errors, even with an empty list.

## First use

Log in once for each account, in your own terminal with a browser at hand.

1. `agy-pool pool login acc1`
2. Open the URL that appears, sign in with the first account, copy the code shown and paste it in the terminal.
3. Type `ping`, then `/exit`.
4. Repeat with `acc2`, `acc3`, ...
5. `agy-pool pool check` sends one request to each account and tells you which ones work.

Optional, if you use Claude Code: `agy-pool pool init` (see [Bringing your Claude Code configuration](#bringing-your-claude-code-configuration)).

## Daily use

`agy-pool` accepts the same arguments as `agy`.

| Command | What it does |
|---|---|
| `agy-pool` | Interactive session on the current account |
| `agy-pool -c` | Resumes the last conversation |
| `agy-pool -p "prompt"` | Single prompt on the current account |
| `agy-pool --agent NAME -p "..."` | Runs an agent (see `pool init`) |
| `agy-pool pool status` | Accounts that are ready, exhausted or not eligible |
| `agy-pool pool next` / `pool use accN` | Changes the starting account |
| `agy-pool pool login accN` | Adds an account |
| `agy-pool pool check [accN...]` | Checks the accounts with one request each |
| `agy-pool pool setup` | Relinks the shared state and resyncs the agents |

## Bringing your Claude Code configuration

`agy-pool pool init` does all of this in one go:

- links `~/.claude/skills` as `agy` skills (symlink);
- creates a global `AGENTS.md` with an index of your rules in `~/.claude/rules/`, and some included in full (`python-stack`, `git-workflow`, `security`, if they fit within the `agy` limit);
- adds to `settings.json` the read permissions for rules and skills and `command(ls)`;
- copies the agents from `~/.claude/agents/` removing the `model` and `tools` fields, which `agy` does not accept. The copy is refreshed at every start.

The repository contains no skills, rules or agents: `agy-pool` reads them from your `~/.claude` directory when you run `pool init`.

MCP servers are not brought over automatically: add them with `agy mcp add` (in the pool it applies to all accounts). In `-p` mode `agy` denies MCP tools without permission: for the ones you trust, add `mcp(NAME/*)` to `permissions.allow` in `~/.agy-pool/shared/antigravity-cli/settings.json`.

## Automatic account switch (experimental, off by default)

This is an optional feature, **disabled** until you ask for it. With `AGY_POOL_FAILOVER=1`, if `agy -p` answers with a quota error, `agy-pool` reruns the same prompt on the next account. If all accounts are exhausted it stops, prints a message and the estimated time of the first reset. Without the variable, `-p` runs on the current account and a quota error is passed through unchanged.

Turn it on per command:

```bash
AGY_POOL_FAILOVER=1 agy-pool -p "prompt"
```

or permanently with a `.env` file next to the script (ignored by git): `cp .env.example .env` and set `AGY_POOL_FAILOVER=1`. A variable already set in the shell wins over the file.

**Read this before turning it on.** The feature lets work continue when an account has reached its usage limit. The [Antigravity terms](https://antigravity.google/terms/) (clause 6) name as a breach the use of third-party software, tools or services to access the service, and provide for suspension of Antigravity and Gemini CLI accounts. `agy-pool` runs the official `agy` binary with regular logins and does not act as a proxy, but Google has not confirmed that this use is allowed. Turning it on, and any consequence, is the choice and responsibility of whoever turns it on.

Known limits of the feature:

- **Quota detection has not been seen on a real error.** It looks for words such as `429`, `RESOURCE_EXHAUSTED`, `quota`. It is tested with a fake `agy`. On the first real error the text is saved in `~/.agy-pool/quota-errors.log`: if the switch does not trigger, open an issue with that text.
- **The reset time is an estimate** of 5 hours from the first error. For free accounts, sources mention a weekly renewal: change the value with `AGY_POOL_RESET_HOURS=168`.
- **The switch only happens with `-p`.** In an interactive session the account is not changed midway: `/exit`, then `agy-pool pool next`, then `agy-pool -c`.
- **A prompt interrupted by the quota error restarts from the beginning** on the next account. For long jobs use `-c`.

## Configuration

Everything lives in `~/.agy-pool/`: accounts, state (`state.json`), the quota error log and the shared configuration. All variables are optional, from the shell or from `.env` (start from `.env.example`). The file reads only keys that start with `AGY_POOL_`, one per line, with no trailing comments.

| Variable | Required | Effect |
|---|---|---|
| `AGY_POOL_DIR` | ⚠️ | Data directory (default `~/.agy-pool`) |
| `AGY_POOL_FAILOVER` | ⚠️ | `1` turns on the automatic account switch with `-p` (default: off) |
| `AGY_POOL_RESET_HOURS` | ⚠️ | Estimated hours until the quota resets (default 5) |
| `AGY_POOL_ENV_FILE` | ⚠️ | Alternative path to the `.env` file (default: next to the script) |

## Known limits

- **Linux only.** macOS and Windows have not been tried.
- **In `-p`, MCP tools with long responses can produce empty output.** `agy` moves the response to a file in `brain/` and sometimes denies reading it for lack of permission. In an interactive session it asks for confirmation and works.
- **Agents used as subagents from another session are not verified.** As the main agent (`--agent`) they work.
- **Claude Code hooks do not run in `agy`.** A prohibition written in your rules (for example on `git push`) is not enforced by anything in `agy`.

## Repository structure

```text
agy-pool                # the script, a single file, standard library only
tests/                  # unit and integration tests with a fake agy
.github/                # CI workflow and the script that builds the badges
pyproject.toml          # lint, tests and coverage threshold
.env.example            # optional AGY_POOL_* variables
README.md               # documentation in English
README.it.md            # documentation in Italian
SECURITY.md             # security policy (English)
SECURITY.it.md          # security policy (Italian)
LICENSE
```

## Testing

The tests use a fake `agy` (`FAKE_AGY`) and run the script as a subprocess. The test count and coverage are in the badges at the top, refreshed by the CI on every push to `main`. Coverage counts lines and branches, with `fail_under = 100`.

```bash
uv run pytest
uv run ruff check
uv run coverage run -m pytest && uv run coverage combine -q && uv run coverage report
```

`pytest-cov` must not be used: the script runs in a subprocess and it sees only about 29% of it. The `patch = ["subprocess", "execv"]` setting in `pyproject.toml` measures those too.

## Contributing

For a bug, open an issue with the command you ran and its output. For a change, `uv run pytest`, `uv run ruff check` and 100% coverage must pass. Code and comments in English, documentation in English and Italian, named arguments in functions.

## Security

Use only accounts of your own. The OAuth tokens stay separate per account in `~/.agy-pool/accN/.gemini/antigravity-cli/antigravity-oauth-token`: do not copy them and do not put them in a repository. To report a vulnerability, see [SECURITY.md](./SECURITY.md).

## License

Released under the MIT License. See [LICENSE](./LICENSE).

## Support the project

If this project was useful to you, leave a star on [GitHub](https://github.com/AndreaBonn/agy-profiles): it helps others find it.
