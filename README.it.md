[English](README.md) | **Italiano**

```
  __ _   __ _  _   _
 / _` | / _` || | | |
| (_| || (_| || |_| |
 \__,_| \__, | \__, |
        |___/  |___/
```

# agy-profiles

Più account Google su Antigravity CLI senza rifare il login, e la tua configurazione di Claude Code dentro `agy`.

[![CI](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml/badge.svg)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/agy-profiles/badges/test-badge.json)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/AndreaBonn/agy-profiles/badges/coverage-badge.json)](https://github.com/AndreaBonn/agy-profiles/actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-%3E%3D3.10-3776ab)
![Platform](https://img.shields.io/badge/platform-linux-lightgrey)

> **Progetto di studio, non ufficiale.** Non è affiliato né approvato da Google e non incoraggia a eludere i limiti d'uso di Antigravity. Come lo usi, e se il tuo uso rispetta i [termini di Antigravity](https://antigravity.google/terms/), resta una tua responsabilità.

`agy-pool` è un comando che usa al posto di `agy` (Antigravity CLI) e tiene ogni account Google in un profilo separato. Passi dall'uno all'altro con un comando, senza uscire e rientrare ogni volta.

`agy` di norma conserva un solo login per macchina, nel portachiavi di sistema. Chi ha un account personale e uno di lavoro deve quindi rifare il login a ogni cambio. `agy-pool` lancia `agy` con una cartella `HOME` diversa per ogni account, così ogni login si fa una volta sola. Conversazioni, cronologia e configurazione restano condivise tra i profili. Il comando `pool init` porta in `agy` anche skill, regole e agent di una configurazione Claude Code già esistente.

## In pratica

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

Output reale su un pool di prova con tre account, di cui `acc3` senza login. L'asterisco segna l'account corrente.

## Cosa fa

- Tiene ogni account in una cartella separata (`acc1`, `acc2`, ...), ciascuno con il proprio login.
- Cambia l'account di partenza con un comando (`pool use`, `pool next`) e ricorda l'ultimo usato.
- Condivide tra gli account conversazioni, cronologia e configurazione, così `-c` riprende un lavoro anche dopo un cambio.
- Con `pool init` porta in `agy` skill, regole e agent di Claude Code.
- Su richiesta, e solo con `-p`, può passare all'account successivo quando uno risponde con un errore di quota. La funzione è sperimentale e **spenta di default** (vedi [Cambio automatico account](#cambio-automatico-account-sperimentale-spento-di-default)).

## Stack tecnologico

- Python 3.10 o superiore, solo libreria standard, in un unico file (`agy-pool`)
- [`uv`](https://docs.astral.sh/uv/) per eseguire lo script e gli strumenti di sviluppo
- pytest, coverage e ruff per test, copertura e lint

## Prerequisiti

- Linux. Provato solo qui, macOS non verificato.
- [`agy`](https://antigravity.google/docs/getting-started?tab=cli) installato e `uv`.
- Account Google con l'età verificata. Senza, Antigravity risponde "Eligibility check failed" e l'account viene escluso dal giro.

## Installazione

1. `git clone https://github.com/AndreaBonn/agy-profiles.git`
2. `cd agy-profiles`
3. `ln -s "$PWD/agy-pool" ~/.local/bin/agy-pool`
4. `agy-pool pool status`

Il passo 4 deve rispondere senza errori, anche con l'elenco vuoto.

## Primo uso

Fai il login una volta per ogni account, in un terminale tuo con il browser a disposizione.

1. `agy-pool pool login acc1`
2. Apri l'URL che compare, accedi con il primo account, copia il codice mostrato e incollalo nel terminale.
3. Scrivi `ping`, poi `/exit`.
4. Ripeti con `acc2`, `acc3`, ...
5. `agy-pool pool check` manda una richiesta a ogni account e dice quali funzionano.

Opzionale, se usi Claude Code: `agy-pool pool init` (vedi [Portare la configurazione di Claude Code](#portare-la-configurazione-di-claude-code)).

## Uso quotidiano

`agy-pool` accetta gli stessi argomenti di `agy`.

| Comando | Cosa fa |
|---|---|
| `agy-pool` | Sessione interattiva sull'account corrente |
| `agy-pool -c` | Riprende l'ultima conversazione |
| `agy-pool -p "prompt"` | Prompt singolo sull'account corrente |
| `agy-pool --agent NOME -p "..."` | Esegue un agent (vedi `pool init`) |
| `agy-pool pool status` | Account pronti, esauriti, non idonei |
| `agy-pool pool next` / `pool use accN` | Cambia l'account di partenza |
| `agy-pool pool login accN` | Aggiunge un account |
| `agy-pool pool check [accN...]` | Verifica gli account con una richiesta ciascuno |
| `agy-pool pool setup` | Ricollega lo stato condiviso e risincronizza gli agent |

## Portare la configurazione di Claude Code

`agy-pool pool init` fa in un colpo solo:

- collega `~/.claude/skills` come skill di `agy` (symlink);
- crea un `AGENTS.md` globale con l'indice delle tue regole in `~/.claude/rules/` e alcune incluse per intero (`python-stack`, `git-workflow`, `security`, se ci stanno nel limite di `agy`);
- aggiunge a `settings.json` i permessi di lettura per regole e skill e `command(ls)`;
- copia gli agent di `~/.claude/agents/` togliendo i campi `model` e `tools`, che `agy` non accetta. La copia si aggiorna a ogni avvio.

Il repository non contiene skill, regole o agent: `agy-pool` li legge dalla tua cartella `~/.claude` quando lanci `pool init`.

I server MCP non si portano in automatico: aggiungili con `agy mcp add` (nel pool vale per tutti gli account). In modalità `-p` `agy` nega i tool MCP senza permesso: per quelli di cui ti fidi aggiungi `mcp(NOME/*)` in `permissions.allow` di `~/.agy-pool/shared/antigravity-cli/settings.json`.

## Cambio automatico account (sperimentale, spento di default)

Funzione opzionale, **disattivata** finché non la chiedi tu. Con `AGY_POOL_FAILOVER=1`, se `agy -p` risponde con un errore di quota, `agy-pool` rilancia lo stesso prompt sull'account successivo. Se tutti gli account sono esauriti si ferma, stampa un messaggio e l'orario stimato del primo ripristino. Senza la variabile, `-p` gira sull'account corrente e un errore di quota viene passato così com'è.

Si accende a comando:

```bash
AGY_POOL_FAILOVER=1 agy-pool -p "prompt"
```

oppure in modo permanente con un file `.env` accanto allo script (ignorato da git): `cp .env.example .env` e metti `AGY_POOL_FAILOVER=1`. Una variabile già impostata nella shell vince sul file.

**Leggi prima di attivarla.** La funzione fa continuare il lavoro quando un account ha raggiunto il limite d'uso. I [termini di Antigravity](https://antigravity.google/terms/) (clausola 6) indicano come violazione l'uso di software, strumenti o servizi di terze parti per accedere al servizio e prevedono la sospensione degli account Antigravity e Gemini CLI. `agy-pool` lancia il binario `agy` ufficiale con login normali e non fa da proxy, ma Google non ha confermato che questo uso sia consentito. Attivarla e subirne le conseguenze è una scelta e una responsabilità di chi la attiva.

Limiti noti della funzione:

- **Il riconoscimento della quota non è stato visto su un errore reale.** Cerca parole come `429`, `RESOURCE_EXHAUSTED`, `quota`. È provato con un `agy` finto. Al primo errore vero il testo viene salvato in `~/.agy-pool/quota-errors.log`: se il cambio account non scatta, apri una issue con quel testo.
- **L'orario di ripristino è una stima** di 5 ore dal primo errore. Per gli account gratuiti le fonti parlano di un rinnovo settimanale: cambia il valore con `AGY_POOL_RESET_HOURS=168`.
- **Il cambio c'è solo con `-p`.** In una sessione interattiva non si cambia account a metà: `/exit`, poi `agy-pool pool next`, poi `agy-pool -c`.
- **Un prompt interrotto dall'errore di quota riparte da capo** sull'account successivo. Per i lavori lunghi usa `-c`.

## Configurazione

Tutto sta in `~/.agy-pool/`: account, stato (`state.json`), log degli errori di quota e configurazione condivisa. Le variabili sono opzionali, da shell o da `.env` (parti da `.env.example`). Il file legge solo le chiavi che iniziano con `AGY_POOL_`, una per riga, senza commenti a fine riga.

| Variabile | Obbligatoria | Effetto |
|---|---|---|
| `AGY_POOL_DIR` | ⚠️ | Cartella dei dati (default `~/.agy-pool`) |
| `AGY_POOL_FAILOVER` | ⚠️ | `1` attiva il cambio automatico account con `-p` (default: spento) |
| `AGY_POOL_RESET_HOURS` | ⚠️ | Ore stimate al ripristino della quota (default 5) |
| `AGY_POOL_ENV_FILE` | ⚠️ | Percorso alternativo al `.env` (default: accanto allo script) |

## Limiti noti

- **Linux soltanto.** macOS e Windows non sono stati provati.
- **In `-p` i tool MCP con risposte lunghe possono dare output vuoto.** `agy` sposta la risposta su un file in `brain/` e a volte nega la lettura per mancanza di permesso. In sessione interattiva chiede conferma e funziona.
- **Gli agent usati come subagent da un'altra sessione non sono verificati.** Come agent principale (`--agent`) funzionano.
- **Gli hook di Claude Code non girano in `agy`.** Un divieto scritto nelle tue regole (per esempio sul `git push`) in `agy` non è bloccato da nulla.

## Struttura del repository

```text
agy-pool                # lo script, unico file, solo libreria standard
tests/                  # test unitari e di integrazione con un agy finto
.github/                # workflow CI e script che costruisce i badge
pyproject.toml          # lint, test e soglia di copertura
.env.example            # variabili opzionali AGY_POOL_*
README.md               # documentazione in inglese
README.it.md            # documentazione in italiano
SECURITY.md             # politica di sicurezza (inglese)
SECURITY.it.md          # politica di sicurezza (italiano)
LICENSE
```

## Testing

I test usano un `agy` finto (`FAKE_AGY`) e lanciano lo script come subprocess. Il numero di test e la copertura sono nei badge in cima, aggiornati dalla CI a ogni push su `main`. La copertura conta linee e rami, con `fail_under = 100`.

```bash
uv run pytest
uv run ruff check
uv run coverage run -m pytest && uv run coverage combine -q && uv run coverage report
```

`pytest-cov` non va usato: lo script gira in subprocess e ne vede solo il 29% circa. La configurazione `patch = ["subprocess", "execv"]` in `pyproject.toml` misura anche quelli.

## Come contribuire

Per un bug apri una issue con il comando lanciato e l'output. Per una modifica, `uv run pytest`, `uv run ruff check` e la copertura al 100% devono passare. Codice e commenti in inglese, documentazione in inglese e italiano, argomenti nominati nelle funzioni.

## Sicurezza

Usa solo account tuoi. I token OAuth restano separati per account in `~/.agy-pool/accN/.gemini/antigravity-cli/antigravity-oauth-token`: non copiarli e non metterli in un repository. Per segnalare una vulnerabilità, consulta [SECURITY.it.md](./SECURITY.it.md).

## Licenza

Rilasciato con licenza MIT. Vedi [LICENSE](./LICENSE).

## Supporta il progetto

Se questo progetto ti è stato utile, lascia una stella su [GitHub](https://github.com/AndreaBonn/agy-profiles): aiuta altri a scoprirlo.

agy-profiles è gratuito. Se ti è utile e vuoi contribuire, puoi lasciare un'offerta tramite PayPal. L'importo lo scegli tu ed è del tutto facoltativo.

<div align="center">

[![Dona con PayPal](https://img.shields.io/badge/Dona-PayPal-00457C?logo=paypal&logoColor=white&style=for-the-badge)](https://paypal.me/AndreaBonacci19)

</div>
