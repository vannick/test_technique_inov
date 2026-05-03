# Assistante de direction INOVIE - Backend IA

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

Le `docker-compose.yml` inclut un profil `caldav` qui démarre **Radicale**
(image `tomsquest/docker-radicale`) sur `http://127.0.0.1:5232`.

#### 1. Démarrer Radicale

```bash
docker compose --profile caldav up -d radicale
```

Les données sont persistées dans `~/radicale/data` sur l'hôte.

#### 2. Créer un utilisateur 

Créer un utilisateur `admin` et Mot de passe `admin`:


#### 3. Créer une collection (calendrier) et récupérer son URL

Ouvrir <http://127.0.0.1:5232> dans un navigateur, se connecter avec
`admin` / `admin`, puis **Create new addressbook or calendar** :

- **Title** : `Agenda principal` (libre)
- **Type** : `Calendar`
- **Color** : libre

le plus important note le uuid sur la page de la collection

Après création, la collection apparaît dans la liste avec une URL de la forme :

```
http://127.0.0.1:5232/admin/<uuid>/
```

Exemple réel :

```
http://127.0.0.1:5232/admin/ed06ced5-0851-39bc-fe2c-3ac4a61b08fe/
```

#### 4. Configurer `.env`

```bash
CALENDAR_BACKEND=caldav
CALDAV_URL=http://127.0.0.1:5232
CALDAV_USERNAME=admin
CALDAV_PASSWORD=admin
CALDAV_CALENDAR_URL=http://127.0.0.1:5232/admin/<uuid-de-l-étape-3>/
```

> Note: si l'API tourne **aussi** dans `docker compose` (pas en local),
> utiliser `CALDAV_URL=http://radicale:5232` (résolution via le réseau Docker).

Au premier lancement, `seed_agenda` pousse les événements de démonstration
dans la collection (idempotent : relance sans doublons grâce au marqueur
`[seed]` dans les notes).

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `LLM_API_KEY` | Clé API Groq (**obligatoire**) | - |
| `LLM_MODEL` | Modèle Groq | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./data/app.db` |
| `CALENDAR_BACKEND` | `db` ou `caldav` | `db` |
| `CALDAV_URL` | Racine du serveur CalDAV | - |
| `CALDAV_USERNAME` / `CALDAV_PASSWORD` | Credentials CalDAV | - |
| `CALDAV_CALENDAR_NAME` | Nom de calendrier à cibler | *premier trouvé* |
| `CALDAV_CALENDAR_URL` | URL directe de collection (prioritaire sur `_NAME`) | - |
| `JWT_SECRET` | Clé HMAC pour signer les JWT (≥32 octets recommandé) | `change-me-super-secret` |
| `LOG_LEVEL` | Niveau de log (`DEBUG`/`INFO`/…) | `INFO` |

## Authentification

L'API utilise des **access tokens JWT** (valides 24 h). Les routes sont protégées
sauf `/auth/login` et `/health`.

### 1. Créer un utilisateur (temporaire, pour le dev)

En local, tu peux créer un utilisateur directement en base :

```python
from src.auth import hash_password
from src.db.database import SessionLocal
from src.models.orm import User

hashed = hash_password("secret")
user = User(id="user-1", email="alice@example.com", password_hash=hashed)
with SessionLocal() as db:
    db.add(user)
    db.commit()
```

### 2. Se connecter

```bash
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "alice@example.com", "password": "secret"}'
```

Réponse :

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "email": "alice@example.com"
}
```

### 3. Utiliser le token

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/agenda
```

- Token absent ou invalide → `401 Unauthorized`
- Token expiré → `401 Unauthorized`

Dans Swagger (`/docs`), clique sur **Authorize** → `Bearer <token>`.

> **Important** : change `JWT_SECRET` en production (≥32 octets recommandé).

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

### Exemple - dialoguer avec l'agent

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

### Exemple - CRUD direct

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Créer
curl -X POST http://localhost:8001/agenda \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title": "Réunion projet", "date": "2026-05-03", "time": "10:00", "participants": "bob@example.com"}'

# Lister
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/agenda

# Mettre à jour
curl -X PATCH http://localhost:8001/agenda/<id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"notes": "Préparer slides"}'

# Supprimer
curl -X DELETE http://localhost:8001/agenda/<id> \
  -H "Authorization: Bearer $TOKEN"
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

Aucune modification de l'orchestrateur n'est nécessaire - LangChain
génère le schéma automatiquement depuis la signature + docstring.
