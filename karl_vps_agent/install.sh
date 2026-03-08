#!/usr/bin/env bash
# ============================================================
# Karl VPS Agent — Script d'installation sur le VPS
# Usage: curl -sSL https://your-server/install.sh | bash
#    ou: bash install.sh
# ============================================================
set -e

AGENT_DIR="/opt/karl/agent"
SERVICE_NAME="karl-vps-agent"
PYTHON_BIN="python3"
VENV_DIR="$AGENT_DIR/venv"

echo "==> Installation de Karl VPS Agent"

# 1. Dépendances système
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx curl

# 2. Répertoires
mkdir -p /opt/karl/deployments
mkdir -p /opt/karl/agent
mkdir -p /etc/nginx/sites-enabled

# 3. Copier les fichiers de l'agent
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp -r "$SCRIPT_DIR"/*.py "$AGENT_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$AGENT_DIR/"

# 4. Virtualenv + dépendances Python
$PYTHON_BIN -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$AGENT_DIR/requirements.txt" -q

# 5. Fichier .env (à configurer manuellement)
if [ ! -f "$AGENT_DIR/.env" ]; then
    cat > "$AGENT_DIR/.env" << 'EOF'
KARL_AGENT_API_KEY=CHANGE_ME_RANDOM_SECRET_KEY
KARL_AGENT_PORT=8001
APPS_BASE_DIR=/opt/karl/deployments
NGINX_SITES_DIR=/etc/nginx/sites-enabled
EOF
    echo "==> Fichier .env créé dans $AGENT_DIR/.env"
    echo "==> IMPORTANT: Modifie KARL_AGENT_API_KEY avec une clé secrète forte !"
fi

# 6. Service systemd
cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Karl VPS Agent
After=network.target docker.service
Wants=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$AGENT_DIR
EnvironmentFile=$AGENT_DIR/.env
ExecStart=$VENV_DIR/bin/python main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 7. Activer et démarrer le service
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

echo ""
echo "==> Karl VPS Agent installé et démarré !"
echo "==> Status: systemctl status $SERVICE_NAME"
echo "==> Logs:   journalctl -u $SERVICE_NAME -f"
echo "==> Port:   8001 (modifier dans .env si nécessaire)"
echo ""
echo "==> Prochaine étape: configurer KARL_AGENT_API_KEY dans:"
echo "    $AGENT_DIR/.env"
echo "    et aussi dans karl_brain/.env (VPS_AGENT_API_KEY)"
