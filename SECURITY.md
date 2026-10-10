**English** | [Italiano](SECURITY.it.md)

# Security Policy

## Supported Versions

The project is in active development and has no tagged releases. Security updates are applied to the latest commit on `main`.

## Reporting a Vulnerability

To report a vulnerability, use the repository's [GitHub Security Advisories](https://github.com/AndreaBonn/agy-profiles/security/advisories/new). Do not open a public issue for security problems.

Include:

- a description of the problem
- steps to reproduce it
- expected and observed behavior
- impact: what an attacker could achieve

The project is maintained by one person and has no guaranteed response times. Reports are read and, if confirmed, fixed before the details are disclosed.

## Security Measures Implemented

The list is limited to what has been verified in the code.

- **No shell**: `agy` is started with `subprocess.Popen` and arguments passed as a list, without `shell=True` (`agy-pool:220`).
- **The `.env` file cannot change the execution environment**: only `AGY_POOL_*` keys are read, others (for example `PATH`, `LD_PRELOAD`) are ignored (`agy-pool:22-30`).
- **The token stays per account**: `antigravity-oauth-token` (`agy-pool:67`) is not among the items shared between profiles (`SHARED_ITEMS`, `agy-pool:68-76`).
- **Risky features off by default**: the automatic account switch turns on only with `AGY_POOL_FAILOVER=1` (`agy-pool:79`).
- **Dependencies**: the script uses only the Python standard library and `uv.lock` is in the repository.

What the project does not do: it does not set permissions on the token files (`agy` creates them, not `agy-pool`), it does not encrypt the data in `~/.agy-pool/`, and it has no automated vulnerability scanning (no CI).

## Security Best Practices for Users

- Use only accounts of your own. If your work account belongs to an organization, check with whoever administers it that using multiple accounts is allowed.
- Check that the `antigravity-oauth-token` files in `~/.agy-pool/accN/.gemini/antigravity-cli/` are not readable by other users on the machine.
- Do not copy tokens and do not put them in a repository or a shared backup.
- The `quota-errors.log` file in `~/.agy-pool/` contains the text of `agy` errors: review it before pasting it into an issue.
- The automatic account switch is experimental. Read the dedicated section of the [README](./README.md) and the [Antigravity terms](https://antigravity.google/terms/) before turning it on.

## Out of Scope

The following are not considered vulnerabilities of this project:

- problems in `agy`, in Antigravity or in Google services (report these to Google)
- suspension or limitation of an account by Google
- access to the files in `~/.agy-pool/` by someone who already has access to your system user
- social engineering or physical attacks

## Acknowledgments

People who report vulnerabilities responsibly will be listed here.

---

[Back to README](./README.md)
