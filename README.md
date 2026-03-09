# Karl — Hyper-Assistant VPS IA

> Orchestrez votre VPS en langage naturel. Déployez des applications, gérez votre sécurité, surveillez vos serveurs, automatisez vos workflows et bien plus — le tout depuis une interface de chat propulsée par l'IA.

---

## Table des matières

1. [Présentation](#-présentation)
2. [Architecture](#-architecture)
3. [Fonctionnalités](#-fonctionnalités)
4. [Interface](#-interface)
5. [Providers LLM supportés](#-providers-llm-supportés)
6. [Prérequis](#-prérequis)
7. [Démarrage rapide (Docker)](#-démarrage-rapide-docker)
8. [Déploiement local (développement)](#-déploiement-local-développement)
9. [Déploiement production (VPS réel)](#-déploiement-production-vps-réel)
10. [Variables d'environnement](#-variables-denvironnement)
11. [Outils disponibles](#-outils-disponibles)
12. [Structure du projet](#-structure-du-projet)
13. [Sécurité](#-sécurité)
14. [Dépannage](#-dépannage)

---

## 🎯 Présentation

Karl est un assistant IA conversationnel qui agit comme un ingénieur DevOps personnel. Il comprend vos demandes en langage naturel (français ou anglais) et exécute les opérations nécessaires sur votre VPS via un agent dédié.

**Exemples de commandes :**

```
"Déploie mon app Node.js nommée 'api-prod' sur le port 3000 avec le domaine api.monsite.com"
"Lance un audit de sécurité complet et montre-moi les vulnérabilités"
"Sauvegarde toutes mes bases de données PostgreSQL maintenant"
"Bloque le port 3306 sur le firewall"
"Active l'auto-healing sur le service api-prod"
"Configure un webhook GitHub pour déployer automatiquement à chaque push"
"Crée un certificat SSL wildcard pour *.monsite.com"
"Montre-moi les logs d'erreur des dernières 24h et explique les problèmes"
"Optimise les performances du serveur — RAM utilisée à 85%"
"Crée un prospect CRM : Jean Dupont, jean@dupont.com"
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Navigateur                               │
│                React + Vite + TypeScript                        │
│   Chat │ Aperçu │ Sécurité │ SSL & DNS │ DB │ Sauvegardes │ App Store │
└──────────────────────────┬──────────────────────────────────────┘
                           │  WebSocket / REST + JWT
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Karl Brain                                 │
│                FastAPI + Python 3.11+                           │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │           Provider LLM (multi-provider)                │     │
│  │  Anthropic Claude │ OpenAI │ Gemini │ Ollama (local)   │     │
│  └────────────────────────────────────────────────────────┘     │
│  ┌──────────────┐  ┌──────────┐  ┌────────────────────────┐    │
│  │  43+ outils  │  │  SQLite  │  │  Auth JWT + Mémoire IA │    │
│  └──────────────┘  └──────────┘  └────────────────────────┘    │
└──────────────────────────┬──────────────────────────────────────┘
                           │  HTTP + Bearer Token
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Karl VPS Agent                               │
│                FastAPI daemon sur le VPS                        │
│                                                                 │
│  Docker │ Nginx │ Certbot │ psutil │ UFW │ Cron │ Webhooks     │
│  PostgreSQL │ MySQL │ MongoDB │ Redis │ Logs │ Fail2ban        │
└─────────────────────────────────────────────────────────────────┘
```

### Flux d'une requête

```
User: "Sauvegarde PostgreSQL et envoie-moi une notification Telegram"
   ↓
WebSocket → karl_brain/api/chat.py
   ↓
Provider LLM → tool_call: backup_database(...) + send_notification(...)
   ↓
tool_executor.py → backup_tools.py → POST /backups/create → VPS Agent
   ↓
VPS Agent: pg_dump → compression → stockage dans /backups/
   ↓
notification_tools.py → Telegram Bot API → message de confirmation
   ↓
Réponse finale streamée → WebSocket → frontend
```

---

## ✨ Fonctionnalités

### F1 — Notifications (Telegram)
- Notifications automatiques pour les événements critiques : déploiements, alertes CPU/RAM, expiration SSL, backups
- Commandes de notification sur demande
- Configuration via `TELEGRAM_BOT_TOKEN` et `TELEGRAM_CHAT_ID`

### F2 — Sauvegardes automatisées
- Backup de bases de données : **PostgreSQL**, **MySQL**, **MongoDB**, **Redis**
- Backup de fichiers et répertoires d'applications
- Compression automatique (`.tar.gz`)
- Restauration à la demande depuis le chat ou le panneau Sauvegardes
- Programmation de sauvegardes récurrentes via cron

### F3 — Analyse des logs par IA
- Analyse intelligente des logs Docker, Nginx, systemd
- Détection automatique des erreurs et anomalies
- Suggestions de résolution basées sur les patterns détectés
- Résumé des incidents des dernières N heures

### F4 — App Store (applications self-hosted)
- Catalogue de **16+ applications** installables en un clic :
  WordPress, Ghost, Nextcloud, n8n, Gitea, GitLab CE, Uptime Kuma, Grafana, Mattermost, Plausible, Umami, Portainer, Vaultwarden, Penpot, Monica CRM, Outline Wiki
- Recherche et filtrage par catégorie (CMS, Cloud, Dev, Monitoring, etc.)
- Karl génère automatiquement le `docker-compose.yml`, configure Nginx et SSL

### F5 — Firewall (UFW)
- Consultation du statut et des règles actives
- Ajout / suppression de règles (ports, IPs, protocoles)
- Profils prédéfinis : web, ssh, db
- Protection automatique contre les IPs malveillantes via Fail2ban

### F6 — Auto-healing
- Surveillance proactive des services critiques
- Redémarrage automatique des conteneurs tombés
- Alertes Telegram en cas d'incident
- Configuration des seuils d'alerte (CPU, RAM, disk)
- Historique des événements d'auto-correction

### F7 — CI/CD Webhooks
- Réception de webhooks **GitHub** et **GitLab** (push, tag, PR merge)
- Déclenchement automatique de pipelines : `git pull` → rebuild → redeploy
- Vérification de signature HMAC
- Logs de pipeline consultables depuis le chat

### F8 — Mémoire persistante
- Karl se souvient du contexte entre les sessions
- Préférences utilisateur mémorisées (stack préférée, conventions de nommage, domaines)
- Résumé automatique des conversations longues
- Base de données SQLite pour l'historique complet

### F9 — Outils base de données
- Détection automatique des conteneurs DB (PostgreSQL, MySQL, MongoDB, Redis, MariaDB)
- Statistiques : taille, connexions actives, tables, performances
- Création de bases de données et d'utilisateurs
- Exécution de requêtes simples depuis le chat
- Import/export de données

### F10 — Optimisation des performances
- Analyse de l'utilisation des ressources (CPU, RAM, I/O)
- Recommandations d'optimisation contextuelles
- Tuning de paramètres PostgreSQL, Nginx, système
- Identification des processus gourmands
- Suggestions de mise en cache (Redis)

### F11 — DNS & Cloudflare
- Gestion des enregistrements DNS (A, AAAA, CNAME, TXT, MX)
- Intégration native **Cloudflare API** (zones, records, cache purge)
- Propagation DNS en temps réel
- Configuration automatique à la création d'un nouveau domaine

### F12 — Mode pédagogique
- Karl explique chaque commande avant de l'exécuter
- Mode "explique-moi" : détail des opérations système
- Suggestions de bonnes pratiques DevOps
- Documentation inline des configurations générées
- Adapte le niveau technique selon vos questions

### F13 — Audit de sécurité
- Score de sécurité global (0-100) avec détail des points
- Vérifications : auth SSH par clé, root désactivé, mises à jour sécurité, conteneurs non-root, fail2ban actif
- Scan des ports ouverts et services exposés
- Détection de configurations dangereuses
- Plan de remédiation prioritisé

### F14 — Multi-environnements
- Gestion de plusieurs environnements : **dev**, **staging**, **production**
- Isolation des ressources par environnement
- Promotion automatique entre environnements
- Variables d'environnement spécifiques par contexte

### F15 — SSL avancé
- Certificats **wildcard** (`*.domaine.com`) via DNS challenge
- Gestion multi-domaines (Subject Alternative Names)
- Renouvellement automatique avec alertes avant expiration
- Panneau de supervision des certificats avec indicateurs d'expiration (vert/jaune/rouge)
- Support Let's Encrypt + certificats personnalisés

---

## 🖥️ Interface

L'interface comprend **7 onglets** dans la barre latérale :

| Onglet | Description |
|--------|-------------|
| **Chat** | Interface conversationnelle principale avec Karl |
| **Aperçu** | Métriques temps réel (CPU, RAM, Disque) + liste des déploiements |
| **Sécurité** | Score de sécurité, audit, gestion du firewall |
| **SSL & DNS** | Certificats SSL avec statut d'expiration, gestion DNS |
| **Bases de données** | Conteneurs DB détectés + actions rapides |
| **Sauvegardes** | Liste des backups + restauration en un clic |
| **App Store** | Catalogue d'apps self-hosted installables depuis le chat |

Chaque panneau dispose d'un bouton **"Gérer dans le chat"** qui bascule vers Chat et envoie automatiquement la commande correspondante à Karl.

---

## 🤖 Providers LLM supportés

| Provider | Modèles recommandés | Clé requise |
|---|---|---|
| **Anthropic Claude** (défaut) | `claude-opus-4-6`, `claude-sonnet-4-6` | `ANTHROPIC_API_KEY` |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini`, `o1`, `o3-mini` | `OPENAI_API_KEY` |
| **Ollama** (local, gratuit) | `llama3.1`, `mistral`, `qwen2.5`, `deepseek-r1` | Aucune |
| **Google Gemini** | `gemini-2.0-flash`, `gemini-1.5-pro` | `GEMINI_API_KEY` |

Changement de provider : modifier `PROVIDER=` dans `.env` — aucune modification de code.

---

## 📋 Prérequis

### Démarrage rapide (Docker — recommandé)
- Docker Engine 24+
- Docker Compose v2+

### Machine locale (développement sans Docker)
- Python 3.11+
- Node.js 18+ et npm
- Git

### VPS de production
- Ubuntu 22.04 / Debian 12 (recommandé)
- Accès root ou sudo
- Docker + Docker Compose installés
- Nginx installé
- Certbot installé
- Port 8001 **fermé** publiquement (accessible uniquement depuis localhost)
- Nom de domaine pointant sur le VPS (pour SSL)

---

## 🐳 Démarrage rapide (Docker)

La façon la plus simple de lancer Karl sur n'importe quelle machine disposant de Docker.

### 1. Cloner et configurer

```bash
git clone <repo-url> karl_assistant
cd karl_assistant

cp .env.example .env
```

Éditer `.env` avec vos valeurs minimales :

```env
# Provider LLM
PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...

# Secrets (générer avec: openssl rand -hex 32)
VPS_AGENT_API_KEY=votre-cle-agent-secrete
KARL_ADMIN_PASSWORD=votre-mot-de-passe
JWT_SECRET=votre-secret-jwt-32-chars-minimum
```

### 2. Lancer avec Docker Compose

```bash
docker compose up -d
```

Les images sont construites automatiquement :
- **karl-brain** → `http://localhost:8000`
- **karl-vps-agent** → `http://localhost:8001` (interne uniquement)
- **karl-frontend** → `http://localhost:3000`

### 3. Se connecter

Ouvrir `http://localhost:3000` → entrer le mot de passe (`KARL_ADMIN_PASSWORD`).

### Commandes utiles

```bash
# Voir les logs
docker compose logs -f karl-brain
docker compose logs -f karl-vps-agent

# Redémarrer un service
docker compose restart karl-brain

# Arrêter tout
docker compose down

# Mise à jour
git pull && docker compose up -d --build
```

---

## 🖥️ Déploiement local (développement)

### 1. Cloner le projet

```bash
git clone <repo-url> karl_assistant
cd karl_assistant
```

### 2. Configurer l'environnement

```bash
cp .env.example .env
# Éditer .env avec vos valeurs
```

### 3. Démarrer le VPS Agent

```bash
cd karl_vps_agent
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt

cat > .env << EOF
KARL_AGENT_API_KEY=local-secret-key
APPS_BASE_DIR=./deployments
NGINX_SITES_DIR=./nginx-sites
EOF

mkdir -p deployments nginx-sites
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

### 4. Démarrer Karl Brain

```bash
cd karl_brain
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Documentation API interactive : `http://localhost:8000/docs`

### 5. Démarrer le Frontend

```bash
cd frontend
npm install
npm run dev
```

Ouvrir `http://localhost:5173` → se connecter → tester :

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
[Nginx] :80/:443  →  /      → Frontend (fichiers statiques)
                  →  /api   → Karl Brain :8000
                  →  /ws    → Karl Brain :8000 (WebSocket)
                  →  :8001  → Karl VPS Agent (LAN uniquement, jamais exposé)
```

> **Sécurité** : Le port 8001 ne doit **jamais** être exposé publiquement.

---

### Étape 1 — Préparer le VPS

```bash
ssh root@VOTRE_IP_VPS

apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip \
               nginx certbot python3-certbot-nginx \
               git curl wget ufw

# Docker
curl -fsSL https://get.docker.com | sh
systemctl enable docker && systemctl start docker

# Firewall de base
ufw allow ssh
ufw allow 80
ufw allow 443
ufw deny 8001
ufw enable
```

---

### Étape 2 — Déployer le VPS Agent

```bash
git clone <repo-url> /opt/karl
cd /opt/karl/karl_vps_agent

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cat > /opt/karl/karl_vps_agent/.env << 'EOF'
KARL_AGENT_API_KEY=VOTRE_CLE_SECRETE_TRES_LONGUE
APPS_BASE_DIR=/opt/karl/deployments
NGINX_SITES_DIR=/etc/nginx/sites-enabled
EOF

chmod 600 /opt/karl/karl_vps_agent/.env
mkdir -p /opt/karl/deployments

bash /opt/karl/karl_vps_agent/install.sh

systemctl status karl-agent
curl http://localhost:8001/health
```

---

### Étape 3 — Déployer Karl Brain

```bash
cd /opt/karl/karl_brain

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp /opt/karl/.env.example /opt/karl/karl_brain/.env
nano /opt/karl/karl_brain/.env
```

Valeurs clés pour la production :

```env
PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-VOTRE_CLE

VPS_AGENT_URL=http://localhost:8001
VPS_AGENT_API_KEY=VOTRE_CLE_SECRETE_TRES_LONGUE

KARL_ADMIN_PASSWORD=mot_de_passe_complexe
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

DEBUG=false
CORS_ORIGINS=https://karl.mondomaine.com
```

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
systemctl enable --now karl-brain
```

---

### Étape 4 — Compiler le Frontend

```bash
# Sur le VPS
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

cd /opt/karl/frontend
npm install
npm run build
```

---

### Étape 5 — Configurer Nginx

```bash
cat > /etc/nginx/sites-available/karl << 'EOF'
server {
    listen 80;
    server_name karl.mondomaine.com;

    root /opt/karl/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600;
    }
}
EOF

ln -s /etc/nginx/sites-available/karl /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

---

### Étape 6 — SSL

```bash
certbot --nginx -d karl.mondomaine.com --non-interactive --agree-tos -m votre@email.com
certbot renew --dry-run
```

---

### Étape 7 — Vérification

```bash
systemctl status karl-agent karl-brain nginx
curl -s https://karl.mondomaine.com/api/health | python3 -m json.tool
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
| `OPENAI_BASE_URL` | — | URL custom (vide = API officielle, Ollama = `http://localhost:11434/v1`) |
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
| `KARL_ADMIN_PASSWORD` | **requis** — Mot de passe de connexion |
| `JWT_SECRET` | **requis** — Secret de signature JWT (min 32 chars) |
| `JWT_EXPIRE_HOURS` | Durée de validité du token (défaut : 24h) |

#### Notifications (optionnel)

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token du bot Telegram (créer via @BotFather) |
| `TELEGRAM_CHAT_ID` | ID du chat ou canal de destination |

#### Intégrations CRM & Analytics (optionnel)

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

#### DNS & Cloudflare (optionnel)

| Variable | Description |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Token API Cloudflare (permissions DNS:Edit) |
| `CLOUDFLARE_ZONE_ID` | ID de zone Cloudflare |

### Karl VPS Agent (`.env`)

| Variable | Défaut | Description |
|---|---|---|
| `KARL_AGENT_API_KEY` | **requis** | Clé Bearer (même que `VPS_AGENT_API_KEY`) |
| `APPS_BASE_DIR` | `/opt/karl/deployments` | Répertoire des applications |
| `NGINX_SITES_DIR` | `/etc/nginx/sites-enabled` | Sites Nginx actifs |

### Frontend (`frontend/.env`)

Le frontend n'a qu'**une seule variable** optionnelle :

| Variable | Valeur | Quand l'utiliser |
|---|---|---|
| `VITE_API_URL` | *(vide)* | **Production** : frontend servi par FastAPI sur le même domaine — laisser vide (URLs relatives) |
| `VITE_API_URL` | `http://localhost:8000` | **Développement local** : frontend sur port 5173, API sur port 8000 |
| `VITE_API_URL` | `https://karl.mondomaine.com` | **Production domaine différent** : API et frontend sur des domaines distincts |

**Cas typiques :**

```bash
# Production — FastAPI sert frontend/dist/ sur le même domaine (cas recommandé)
# frontend/.env est inutile, ou :
echo "VITE_API_URL=" > frontend/.env

# Développement local — deux serveurs séparés
echo "VITE_API_URL=http://localhost:8000" > frontend/.env

# Puis builder :
cd frontend && npm run build
```

> **Note** : En production sur VPS avec Nginx, si Karl Brain écoute sur `127.0.0.1:8000`
> et que Nginx reverse-proxie tout sur le même domaine, laissez `VITE_API_URL` vide
> (les appels `/api/...` et `/ws/chat` seront relatifs au domaine courant).

---

## 🛠️ Outils disponibles

Karl dispose de **43+ outils** répartis en catégories :

### Déploiement & Conteneurs

| Outil | Description |
|---|---|
| `deploy_application` | Déploie une app via Docker Compose (Node.js, Python, PHP, Static) |
| `list_deployments` | Liste les applications déployées avec leur statut |
| `manage_container` | start / stop / restart / remove un conteneur |
| `get_logs` | Logs en temps réel d'un service (tail N lignes) |
| `check_health` | Vérifie qu'un endpoint HTTP répond |
| `get_running_containers` | État de tous les conteneurs Docker |

### Nginx & Reverse Proxy

| Outil | Description |
|---|---|
| `configure_nginx` | Génère et active une config Nginx (HTTP/HTTPS/WebSocket) |
| `reload_nginx` | Recharge Nginx après validation syntaxique |
| `list_nginx_sites` | Liste les sites Nginx actifs et inactifs |
| `remove_nginx_site` | Supprime une configuration de site |

### SSL / TLS

| Outil | Description |
|---|---|
| `enable_ssl` | Certificat Let's Encrypt via Certbot (domain + www) |
| `enable_ssl_wildcard` | Certificat wildcard via DNS challenge Cloudflare |
| `renew_ssl` | Renouvelle un ou tous les certificats |
| `list_ssl_certificates` | Liste les certs avec dates d'expiration |
| `check_ssl_expiry` | Vérifie l'expiration et alerte si < 30 jours |

### Monitoring & Métriques

| Outil | Description |
|---|---|
| `get_server_metrics` | CPU, RAM, Disque, Réseau, top processus |
| `get_disk_usage` | Utilisation détaillée par partition et répertoire |
| `get_network_stats` | Trafic réseau entrant/sortant par interface |
| `get_process_list` | Top N processus par CPU ou mémoire |

### Analyse des logs

| Outil | Description |
|---|---|
| `analyze_logs` | Analyse IA des logs Docker/Nginx/systemd |
| `get_error_summary` | Résumé des erreurs des dernières N heures |
| `search_logs` | Recherche par motif dans les logs |
| `get_access_patterns` | Patterns d'accès HTTP depuis les logs Nginx |

### Sécurité & Firewall

| Outil | Description |
|---|---|
| `security_audit` | Audit complet : SSH, root, updates, conteneurs, fail2ban |
| `get_security_score` | Score de sécurité global (0-100) |
| `manage_firewall` | Ajouter / supprimer des règles UFW |
| `get_firewall_status` | Statut et règles actives |
| `block_ip` | Bloque une IP via UFW ou fail2ban |
| `get_failed_logins` | Tentatives de connexion échouées |

### Sauvegardes

| Outil | Description |
|---|---|
| `backup_database` | Sauvegarde PostgreSQL / MySQL / MongoDB |
| `backup_files` | Archive compressée d'un répertoire |
| `list_backups` | Liste des sauvegardes disponibles |
| `restore_backup` | Restaure une sauvegarde |
| `schedule_backup` | Programme une sauvegarde récurrente (cron) |

### Bases de données

| Outil | Description |
|---|---|
| `list_databases` | Détecte et liste les conteneurs DB |
| `get_db_stats` | Statistiques : taille, tables, connexions |
| `create_database` | Crée une base de données et un utilisateur |
| `execute_query` | Exécute une requête SQL (lecture seule) |

### CI/CD & Webhooks

| Outil | Description |
|---|---|
| `register_webhook` | Enregistre un webhook GitHub/GitLab |
| `list_webhooks` | Liste les webhooks configurés |
| `get_pipeline_logs` | Logs des pipelines de déploiement |
| `trigger_deploy` | Déclenche un redéploiement manuel |

### Auto-healing

| Outil | Description |
|---|---|
| `configure_autohealing` | Active la surveillance d'un service |
| `get_autohealing_status` | État du watchdog et historique des redémarrages |
| `set_alert_thresholds` | Configure les seuils CPU/RAM/disk |

### DNS & Cloudflare

| Outil | Description |
|---|---|
| `list_dns_records` | Liste les enregistrements DNS d'un domaine |
| `create_dns_record` | Crée un enregistrement A/AAAA/CNAME/TXT |
| `update_dns_record` | Modifie un enregistrement existant |
| `delete_dns_record` | Supprime un enregistrement DNS |
| `purge_cloudflare_cache` | Purge le cache Cloudflare |

### Notifications

| Outil | Description |
|---|---|
| `send_notification` | Envoie un message Telegram |
| `configure_alerts` | Configure les seuils d'alerte automatiques |

### CRM & Analytics

| Outil | Description |
|---|---|
| `odoo_create_prospect` | Crée un lead CRM dans Odoo |
| `odoo_list_prospects` | Recherche / filtre des leads |
| `odoo_update_prospect` | Modifie un lead existant |
| `get_analytics` | Métriques de trafic (Plausible ou GA4) |

---

## 📁 Structure du projet

```
karl_assistant/
├── .env.example                   # Template de configuration
├── .gitignore
├── README.md
├── docker-compose.yml             # Orchestration Docker (3 services)
│
├── karl_brain/                    # Backend IA (FastAPI)
│   ├── main.py                    # Entrée FastAPI + lifespan + routes
│   ├── requirements.txt
│   ├── Dockerfile
│   │
│   ├── core/
│   │   ├── config.py              # Settings Pydantic (tous les env vars)
│   │   ├── database.py            # SQLite async (conversations, messages)
│   │   └── security.py            # JWT + auth
│   │
│   ├── ai/
│   │   ├── claude_client.py       # Boucle agentic multi-provider
│   │   ├── tool_definitions.py    # Schémas JSON des 43+ outils
│   │   ├── tool_executor.py       # Dispatch tool_call → fonction
│   │   ├── system_prompt.py       # Persona Karl + instructions
│   │   └── providers/
│   │       ├── base.py            # Interface abstraite LLMProvider
│   │       ├── anthropic_provider.py
│   │       ├── openai_provider.py  # OpenAI + Ollama
│   │       ├── gemini_provider.py
│   │       └── __init__.py        # Factory get_provider()
│   │
│   ├── tools/
│   │   ├── vps_tools.py           # Déploiement, conteneurs, métriques
│   │   ├── nginx_tools.py         # Configuration Nginx
│   │   ├── ssl_tools.py           # Certbot + wildcard
│   │   ├── security_tools.py      # Audit, firewall, fail2ban
│   │   ├── backup_tools.py        # Sauvegardes DB + fichiers
│   │   ├── log_analysis_tools.py  # Analyse IA des logs
│   │   ├── database_tools.py      # PostgreSQL, MySQL, MongoDB, Redis
│   │   ├── webhook_tools.py       # CI/CD webhooks
│   │   ├── autohealing_tools.py   # Watchdog + auto-restart
│   │   ├── dns_tools.py           # Cloudflare DNS
│   │   ├── notification_tools.py  # Telegram
│   │   ├── optimization_tools.py  # Tuning performances
│   │   ├── memory_tools.py        # Contexte persistant
│   │   ├── odoo_tools.py          # CRM via XML-RPC
│   │   └── analytics_tools.py     # Plausible + GA4
│   │
│   ├── api/
│   │   ├── chat.py                # WebSocket /ws/chat + POST /api/chat
│   │   ├── auth.py                # POST /api/auth/login
│   │   ├── metrics.py             # GET /api/metrics
│   │   ├── deployments.py         # GET /api/deployments + conteneurs
│   │   └── dashboard.py           # Proxy vers VPS Agent (SSL, security, backups...)
│   │
│   └── templates/
│       ├── docker/                # Compose templates (nodejs/python/php/static)
│       └── nginx/                 # Config templates (http/https/websocket)
│
├── karl_vps_agent/                # Daemon sur le VPS
│   ├── main.py                    # FastAPI + auth middleware + routes
│   ├── system_metrics.py          # psutil (CPU, RAM, disk, network)
│   ├── docker_manager.py          # docker compose up/down/ps/logs
│   ├── nginx_manager.py           # Génère config + teste + recharge
│   ├── ssl_manager.py             # Certbot integration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── install.sh                 # Script bootstrap systemd
│
└── frontend/                      # Interface React
    ├── package.json
    ├── vite.config.ts
    ├── Dockerfile
    └── src/
        ├── App.tsx
        ├── api/
        │   └── client.ts          # apiFetch helper (Bearer auth)
        ├── hooks/
        │   └── useChat.ts         # WebSocket hook + streaming
        └── components/
            ├── Login.tsx
            ├── Layout.tsx          # 7 onglets + useChat levé ici
            ├── Chat/
            │   ├── ChatWindow.tsx  # Interface de chat (14 suggestions)
            │   ├── MessageBubble.tsx  # Markdown + code highlight
            │   └── InputBar.tsx    # Saisie + envoi
            └── Dashboard/
                ├── Dashboard.tsx        # Aperçu : métriques + déploiements
                ├── MetricsPanel.tsx     # CPU/RAM/Disk/Network
                ├── DeploymentList.tsx   # Apps déployées + bouton Gérer
                ├── SecurityPanel.tsx    # Score sécurité + audit
                ├── SSLPanel.tsx         # Certificats + expiration
                ├── BackupsPanel.tsx     # Liste backups + restauration
                ├── DatabasePanel.tsx    # Conteneurs DB détectés
                └── AppStore.tsx         # Catalogue 16+ apps self-hosted
```

---

## 🔒 Sécurité

- **VPS Agent** : toutes les routes exigent `Authorization: Bearer <VPS_AGENT_API_KEY>`
- **Karl Brain → Frontend** : JWT signé, expire après `JWT_EXPIRE_HOURS`
- **Port 8001** : ne jamais exposer publiquement — `ufw deny 8001`
- **Nginx** : seuls les ports 80/443 sont exposés
- **Commandes Docker** : noms de services sanitisés (regex alphanumérique)
- **Nginx** : validation `nginx -t` systématique avant rechargement
- **Secrets** : jamais de valeurs en dur dans le code — uniquement `.env`
- **Webhooks** : signature HMAC vérifiée (GitHub `X-Hub-Signature-256`)

```bash
# Configuration firewall recommandée
ufw allow ssh
ufw allow 80
ufw allow 443
ufw deny 8001
ufw enable
```

---

## 🐛 Dépannage

### Karl Brain ne démarre pas

```bash
journalctl -fu karl-brain --no-pager | tail -50
# Variables requises : KARL_ADMIN_PASSWORD, JWT_SECRET, VPS_AGENT_API_KEY
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
cd /opt/karl/karl_brain && source venv/bin/activate
python -c "import anthropic; print('OK')"       # anthropic
python -c "import openai; print('OK')"          # openai/ollama
python -c "import google.generativeai; print('OK')"  # gemini
```

### Notifications Telegram silencieuses

1. Créer un bot via `@BotFather` → récupérer `TELEGRAM_BOT_TOKEN`
2. Envoyer un message au bot puis `https://api.telegram.org/bot<TOKEN>/getUpdates` pour obtenir le `chat_id`

### Les certificats wildcard échouent

Le challenge DNS (wildcard) requiert les variables `CLOUDFLARE_API_TOKEN` et `CLOUDFLARE_ZONE_ID` configurées.

---

## 📄 Licence

MIT — libre d'utilisation, modification et distribution.
