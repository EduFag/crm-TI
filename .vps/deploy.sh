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
GUNICORN_PORT=9001

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

# Verifica se o Gunicorn está no ar (systemd ou porta local — fallback para CI SSH).
servico_responde() {
    local estado
    estado="$(sudo -n /usr/bin/systemctl is-active "${SERVICE}" 2>/dev/null || true)"
    estado="${estado//$'\r'/}"
    if [[ "${estado}" == "active" ]]; then
        return 0
    fi
    if ss -tln 2>/dev/null | grep -q ":${GUNICORN_PORT} "; then
        return 0
    fi
    if curl -sf --max-time 3 "http://127.0.0.1:${GUNICORN_PORT}/login/" >/dev/null 2>&1; then
        return 0
    fi
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

log "Verificando aplicação Django..."
if ! python manage.py check; then
    log "ERRO: manage.py check falhou — corrija antes de reiniciar o Gunicorn."
    exit 1
fi

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
# Preferência: stop + start (libera porta). Fallback: restart (sudoers antigo).
if sudo -n systemctl stop "${SERVICE}" 2>/dev/null; then
    sleep 2
    if command -v fuser >/dev/null 2>&1; then
        sudo -n fuser -k "${GUNICORN_PORT}/tcp" 2>/dev/null || true
    fi
    if ! sudo -n systemctl start "${SERVICE}" 2>/dev/null; then
        log "AVISO: start falhou — tentando restart."
        sudo_deploy systemctl restart "${SERVICE}"
    fi
else
    log "AVISO: stop não permitido no sudoers — usando restart."
    sudo_deploy systemctl restart "${SERVICE}"
fi

# Aguarda até 45s — unit usa graceful-timeout 30s + TimeoutStopSec 35s
log "Aguardando ${SERVICE} ficar ativo..."
for tentativa in $(seq 1 15); do
    if servico_responde; then
        log "Deploy finalizado com sucesso."
        exit 0
    fi
    sleep 3
done

log "ERRO: serviço ${SERVICE} não respondeu após 45s."
estado="$(sudo -n /usr/bin/systemctl is-active "${SERVICE}" 2>/dev/null || echo 'sem-permissao-sudo')"
log "Último estado systemd: ${estado}"
sudo -n systemctl status "${SERVICE}" --no-pager 2>/dev/null || true
log "--- Últimas linhas do journal (${SERVICE}) ---"
sudo -n journalctl -u "${SERVICE}" -n 50 --no-pager 2>/dev/null || true
exit 1
