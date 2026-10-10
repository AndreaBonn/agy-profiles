# antigravity-account-pool

> **Progetto di studio.** Non incoraggia a eludere i limiti d'uso di Antigravity. Leggi i [termini di Antigravity](https://antigravity.google/terms/) prima di usarlo.

`agy-pool` è un comando che permette di usare più account Google con Antigravity CLI (`agy`) senza rifare il login a ogni cambio. Il caso tipico è un account personale e uno di lavoro sulla stessa macchina: `agy` di norma conserva un solo login per macchina (nel portachiavi di sistema), e passare da un account all'altro vorrebbe dire uscire e rientrare ogni volta.

Funziona come `agy`: al posto di `agy` lanci `agy-pool`, con gli stessi argomenti.

## Cosa fa

- Tiene ogni account in una cartella separata (`acc1`, `acc2`, ...), ciascuno con il proprio login fatto una volta sola.
- Cambia l'account di partenza con un comando (`pool use`, `pool next`) e ricorda l'ultimo usato.
- Condivide tra gli account conversazioni, cronologia e configurazione, così `-c` riprende un lavoro anche dopo un cambio.
- Con `pool init` porta in `agy` skill, regole e agent di una configurazione Claude Code già esistente.

Esiste anche una funzione sperimentale di cambio automatico account, **spenta di default** (vedi [Cambio automatico account](#cambio-automatico-account-sperimentale-spento-di-default)).

## Requisiti

- Linux. Provato solo qui, macOS non verificato.
- [`agy`](https://antigravity.google/docs/getting-started?tab=cli) installato e [`uv`](https://docs.astral.sh/uv/).
- Account Google con l'età verificata. Senza, Antigravity risponde "Eligibility check failed" e l'account viene escluso dal giro.

## Installazione

```bash
git clone <url-del-repository> antigravity-account-pool
cd antigravity-account-pool
ln -s "$PWD/agy-pool" ~/.local/bin/agy-pool
agy-pool pool status
```

L'ultimo comando deve rispondere senza errori (anche con l'elenco vuoto).

## Primo uso

Fai il login una volta per ogni account, in un terminale tuo con il browser a disposizione.

1. `agy-pool pool login acc1`
2. Apri l'URL che compare, accedi con il primo account, copia il codice mostrato e incollalo nel terminale.
3. Scrivi `ping`, poi `/exit`.
4. Ripeti con `acc2`, `acc3`, ...
5. `agy-pool pool check` manda una richiesta a ogni account e dice quali funzionano.

Opzionale, se usi Claude Code: `agy-pool pool init` (vedi sotto).

## Uso quotidiano

| Comando | Cosa fa |
|---|---|
| `agy-pool` | Sessione interattiva sull'account corrente, come `claude` |
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

I server MCP non si portano in automatico: aggiungili con `agy mcp add` (nel pool vale per tutti gli account). In modalità `-p` `agy` nega i tool MCP senza permesso: per quelli che ti fidi di usare aggiungi `mcp(NOME/*)` in `permissions.allow` di `~/.agy-pool/shared/antigravity-cli/settings.json`.

I dettagli e le scoperte sul formato sono in [docs/COMPATIBILITA-CLAUDE-CODE.md](docs/COMPATIBILITA-CLAUDE-CODE.md).

## Limiti noti

- **Linux soltanto.** macOS e Windows non sono stati provati.
- **In `-p` i tool MCP con risposte lunghe possono dare output vuoto.** `agy` sposta la risposta su un file in `brain/` e a volte nega la lettura per mancanza di permesso. In sessione interattiva chiede conferma e funziona.
- **Gli agent usati come subagent da un'altra sessione non sono verificati.** Come agent principale (`--agent`) funzionano.
- **Gli hook di Claude Code non girano in `agy`.** Un divieto scritto nelle tue regole (per esempio sul `git push`) in `agy` non è bloccato da nulla.

## Sicurezza

- Usa solo account tuoi. I token OAuth stanno in `~/.agy-pool/accN/.gemini/antigravity-cli/antigravity-oauth-token` (permessi `0600`): non copiarli e non metterli in un repository.
- Se l'account di lavoro appartiene a un'organizzazione, verifica con chi lo amministra che l'uso di più account sia consentito.
- L'uso di più account e il rischio di sospensione sono a tuo carico: questo repository non dà garanzie in merito.

## Cambio automatico account (sperimentale, spento di default)

Questa funzione è **disattivata** se non la chiedi. Si accende con `AGY_POOL_FAILOVER=1`, a comando:

```bash
AGY_POOL_FAILOVER=1 agy-pool -p "prompt"
```

oppure in modo permanente sulla tua macchina con un file `.env` accanto allo script (ignorato da git): `cp .env.example .env` e metti `AGY_POOL_FAILOVER=1`. Una variabile già impostata nella shell vince sul file.

Con la variabile attiva, se `agy` risponde con un errore di quota, `agy-pool` rilancia lo stesso prompt sull'account successivo. Se tutti gli account sono esauriti si ferma, stampa un messaggio e l'orario stimato del primo ripristino. Senza la variabile, `-p` gira sull'account corrente e un errore di quota viene passato così com'è.

**Rischio a tuo carico.** Questa funzione di fatto permette di continuare a lavorare quando un limite d'uso è stato raggiunto. I [termini aggiuntivi di Antigravity](https://antigravity.google/terms/) (clausola 6) vietano l'uso di software o servizi di terze parti per accedere al servizio e prevedono la sospensione degli account Antigravity e Gemini CLI. Google ha già sospeso account per l'uso di strumenti che consumavano le quote di Antigravity. `agy-pool` lancia il binario `agy` ufficiale con login normali e non fa da proxy, ma non c'è una conferma di Google che questo uso sia consentito. Se non vuoi correre il rischio, non attivarla.

Limiti noti della funzione:

- **Il riconoscimento della quota non è stato visto su un errore reale.** Cerca parole come `429`, `RESOURCE_EXHAUSTED`, `quota`. È provato con un `agy` finto. Al primo errore vero il testo viene salvato in `~/.agy-pool/quota-errors.log`: se il cambio account non scatta, apri una issue con quel testo.
- **L'orario di ripristino è una stima** di 5 ore dal primo errore. Per gli account gratuiti le fonti parlano di un rinnovo settimanale: cambia il valore con `AGY_POOL_RESET_HOURS=168`.
- **Il cambio c'è solo con `-p`.** In una sessione interattiva non si cambia account a metà: `/exit`, poi `agy-pool pool next`, poi `agy-pool -c`.
- **Un prompt interrotto dall'errore di quota riparte da capo** sull'account successivo. Per i lavori lunghi usa `-c`.

## Dati e variabili

Tutto sta in `~/.agy-pool/` (account, stato, log degli errori di quota, configurazione condivisa). Variabili opzionali, da shell o da `.env` (vedi `.env.example`; il file legge solo le chiavi che iniziano con `AGY_POOL_`, una per riga, senza commenti a fine riga):

| Variabile | Effetto |
|---|---|
| `AGY_POOL_DIR` | Cartella dei dati |
| `AGY_POOL_FAILOVER` | `1` attiva il cambio automatico account con `-p` (default: spento) |
| `AGY_POOL_RESET_HOURS` | Ore stimate al ripristino della quota (default 5) |
| `AGY_POOL_ENV_FILE` | Percorso alternativo al `.env` (default: accanto allo script) |

## Sviluppo

```bash
uv run pytest      # test con un agy finto
uv run ruff check
```

Lo script è un unico file (`agy-pool`) con la sola libreria standard di Python.
