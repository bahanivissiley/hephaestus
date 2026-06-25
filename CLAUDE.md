# TravelMind AI — Contexte projet

Agent de voyage intelligent. Projet Hephaestus, Epitech Lyon, MSc 1 — janvier 2026.
Voir `README.md` pour la doc complète (architecture, install, choix techniques).

## Règle d'or du projet

**Avant d'appeler une API externe, toujours vérifier la base de données d'abord.**
Le flux correct est : BD → si absent, tool externe → si absent, message d'indisponibilité honnête.
Ne JAMAIS inventer un hôtel, restaurant ou attraction qui n'existe pas réellement. Voir
`backend/app/tools/restaurant_tool.py` et `attraction_tool.py` pour le pattern exact (retourner
liste vide + message plutôt que générer du contenu factice).

## Stack

- Backend : Python 3.11, FastAPI (async), SQLAlchemy, PostgreSQL
- Frontend : React 18 + TypeScript + Vite (pas de framework UI, CSS custom dans `index.css`)
- LLM : Ollama local, modèle `qwen3-fast` (variante de qwen3:1.7b avec `/no_think` dans le Modelfile)
- Tout tourne en Docker sauf Ollama (doit rester sur l'hôte — voir Limites ci-dessous)

## Commandes utiles

```bash
# Démarrer l'environnement complet
docker compose up

# Rebuild après changement de requirements.txt ou package.json
docker compose up --build

# Logs backend en direct
docker compose logs backend -f --tail=50

# Exécuter un script Python dans le conteneur backend
docker exec -it hephaestus-backend-1 bash -c "cd /app && python3 -m <module.path>"

# Repeupler la base de données (n'écrase pas si déjà peuplée)
docker exec -it hephaestus-backend-1 bash -c "cd /app && python3 -m app.database.seed"

# Accès direct PostgreSQL
docker exec -it hephaestus-db-1 psql -U travelmind -d travelmind

# Vérifier qu'Ollama tourne sur l'hôte (PAS dans Docker)
ollama list
```

## Fichiers clés à connaître

| Fichier | Rôle |
|---|---|
| `backend/app/services/agent.py` | Orchestrateur principal. `process_message_events` est la machine à états complète (social → slot-filling → planification). Toute modification du flux agentique passe par ce fichier. |
| `backend/app/services/trip_state.py` | Slot-filling : `REQUIRED_SLOTS` définit les infos obligatoires avant de planifier. `merge_state` fusionne sans écraser ce qui est déjà connu. |
| `backend/app/core/prompts.py` | Tous les prompts système. Ne jamais coder un prompt en dur ailleurs dans le code — centraliser ici. |
| `backend/app/services/intent_service.py` | Classification + extraction de slots via LLM, sortie JSON contrainte par `INTENT_SCHEMA`. |
| `backend/app/services/ollama_client.py` | Client HTTP Ollama. `chat()` non-streamé (classification), `chat_stream()` pour la génération de réponse visible par l'utilisateur. |
| `backend/app/services/place_ingest_service.py` | Sauvegarde les découvertes externes en base avec `status="pending"`. Ne jamais mettre `status="approved"` directement depuis l'agent. |
| `backend/app/tools/*.py` | Chaque tool suit le contrat : retourne `source` (`"database"`, `"unavailable"`, ou le nom de l'API), jamais d'exception non gérée. |
| `frontend/src/pages/Chat.tsx` | Page principale. Consomme le flux SSE de `/chat/stream`, gère le carnet de voyage (panneau droit). |
| `frontend/src/index.css` | Design system complet (variables CSS, classes). Pas de Tailwind ni de lib UI — tout est dans ce fichier. |

## Conventions de code

- **Backend** : async partout (`async def`, `httpx.AsyncClient`). Sessions SQLAlchemy toujours fermées dans un `finally`.
- **Prompts** : toujours en français dans le contenu, anglais dans les noms de variables/fonctions.
- **Tools** : signature `async def xxx_tool(destination: str, ...) -> dict`, jamais de levée d'exception vers l'appelant — toujours retourner un dict avec `error` ou `source: "unavailable"`.
- **Frontend** : pas de `any` TypeScript. Types explicites pour chaque event SSE (voir `StreamEvent` dans `Chat.tsx`).
- **Commits** : `feat(SCRUM-XX): description`, `fix(SCRUM-XX): description` — la clé Jira lie le commit au ticket.
- **Branches** : jamais de push direct sur `main` ou `develop`. Toujours `feat/...` ou `fix/...` + Pull Request.

## Limites connues (ne pas re-déboguer, c'est documenté)

- **Ollama est lent sur cette machine** (GTX 1060, CUDA 11.8, Ollama tourne en fait sur Vulkan/CPU à
  ~3-5 tokens/s). Une planification complète prend 1-2 minutes. C'est une limite matérielle acceptée,
  pas un bug à corriger.
- **Ollama doit rester sur l'hôte Windows, pas dans Docker.** `OLLAMA_HOST=http://host.docker.internal:11434`
  dans `docker-compose.yml`. Ne pas réintroduire de service `ollama` dans le compose.
- **Le modèle `qwen3-fast` doit exister sur l'hôte** avant de lancer le projet (`ollama create qwen3-fast -f modelfile.txt`
  avec `SYSTEM "/no_think"` dans le Modelfile). Si absent, fallback silencieux possible vers `qwen3:1.7b` avec le thinking activé (lent).
- **RapidAPI (Booking.com) a un quota gratuit limité.** Si les tools hôtel/vol retournent systématiquement
  `source: "unavailable"`, vérifier le quota avant de chercher un bug côté code.
- **Contrainte du sujet Epitech : aucune API LLM payante.** Ne jamais proposer Groq, OpenAI, Claude API
  etc. comme solution même "temporaire pour le dev" — c'est explicitement exclu par les règles du projet.

## Ce qui n'est PAS encore fait (backlog connu)

- Rate limiting sur `/chat` (évoqué, pas implémenté — pas de `slowapi` dans `requirements.txt`)
- Seed data limité à 4 destinations (Tokyo, Paris, Marrakech, Lisbonne) — New York et Dubai
  pas encore dans `seed.py`
- `kb_service.py` et `backend/kb/kb.json` ont été supprimés (code mort remplacé par
  `db_service.py` + PostgreSQL) — ne pas les réintroduire

## Avant de proposer une solution

1. Vérifier si la BD couvre déjà le besoin avant d'ajouter un appel API externe
2. Si ça touche `agent.py`, relire `process_message_events` en entier — c'est une machine à états,
   modifier une étape sans comprendre les suivantes casse facilement le flux
3. Ne pas réintroduire `kb_service.py` même par réflexe — `db_service.py` est l'unique source de vérité
4. Pour toute nouvelle table/colonne, mettre à jour `connection.py::_migrate()` (migrations légères
   par `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, pas d'Alembic en place malgré sa présence dans requirements.txt)
