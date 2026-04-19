# Mon projet — API Django « Tasks »

Application web minimaliste basée sur **Django 6** : API JSON pour gérer des **tâches** (CRUD), vérifications de santé (`/health`), déploiement **Docker** avec **PostgreSQL**, **Redis** (contrôle de disponibilité), **Nginx** en reverse proxy, et pipeline **GitHub Actions** (tests, couverture, image Docker, scan **Trivy**, publication sur **GHCR**).

---

## Sommaire

1. [Fonctionnalités](#fonctionnalités)
2. [Stack technique](#stack-technique)
3. [Structure du dépôt](#structure-du-dépôt)
4. [Prérequis](#prérequis)
5. [Installation et exécution en local](#installation-et-exécution-en-local)
6. [Variables d’environnement](#variables-denvironnement)
7. [Docker et Compose](#docker-et-compose)
8. [API HTTP](#api-http)
9. [Modèle de données](#modèle-de-données)
10. [Tests](#tests)
11. [Intégration continue (CI)](#intégration-continue-ci)
12. [Sécurité et bonnes pratiques](#sécurité-et-bonnes-pratiques)
13. [Dépannage](#dépannage)

---

## Fonctionnalités

- **CRUD** sur des tâches via JSON (`GET` / `POST` sur la collection, `GET` / `PUT` / `DELETE` sur une ressource).
- **Health check** agrégé : état de la base de données et test **PING** minimal sur **Redis** (socket brut, sans `redis-py`).
- **Base de données** : **SQLite** si `POSTGRES_DB` n’est pas défini ; **PostgreSQL** dès que `POSTGRES_DB` est renseigné (typique sous Docker).
- **Fichiers statiques** : **WhiteNoise** avec stockage compressé et manifeste.
- **Conteneur** : image multi-étapes **Alpine**, utilisateur non-root, **Gunicorn** après migrations.

---

## Stack technique

| Composant        | Rôle |
|-----------------|------|
| Python 3.12     | Runtime |
| Django 6.0.4    | Framework web |
| Gunicorn        | Serveur WSGI en production / conteneur |
| WhiteNoise      | Fichiers statiques |
| psycopg2-binary | Driver PostgreSQL |
| PostgreSQL 16   | Base de données (Compose / prod) |
| Redis 7         | Vérification de disponibilité dans `/health` |
| Nginx 1.27      | Reverse proxy (port 80) |

Fichiers de dépendances : `requirements.txt` (runtime). `requirements-dev.txt` est réservé aux outils de développement optionnels (commenté pour l’instant).

---

## Structure du dépôt

```text
mon-projet/
├── .github/workflows/ci.yml   # CI : tests, couverture, build Docker, Trivy, push GHCR
├── docker-compose.yml         # Développement : api, db, redis, nginx
├── docker-compose.prod.yml    # Variante prod simplifiée (web, nginx, db)
├── Dockerfile                 # Build multi-stage, user non-root
├── nginx/default.conf         # Proxy vers l’application (hostname du service Docker)
├── requirements.txt
├── requirements-dev.txt
├── src/
│   ├── manage.py
│   ├── config/                # Projet Django (settings, urls, wsgi, db)
│   ├── core/                  # App : modèle Task, vues health
│   └── routes/                # URLs API + vues CRUD tasks
└── tests/                     # Tests Django (hors package src, utilisés par CI)
```

Le répertoire `trivy-bin/` (binaire local Trivy) est ignoré par le build Docker (`.dockerignore`) et ne fait pas partie du déploiement applicatif standard.

---

## Prérequis

- **Python 3.12** (aligné sur le `Dockerfile` et la CI).
- Pour le mode **PostgreSQL** : instance accessible ou stack **Docker Compose**.
- **Docker** et **Docker Compose** si vous exécutez l’application via les fichiers `docker-compose*.yml`.

---

## Installation et exécution en local

### 1. Cloner et créer un environnement virtuel

```bash
git clone <url-du-depot>
cd mon-projet
python -m venv .venv
```

Sous Windows (PowerShell) :

```powershell
.\.venv\Scripts\Activate.ps1
```

Sous Linux ou macOS :

```bash
source .venv/bin/activate
```

### 2. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 3. Migrations et serveur de développement

Depuis la racine du dépôt (là où se trouve le dossier `src/`) :

```bash
python src/manage.py migrate
python src/manage.py runserver
```

Sans variable `POSTGRES_DB`, Django utilise **SQLite** (`db.sqlite3` à la racine du projet, au même niveau que `src/` selon `config/db.py`).

### 4. Interface d’administration (optionnel)

Les modèles ne sont pas enregistrés dans `core/admin.py` par défaut ; l’URL `/admin/` reste disponible si vous créez un superutilisateur :

```bash
python src/manage.py createsuperuser
```

---

## Variables d’environnement

| Variable | Rôle | Défaut / remarque |
|----------|------|-------------------|
| `DJANGO_SECRET_KEY` | Clé secrète Django | Défaut de développement si absent — **à définir en production** |
| `DJANGO_DEBUG` | Mode debug (`1` / `0`) | `1` → debug activé |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules | `localhost,127.0.0.1,testserver` |
| `POSTGRES_DB` | Nom de la base PostgreSQL | Si **non défini** → SQLite |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `django` |
| `POSTGRES_PASSWORD` | Mot de passe | `django` |
| `POSTGRES_HOST` | Hôte PostgreSQL | `db` (adapté à Compose) |
| `POSTGRES_PORT` | Port PostgreSQL | `5432` |
| `REDIS_HOST` | Hôte Redis pour `/health` | `redis` |
| `REDIS_PORT` | Port Redis | `6379` |

Pour Docker Compose, placez ces valeurs dans un fichier **`.env`** à la racine (non versionné). Exemple minimal pour la base sous Compose :

```env
DJANGO_SECRET_KEY=changez-moi-en-production
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=django
POSTGRES_USER=django
POSTGRES_PASSWORD=django
```

---

## Docker et Compose

### Développement (`docker-compose.yml`)

Services : **`api`** (Django + Gunicorn), **`db`** (PostgreSQL), **`redis`**, **`nginx`** (port **80** → proxy vers l’API).

```bash
docker compose up --build
```

- L’API est joignable via Nginx sur **http://localhost/** (qui proxifie vers `api:8000`).
- Le dossier projet est monté dans le conteneur `api` (`volumes: .:/app`) pour un cycle de dev rapide.

### Production simplifiée (`docker-compose.prod.yml`)

Services : **`web`**, **`nginx`**, **`db`**. Pas de service Redis dans ce fichier ; l’endpoint `/health` peut alors indiquer le cache en erreur si Redis n’est pas joignable (voir [Dépannage](#dépannage)).

### Image Docker (build local)

```bash
docker build -t mon-projet:local .
```

Commande par défaut du conteneur : migrations `migrate --noinput` puis **Gunicorn** (`config.wsgi:application`, 3 workers, port 8000).

### Cohérence Nginx ↔ nom du service

Le fichier `nginx/default.conf` utilise `proxy_pass http://api:8000;`, ce qui correspond au service nommé **`api`** dans `docker-compose.yml`. Dans `docker-compose.prod.yml`, le service Django s’appelle **`web`** : pour que Nginx résolve correctement l’upstream, renommez le service en `api`, ou adaptez `default.conf` (par exemple `http://web:8000`) selon le fichier Compose utilisé.

---

## API HTTP

Les routes sont définies dans `src/routes/api_urls.py`. Préfixe racine : pas de `/api` global au niveau projet ; les chemins ci-dessous sont relatifs à la racine du site.

### Santé

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/health` ou `/health/` | JSON : `status`, `database`, `cache` (Redis) |
| `GET` | `/healthz/` | Identique à `/health` (alias) |

Exemple de corps JSON (schéma logique) :

```json
{
  "status": "ok",
  "database": { "status": "up" },
  "cache": { "status": "up" }
}
```

Si la base ou Redis est indisponible, `status` vaut `"error"` et les sous-objets peuvent contenir `"error"` avec un message.

### Tâches

Les vues API sont exemptées de la vérification CSRF (`csrf_exempt`) pour permettre les clients JSON classiques ; en production, sécurisez l’exposition (réseau privé, authentification, etc.).

| Méthode | Chemin | Description |
|---------|--------|-------------|
| `GET` | `/api/tasks` ou `/api/tasks/` | Liste des tâches, tri par `created_at` décroissant |
| `POST` | idem | Création ; corps JSON |
| `GET` | `/api/tasks/<id>` | Détail |
| `PUT` | idem | Mise à jour partielle ou complète (champs présents dans le JSON) |
| `DELETE` | idem | Suppression ; réponse **204** sans corps |

**Création (`POST`)** — champs JSON :

- `title` (string, **obligatoire**, non vide après trim)
- `description` (string, optionnel, défaut `""`)
- `completed` (booléen, optionnel, défaut `false`)

**Mise à jour (`PUT`)** — tout champ absent est laissé inchangé ; si `title` est présent, il ne peut pas devenir vide.

**Représentation d’une tâche** :

```json
{
  "id": 1,
  "title": "string",
  "description": "string",
  "completed": false,
  "created_at": "2026-04-20T12:00:00+00:00",
  "updated_at": "2026-04-20T12:00:00+00:00"
}
```

Codes d’erreur courants : **400** (JSON invalide, titre manquant ou vide), **404** (tâche inexistante), **405** (méthode HTTP non supportée sur la ressource).

---

## Modèle de données

Modèle **`Task`** (`src/core/models.py`) :

| Champ | Type |
|-------|------|
| `title` | `CharField(max_length=255)` |
| `description` | `TextField`, blanc autorisé |
| `completed` | `BooleanField`, défaut `False` |
| `created_at` | `DateTimeField`, auto à la création |
| `updated_at` | `DateTimeField`, auto à chaque sauvegarde |

---

## Tests

Les tests vivent dans `tests/` et ciblent l’URLconf montée à la racine (`config.urls`).

```bash
python src/manage.py test tests --verbosity 2
```

La CI exécute en plus **`coverage`** sur le code sous `src/` (rapport terminal et fichier `coverage.xml`).

---

## Intégration continue (CI)

Fichier : `.github/workflows/ci.yml`.

- **Déclencheurs** : `push` et `pull_request` sur toutes les branches.
- **Job `test`** (Ubuntu, Python 3.12) :
  - installation `requirements.txt` + `coverage`
  - « lint » léger : `compileall` sur `src` et `tests`, puis `python src/manage.py check`
  - tests : `coverage run --source=src src/manage.py test tests`
  - rapports `coverage report` et `coverage xml`
- **Job `build`** (uniquement sur **push** vers **`main`**, après succès de `test`) :
  - construction de l’image Docker (cache Buildx GitHub Actions)
  - scan **Trivy** des vulnérabilités, sévérité **CRITICAL** avec `exit-code: 1` (échec du job si critique)
  - connexion à **ghcr.io** et push des tags `<sha>` et `latest` vers `ghcr.io/<owner>/<repo>` (nom en minuscules)

---

## Sécurité et bonnes pratiques

- Ne commitez pas **`.env`** ni de secrets ; la CI utilise `GITHUB_TOKEN` pour GHCR.
- En production : `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` fort et unique, `DJANGO_ALLOWED_HOSTS` restreint au domaine réel.
- L’API tasks est **sans authentification** dans l’état actuel du code ; ne l’exposez pas sur Internet sans couche d’auth (JWT, session, clé API, etc.) et sans **HTTPS** (terminaison TLS souvent gérée devant Nginx).
- Le dossier `trivy-bin/` sert d’outil local ; le scan en CI utilise l’action Trivy officielle, pas ce binaire.

---

## Dépannage

- **`/health` indique le cache en erreur avec `docker-compose.prod.yml`** : ce fichier ne lance pas Redis ; soit ajoutez un service Redis et les variables `REDIS_*`, soit acceptez que le health check signale le cache comme indisponible.
- **Nginx renvoie 502** : vérifiez que le nom d’hôte dans `nginx/default.conf` correspond au nom du service Compose (`api` vs `web`).
- **Migrations** : en cas de changement de modèles, `python src/manage.py makemigrations` puis `migrate` (le conteneur exécute `migrate` au démarrage).

---


