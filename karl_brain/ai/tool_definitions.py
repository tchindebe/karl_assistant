"""
Définitions des outils Claude (JSON Schema format).
Ces schemas sont envoyés à l'API Anthropic pour que Claude sache quels outils il peut appeler.
"""
from typing import List, Dict, Any

TOOLS: List[Dict[str, Any]] = [
    # ─── Déploiement ───────────────────────────────────────────────────────────
    {
        "name": "deploy_application",
        "description": (
            "Déploie une application sur le VPS via Docker Compose. "
            "Génère automatiquement un docker-compose.yml adapté au stack choisi si non fourni. "
            "Utilisez pour déployer Node.js, Python, PHP, sites statiques, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom de l'application (alphanumérique + tirets). Ex: 'mon-api', 'blog-wordpress'",
                },
                "stack": {
                    "type": "string",
                    "enum": ["nodejs", "python", "php", "static", "docker", "custom"],
                    "description": "Type/stack de l'application",
                },
                "compose_content": {
                    "type": "string",
                    "description": "Contenu du docker-compose.yml. Si non fourni, sera généré automatiquement selon le stack.",
                },
                "env_vars": {
                    "type": "object",
                    "description": "Variables d'environnement pour l'application",
                    "additionalProperties": {"type": "string"},
                },
                "port": {
                    "type": "integer",
                    "description": "Port interne de l'application (ex: 3000, 8080)",
                },
                "image": {
                    "type": "string",
                    "description": "Image Docker à utiliser (ex: 'node:20-alpine', 'nginx:alpine')",
                },
                "pull": {
                    "type": "boolean",
                    "description": "Forcer le pull des images avant déploiement",
                    "default": True,
                },
            },
            "required": ["name", "stack"],
        },
    },

    # ─── Liste des déploiements ─────────────────────────────────────────────────
    {
        "name": "list_deployments",
        "description": "Liste toutes les applications déployées sur le VPS avec leur statut.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    # ─── Gestion containers ─────────────────────────────────────────────────────
    {
        "name": "manage_container",
        "description": "Démarre, arrête, redémarre ou supprime un container Docker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom du container Docker",
                },
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart", "remove", "pause", "unpause"],
                    "description": "Action à effectuer",
                },
            },
            "required": ["name", "action"],
        },
    },

    # ─── Logs ──────────────────────────────────────────────────────────────────
    {
        "name": "get_logs",
        "description": "Récupère les logs d'un service/container Docker.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Nom du container ou service",
                },
                "lines": {
                    "type": "integer",
                    "description": "Nombre de lignes à récupérer (défaut: 100)",
                    "default": 100,
                },
                "since": {
                    "type": "string",
                    "description": "Depuis quand (ex: '1h', '30m', '2024-01-01')",
                },
            },
            "required": ["service"],
        },
    },

    # ─── Métriques serveur ──────────────────────────────────────────────────────
    {
        "name": "get_server_metrics",
        "description": "Récupère les métriques du serveur: CPU, RAM, disque, réseau, uptime, top processus.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },

    # ─── Nginx ─────────────────────────────────────────────────────────────────
    {
        "name": "configure_nginx",
        "description": (
            "Configure un virtual host Nginx pour exposer une application sur un domaine. "
            "Génère et active la configuration, teste et recharge Nginx automatiquement."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Nom de domaine (ex: 'app.monsite.com')",
                },
                "upstream_port": {
                    "type": "integer",
                    "description": "Port interne de l'application (ex: 3000)",
                },
                "ssl": {
                    "type": "boolean",
                    "description": "Activer HTTPS (nécessite que le domaine pointe sur le VPS)",
                    "default": False,
                },
                "websocket": {
                    "type": "boolean",
                    "description": "Activer le support WebSocket",
                    "default": False,
                },
                "upstream_host": {
                    "type": "string",
                    "description": "Host de l'application (défaut: 127.0.0.1)",
                    "default": "127.0.0.1",
                },
            },
            "required": ["domain", "upstream_port"],
        },
    },

    # ─── SSL ───────────────────────────────────────────────────────────────────
    {
        "name": "enable_ssl",
        "description": (
            "Active HTTPS sur un domaine via Let's Encrypt (certbot). "
            "Le domaine doit déjà pointer sur le VPS et Nginx doit être configuré."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domaine pour lequel obtenir le certificat SSL",
                },
                "email": {
                    "type": "string",
                    "description": "Email pour les notifications Let's Encrypt",
                },
            },
            "required": ["domain", "email"],
        },
    },

    # ─── Health check ──────────────────────────────────────────────────────────
    {
        "name": "check_health",
        "description": "Vérifie si un endpoint HTTP répond correctement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL à tester (ex: 'https://app.monsite.com/health')",
                },
                "expected_status": {
                    "type": "integer",
                    "description": "Code HTTP attendu (défaut: 200)",
                    "default": 200,
                },
            },
            "required": ["url"],
        },
    },

    # ─── Odoo CRM ──────────────────────────────────────────────────────────────
    {
        "name": "odoo_create_prospect",
        "description": "Crée un nouveau prospect/lead dans Odoo CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Nom du prospect ou de l'entreprise"},
                "email": {"type": "string", "description": "Email du prospect"},
                "phone": {"type": "string", "description": "Téléphone du prospect"},
                "company": {"type": "string", "description": "Nom de l'entreprise"},
                "description": {"type": "string", "description": "Notes ou description"},
                "stage": {"type": "string", "description": "Étape du pipeline CRM"},
                "expected_revenue": {"type": "number", "description": "Revenu estimé"},
            },
            "required": ["name"],
        },
    },

    {
        "name": "odoo_list_prospects",
        "description": "Liste et filtre les prospects/leads dans Odoo CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Nombre max de résultats (défaut: 20)",
                    "default": 20,
                },
                "stage": {"type": "string", "description": "Filtrer par étape du pipeline"},
                "search": {"type": "string", "description": "Recherche textuelle"},
            },
        },
    },

    {
        "name": "odoo_update_prospect",
        "description": "Met à jour un prospect existant dans Odoo CRM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "prospect_id": {"type": "integer", "description": "ID du prospect à modifier"},
                "fields": {
                    "type": "object",
                    "description": "Champs à mettre à jour",
                    "additionalProperties": True,
                },
            },
            "required": ["prospect_id", "fields"],
        },
    },

    # ─── Analytics ─────────────────────────────────────────────────────────────
    {
        "name": "get_analytics",
        "description": "Récupère les analytics marketing (GA4 ou Plausible).",
        "input_schema": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "enum": ["pageviews", "sessions", "users", "bounce_rate", "top_pages", "top_sources", "overview"],
                    "description": "Type de métrique à récupérer",
                },
                "period": {
                    "type": "string",
                    "enum": ["today", "yesterday", "7d", "30d", "90d", "12m"],
                    "description": "Période d'analyse",
                    "default": "7d",
                },
                "site": {"type": "string", "description": "Site à analyser (si plusieurs configurés)"},
            },
            "required": ["metric"],
        },
    },

    # ─── Notifications ──────────────────────────────────────────────────────────
    {
        "name": "send_notification",
        "description": "Envoie une notification sur les canaux configurés (Telegram, Slack, email, webhook).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Corps du message"},
                "title": {"type": "string", "description": "Titre de la notification", "default": "Karl"},
                "level": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                    "description": "Niveau de sévérité",
                    "default": "info",
                },
            },
            "required": ["message"],
        },
    },

    # ─── Sauvegardes ────────────────────────────────────────────────────────────
    {
        "name": "backup_create",
        "description": "Crée une sauvegarde: volumes Docker, base de données, ou fichiers de configuration.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["volumes", "database", "configs"],
                    "description": "Type de sauvegarde",
                },
                "app_name": {"type": "string", "description": "Nom de l'app (pour volumes)"},
                "db_type": {
                    "type": "string",
                    "enum": ["postgresql", "mysql", "mongodb", "sqlite"],
                    "description": "Type de BDD (pour database)",
                },
                "container": {"type": "string", "description": "Nom du conteneur BDD"},
                "db_name": {"type": "string", "description": "Nom de la base de données"},
            },
            "required": ["type"],
        },
    },
    {
        "name": "backup_list",
        "description": "Liste les sauvegardes disponibles sur le VPS.",
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["volumes", "databases", "configs", "all"],
                    "default": "all",
                },
            },
        },
    },

    # ─── Analyse de logs ────────────────────────────────────────────────────────
    {
        "name": "analyze_logs",
        "description": (
            "Analyse les logs d'un service avec l'IA. Détecte les erreurs, warnings, "
            "crashes OOM, timeouts et fournit un résumé intelligent."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {"type": "string", "description": "Nom du container/service"},
                "lines": {"type": "integer", "description": "Nombre de lignes à analyser", "default": 200},
                "since": {"type": "string", "description": "Depuis quand (ex: '1h', '30m')"},
                "focus": {
                    "type": "string",
                    "enum": ["errors", "warnings", "performance", "all"],
                    "default": "all",
                },
            },
            "required": ["service"],
        },
    },

    # ─── App Store ──────────────────────────────────────────────────────────────
    {
        "name": "list_available_apps",
        "description": "Liste les applications disponibles dans le catalogue Karl (WordPress, Ghost, Nextcloud, n8n, Gitea...).",
        "input_schema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Filtrer par tag (cms, productivity, devtools, monitoring...)"},
            },
        },
    },
    {
        "name": "install_app",
        "description": "Installe une application depuis le catalogue App Store (Docker Compose + Nginx + SSL automatiques).",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_id": {
                    "type": "string",
                    "enum": ["wordpress", "ghost", "nextcloud", "n8n", "gitea", "uptime-kuma", "nodejs", "python", "static"],
                    "description": "Identifiant de l'application",
                },
                "name": {"type": "string", "description": "Nom unique pour cette instance"},
                "port": {"type": "integer", "description": "Port à utiliser"},
                "domain": {"type": "string", "description": "Domaine pour accéder à l'app"},
                "env_vars": {
                    "type": "object",
                    "description": "Variables requises (mots de passe, secrets...)",
                    "additionalProperties": {"type": "string"},
                },
                "enable_ssl": {"type": "boolean", "default": True},
                "ssl_email": {"type": "string", "description": "Email pour Let's Encrypt"},
                "environment": {
                    "type": "string",
                    "enum": ["production", "staging", "dev"],
                    "default": "production",
                },
            },
            "required": ["app_id", "name", "port"],
        },
    },

    # ─── Pare-feu ───────────────────────────────────────────────────────────────
    {
        "name": "firewall_status",
        "description": "Vérifie le statut du pare-feu UFW et liste les règles actives.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "firewall_add_rule",
        "description": "Ajoute une règle au pare-feu (autoriser ou bloquer un port/IP).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["allow", "deny"], "description": "Autoriser ou bloquer"},
                "port": {"type": "integer", "description": "Port à cibler"},
                "protocol": {"type": "string", "enum": ["tcp", "udp", "any"], "default": "tcp"},
                "from_ip": {"type": "string", "description": "IP source (optionnel, ex: '192.168.1.0/24')"},
            },
            "required": ["action", "port"],
        },
    },
    {
        "name": "firewall_block_ip",
        "description": "Bloque une adresse IP spécifique sur tous les ports (brute-force, attaque).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {"type": "string", "description": "Adresse IP à bloquer"},
            },
            "required": ["ip"],
        },
    },
    {
        "name": "firewall_detect_brute_force",
        "description": "Détecte les IPs qui font du brute-force SSH et les bloque automatiquement si désiré.",
        "input_schema": {
            "type": "object",
            "properties": {
                "threshold": {"type": "integer", "description": "Seuil de tentatives avant alerte", "default": 10},
                "auto_block": {"type": "boolean", "description": "Bloquer automatiquement les IPs détectées", "default": False},
            },
        },
    },

    # ─── Mémoire infrastructure ─────────────────────────────────────────────────
    {
        "name": "remember",
        "description": "Mémorise une information sur l'infrastructure pour les conversations futures.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["infrastructure", "deployments", "incidents", "decisions", "configs", "notes"],
                },
                "key": {"type": "string", "description": "Clé unique pour cette information"},
                "value": {"type": "string", "description": "Information à mémoriser (peut être du JSON)"},
            },
            "required": ["category", "key", "value"],
        },
    },
    {
        "name": "recall",
        "description": "Rappelle des informations mémorisées sur l'infrastructure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Catégorie à consulter (optionnel)"},
                "key": {"type": "string", "description": "Clé à rechercher (optionnel)"},
            },
        },
    },
    {
        "name": "get_infrastructure_summary",
        "description": "Retourne un résumé complet de la mémoire infrastructure: apps, incidents, décisions.",
        "input_schema": {"type": "object", "properties": {}},
    },

    # ─── Bases de données ───────────────────────────────────────────────────────
    {
        "name": "database_stats",
        "description": "Statistiques d'une base de données: version, connexions, taille, cache hit ratio.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string", "description": "Nom du conteneur Docker"},
                "db_type": {"type": "string", "enum": ["postgresql", "mysql", "mongodb", "redis"]},
            },
            "required": ["container", "db_type"],
        },
    },
    {
        "name": "database_slow_queries",
        "description": "Affiche les requêtes SQL lentes en cours pour identifier les goulots d'étranglement.",
        "input_schema": {
            "type": "object",
            "properties": {
                "container": {"type": "string"},
                "db_type": {"type": "string", "enum": ["postgresql", "mysql"], "default": "postgresql"},
                "threshold_ms": {"type": "integer", "description": "Seuil en ms", "default": 1000},
            },
            "required": ["container"],
        },
    },
    {
        "name": "database_dump",
        "description": "Crée un dump (sauvegarde) d'une base de données.",
        "input_schema": {
            "type": "object",
            "properties": {
                "db_type": {"type": "string", "enum": ["postgresql", "mysql", "mongodb", "sqlite"]},
                "container": {"type": "string"},
                "db_name": {"type": "string"},
                "user": {"type": "string"},
            },
            "required": ["db_type", "container", "db_name"],
        },
    },

    # ─── Optimisation ───────────────────────────────────────────────────────────
    {
        "name": "analyze_resources",
        "description": "Analyse complète des ressources serveur avec recommandations d'optimisation (CPU, RAM, disque, conteneurs).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_top_processes",
        "description": "Retourne les processus qui consomment le plus de CPU et RAM.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
            },
        },
    },

    # ─── DNS / Cloudflare ───────────────────────────────────────────────────────
    {
        "name": "dns_list_records",
        "description": "Liste les enregistrements DNS Cloudflare de la zone configurée.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_type": {"type": "string", "description": "Filtrer par type: A, AAAA, CNAME, MX, TXT"},
            },
        },
    },
    {
        "name": "dns_create_record",
        "description": "Crée un enregistrement DNS dans Cloudflare.",
        "input_schema": {
            "type": "object",
            "properties": {
                "record_type": {"type": "string", "enum": ["A", "AAAA", "CNAME", "MX", "TXT"]},
                "name": {"type": "string", "description": "Sous-domaine (ex: 'app', 'www')"},
                "content": {"type": "string", "description": "Valeur (IP pour A, domaine pour CNAME)"},
                "proxied": {"type": "boolean", "default": True},
            },
            "required": ["record_type", "name", "content"],
        },
    },
    {
        "name": "dns_check_propagation",
        "description": "Vérifie la propagation DNS d'un domaine sur plusieurs serveurs DNS publics.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "record_type": {"type": "string", "default": "A"},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "cloudflare_purge_cache",
        "description": "Purge le cache Cloudflare (tout ou URLs spécifiques).",
        "input_schema": {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "URLs à purger (laisser vide + purge_all=true pour tout purger)",
                },
                "purge_all": {"type": "boolean", "default": False},
            },
        },
    },

    # ─── Audit sécurité ─────────────────────────────────────────────────────────
    {
        "name": "security_full_audit",
        "description": "Lance un audit de sécurité complet: ports, Docker, fichiers, SSH, mises à jour. Retourne un score et des recommandations.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "security_check_open_ports",
        "description": "Vérifie les ports ouverts et identifie les services exposés dangereux.",
        "input_schema": {"type": "object", "properties": {}},
    },

    # ─── SSL avancé ─────────────────────────────────────────────────────────────
    {
        "name": "ssl_check_expiry",
        "description": "Vérifie l'expiration de tous les certificats SSL. Alerte sur les certificats expirant bientôt.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "ssl_check_domain",
        "description": "Vérifie le certificat SSL d'un domaine depuis l'extérieur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
                "port": {"type": "integer", "default": 443},
            },
            "required": ["domain"],
        },
    },
    {
        "name": "ssl_force_renew",
        "description": "Force le renouvellement d'un certificat SSL spécifique.",
        "input_schema": {
            "type": "object",
            "properties": {
                "domain": {"type": "string"},
            },
            "required": ["domain"],
        },
    },

    # ─── Multi-environnements ────────────────────────────────────────────────────
    {
        "name": "list_environments",
        "description": "Liste toutes les applications groupées par environnement (production, staging, dev).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "promote_to_production",
        "description": "Promeut une application de staging vers production.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string"},
                "from_environment": {"type": "string", "default": "staging"},
            },
            "required": ["app_name"],
        },
    },
]
