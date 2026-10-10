# antigravity-account-pool

`agy-pool` è un comando che usa più account Google con Antigravity CLI (`agy`) e passa al successivo quando la quota di uno finisce. Serve a chi lavora con `agy` e consuma la quota di un solo account prima di fine giornata.

Funziona come `agy`: al posto di `agy` lanci `agy-pool`, con gli stessi argomenti.

## Cosa fa

- Tiene gli account in un giro fisso (`acc1`, `acc2`, ...) e riparte dall'ultimo che ha funzionato.
- Con `-p` (prompt singolo) passa da solo all'account successivo quando riceve un errore di quota.
- Se tutti gli account sono esauriti si ferma, stampa un messaggio e l'orario stimato del primo ripristino.
- Condivide tra gli account conversazioni, cronologia e configurazione, così `-c` riprende un lavoro anche dopo un cambio.
- Con `pool init` porta in `agy` skill, regole e agent di una configurazione Claude Code già esistente.

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
| `agy-pool -p "prompt"` | Prompt singolo con cambio automatico di account |
| `agy-pool --agent NOME -p "..."` | Esegue un agent (vedi `pool init`) |
| `agy-pool pool status` | Account pronti, esauriti, non idonei |
| `agy-pool pool next` / `pool use accN` | Cambia l'account di partenza |
| `agy-pool pool login accN` | Aggiunge un account |
| `agy-pool pool check [accN...]` | Verifica gli account con una richiesta ciascuno |
| `agy-pool pool setup` | Ricollega lo stato condiviso e risincronizza gli agent |

Se la quota finisce in una sessione interattiva: `/exit`, poi `agy-pool pool next`, poi `agy-pool -c`.

## Portare la configurazione di Claude Code

`agy-pool pool init` fa in un colpo solo:

- collega `~/.claude/skills` come skill di `agy` (symlink);
- crea un `AGENTS.md` globale con l'indice delle tue regole in `~/.claude/rules/` e alcune incluse per intero (`python-stack`, `git-workflow`, `security`, se ci stanno nel limite di `agy`);
- aggiunge a `settings.json` i permessi di lettura per regole e skill e `command(ls)`;
- copia gli agent di `~/.claude/agents/` togliendo i campi `model` e `tools`, che `agy` non accetta. La copia si aggiorna a ogni avvio.

I server MCP non si portano in automatico: aggiungili con `agy mcp add` (nel pool vale per tutti gli account). In modalità `-p` `agy` nega i tool MCP senza permesso: per quelli che ti fidi di usare aggiungi `mcp(NOME/*)` in `permissions.allow` di `~/.agy-pool/shared/antigravity-cli/settings.json`.

I dettagli e le scoperte sul formato sono in [docs/COMPATIBILITA-CLAUDE-CODE.md](docs/COMPATIBILITA-CLAUDE-CODE.md).

## Limiti noti

- **Il riconoscimento della quota non è stato visto su un errore reale.** Cerca parole come `429`, `RESOURCE_EXHAUSTED`, `quota`. È provato con un `agy` finto. Al primo errore vero il testo viene salvato in `~/.agy-pool/quota-errors.log`: se il cambio account non scatta, apri una issue con quel testo.
- **L'orario di ripristino è una stima** di 5 ore dal primo errore. Per gli account gratuiti le fonti parlano di un rinnovo settimanale: cambia il valore con `AGY_POOL_RESET_HOURS=168`.
- **Il cambio automatico c'è solo con `-p`.** In una sessione interattiva non si cambia account a metà.
- **Un prompt interrotto dall'errore di quota riparte da capo** sull'account successivo. Per i lavori lunghi usa `-c`.
- **In `-p` i tool MCP con risposte lunghe possono dare output vuoto.** `agy` sposta la risposta su un file in `brain/` e a volte nega la lettura per mancanza di permesso. In sessione interattiva chiede conferma e funziona.
- **Gli agent usati come subagent da un'altra sessione non sono verificati.** Come agent principale (`--agent`) funzionano.

## Termini d'uso e sicurezza

- Controlla i termini di Google sull'uso di più account prima di usarlo. Questo repository non dà garanzie in merito.
- Usa solo account tuoi. I token OAuth stanno in `~/.agy-pool/accN/.gemini/antigravity-cli/antigravity-oauth-token` (permessi `0600`): non copiarli e non metterli in un repository.
- Gli hook di Claude Code non girano in `agy`. Un divieto scritto nelle tue regole (per esempio sul `git push`) in `agy` non è bloccato da nulla.

## Dati e variabili

Tutto sta in `~/.agy-pool/` (account, stato, log degli errori di quota, configurazione condivisa). Variabili opzionali: `AGY_POOL_DIR` (cartella dei dati) e `AGY_POOL_RESET_HOURS` (ore stimate al ripristino, default 5).

## Sviluppo

```bash
uv run pytest      # 24 test, con un agy finto
uv run ruff check
```

Lo script è un unico file (`agy-pool`) con la sola libreria standard di Python.
