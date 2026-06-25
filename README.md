# TravelMind AI

Agent de voyage intelligent — projet Hephaestus, Epitech Lyon, MSc 1 (janvier 2026).

TravelMind ne se contente pas de répondre : il **décide**. Avant d'appeler un outil externe, il vérifie d'abord ce qu'il sait déjà en base de données. Il ne scrape que ce qui lui manque réellement, et ne propose jamais d'hôtel, de restaurant ou d'attraction qu'il aurait inventé.

---

## Sommaire

- [Concept](#concept)
- [Architecture](#architecture)
- [Flux agentique](#flux-agentique)
- [Stack technique](#stack-technique)
- [Installation](#installation)
- [Structure du projet](#structure-du-projet)
- [API — endpoints principaux](#api--endpoints-principaux)
- [Choix techniques justifiés](#choix-techniques-justifiés)
- [Limites connues](#limites-connues)
- [Équipe](#équipe)

---

## Concept

L'utilisateur décrit son voyage en langage naturel ("5 jours à Tokyo en avril, budget 2000€"). L'agent :

1. Extrait les informations utiles du message (destination, dates, budget, préférences)
2. Pose une question ciblée si une information obligatoire manque
3. Consulte sa base de données interne (hôtels, attractions, restaurants vérifiés)
4. Appelle des outils externes **uniquement** pour ce que la base ne couvre pas (météo en direct, vols, hôtels d'une ville absente de la base)
5. Construit une planification jour par jour, heure par heure
6. Permet de remplacer n'importe quel lieu proposé par une alternative

Toutes les découvertes faites via les APIs externes (nouvel hôtel, nouvelle destination) sont enregistrées en base avec un statut `pending` et doivent être validées par un administrateur avant d'être réutilisées par l'agent ou affichées sur le site — l'agent ne fait jamais confiance aveuglément à une source externe.

---

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────────┐
│  Frontend   │◄────►│  Backend FastAPI  │◄────►│  PostgreSQL     │
│  React + TS │ SSE  │  (orchestrateur)  │      │  (hôtels, etc.) │
└─────────────┘      └────────┬─────────┘      └─────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
        ┌───────▼──────┐ ┌─────▼──────┐ ┌─────▼──────┐
        │  Ollama       │ │  Tools MCP │ │  RapidAPI   │
        │  (qwen3-fast) │ │  (weather, │ │  (Booking   │
        │  raisonnement │ │  attraction│ │  hôtels/vols│
        │  local        │ │  ...)      │ │  )          │
        └───────────────┘ └────────────┘ └─────────────┘
```

Le frontend ne contient aucune logique de décision : il affiche un flux d'événements envoyés par le backend (`/chat/stream`, Server-Sent Events). Le backend Python est le seul endroit où l'agent raisonne.

---

## Flux agentique

Pour chaque message utilisateur, l'orchestrateur (`app/services/agent.py`) suit cette séquence :

1. **Classification d'intention** — social, hors-sujet, ou voyage (via le LLM, sortie JSON contrainte)
2. **Slot-filling** — fusion des informations extraites dans l'état de la conversation (destination, origine, dates, durée, budget, préférences)
3. **Vérification des slots obligatoires** — si une information manque, l'agent pose une question ciblée plutôt que de tout redemander
4. **Consultation de la base de données** — hôtels, attractions, restaurants pour la destination
5. **Appels externes ciblés**, lancés en parallèle, uniquement pour ce que la base ne couvre pas :
   - météo en temps réel (toujours, via `wttr.in`)
   - vols (toujours, via l'API Booking/RapidAPI — donnée non stockée en base)
   - hôtels (uniquement si absents de la base, via l'API Booking)
   - informations destination (uniquement si la destination est inconnue, via Wikipedia)
6. **Construction du contexte** — fusion des données base + outils dans un prompt enrichi
7. **Génération de la réponse** — streamée token par token vers le frontend
8. **Structuration de l'itinéraire** — le texte rédigé par le LLM est reconverti en JSON structuré (jours, créneaux horaires) pour alimenter le carnet de voyage visuel, sans jamais s'écarter de ce qui a été annoncé dans le texte

Aucun outil externe n'est appelé "par défaut" : chaque appel est conditionné à l'absence de la donnée en base.

---

## Stack technique

| Composant | Technologie | Justification |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Typage fort, SSE natif via `fetch` + `ReadableStream` |
| Backend | Python 3.11 + FastAPI | Async natif, streaming SSE, documentation Swagger automatique |
| Base de données | PostgreSQL + SQLAlchemy | Relationnel, adapté à la volumétrie cible (centaines de lieux, relations destination → hôtels/attractions/restaurants) |
| LLM | Ollama, modèle Qwen3 (`qwen3-fast`, variante sans mode *thinking*) | Modèle local open-source, conforme à la contrainte du sujet (aucune API LLM payante) |
| Tools MCP | Python pur (fonctions async) | Contrat clair input/output, pas de dépendance à une lib MCP externe |
| Données externes | RapidAPI (Booking.com), Wikipedia REST, wttr.in | Sources réelles ; fallback explicite si indisponibles (jamais de données inventées) |
| Authentification | JWT (python-jose) + bcrypt | Sessions utilisateur pour sauvegarder les conversations |

---

## Installation

### Prérequis

- Docker Desktop
- [Ollama](https://ollama.ai) installé **sur la machine hôte** (pas dans Docker — voir [Limites connues](#limites-connues))
- Une clé [RapidAPI](https://rapidapi.com) abonnée à l'API Booking.com (optionnel — sans clé, l'agent fonctionne en mode "base de données uniquement")

### Étapes

```bash
# 1. Cloner le repo
git clone https://github.com/bahanivissiley/hephaestus.git
cd hephaestus

# 2. Préparer le modèle Ollama (sur l'hôte, pas dans Docker)
ollama pull qwen3:1.7b
# Créer la variante sans mode thinking (voir backend/app/services/ollama_client.py)
ollama show qwen3:1.7b --modelfile > modelfile.txt
# Ajouter la ligne suivante au fichier avant de le créer :
#   SYSTEM "/no_think"
ollama create qwen3-fast -f modelfile.txt

# 3. Configurer les variables d'environnement
cp backend/.env.example backend/.env
# Éditer backend/.env : renseigner RAPIDAPI_KEY et JWT_SECRET

# 4. Lancer l'ensemble (backend + frontend + PostgreSQL)
docker compose up --build

# 5. Peupler la base de données (une seule fois)
docker exec -it hephaestus-backend-1 bash -c "cd /app && python3 -m app.database.seed"
```

### Accès

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| API + documentation Swagger | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |

---

## Structure du projet

```
hephaestus/
├── backend/
│   ├── app/
│   │   ├── core/prompts.py        # Tous les prompts système du LLM
│   │   ├── database/
│   │   │   ├── models.py          # Modèles SQLAlchemy (Destination, Hotel, Attraction, Restaurant, User, Conversation)
│   │   │   └── seed.py            # Données initiales (Tokyo, Paris, Marrakech, Lisbonne)
│   │   ├── routers/                # Endpoints FastAPI (chat, destinations, places, auth, conversations)
│   │   ├── services/
│   │   │   ├── agent.py            # Orchestrateur principal — le cœur agentique
│   │   │   ├── db_service.py       # Lecture de la base de données
│   │   │   ├── intent_service.py   # Classification d'intention + extraction de slots
│   │   │   ├── trip_state.py       # Gestion du slot-filling
│   │   │   ├── place_ingest_service.py  # Sauvegarde des découvertes en "pending"
│   │   │   └── ollama_client.py    # Client HTTP vers Ollama (chat + streaming)
│   │   └── tools/                  # Tools MCP : weather, hotel, flight, attraction, restaurant, destination
│   └── main.py
├── frontend/
│   └── src/
│       ├── pages/                  # Landing, Chat (atelier), Explore, Admin (modération)
│       ├── components/             # Nav, Footer, AuthModal, SmartImage...
│       └── context/AuthContext.tsx
└── docker-compose.yml
```

---

## API — endpoints principaux

| Méthode | Route | Description |
|---|---|---|
| `POST` | `/chat/stream` | Endpoint principal — flux SSE d'événements (statut, tokens, lieux, itinéraire) |
| `POST` | `/chat` | Version non-streamée du même flux |
| `POST` | `/chat/alternative` | Propose un lieu alternatif (base de données puis API si nécessaire) |
| `GET` | `/destinations` | Liste des destinations approuvées |
| `GET` | `/places` | Lieux filtrables par catégorie, destination, budget |
| `GET` | `/places/pending` | Lieux découverts par l'agent en attente de validation |
| `PATCH` | `/places/{type}/{id}/validate` | Approuve un lieu découvert |
| `POST` | `/auth/register`, `/auth/login` | Authentification JWT |
| `GET`/`POST`/`PUT`/`DELETE` | `/conversations` | Sauvegarde des voyages (historique, carnet, état) |

Documentation interactive complète disponible sur `/docs` une fois le backend lancé.

---

## Choix techniques justifiés

**PostgreSQL plutôt qu'un fichier JSON.** Le projet a démarré avec un simple `kb.json`, remplacé dès que le besoin de filtrage (budget, catégorie), de relations (destination → hôtels) et de modération (statut pending/approved) est devenu réel. Un fichier plat ne permettait plus ces opérations proprement.

**Aucune donnée inventée.** Les tools `restaurant_tool` et `attraction_tool` renvoient une liste vide plutôt qu'un "restaurant local générique" si la base ne contient rien — l'agent le signale honnêtement à l'utilisateur plutôt que de fabriquer une fausse recommandation.

**Modération humaine des découvertes externes.** Un hôtel trouvé via l'API Booking n'est jamais directement injecté dans la base "publique" : il atterrit en `pending` et doit être validé via la page `/admin`. Cela protège la fiabilité des données affichées sur le site vitrine.

**Streaming SSE plutôt que requête/réponse classique.** Une planification complète peut prendre 1 à 2 minutes sur un modèle local exécuté sur CPU. Le streaming permet d'afficher la progression (statuts, puis tokens de la réponse) plutôt qu'un écran de chargement silencieux.

**Désactivation du mode *thinking* de Qwen3.** Le modèle Qwen3 génère par défaut un raisonnement interne verbeux avant sa réponse, ce qui multiplie le temps de génération sans bénéfice pour ce cas d'usage. Une variante du modèle (`qwen3-fast`) est créée avec `SYSTEM "/no_think"` dans le Modelfile Ollama.

---

## Limites connues

- **Performance sur CPU.** Sans GPU CUDA fonctionnel, Ollama tourne sur Vulkan/CPU et génère environ 3 à 5 tokens/seconde avec Qwen3 1.7B, soit 1 à 2 minutes pour une planification complète. C'est une contrainte matérielle, pas applicative — testé et documenté sur GTX 1060 (architecture Pascal, support CUDA limité par les versions récentes d'Ollama).
- **Ollama doit tourner sur l'hôte, pas dans Docker.** Le conteneur Docker `ollama/ollama` ne donne pas accès au GPU de la machine hôte sous Windows de façon fiable ; le backend communique avec Ollama via `host.docker.internal:11434`.
- **API Booking (RapidAPI) plan gratuit.** Quota limité ; au-delà, les tools hôtel/vol retournent un message d'indisponibilité explicite plutôt que d'inventer des données — comportement voulu, pas un bug.
- **4 destinations en base au lancement** (Tokyo, Paris, Marrakech, Lisbonne). Toute autre destination passe par les outils externes et alimente automatiquement la file de modération.

---

## Équipe

Projet réalisé dans le cadre du module Hephaestus, Epitech Lyon, MSc 1 Management des Systèmes d'Information — janvier 2026.
