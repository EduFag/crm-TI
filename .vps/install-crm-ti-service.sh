#!/usr/bin/env bash
# Instala ou atualiza o unit systemd crm-ti com ExecReload (reload suave do Gunicorn).
# Rodar na VPS como root:
#   sudo bash /home/edufa/crm-TI/.vps/install-crm-ti-service.sh

set -euo pipefail

APP_DIR="/home/edufa/crm-TI"
SERVICE="crm-ti"
SRC="${APP_DIR}/.vps/gunicorn.service.exemple"
DEST="/etc/systemd/system/${SERVICE}.service"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Execute como root: sudo bash ${APP_DIR}/.vps/install-crm-ti-service.sh"
    exit 1
fi

if [[ ! -f "${SRC}" ]]; then
    echo "Arquivo não encontrado: ${SRC}"
    exit 1
fi

echo "[install] Copiando ${SRC} -> ${DEST}"
cp "${SRC}" "${DEST}"
chmod 644 "${DEST}"

echo "[install] systemctl daemon-reload..."
systemctl daemon-reload

reload_val="$(systemctl show "${SERVICE}" -p ExecReload --value 2>/dev/null || true)"
if [[ -z "${reload_val}" ]]; then
    echo "[install] ERRO: ExecReload não está definido no unit."
    exit 1
fi
echo "[install] ExecReload: ${reload_val}"

if systemctl is-active --quiet "${SERVICE}" 2>/dev/null; then
    echo "[install] Serviço ativo — aplicando reload suave..."
    systemctl reload "${SERVICE}"
else
    echo "[install] Habilitando e iniciando serviço..."
    systemctl enable "${SERVICE}"
    systemctl start "${SERVICE}"
fi

if systemctl is-active --quiet "${SERVICE}"; then
    echo "[install] OK — use: systemctl reload ${SERVICE}  (deploy de código)"
    echo "[install]      systemctl restart ${SERVICE}  (após alterar .env)"
else
    echo "[install] ERRO: serviço não está ativo."
    systemctl status "${SERVICE}" --no-pager || true
    exit 1
fi
