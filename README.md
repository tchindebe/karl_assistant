# Karl — Hyper-Assistant VPS IA

> Orchestrez votre VPS en langage naturel. Déployez des applications, configurez Nginx, surveillez vos serveurs, gérez vos prospects Odoo et analysez votre trafic — le tout depuis une interface de chat.

---

## Table des matières

1. [Présentation](#-présentation)
2. [Architecture](#-architecture)
3. [Fonctionnalités](#-fonctionnalités)
4. [Providers LLM supportés](#-providers-llm-supportés)
5. [Prérequis](#-prérequis)
6. [Déploiement local (développement)](#-déploiement-local-développement)
7. [Déploiement production (VPS réel)](#-déploiement-production-vps-réel)
8. [Variables d'environnement](#-variables-denvironnement)
9. [Outils disponibles](#-outils-disponibles)
10. [Structure du projet](#-structure-du-projet)

---

## 🎯 Présentation

Karl est un assistant IA conversationnel qui agit comme un ingénieur DevOps personnel. Il comprend vos demandes en langage naturel (français ou anglais) et exécute les opérations nécessaires sur votre VPS via un agent dédié.

**Exemples de commandes :**

```
"Déploie mon app Node.js nommée 'api-prod' sur le port 3000 avec le domaine api.monsite.com"
"Configure un certificat SSL pour blog.monsite.com"
"Montre-moi les métriques du serveur"
"Redémarre le conteneur api-prod"
"Crée un prospect CRM : Jean Dupont, jean@dupont.com, intéressé par notre offre Pro"
"Affiche les pages les plus visitées ce mois"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     Navigateur                          │
│              React + Vite + TypeScript                  │
│        Chat UI │ Dashboard │ Métriques live             │
└────────────────────────┬────────────────────────────────┘
                         │  WebSocket / REST + JWT
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Karl Brain                            │
│              FastAPI + Python 3.11+                     │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Provider LLM (multi)                │   │
│  │  Anthropic Claude │ OpenAI │ Gemini │ Ollama     │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  Tools   │  │  DB      │  │  Auth JWT            │   │
│  │ 12 outils│  │ SQLite   │  │                      │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
└────────────────────────┬────────────────────────────────┘
                         │  HTTP + Bearer Token
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Karl VPS Agent                         │
│              FastAPI daemon sur le VPS                  │
│                                                         │
│  Docker Compose │ Nginx │ Certbot │ psutil │ Logs       │
└─────────────────────────────────────────────────────────┘
```

### Flux d'une requête

```
User: "Déploie mon app Node.js"
   ↓
WebSocket → karl_brain/api/chat.py
   ↓
Provider LLM → retourne tool_call: deploy_application(...)
   ↓
tool_executor.py → vps_tools.py → POST /deploy → Karl VPS Agent
   ↓
VPS Agent: génère docker-compose → docker compose up -d
   ↓
Résultat → LLM → génère config Nginx → configure SSL
   ↓
Réponse finale streamée → WebSocket → frontend
```

---

## ✨ Fonctionnalités

### Déploiement d'applications
- Stacks supportées : **Node.js**, **Python**, **PHP**, **Static** (HTML/CSS/JS)
- Génération automatique de `docker-compose.yml` via templates Jinja2
- Mapping de domaine automatique
- Variables d'environnement configurables

### Reverse Proxy Nginx
- Génération de configuration HTTP/HTTPS/WebSocket
- Validation syntaxique avant application (`nginx -t`)
- Reload à chaud sans interruption

### SSL / TLS
- Obtention automatique de certificats Let's Encrypt via Certbot
- Renouvellement automatisé

### Monitoring
- CPU, RAM, Disque, Réseau en temps réel (polling 5s)
- Top processus
- Logs Docker en tail live

### Gestion des conteneurs
- Start / Stop / Restart / Remove
- Liste des déploiements avec statut

### CRM Odoo
- Créer, lister, mettre à jour des prospects (leads)
- Connexion via XML-RPC

### Analytics
- **Plausible Analytics** (recommandé, privacy-first)
- **Google Analytics 4** (alternative)
- Métriques : vues, sessions, pages populaires, sources de trafic

---

## 🤖 Providers LLM supportés

| Provider | Modèles recommandés | Clé requise |
|---|---|---|
| **Anthropic Claude** (défaut) | `claude-opus-4-6`, `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` | `OPENAI_API_KEY` |
| **Ollama** (local) | `llama3.1`, `mistral`, `qwen2.5`, `deepseek-r1` | Aucune |
| **Google Gemini** | `gemini-2.0-flash`, `gemini-1.5-pro` | `GEMINI_API_KEY` |

Changement de provider : modifier `PROVIDER=` dans `.env` — aucune modification de code.

---

## 📋 Prérequis

### Machine locale (développement)
- Python 3.11+
- Node.js 18+ et npm
- Git

### VPS de production
- Ubuntu 22.04 / Debian 12 (recommandé)
- Accès root ou sudo
- Docker + Docker Compose installés
- Nginx installé
- Certbot installé
- Port 8001 ouvert (Karl VPS Agent)
- Nom de domaine pointant sur le VPS (pour SSL)

---

## 🖥️ Déploiement local (développement)

Ce mode simule l'architecture complète sur votre machine. L'agent VPS tourne localement, Docker doit être installé.

### 1. Cloner le projet

```bash
git clone <repo-url> karl_assistant
cd karl_assistant
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Éditer `.env` avec vos valeurs minimales :

```env
# Choisir votre provider LLM
PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# Secrets de sécurité (générer des valeurs aléatoires)
VPS_AGENT_API_KEY=local-secret-key-change-me
KARL_ADMIN_PASSWORD=monmotdepasse
JWT_SECRET=une-chaine-aleatoire-longue-32-chars

# En local, l'agent tourne sur localhost
VPS_AGENT_URL=http://localhost:8001
```

### 3. Démarrer le VPS Agent

```bash
cd karl_vps_agent

# Créer et activer l'environnement virtuel
python -m venv venv
source venv/bin/activate          # Linux/macOS
# venv\Scripts\activate           # Windows

pip install -r requirements.txt

# Créer le .env local pour l'agent
cat > .env << EOF
KARL_AGENT_API_KEY=local-secret-key-change-me
APPS_BASE_DIR=./deployments
NGINX_SITES_DIR=./nginx-sites
EOF

mkdir -p deployments nginx-sites

# Lancer l'agent
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

L'agent est accessible sur `http://localhost:8001`.

### 4. Démarrer Karl Brain

```bash
# Nouveau terminal
cd karl_brain

python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

# Installer le SDK du provider choisi
# pip install openai              # si PROVIDER=openai ou ollama
# pip install google-generativeai # si PROVIDER=gemini

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Le backend est accessible sur `http://localhost:8000`.
Documentation API : `http://localhost:8000/docs`

### 5. Démarrer le Frontend

```bash
# Nouveau terminal
cd frontend

npm install
npm run dev
```

Le frontend est accessible sur `http://localhost:5173`.

### 6. Se connecter

Ouvrir `http://localhost:5173` → entrer le mot de passe configuré dans `KARL_ADMIN_PASSWORD`.

### Test rapide

Une fois connecté, tester dans le chat :

```
"Montre-moi les métriques du serveur"
```

---

## 🚀 Déploiement production (VPS réel)

### Vue d'ensemble

```
Internet
   │
   ▼
[Nginx] :80/:443  →  /                    → Frontend (fichiers statiques)
                  →  /api                 → Karl Brain :8000
                  →  /ws                  → Karl Brain :8000 (WebSocket)
                  →  (interne) :8001      → Karl VPS Agent (non exposé)
```

> **Sécurité** : Le port 8001 (VPS Agent) ne doit **jamais** être exposé publiquement. Il n'est accessible que depuis `localhost` ou via un réseau privé.

---

### Étape 1 — Préparer le VPS

```bash
# Connexion SSH
ssh root@VOTRE_IP_VPS

# Mise à jour
apt update && apt upgrade -y

# Dépendances système
apt install -y python3.11 python3.11-venv python3-pip \
               nginx certbot python3-certbot-nginx \
               git curl wget

# Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# Vérifications
docker --version
nginx -v
python3.11 --version
```

---

### Étape 2 — Déployer le VPS Agent

```bash
# Cloner le projet sur le VPS
git clone <repo-url> /opt/karl
cd /opt/karl/karl_vps_agent

# Créer l'environnement Python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configurer le .env de l'agent
cat > /opt/karl/karl_vps_agent/.env << 'EOF'
KARL_AGENT_API_KEY=VOTRE_CLE_SECRETE_TRES_LONGUE
APPS_BASE_DIR=/opt/karl/deployments
NGINX_SITES_DIR=/etc/nginx/sites-enabled
EOF

chmod 600 /opt/karl/karl_vps_agent/.env

# Créer les répertoires
mkdir -p /opt/karl/deployments
```

#### Installer comme service systemd

```bash
bash /opt/karl/karl_vps_agent/install.sh
```

Le script `install.sh` crée et démarre le service `karl-agent`. Vérifier :

```bash
systemctl status karl-agent
# ● karl-agent.service - Karl VPS Agent
#    Active: active (running)

# Tester l'API (depuis le VPS uniquement)
curl http://localhost:8001/health
```

---

### Étape 3 — Déployer Karl Brain

```bash
cd /opt/karl/karl_brain

python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Installer le SDK du provider choisi
# pip install openai              # OpenAI ou Ollama
# pip install google-generativeai # Gemini
# (anthropic est déjà dans requirements.txt)
```

#### Configurer l'environnement

```bash
cp /opt/karl/.env.example /opt/karl/karl_brain/.env
nano /opt/karl/karl_brain/.env
```

Valeurs importantes pour la production :

```env
# Provider LLM
PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-VOTRE_CLE

# VPS Agent (localhost car même machine)
VPS_AGENT_URL=http://localhost:8001
VPS_AGENT_API_KEY=VOTRE_CLE_SECRETE_TRES_LONGUE

# Sécurité
KARL_ADMIN_PASSWORD=mot_de_passe_complexe
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Production
DEBUG=false
CORS_ORIGINS=https://karl.mondomaine.com
APP_PORT=8000
```

#### Service systemd pour Karl Brain

```bash
cat > /etc/systemd/system/karl-brain.service << 'EOF'
[Unit]
Description=Karl Brain — AI VPS Assistant
After=network.target karl-agent.service
Requires=karl-agent.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/karl/karl_brain
Environment="PATH=/opt/karl/karl_brain/venv/bin"
EnvironmentFile=/opt/karl/karl_brain/.env
ExecStart=/opt/karl/karl_brain/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable karl-brain
systemctl start karl-brain
systemctl status karl-brain
```

---

### Étape 4 — Compiler le Frontend

```bash
# Sur votre machine locale (ou sur le VPS si Node.js installé)
cd frontend

npm install
npm run build

# Copier le build sur le VPS
scp -r dist/ root@VOTRE_IP_VPS:/opt/karl/frontend/dist/
```

Ou directement sur le VPS :

```bash
# Sur le VPS (si Node.js installé)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

cd /opt/karl/frontend
npm install
npm run build
```

---

### Étape 5 — Configurer Nginx

```bash
# Créer la configuration Nginx pour Karl
cat > /etc/nginx/sites-available/karl << 'EOF'
server {
    listen 80;
    server_name karl.mondomaine.com;

    # Frontend — fichiers statiques
    root /opt/karl/frontend/dist;
    index index.html;

    # SPA routing — toujours servir index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API REST → Karl Brain
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
    }

    # WebSocket → Karl Brain
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600;
        proxy_send_timeout 3600;
    }
}
EOF

# Activer le site
ln -s /etc/nginx/sites-available/karl /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

### Étape 6 — Obtenir le certificat SSL

```bash
certbot --nginx -d karl.mondomaine.com --non-interactive --agree-tos -m votre@email.com

# Vérifier le renouvellement automatique
certbot renew --dry-run
```

---

### Étape 7 — Vérification finale

```bash
# Statut de tous les services
systemctl status karl-agent karl-brain nginx

# Logs en temps réel
journalctl -fu karl-brain     # Karl Brain
journalctl -fu karl-agent     # VPS Agent
tail -f /var/log/nginx/access.log

# Test API
curl -s https://karl.mondomaine.com/api/health | python3 -m json.tool
```

Ouvrir `https://karl.mondomaine.com` → se connecter → tester :

```
"Montre-moi les métriques du serveur"
"Liste les applications déployées"
```

---

### Mises à jour en production

```bash
cd /opt/karl
git pull

# Redémarrer les services
systemctl restart karl-brain
systemctl restart karl-agent  # si des changements dans l'agent

# Recompiler le frontend si modifié
cd frontend && npm install && npm run build
```

---

## ⚙️ Variables d'environnement

### Karl Brain (`.env`)

#### Provider LLM

| Variable | Défaut | Description |
|---|---|---|
| `PROVIDER` | `anthropic` | Provider actif : `anthropic` / `openai` / `ollama` / `gemini` |
| `ANTHROPIC_API_KEY` | — | Clé API Anthropic |
| `CLAUDE_MODEL` | `claude-opus-4-6` | Modèle Claude |
| `OPENAI_API_KEY` | — | Clé API OpenAI |
| `OPENAI_MODEL` | `gpt-4o` | Modèle OpenAI |
| `OPENAI_BASE_URL` | — | URL custom (vide = API officielle) |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Endpoint Ollama |
| `OLLAMA_MODEL` | `llama3.1` | Modèle Ollama |
| `GEMINI_API_KEY` | — | Clé API Google AI Studio |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Modèle Gemini |

#### Infrastructure

| Variable | Défaut | Description |
|---|---|---|
| `VPS_AGENT_URL` | `http://localhost:8001` | URL de l'agent VPS |
| `VPS_AGENT_API_KEY` | **requis** | Clé partagée avec l'agent |
| `VPS_AGENT_TIMEOUT` | `120` | Timeout requêtes agent (secondes) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./karl.db` | Base de données |
| `APP_PORT` | `8000` | Port Karl Brain |
| `DEBUG` | `false` | Mode debug |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Origines autorisées (séparées par virgule) |

#### Auth

| Variable | Description |
|---|---|
| `KARL_ADMIN_PASSWORD` | Mot de passe de connexion à l'interface |
| `JWT_SECRET` | Secret de signature des tokens JWT (min 32 chars) |
| `JWT_EXPIRE_HOURS` | Durée de validité du token (défaut : 24h) |

#### Intégrations optionnelles

| Variable | Description |
|---|---|
| `ODOO_URL` | URL de votre instance Odoo |
| `ODOO_DB` | Nom de la base de données Odoo |
| `ODOO_USERNAME` | Utilisateur Odoo |
| `ODOO_API_KEY` | Clé API Odoo |
| `PLAUSIBLE_API_KEY` | Clé API Plausible Analytics |
| `PLAUSIBLE_SITE_ID` | Identifiant du site Plausible |
| `GA4_PROPERTY_ID` | ID propriété Google Analytics 4 |
| `GA4_CREDENTIALS_JSON` | JSON clé de service Google (une seule ligne) |

### Karl VPS Agent (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `KARL_AGENT_API_KEY` | **requis** | Clé Bearer (même que `VPS_AGENT_API_KEY`) |
| `APPS_BASE_DIR` | `/opt/karl/deployments` | Répertoire des applications |
| `NGINX_SITES_DIR` | `/etc/nginx/sites-enabled` | Sites Nginx actifs |

---

## 🛠️ Outils disponibles

| Outil | Description |
|---|---|
| `deploy_application` | Déploie une app via Docker Compose |
| `list_deployments` | Liste les applications déployées |
| `manage_container` | start / stop / restart / remove |
| `get_logs` | Logs en temps réel d'un service |
| `get_server_metrics` | CPU, RAM, Disque, Réseau, processus |
| `configure_nginx` | Génère et active une config Nginx |
| `enable_ssl` | Certificat Let's Encrypt via Certbot |
| `check_health` | Vérifie qu'un endpoint répond |
| `odoo_create_prospect` | Crée un lead CRM dans Odoo |
| `odoo_list_prospects` | Recherche/filtre des leads |
| `odoo_update_prospect` | Modifie un lead existant |
| `get_analytics` | Métriques de trafic (Plausible ou GA4) |

---

## 📁 Structure du projet

```
karl_assistant/
├── .env.example                  # Template de configuration
├── .gitignore
├── README.md
│
├── karl_brain/                   # Backend IA (FastAPI)
│   ├── main.py                   # Entrée FastAPI + lifespan + routes
│   ├── requirements.txt
│   │
│   ├── core/
│   │   ├── config.py             # Settings Pydantic (tous les env vars)
│   │   ├── database.py           # SQLite async (conversations, messages)
│   │   └── security.py          # JWT + auth
│   │
│   ├── ai/
│   │   ├── claude_client.py      # Boucle agentic multi-provider
│   │   ├── tool_definitions.py   # Schémas JSON des 12 outils
│   │   ├── tool_executor.py      # Dispatch tool_call → fonction
│   │   ├── system_prompt.py      # Persona Karl
│   │   └── providers/
│   │       ├── base.py           # Interface abstraite LLMProvider
│   │       ├── anthropic_provider.py  # Claude + streaming + thinking
│   │       ├── openai_provider.py     # OpenAI + Ollama
│   │       ├── gemini_provider.py     # Google Gemini
│   │       └── __init__.py            # Factory get_provider()
│   │
│   ├── tools/
│   │   ├── vps_tools.py          # HTTP → VPS Agent (deploy, logs, metrics)
│   │   ├── nginx_tools.py        # Configuration Nginx
│   │   ├── ssl_tools.py          # Certbot SSL
│   │   ├── odoo_tools.py         # CRM via XML-RPC
│   │   └── analytics_tools.py    # Plausible + GA4
│   │
│   ├── api/
│   │   ├── chat.py               # WebSocket /ws/chat + POST /api/chat
│   │   ├── auth.py               # POST /api/auth/login
│   │   ├── metrics.py            # GET /api/metrics
│   │   └── deployments.py        # GET /api/deployments + conteneurs
│   │
│   └── templates/
│       ├── docker/               # Compose templates (nodejs/python/php/static)
│       └── nginx/                # Config templates (http/https/websocket)
│
├── karl_vps_agent/               # Daemon sur le VPS
│   ├── main.py                   # FastAPI + auth middleware
│   ├── system_metrics.py         # psutil (CPU, RAM, disk, network)
│   ├── docker_manager.py         # docker compose up/down/ps/logs
│   ├── nginx_manager.py          # Génère config + teste + recharge
│   ├── ssl_manager.py            # Certbot integration
│   ├── requirements.txt
│   └── install.sh               # Script bootstrap systemd
│
└── frontend/                     # Interface React
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── App.tsx
        ├── hooks/
        │   └── useChat.ts        # WebSocket hook + streaming
        └── components/
            ├── Login.tsx
            ├── Layout.tsx
            ├── Chat/
            │   ├── ChatWindow.tsx       # Interface de chat
            │   ├── MessageBubble.tsx    # Markdown + code highlight
            │   └── InputBar.tsx        # Saisie + envoi
            └── Dashboard/
                ├── Dashboard.tsx        # Vue globale (polling 5s)
                ├── MetricsPanel.tsx     # CPU/RAM/Disk/Network
                └── DeploymentList.tsx   # Apps déployées + statuts
```

---

## 🔒 Sécurité

- **VPS Agent** : toutes les routes exigent `Authorization: Bearer <VPS_AGENT_API_KEY>`
- **Karl Brain → Frontend** : JWT signé, expire après `JWT_EXPIRE_HOURS`
- **Port 8001** : ne jamais exposer publiquement (firewall `ufw deny 8001`)
- **Nginx** : seuls les ports 80/443 sont exposés
- **Commandes Docker** : noms de services sanitisés (regex alphanumérique)
- **Nginx** : validation `nginx -t` systématique avant rechargement
- **Secrets** : jamais de valeurs en dur dans le code — uniquement `.env`

```bash
# Fermer le port de l'agent sur le VPS
ufw deny 8001
ufw allow 80
ufw allow 443
ufw allow 22
ufw enable
```

---

## 🐛 Dépannage

### Karl Brain ne démarre pas

```bash
journalctl -fu karl-brain --no-pager | tail -50
# Vérifier que .env est présent et complet
cat /opt/karl/karl_brain/.env
```

### L'agent VPS ne répond pas

```bash
systemctl status karl-agent
curl -H "Authorization: Bearer VOTRE_CLE" http://localhost:8001/health
```

### Erreur de connexion WebSocket

Vérifier la configuration Nginx (`Upgrade` et `Connection` headers) et que `CORS_ORIGINS` inclut l'URL du frontend.

### Provider LLM non disponible

```bash
# Vérifier que le SDK est installé
cd /opt/karl/karl_brain
source venv/bin/activate
python -c "import anthropic; print('OK')"     # pour anthropic
python -c "import openai; print('OK')"        # pour openai/ollama
python -c "import google.generativeai; print('OK')"  # pour gemini
```

### Les certificats SSL échouent

S'assurer que le domaine pointe sur le VPS et que le port 80 est accessible (Certbot utilise HTTP-01 challenge).

---

## 📄 Licence

MIT — libre d'utilisation, modification et distribution.
