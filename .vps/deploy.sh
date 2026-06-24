#!/usr/bin/env bash
# Deploy automático — chamado pelo GitHub Actions após push na main.
# Uso manual na VPS: bash /home/edufa/crm-TI/.vps/deploy.sh

set -euo pipefail

APP_DIR="/home/edufa/crm-TI"
VENV="${APP_DIR}/myvenv"
BRANCH="main"
SERVICE="crm-ti"

log() {
    echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cd "${APP_DIR}"

log "Atualizando código (origin/${BRANCH})..."
git fetch origin "${BRANCH}"
git checkout "${BRANCH}"
git pull --ff-only origin "${BRANCH}"

log "Ativando ambiente virtual..."
# shellcheck source=/dev/null
source "${VENV}/bin/activate"

log "Instalando dependências..."
pip install -r requirements.txt --quiet

log "Aplicando migrations..."
python manage.py migrate --noinput

log "Coletando arquivos estáticos..."
python manage.py collectstatic --noinput

log "Ajustando permissões de staticfiles..."
sudo chown -R edufa:www-data "${APP_DIR}/staticfiles"
sudo chmod -R 755 "${APP_DIR}/staticfiles"
sudo chmod 755 /home/edufa "${APP_DIR}"

log "Recarregando Gunicorn (${SERVICE})..."
if sudo systemctl reload "${SERVICE}" 2>/dev/null; then
    log "Reload concluído."
    log "Deploy finalizado com sucesso."
    exit 0
fi

log "Reload indisponível — reiniciando serviço..."
sudo systemctl restart "${SERVICE}"

if sudo systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
    log "Deploy finalizado com sucesso."
else
    log "ERRO: serviço ${SERVICE} não está ativo."
    sudo systemctl status "${SERVICE}" --no-pager 2>/dev/null || true
    exit 1
fi
