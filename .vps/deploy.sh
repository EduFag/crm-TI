#!/usr/bin/env bash
# Deploy automático — chamado pelo GitHub Actions após push na main.
# Uso manual na VPS: bash /home/edufa/crm-TI/.vps/deploy.sh
# IMPORTANTE: GitHub Actions conecta como edufa (não root). Teste com:
#   bash .vps/verify-deploy-permissions.sh

set -euo pipefail

APP_DIR="/home/edufa/crm-TI"
VENV="${APP_DIR}/myvenv"
BRANCH="main"
SERVICE="crm-ti"

log() {
    echo "[deploy $(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# sudo sem senha (GitHub Actions); falha com mensagem clara se sudoers incompleto
sudo_deploy() {
    if sudo -n "$@"; then
        return 0
    fi
    log "ERRO: sudo falhou para: $*"
    log "Configure /etc/sudoers.d/crm-ti-deploy (modelo: .vps/crm-ti-deploy.sudoers.exemple)"
    log "Teste: bash .vps/verify-deploy-permissions.sh"
    return 1
}

cd "${APP_DIR}"

log "Deploy como usuário: $(whoami)"

log "Atualizando código (origin/${BRANCH})..."
if ! git fetch origin "${BRANCH}"; then
    log "ERRO: git fetch falhou — o usuário $(whoami) precisa de acesso ao GitHub (deploy key ou token)."
    exit 1
fi
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
sudo_deploy chown -R edufa:www-data "${APP_DIR}/staticfiles"
sudo_deploy chmod -R 755 "${APP_DIR}/staticfiles"
sudo_deploy chmod 755 /home/edufa "${APP_DIR}"

log "Sincronizando unit systemd (${SERVICE})..."
UNIT_SRC="${APP_DIR}/.vps/gunicorn.service.exemple"
UNIT_DEST="/etc/systemd/system/${SERVICE}.service"
if [[ -f "${UNIT_SRC}" ]] && sudo -n cp "${UNIT_SRC}" "${UNIT_DEST}" 2>/dev/null; then
    sudo -n systemctl daemon-reload 2>/dev/null \
        || log "AVISO: daemon-reload ignorado (adicione ao sudoers se necessário)"
    log "Unit atualizado (ExecReload habilitado)."
else
    log "AVISO: unit não sincronizado — rode: sudo bash .vps/install-crm-ti-service.sh"
fi

log "Reiniciando Gunicorn (${SERVICE})..."
# Com --preload no unit, reload (HUP) não recarrega código Python no master — restart obrigatório após deploy
sudo_deploy systemctl restart "${SERVICE}"

if sudo -n systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
    log "Deploy finalizado com sucesso."
else
    log "ERRO: serviço ${SERVICE} não está ativo."
    sudo -n systemctl status "${SERVICE}" --no-pager 2>/dev/null || true
    exit 1
fi
