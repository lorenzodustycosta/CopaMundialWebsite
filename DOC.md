# Panoramica architettura

- Progetto Django classico con un’app principale tournament dentro il progetto football_tournament (config, urls, settings).
Strati separati per: domain (logica pura), services (orchestrazione con DB), viewmodels (DTO per template), views (controller), models (schema dati).
- Presentazione: template HTML in football_tournament/templates/tournament e statici in football_tournament/tournament/static.

# Cartelle chiave

- football_tournament/football_tournament: configurazione Django (settings.py, urls.py, wsgi.py).
- football_tournament/tournament: app principale con MVC esteso e logica torneo.
- football_tournament/templates/tournament: pagine HTML (ranking, calendario, gestione).
- football_tournament/tournament/static: CSS e immagini.

# Models (dati)

- Definiti in models.py.
- Entità principali: Group, Team, Player, Match, Goal, Document.
Sono la base del DB (ORM) e rappresentano le relazioni: squadre in gruppi, giocatori in squadre, match con punteggi, goal e documenti allegati.

# Views (controller HTTP)

- In views.py.
Gestiscono richieste web, caricano dati da DB/servizi e renderizzano template.
Esempi: ranking, calendario partite, dettagli match, gestione torneo, sorteggio gruppi.
ViewModels

- In viewmodels.py.
Servono a “modellare” dati già pronti per il template (es. riga match con score, suffix, kickoff).
Separano trasformazioni di formato dalla view (cleaner code, view più leggere).

# Forms
- In forms.py.
- MatchForm è un ModelForm che imposta campi e filtra i giocatori MVP in base alle squadre del match.
- Serve sia lato admin sia potenzialmente lato frontend.

# Domain

- In football_tournament/tournament/domain/*.
Contiene logica pura e indipendente da Django/DB:
ranking.py: calcolo classifiche con tie‑break head‑to‑head.
knockout.py: regole per determinare vincitore.
match_outcome.py: estrazione vincitore/sconfitto da match validati.
schedule_schema.py: parsing schema CSV e generazione slot.
Vantaggio: testabilità e logica business chiara/riusabile.
Services

- In football_tournament/tournament/services/*.
Orchestrano DB + domain:
group_stage_service.py: calcolo classifiche e qualificati.
ranking_service.py: aggrega tutto per le pagine ranking.
schedule_service.py: crea calendario gironi da CSV.
knockout_service.py: crea quarti/semifinali/finali.
draw_service.py: verifica sorteggio gruppi.
Vantaggio: separa i “use case” dalle view.
Admin

- In admin.py.
Registra modelli e customizza UI di Django admin:
TeamAdmin gestisce giocatori inline.
MatchAdmin usa MatchForm + Goal inline per gestire gol.
Filtri e ricerca per gestione torneo.
In pratica è il pannello gestionale ufficiale per inserire risultati, squadre e documenti.

# Routing

- urls.py: include l’app tournament + admin.
- urls.py: rotte specifiche (ranking, match, sorteggio, login, ecc.).

# Flusso tipico

URL -> view (controller)
view chiama service/domain + DB
service ritorna DTO/viewmodel
view renderizza template con dati
static CSS/JS per UI