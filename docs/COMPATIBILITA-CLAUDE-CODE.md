# Compatibilità tra Claude Code e agy

Cosa abbiamo verificato provando `agy` 1.3.3 con una configurazione Claude Code esistente. Dove non c'è una prova diretta lo dice la colonna "Stato".

| Elemento | Dove lo cerca `agy` | Cosa serve | Stato |
|---|---|---|---|
| Skill | `~/.gemini/config/skills/<nome>/SKILL.md` | Un symlink a `~/.claude/skills` basta: stesso formato (`name` e `description`) | Verificato: `agy` ha elencato le skill `senior-*` |
| Regole globali | `~/.gemini/config/AGENTS.md` | Un file solo, letto in ogni sessione | Verificato con una parola segreta di prova |
| Regole incluse | `@[etichetta](/percorso/file.md)` dentro `AGENTS.md` | Il file incluso viene espanso | Verificato: `agy` ha citato il contenuto di `git-workflow.md` |
| Server MCP | `~/.gemini/config/mcp_config.json` | `agy mcp add` scrive il formato giusto | Verificato su `deepwiki` |
| Agent | `~/.gemini/config/agents/*.md` | Copia senza i campi `model` e `tools` | Verificato: 21 agent su 21 elencati, uno eseguito con `--agent` |
| Hook | `~/.gemini/config/hooks.json` | Formato diverso da quello di Claude Code | Non portati |

## Limiti di `agy` che si incontrano

- **Regole.** Un file di regole può pesare al massimo 24 KB (dopo l'espansione degli include) e tutte insieme 20.000 token. Oltre il limite le regole diventano puntatori al file. Per questo `pool init` include per intero poche regole e indicizza le altre.
- **Agent.** `agy` scarta un agent se `model:` contiene un ID che non conosce (`claude-opus-5-5`), e non lo avvia se `tools:` nomina strumenti di Claude Code (`Read`, `Grep`): errore `tool "Read" not found in registry`. `memory`, `color`, `skills` e `maxTurns` vengono accettati: l'agent risulta elencato.
- **Permessi in modalità `-p`.** Senza una regola in `permissions.allow` ogni tool che chiede conferma viene negato e la sessione termina con output vuoto (`no output produced`).
  - MCP: `mcp(server/*)`; senza la barra e l'asterisco non è documentato.
  - Lettura file: `read_file(/percorso/cartella)` dà accesso ricorsivo; i glob `**` non sono documentati.
  - Comandi: `command(ls)` per prefisso.
  - Il file è `~/.gemini/antigravity-cli/settings.json`.
- **Percorsi dei permessi.** Non è chiaro se `agy` confronti il percorso che apre o quello a cui punta un symlink. Per sicurezza `pool setup` aggiunge una regola di lettura per ogni account, oltre a quella sulla cartella condivisa.
- **Risposte MCP lunghe.** `agy` le scrive in `brain/<id>/.system_generated/steps/N/output.txt` e le rilegge con `view_file`. In `-p` quella lettura a volte è negata anche con la regola sulla cartella, e la sessione finisce con output vuoto. Non abbiamo trovato la causa: succedeva in circa una prova su tre.
- **Login senza keyring.** Con `DBUS_SESSION_BUS_ADDRESS=disabled` `agy` salva il token nel file `antigravity-oauth-token` invece che nel portachiavi. È quello che permette un account per cartella `HOME`.
