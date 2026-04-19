# Assistante de direction INOVIE — Backend IA

API FastAPI d'un agent IA (tool calling via Groq + LangChain) capable de :

- **Gérer un agenda** en langage naturel (lecture, création, mise à jour, suppression)
- **Synthétiser des documents** en sortie JSON structurée
- **Maintenir une mémoire de session** (historique conversationnel persisté en DB)

Le backend de l'agenda est **commutable** via variable d'environnement :

- `CALENDAR_BACKEND=db` → stockage SQL local (SQLAlchemy + SQLite par défaut)
- `CALENDAR_BACKEND=caldav` → serveur CalDAV externe (Radicale, Nextcloud, iCloud…)

## Stack

| Composant | Rôle | Justification |
|---|---|---|
| **FastAPI 0.115** | API HTTP + OpenAPI auto | Typage Pydantic, Swagger `/docs`, léger |
| **LangChain 0.3** + `langchain-groq` | Orchestrateur tool calling | Génère le schéma des outils depuis les docstrings (1 seule source de vérité) |
| **Groq** (`llama-3.3-70b-versatile`) | LLM rapide, tool calling natif | Gratuit, latence faible |
| **SQLAlchemy 2.0** + SQLite | DB locale (agenda + mémoire) | Aucune infra externe requise |
| **caldav 3.1** + **icalendar 7** | Client CalDAV | Interop Radicale/Nextcloud |
| **loguru** | Logs structurés | Configurable via `LOG_LEVEL` |
| **pytest** | Suite de tests (35 tests) | Couvre routes, services, tools, agent mocké |

## Prérequis

- **Python 3.11+**
- Une clé **Groq** gratuite → <https://console.groq.com/keys>
- (Optionnel) Docker + Docker Compose pour le déploiement conteneurisé

## Lancement rapide (< 5 min)

```bash
git clone <repo>
cd test_technique_inov

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Éditer .env: renseigner LLM_API_KEY=<clé Groq>

uvicorn main:app --reload --port 8001
```

- API → <http://localhost:8001>
- Swagger UI → <http://localhost:8001/docs>
- OpenAPI JSON → <http://localhost:8001/openapi.json>

## Lancement via Docker

```bash
cp .env.example .env   # renseigner LLM_API_KEY
docker compose up --build
```

L'API est exposée sur **<http://localhost:8002>**.

### Avec serveur CalDAV local (Radicale)

Le `docker-compose.yml` inclut un profil `caldav` qui démarre Radicale :

```bash
docker compose --profile caldav up --build
```

Ensuite, dans `.env` :

```bash
CALENDAR_BACKEND=caldav
CALDAV_URL=http://radicale:5232           # ou http://127.0.0.1:5232 en local
CALDAV_USERNAME=admin
CALDAV_PASSWORD=<mot de passe configuré>
CALDAV_CALENDAR_URL=http://127.0.0.1:5232/admin/<uuid-collection>/
```

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `LLM_API_KEY` | Clé API Groq (**obligatoire**) | — |
| `LLM_MODEL` | Modèle Groq | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./data/app.db` |
| `CALENDAR_BACKEND` | `db` ou `caldav` | `db` |
| `CALDAV_URL` | Racine du serveur CalDAV | — |
| `CALDAV_USERNAME` / `CALDAV_PASSWORD` | Credentials CalDAV | — |
| `CALDAV_CALENDAR_NAME` | Nom de calendrier à cibler | *premier trouvé* |
| `CALDAV_CALENDAR_URL` | URL directe de collection (prioritaire sur `_NAME`) | — |
| `API_KEY` | Si définie, toutes les routes (hors `/health`) exigent le header `X-API-Key` | *vide = auth désactivée* |
| `LOG_LEVEL` | Niveau de log (`DEBUG`/`INFO`/…) | `INFO` |

## Authentification

Si `API_KEY` est renseignée dans `.env`, toutes les routes sauf `/health` requièrent le header :

```
X-API-Key: <valeur>
```

- Header absent → `401 Unauthorized`
- Header incorrect → `403 Forbidden`
- `API_KEY` vide côté serveur → auth désactivée (utile en dev)

Dans Swagger (`/docs`), cliquer sur *Authorize* pour renseigner la clé une fois.

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8001/agenda
```

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/agent/chat` | Dialoguer avec l'agent (tool calling) |
| `GET` | `/agent/tools` | Lister les outils exposés au LLM + leur schéma |
| `GET` | `/agenda` | Lister les événements (`?date=YYYY-MM-DD` / `?range=week`) |
| `POST` | `/agenda` | Créer un événement |
| `PATCH` | `/agenda/{id}` | Mettre à jour un événement |
| `DELETE` | `/agenda/{id}` | Supprimer un événement |
| `GET` | `/session/{id}/history` | Historique d'une session de chat |
| `GET` | `/health` | Statut API + DB + backend calendrier + LLM |

### Exemple — dialoguer avec l'agent

```bash
curl -X POST http://localhost:8001/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "message": "Quels sont mes rendez-vous demain ?"}'
```

Réponse :

```json
{
  "session_id": "4c9e1b17-2b9b-4dfe-9e4a-1f3a...",
  "response": "Vous avez 2 rendez-vous demain : Comité de direction à 9h et Réunion équipe Tech à 14h30.",
  "tool_used": "get_agenda",
  "turn": 1
}
```

Pour continuer la conversation, réutilise le `session_id` renvoyé.

### Exemple — CRUD direct

```bash
# Créer
curl -X POST http://localhost:8001/agenda \
  -H "Content-Type: application/json" \
  -d '{"title":"Point RH","date":"2026-04-25","time":"10:00","participants":"Alice, Bob"}'

# Lister la semaine
curl "http://localhost:8001/agenda?range=week"
```

## Architecture

```
src/
├── app.py                    # factory FastAPI + lifespan (init DB + seed)
├── config.py                 # Settings pydantic-settings
├── routes/
│   ├── agent.py              # /agent/chat + /agent/tools
│   ├── agenda.py             # CRUD /agenda
│   ├── session.py            # /session/{id}/history
│   └── health.py             # /health
├── services/
│   ├── agent.py              # orchestrateur LangChain (+ retry Groq)
│   ├── memory.py             # mémoire de session persistée
│   └── calendar/
│       ├── __init__.py       # factory DB | CalDAV
│       ├── base.py           # interface CalendarRepository
│       ├── db_repo.py        # impl. SQLAlchemy
│       └── caldav_repo.py    # impl. CalDAV (avec ATTENDEE)
├── tools/
│   └── handlers.py           # @tool LangChain (1 fichier = 1 source de vérité)
├── models/
│   ├── orm.py                # Event, ChatSession, Message (SQLAlchemy)
│   └── schemas.py            # Pydantic (ChatIn, ChatOut, EventIn, …)
└── db/
    ├── database.py           # engine + SessionLocal + Base
    └── seed.py               # seed idempotent (marqueur [seed])
tests/                        # 35 tests pytest
```

### Flux d'une requête `/agent/chat`

1. **Route** `agent.chat()` appelle `run_agent(session_id, message)`
2. **memory** : `ensure_session` + persiste le message user
3. **LangChain** `AgentExecutor` :
   - compose `SYSTEM_PROMPT` (avec date du jour) + historique + tools
   - boucle appels LLM → exécution outil → re-injection, jusqu'à `MAX_TOOL_LOOPS`
4. **Retry** sur erreur Groq malformée (voir plus bas)
5. **memory** : persiste la réponse + `tool_used`
6. Réponse → `ChatOut { session_id, response, tool_used, turn }`

### Seed idempotent

Au démarrage, `seed_agenda()` insère 5 événements (J+1…J+5) via la factory
`CalendarRepository`, donc **quel que soit le backend actif** (DB ou CalDAV).
L'idempotence repose sur un marqueur `[seed]` dans les notes : si on en trouve
un, le seed est sauté.

### Outils exposés au LLM

Les outils sont déclarés une seule fois dans `src/tools/handlers.py` avec le
décorateur `@tool` de LangChain. **Le schéma JSON transmis au LLM est généré
automatiquement** depuis les annotations de type et la docstring.

| Outil | Rôle |
|---|---|
| `get_agenda(date?, range?)` | Liste les événements |
| `create_event(title, date, time, participants?, notes?)` | Crée un événement |
| `update_event(event_id, …)` | Modifie un événement |
| `delete_event(event_id)` | Supprime un événement |
| `summarize_document(text, focus?)` | Produit une synthèse JSON structurée |

Introspection possible via `GET /agent/tools`.

## Stabilité du tool calling

`llama-3.3-70b-versatile` produit occasionnellement un tool call malformé
(Groq retourne `tool call validation failed`). Stratégie :

1. `temperature=0` pour maximiser le déterminisme
2. Prompt système explicite avec règles numérotées sur le format attendu
3. Retry automatique (`MAX_AGENT_RETRIES=2`) sur `BadRequestError` reconnu

Les autres erreurs (auth, rate limit, …) remontent immédiatement sans retry.

## Tests

```bash
pytest -q
```

Les tests sont **hermétiques** : `tests/conftest.py` force un `DATABASE_URL`
temporaire, `CALENDAR_BACKEND=db` et une clé LLM factice avant toute
importation de `src`. Chaque test démarre avec une DB vide (tables
recréées via une fixture `autouse`).

Couverture :

| Fichier | Ce que ça teste |
|---|---|
| `test_health.py` | Endpoint `/health` (DB up + flags) |
| `test_agenda_routes.py` | CRUD complet /agenda + filtres `?date` et `?range=week` |
| `test_memory.py` | Sessions, historique, `turn_count`, route `/session/…/history` |
| `test_seed.py` | Idempotence du seed via le marqueur `[seed]` |
| `test_tools.py` | Exécution directe des 4 outils agenda |
| `test_agent.py` | Orchestrateur avec `AgentExecutor` mocké (succès, retry, non-retry) |


## Ajout d'un 3ᵉ outil (ex. `send_email`)

1. Ajouter une fonction `@tool` dans `src/tools/handlers.py` :
   ```python
   @tool
   def send_email(to: str, subject: str, body: str) -> str:
       """Envoie un email."""
       ...
   ```
2. L'ajouter à la liste `TOOLS` en bas du fichier
3. (Optionnel) Créer un service dédié dans `src/services/email/`

Aucune modification de l'orchestrateur n'est nécessaire — LangChain
génère le schéma automatiquement depuis la signature + docstring.
