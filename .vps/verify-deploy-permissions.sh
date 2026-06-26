#!/usr/bin/env bash
# Verifica se o usuário atual (edufa) consegue rodar o deploy como o GitHub Actions.
# Uso na VPS: bash /home/edufa/crm-TI/.vps/verify-deploy-permissions.sh

set -u

APP_DIR="/home/edufa/crm-TI"
SERVICE="crm-ti"
ERROS=0

ok() { echo "[OK] $*"; }
falha() { echo "[FALHA] $*"; ERROS=$((ERROS + 1)); }

echo "=== Verificação de deploy (usuário: $(whoami)) ==="

if [[ "$(whoami)" == "root" ]]; then
    echo "AVISO: você está como root. O GitHub Actions usa o usuário edufa."
    echo "       Rode: su - edufa -c 'bash ${APP_DIR}/.vps/verify-deploy-permissions.sh'"
    echo ""
fi

if git -C "${APP_DIR}" fetch origin main 2>/dev/null; then
    ok "git fetch origin main"
else
    falha "git fetch — rode: bash ${APP_DIR}/.vps/setup-git-deploy-key.sh (como edufa)"
fi

for cmd in \
    "chown -R edufa:www-data ${APP_DIR}/staticfiles" \
    "chmod -R 755 ${APP_DIR}/staticfiles" \
    "chmod 755 /home/edufa ${APP_DIR}" \
    "cp ${APP_DIR}/.vps/gunicorn.service.exemple /etc/systemd/system/${SERVICE}.service" \
    "systemctl daemon-reload" \
    "systemctl reload ${SERVICE}" \
    "systemctl restart ${SERVICE}" \
    "systemctl stop ${SERVICE}" \
    "systemctl start ${SERVICE}" \
    "systemctl status ${SERVICE}"; do
    if sudo -n ${cmd} >/dev/null 2>&1; then
        ok "sudo ${cmd}"
    else
        falha "sudo sem senha — ${cmd}"
    fi
done

if sudo -n systemctl is-active "${SERVICE}" >/dev/null 2>&1; then
    ok "sudo systemctl is-active ${SERVICE} (ativo)"
else
    rc=$?
    if [[ "${rc}" -eq 3 ]]; then
        ok "sudo systemctl is-active ${SERVICE} (permissão OK; serviço inativo)"
    else
        falha "sudo sem senha — systemctl is-active ${SERVICE}"
    fi
fi

echo ""
if [[ "${ERROS}" -eq 0 ]]; then
    echo "Tudo pronto para o GitHub Actions."
    exit 0
fi

echo "${ERROS} problema(s). Atualize /etc/sudoers.d/crm-ti-deploy:"
echo "  sudo visudo -f /etc/sudoers.d/crm-ti-deploy"
echo "  (modelo em .vps/crm-ti-deploy.sudoers.exemple)"
exit 1
