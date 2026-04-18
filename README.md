# Assistant de direction — Backend IA

API FastAPI d'un agent IA (tool calling via Groq) capable de :

- **Gérer un agenda** en langage naturel (lecture, création, mise à jour, suppression)
- **Synthétiser des documents** en sortie structurée
- **Maintenir une mémoire de session** (historique conversationnel persisté)

Le backend de l'agenda est **commutable** via une variable d'environnement :

- `CALENDAR_BACKEND=db` → stockage SQL local (SQLAlchemy + SQLite par défaut)
- `CALENDAR_BACKEND=caldav` → stockage et interrogation via un serveur CalDAV (Nextcloud, Radicale, iCloud…)

## Stack & justification

- **FastAPI** : typage Pydantic strict, génération automatique de Swagger (`/docs`), dépendances légères → respecte la structure et gagne les points documentation.
- **SQLAlchemy + SQLite** : pas d'infra externe requise, seed trivial, suffit au scope.
- **Groq** (Llama 3.3 70B) : tool calling natif OpenAI-compatible, très rapide, clé gratuite.
- **caldav** : client Python de référence, compatible la plupart des serveurs CalDAV.
- **loguru** : logging structuré configurable par `LOG_LEVEL`.

## Prérequis

- Python **3.11+**
- Une clé **Groq** (gratuite) — voir ci-dessous

### Obtenir une clé Groq

1. Créer un compte sur <https://console.groq.com>
2. Aller dans **API Keys** → `Create API Key`
3. Copier la clé et la coller dans `.env` (`GROQ_API_KEY=...`)

## Installation (lancement en < 5 min)

```bash
git clone <repo>
cd test_technique_inov
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # puis éditez GROQ_API_KEY
uvicorn main:app --reload
```

- API : <http://localhost:8000>
- Swagger : <http://localhost:8000/docs>
- OpenAPI JSON : <http://localhost:8000/openapi.json>

### Via Docker

```bash
cp .env.example .env         # renseigner GROQ_API_KEY
docker compose up --build
```

## Variables d'environnement

| Variable | Rôle | Défaut |
|---|---|---|
| `GROQ_API_KEY` | Clé API Groq (obligatoire) | — |
| `GROQ_MODEL` | Modèle Groq | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | URL SQLAlchemy | `sqlite:///./data/app.db` |
| `CALENDAR_BACKEND` | `db` ou `caldav` | `db` |
| `CALDAV_URL` | URL du serveur CalDAV | — |
| `CALDAV_USERNAME` / `CALDAV_PASSWORD` | Credentials CalDAV | — |
| `CALDAV_CALENDAR_NAME` | Nom du calendrier à cibler | *premier trouvé* |
| `API_KEY` | (optionnel) activer l'auth header | — |
| `LOG_LEVEL` | Niveau de log | `INFO` |

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| POST | `/agent/chat` | Point d'entrée de l'agent (tool calling) |
| GET | `/agenda` | Liste les événements (`?date=` / `?range=week`) |
| POST | `/agenda` | Crée un événement |
| PATCH | `/agenda/{id}` | Met à jour un événement |
| DELETE | `/agenda/{id}` | Supprime un événement |
| GET | `/session/{id}/history` | Historique d'une session |
| GET | `/health` | Statut API + DB + backend calendrier |

## Exemple d'appel

```bash
curl -X POST http://localhost:8000/agent/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": null, "message": "Quels sont mes rendez-vous demain ?"}'
```

Réponse type :

```json
{
  "session_id": "4c9e...",
  "response": "Vous avez 2 rendez-vous demain : Comité de direction à 9h et Réunion équipe Tech à 14h30.",
  "tool_used": "get_agenda",
  "turn": 1
}
```

## Tests

```bash
pytest -q
```

## Architecture

```
src/
├── routes/      # endpoints HTTP (agent, agenda, session, health)
├── services/
│   ├── agent.py           # orchestrateur tool calling
│   ├── memory.py          # mémoire de session persistée
│   └── calendar/          # dépôt agenda pluggable
│       ├── base.py        # interface CalendarRepository
│       ├── db_repo.py     # implémentation SQLAlchemy
│       └── caldav_repo.py # implémentation CalDAV
├── tools/       # définitions JSON Schema + handlers Python
├── models/      # ORM SQLAlchemy + schémas Pydantic
├── db/          # engine + seed
└── tests/       # pytest
```

## Seed agenda

Au premier lancement (backend `db`), 5 événements sont insérés relatifs à la date du jour (J+1 à J+4), conformément au sujet.

## Extension — 3e outil

Pour ajouter par ex. un outil `send_email` :

1. Ajouter la définition JSON Schema dans `src/tools/definitions.py`
2. Ajouter un handler dans `src/tools/handlers.py` + l'enregistrer dans `TOOL_HANDLERS`
3. Éventuellement créer un service dédié (`src/services/email/`)

Aucune modification de l'orchestrateur n'est nécessaire.
