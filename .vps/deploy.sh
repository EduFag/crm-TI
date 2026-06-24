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
# Produção deve espelhar o GitHub — descarta alterações locais acidentais
git reset --hard "origin/${BRANCH}"

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

log "Sincronizando unit systemd (${SERVICE})..."
UNIT_SRC="${APP_DIR}/.vps/gunicorn.service.exemple"
UNIT_DEST="/etc/systemd/system/${SERVICE}.service"
if [[ -f "${UNIT_SRC}" ]] && sudo cp "${UNIT_SRC}" "${UNIT_DEST}" 2>/dev/null; then
    sudo systemctl daemon-reload
    log "Unit atualizado (ExecReload habilitado)."
else
    log "AVISO: unit não sincronizado — rode na VPS: sudo bash .vps/install-crm-ti-service.sh"
fi

log "Recarregando Gunicorn (${SERVICE})..."
EXEC_RELOAD="$(systemctl show "${SERVICE}" -p ExecReload --value 2>/dev/null || true)"
if [[ -n "${EXEC_RELOAD}" ]] && sudo systemctl reload "${SERVICE}"; then
    log "Reload concluído."
    log "Deploy finalizado com sucesso."
    exit 0
fi

log "Reload indisponível — reiniciando serviço (rode install-crm-ti-service.sh uma vez)..."
sudo systemctl restart "${SERVICE}"

if sudo systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
    log "Deploy finalizado com sucesso."
else
    log "ERRO: serviço ${SERVICE} não está ativo."
    sudo systemctl status "${SERVICE}" --no-pager 2>/dev/null || true
    exit 1
fi
