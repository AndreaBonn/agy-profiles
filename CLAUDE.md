# antigravity-account-pool

`agy-pool` (file unico `agy-pool`, Python solo libreria standard) ruota più account Antigravity CLI con failover sulla quota e porta la configurazione di Claude Code in `agy`.

## Comandi

```bash
uv run pytest        # test con un agy finto (tests/test_agy_pool.py)
uv run ruff check    # lint, config in pyproject.toml
uv run coverage run -m pytest && uv run coverage combine -q && uv run coverage report  # line+branch, fail_under 100
```

`pytest-cov` non va usato: lo script gira in subprocess e vede solo ~29%. La config `patch = ["subprocess", "execv"]` in `pyproject.toml` misura anche quelli.

## Struttura

- `agy-pool`: script con shebang `uv run --script`. Costanti in cima, comandi `cmd_*`, failover in `run_with_failover`.
- `tests/test_agy_pool.py`: unit test sulle funzioni pure e test di integrazione che lanciano lo script con un `agy` finto (`FAKE_AGY`).
- `docs/COMPATIBILITA-CLAUDE-CODE.md`: cosa `agy` accetta e cosa no, con lo stato di verifica.

## Convenzioni

- Codice, commenti e commit in inglese. README e docs in italiano.
- Keyword argument espliciti nelle funzioni.
- Nessun percorso personale nel codice: tutto parte da `Path.home()` e da `AGY_POOL_DIR`.

## Da sapere

- Il riconoscimento della quota (`QUOTA_RE`) non è stato visto su un errore reale di `agy`. Al primo errore vero guardare `~/.agy-pool/quota-errors.log` e tararlo.
- Lo stato condiviso tra gli account è fatto di symlink (`SHARED_ITEMS`). Il token resta per account e non va mai in `SHARED_ITEMS`.
- `DROPPED_AGENT_FIELDS` elenca i campi degli agent Claude che `agy` rifiuta. Se `agy` cambia versione, rifare la verifica descritta in `docs/`.
