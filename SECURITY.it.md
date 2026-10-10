[English](SECURITY.md) | **Italiano**

# Politica di sicurezza

## Versioni supportate

Il progetto è in sviluppo attivo e non ha release con tag. Gli aggiornamenti di sicurezza vengono applicati all'ultimo commit di `main`.

## Segnalare una vulnerabilità

Per segnalare una vulnerabilità usa le [GitHub Security Advisories](https://github.com/AndreaBonn/agy-profiles/security/advisories/new) del repository. Non aprire una issue pubblica per problemi di sicurezza.

Includi:

- descrizione del problema
- passi per riprodurlo
- comportamento atteso e comportamento osservato
- impatto: cosa potrebbe ottenere un attaccante

Il progetto è mantenuto da una persona sola e non ha tempi di risposta garantiti. Le segnalazioni vengono lette e, se confermate, corrette prima di divulgare i dettagli.

## Misure di sicurezza implementate

Elenco limitato a ciò che è stato verificato nel codice.

- **Nessuna shell**: `agy` viene lanciato con `subprocess.Popen` e argomenti passati come lista, senza `shell=True` (`agy-pool:220`).
- **Il file `.env` non può cambiare l'ambiente di esecuzione**: vengono lette solo le chiavi `AGY_POOL_*`, le altre (per esempio `PATH`, `LD_PRELOAD`) sono ignorate (`agy-pool:22-30`).
- **Il token resta per account**: `antigravity-oauth-token` (`agy-pool:67`) non è tra gli elementi condivisi tra i profili (`SHARED_ITEMS`, `agy-pool:68-76`).
- **Funzioni a rischio spente di default**: il cambio automatico account si attiva solo con `AGY_POOL_FAILOVER=1` (`agy-pool:79`).
- **Dipendenze**: lo script usa solo la libreria standard di Python e `uv.lock` è nel repository.

Cosa non fa il progetto: non imposta i permessi dei file di token (li crea `agy`, non `agy-pool`), non cifra i dati in `~/.agy-pool/`, non ha scansioni di vulnerabilità automatiche (nessuna CI).

## Best practice per gli utenti

- Usa solo account tuoi. Se l'account di lavoro appartiene a un'organizzazione, verifica con chi lo amministra che l'uso di più account sia consentito.
- Controlla che i file `antigravity-oauth-token` in `~/.agy-pool/accN/.gemini/antigravity-cli/` non siano leggibili da altri utenti della macchina.
- Non copiare i token e non metterli in un repository o in un backup condiviso.
- Il file `quota-errors.log` in `~/.agy-pool/` contiene il testo degli errori di `agy`: controllalo prima di incollarlo in una issue.
- Il cambio automatico account è sperimentale. Leggi la sezione dedicata del [README](./README.it.md) e i [termini di Antigravity](https://antigravity.google/terms/) prima di attivarlo.

## Fuori ambito

Non sono considerati vulnerabilità del progetto:

- problemi di `agy`, di Antigravity o dei servizi Google (da segnalare a Google)
- sospensione o limitazione di un account da parte di Google
- accesso ai file di `~/.agy-pool/` da parte di chi ha già accesso al tuo utente di sistema
- attacchi di ingegneria sociale o fisici

## Riconoscimenti

Le persone che segnalano vulnerabilità in modo responsabile saranno elencate qui.

---

[Torna al README](./README.it.md)
